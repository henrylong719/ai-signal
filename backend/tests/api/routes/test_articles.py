import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.api.routes import article as article_routes
from app.core.config import settings
from app.models import Article, User
from app.models.article import EMBEDDING_DIM
from app.schemas import ArticleCreate, UserCreate
from app.schemas.source import SOURCES, Category
from app.services import article_search
from tests.utils.article import create_random_article
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _create_authenticated_user(
    client: TestClient,
    db: Session,
) -> tuple[User, dict[str, str]]:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    return user, user_authentication_headers(
        client=client, email=email, password=password
    )


def _create_article(
    db: Session,
    *,
    url: str | None = None,
    title: str | None = None,
    source: str = "Example",
    category: Category = "models",
    tags: list[str] | None = None,
) -> Article:
    return crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=url or f"https://example.com/{uuid.uuid4()}",
            title=title or random_lower_string(),
            source=source,
            excerpt=random_lower_string(),
            category=category,
            tags=tags or [category],
            published_at=datetime.now(timezone.utc),
        ),
    )


def _embedding(axis: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[axis] = 1.0
    return vector


def test_read_articles(client: TestClient, db: Session) -> None:
    create_random_article(db)
    create_random_article(db)
    response = client.get(f"{settings.API_V1_STR}/articles/")
    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) >= 2
    assert content["count"] >= 2


def test_read_articles_by_category(client: TestClient, db: Session) -> None:
    create_random_article(db, category="engineering")
    create_random_article(db, category="research")
    response = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"category": "engineering"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] >= 1
    assert all(article["category"] == "engineering" for article in content["data"])


def test_read_articles_by_source(client: TestClient, db: Session) -> None:
    source = f"Example {uuid.uuid4()}"
    create_random_article(db, source=source)
    create_random_article(db, source="Different Source")
    response = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"source": source},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 1
    assert all(article["source"] == source for article in content["data"])


def test_read_articles_search_uses_semantic_similarity(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = f"Semantic Source {uuid.uuid4()}"
    near = _create_article(
        db,
        source=source,
        title="A compact roundup about deployment metrics",
    )
    far = _create_article(
        db,
        source=source,
        title="A compact roundup about hardware procurement",
    )
    crud.update_article_embeddings(
        session=db,
        embeddings={
            near.id: _embedding(0),
            far.id: _embedding(1),
        },
    )
    monkeypatch.setattr(article_search, "embed_text", lambda text: _embedding(0))

    response = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "neural retrieval", "source": source},
    )

    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 2
    assert [article["id"] for article in content["data"]] == [
        str(near.id),
        str(far.id),
    ]


def test_read_articles_search_falls_back_to_keyword_when_embeddings_fail(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = f"Keyword Fallback {uuid.uuid4()}"
    match = _create_article(
        db,
        source=source,
        title="Sparse mixture routing in production",
    )
    _create_article(db, source=source, title="Unrelated deployment notes")

    def fail_embed(_text: str) -> list[float]:
        raise RuntimeError("encoder unavailable")

    monkeypatch.setattr(article_search, "embed_text", fail_embed)

    response = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "Sparse mixture", "source": source},
    )

    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 1
    assert [article["id"] for article in content["data"]] == [str(match.id)]


def test_read_sources(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/articles/sources/")
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == len(content["data"])
    assert content["count"] == len(SOURCES)
    assert all(source["topic"] != "AI source" for source in content["data"])
    assert all(
        source["description"] != "Curated source for AI Signal."
        for source in content["data"]
    )

    openai = next(source for source in content["data"] if source["name"] == "OpenAI")
    assert openai == {
        "name": "OpenAI",
        "default_category": "models",
        "source_type": "official",
        "topic": "AI Research Lab",
        "description": "Official research, product, safety, and engineering updates from OpenAI.",
    }


def test_read_sources_by_source_type(client: TestClient) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/articles/sources/",
        params={"source_type": "community"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] >= 1
    assert all(source["source_type"] == "community" for source in content["data"])


def test_read_for_you_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/articles/for-you")
    assert response.status_code == 401


def test_saved_article_static_routes_are_not_captured_by_article_id(
    client: TestClient,
) -> None:
    fresh_client = TestClient(client.app)

    saved_list = fresh_client.get(f"{settings.API_V1_STR}/articles/saved/")
    saved_ids = fresh_client.get(f"{settings.API_V1_STR}/articles/saved/ids")

    assert saved_list.status_code == 401
    assert saved_ids.status_code == 401


def test_read_for_you_articles(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
) -> None:
    create_random_article(db)
    response = client.get(
        f"{settings.API_V1_STR}/articles/for-you",
        headers=normal_user_token_headers,
        params={"skip": 0, "limit": 20},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] >= 1
    assert content["candidate_pool_cap"] == article_routes._CANDIDATE_POOL_SIZE
    assert len(content["data"]) >= 1
    assert "reason" in content["data"][0]


def test_read_for_you_refetches_page_articles_in_one_bulk_query(
    db: Session,
    monkeypatch,
) -> None:
    first = _create_article(db, title="First ranked")
    second = _create_article(db, title="Second ranked")
    captured_article_ids: list[uuid.UUID] = []

    items = [
        SimpleNamespace(
            scored=SimpleNamespace(article=SimpleNamespace(id=second.id)),
            reason="Because you follow RAG",
        ),
        SimpleNamespace(
            scored=SimpleNamespace(article=SimpleNamespace(id=first.id)),
            reason="Because you follow models",
        ),
    ]

    def fake_rank_for_you(**kwargs):
        assert kwargs["skip"] == 0
        assert kwargs["limit"] == 2
        return items, 2

    def fake_get_articles_by_ids(**kwargs):
        captured_article_ids.extend(kwargs["article_ids"])
        return [first, second]

    def fail_get_article(**_kwargs):
        raise AssertionError("read_for_you should bulk-fetch page articles")

    monkeypatch.setattr(article_routes, "rank_for_you", fake_rank_for_you)
    monkeypatch.setattr(
        article_routes.crud, "get_articles_by_ids", fake_get_articles_by_ids
    )
    monkeypatch.setattr(article_routes.crud, "get_article", fail_get_article)

    response = article_routes.read_for_you(
        session=db,
        current_user=SimpleNamespace(id=uuid.uuid4()),
        skip=0,
        limit=2,
    )

    assert captured_article_ids == [second.id, first.id]
    assert [article.id for article in response.data] == [second.id, first.id]
    assert [article.reason for article in response.data] == [
        "Because you follow RAG",
        "Because you follow models",
    ]


def test_read_for_you_excludes_saved_and_dismissed_articles(
    client: TestClient,
    db: Session,
) -> None:
    user, headers = _create_authenticated_user(client, db)
    shown = _create_article(db, title="For You match", category="rag", tags=["rag"])
    saved = _create_article(db, title="Already saved", category="rag", tags=["rag"])
    dismissed = _create_article(db, title="Dismissed", category="rag", tags=["rag"])

    crud.set_interests(
        session=db,
        user_id=user.id,
        categories=["rag"],
        tags=["rag"],
    )
    crud.save_article(
        session=db,
        user_id=user.id,
        article_id=saved.id,
    )
    crud.record_event(
        session=db,
        user_id=user.id,
        article_id=dismissed.id,
        event_type="dismissed",
    )

    response = client.get(
        f"{settings.API_V1_STR}/articles/for-you",
        headers=headers,
        params={"limit": 200},
    )

    assert response.status_code == 200
    ids = {article["id"] for article in response.json()["data"]}
    assert str(shown.id) in ids
    assert str(saved.id) not in ids
    assert str(dismissed.id) not in ids


def test_saved_article_routes_cover_create_list_ids_and_delete(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)
    article = create_random_article(db)

    fresh_client = TestClient(client.app)
    unauthenticated = fresh_client.post(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
    )
    assert unauthenticated.status_code == 401

    saved = client.post(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
        headers=headers,
    )
    assert saved.status_code == 201
    assert saved.json() == {"message": "Article saved"}

    duplicate = client.post(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Article already saved"

    ids = client.get(f"{settings.API_V1_STR}/articles/saved/ids", headers=headers)
    assert ids.status_code == 200
    assert str(article.id) in ids.json()["article_ids"]

    saved_list = client.get(f"{settings.API_V1_STR}/articles/saved/", headers=headers)
    assert saved_list.status_code == 200
    assert str(article.id) in [item["id"] for item in saved_list.json()["data"]]

    removed = client.delete(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
        headers=headers,
    )
    assert removed.status_code == 200
    assert removed.json() == {"message": "Article unsaved"}

    missing = client.delete(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
        headers=headers,
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Saved article not found"


def test_read_saved_articles_preserves_saved_order_when_bulk_fetching(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_saved = _create_article(db, title="Saved first")
    second_saved = _create_article(db, title="Saved second")
    saved_rows = [
        SimpleNamespace(article_id=second_saved.id),
        SimpleNamespace(article_id=first_saved.id),
    ]
    captured_article_ids: list[uuid.UUID] = []

    monkeypatch.setattr(article_routes.crud, "count_saved_articles", lambda **_: 2)
    monkeypatch.setattr(article_routes.crud, "get_saved_articles", lambda **_: saved_rows)

    def fake_get_articles_by_ids(**kwargs):
        captured_article_ids.extend(kwargs["article_ids"])
        return [first_saved, second_saved]

    def fail_get_article(**_kwargs):
        raise AssertionError("read_saved_articles should bulk-fetch articles")

    monkeypatch.setattr(
        article_routes.crud, "get_articles_by_ids", fake_get_articles_by_ids
    )
    monkeypatch.setattr(article_routes.crud, "get_article", fail_get_article)

    response = article_routes.read_saved_articles(
        session=db,
        current_user=SimpleNamespace(id=uuid.uuid4()),
        skip=0,
        limit=2,
    )

    assert captured_article_ids == [second_saved.id, first_saved.id]
    assert [article.id for article in response.data] == [
        second_saved.id,
        first_saved.id,
    ]
    assert response.count == 2


def test_read_saved_articles_skips_saved_rows_for_deleted_articles(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _create_article(db, title="Still exists")
    missing_id = uuid.uuid4()
    saved_rows = [
        SimpleNamespace(article_id=missing_id),
        SimpleNamespace(article_id=existing.id),
    ]

    monkeypatch.setattr(article_routes.crud, "count_saved_articles", lambda **_: 2)
    monkeypatch.setattr(article_routes.crud, "get_saved_articles", lambda **_: saved_rows)
    monkeypatch.setattr(
        article_routes.crud,
        "get_articles_by_ids",
        lambda **_: [existing],
    )

    response = article_routes.read_saved_articles(
        session=db,
        current_user=SimpleNamespace(id=uuid.uuid4()),
        skip=0,
        limit=2,
    )

    assert [article.id for article in response.data] == [existing.id]
    assert response.count == 2


def test_save_article_returns_404_for_missing_article(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.post(
        f"{settings.API_V1_STR}/articles/{uuid.uuid4()}/save",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


def test_dismiss_article_records_idempotent_event(
    client: TestClient,
    db: Session,
) -> None:
    user, headers = _create_authenticated_user(client, db)
    article = create_random_article(db)

    first = client.post(
        f"{settings.API_V1_STR}/articles/{article.id}/dismiss",
        headers=headers,
    )
    second = client.post(
        f"{settings.API_V1_STR}/articles/{article.id}/dismiss",
        headers=headers,
    )

    assert first.status_code == 204
    assert second.status_code == 204
    events = crud.get_events(
        session=db,
        user_id=user.id,
        event_type="dismissed",
    )
    event = next(event for event in events if event.article_id == article.id)
    assert event.count == 2


def test_dismiss_article_returns_404_for_missing_article(
    client: TestClient,
    db: Session,
) -> None:
    _, headers = _create_authenticated_user(client, db)

    response = client.post(
        f"{settings.API_V1_STR}/articles/{uuid.uuid4()}/dismiss",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


def test_go_to_article_redirects_and_records_click_for_authenticated_user(
    client: TestClient,
    db: Session,
) -> None:
    user, headers = _create_authenticated_user(client, db)
    article = _create_article(db, url=f"https://example.com/read/{uuid.uuid4()}")

    anonymous = client.get(
        f"{settings.API_V1_STR}/articles/{article.id}/go",
        follow_redirects=False,
    )
    authenticated = client.get(
        f"{settings.API_V1_STR}/articles/{article.id}/go",
        headers=headers,
        follow_redirects=False,
    )

    assert anonymous.status_code == 302
    assert anonymous.headers["location"] == article.url
    assert authenticated.status_code == 302
    assert authenticated.headers["location"] == article.url
    events = crud.get_events(
        session=db,
        user_id=user.id,
        event_type="clicked",
    )
    assert [event.article_id for event in events].count(article.id) == 1


def test_user_vector_refresh_failure_does_not_break_article_signal_endpoints(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, headers = _create_authenticated_user(client, db)
    article = _create_article(db, url=f"https://example.com/read/{uuid.uuid4()}")

    def fail_refresh(**_kwargs):
        raise RuntimeError("embedding refresh unavailable")

    monkeypatch.setattr(article_routes, "compute_and_save_user_vector", fail_refresh)

    saved = client.post(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
        headers=headers,
    )
    unsaved = client.delete(
        f"{settings.API_V1_STR}/articles/{article.id}/save",
        headers=headers,
    )
    clicked = client.get(
        f"{settings.API_V1_STR}/articles/{article.id}/go",
        headers=headers,
        follow_redirects=False,
    )

    assert saved.status_code == 201
    assert saved.json() == {"message": "Article saved"}
    assert unsaved.status_code == 200
    assert unsaved.json() == {"message": "Article unsaved"}
    assert clicked.status_code == 302
    assert clicked.headers["location"] == article.url


def test_go_to_article_rejects_missing_or_invalid_destination(
    client: TestClient,
    db: Session,
) -> None:
    invalid = _create_article(db, url="javascript:alert(1)")

    missing = client.get(
        f"{settings.API_V1_STR}/articles/{uuid.uuid4()}/go",
        follow_redirects=False,
    )
    invalid_response = client.get(
        f"{settings.API_V1_STR}/articles/{invalid.id}/go",
        follow_redirects=False,
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Article not found"
    assert invalid_response.status_code == 400
    assert invalid_response.json()["detail"] == "Article URL is invalid"


def test_read_article(client: TestClient, db: Session) -> None:
    image_url = "https://example.com/article-image.png"
    article = create_random_article(db, image_url=image_url)
    response = client.get(f"{settings.API_V1_STR}/articles/{article.id}")
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(article.id)
    assert content["url"] == article.url
    assert content["title"] == article.title
    assert content["source"] == article.source
    assert content["image_url"] == image_url


def test_read_article_not_found(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/articles/{uuid.uuid4()}")
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Article not found"

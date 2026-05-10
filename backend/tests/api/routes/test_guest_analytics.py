"""Tests for the guest analytics intake + admin funnel summary."""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app import crud
from app.core.config import settings
from app.models import GuestEvent
from app.schemas import ArticleCreate, UserCreate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _post_event(client: TestClient, payload: dict) -> dict:
    response = client.post(
        f"{settings.API_V1_STR}/analytics/guest-event",
        json=payload,
    )
    return response


def _clear_guest_events(db: Session) -> None:
    db.exec(delete(GuestEvent))  # type: ignore[call-overload]
    db.commit()


def _create_article(db: Session, title: str = "Guest seed article"):
    return crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title=title,
            source="Example",
            excerpt="Guest test article excerpt",
            category="models",
            tags=["models"],
            published_at=datetime.now(timezone.utc),
        ),
    )


def _create_user_headers(client: TestClient, db: Session) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    return user_authentication_headers(client=client, email=email, password=password)


# --- Public intake ---


def test_guest_event_accepts_valid_payload(
    client: TestClient, db: Session
) -> None:
    _clear_guest_events(db)
    anon_id = str(uuid.uuid4())

    response = _post_event(
        client,
        {
            "anonymous_id": anon_id,
            "event_type": "guest_page_view",
            "path": "/",
            "referrer": "https://news.example.com/",
        },
    )

    assert response.status_code == 202
    statement = select(GuestEvent).where(GuestEvent.anonymous_id == anon_id)
    stored = db.exec(statement).all()
    assert len(stored) == 1
    assert stored[0].event_type == "guest_page_view"
    assert stored[0].path == "/"
    assert stored[0].referrer == "https://news.example.com/"


def test_guest_event_does_not_require_authentication(
    client: TestClient, db: Session
) -> None:
    # Tests run with cleared cookies via fixture; an unauthenticated POST
    # should still succeed.
    response = _post_event(
        client,
        {
            "anonymous_id": str(uuid.uuid4()),
            "event_type": "guest_signup_click",
            "metadata": {"location": "hero"},
        },
    )

    assert response.status_code == 202


def test_guest_event_rejects_unknown_event_type(
    client: TestClient, db: Session
) -> None:
    response = _post_event(
        client,
        {
            "anonymous_id": str(uuid.uuid4()),
            "event_type": "guest_unknown_event",
        },
    )

    assert response.status_code == 422


def test_guest_event_requires_anonymous_id(client: TestClient) -> None:
    response = _post_event(
        client,
        {"event_type": "guest_page_view"},
    )

    assert response.status_code == 422


def test_guest_event_rejects_nested_metadata(client: TestClient) -> None:
    response = _post_event(
        client,
        {
            "anonymous_id": str(uuid.uuid4()),
            "event_type": "guest_signup_click",
            "metadata": {"location": {"nested": "hero"}},
        },
    )

    assert response.status_code == 422


def test_guest_event_rejects_oversized_metadata(client: TestClient) -> None:
    # Roughly 4 KiB of payload — well over the 2 KiB cap.
    response = _post_event(
        client,
        {
            "anonymous_id": str(uuid.uuid4()),
            "event_type": "guest_signup_click",
            "metadata": {"junk": "x" * 4096},
        },
    )

    assert response.status_code == 422


def test_guest_event_stores_article_and_source(
    client: TestClient, db: Session
) -> None:
    _clear_guest_events(db)
    article = _create_article(db)

    response = _post_event(
        client,
        {
            "anonymous_id": "anon-test-article",
            "event_type": "guest_article_click",
            "article_id": str(article.id),
            "source_id": article.source,
            "path": "/",
        },
    )

    assert response.status_code == 202
    statement = select(GuestEvent).where(
        GuestEvent.anonymous_id == "anon-test-article"
    )
    stored = db.exec(statement).one()
    assert stored.article_id == article.id
    assert stored.source_name == article.source


def test_guest_signup_completed_links_user_id(
    client: TestClient, db: Session
) -> None:
    user_email = random_email()
    user_password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=user_email, password=user_password),
    )

    response = _post_event(
        client,
        {
            "anonymous_id": "anon-converted",
            "event_type": "guest_signup_completed",
            "user_id": str(user.id),
            "path": "/signup",
        },
    )

    assert response.status_code == 202
    statement = select(GuestEvent).where(
        GuestEvent.anonymous_id == "anon-converted"
    )
    stored = db.exec(statement).one()
    assert stored.user_id == user.id


# --- Admin funnel ---


def test_admin_funnel_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/admin/analytics/guest-funnel")
    assert response.status_code == 401


def test_admin_funnel_rejects_non_superuser(
    client: TestClient,
    db: Session,
) -> None:
    headers = _create_user_headers(client, db)
    response = client.get(
        f"{settings.API_V1_STR}/admin/analytics/guest-funnel",
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_funnel_returns_counts_and_rates(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    _clear_guest_events(db)
    anon_id = "anon-funnel"

    # 4 page views, 2 article clicks, 1 signup CTA click, 0 completions.
    # Expected article_click_rate=0.5, signup_click_rate=0.25,
    # signup_conversion_rate=0.0 (zero-safe).
    for _ in range(4):
        _post_event(
            client,
            {"anonymous_id": anon_id, "event_type": "guest_page_view"},
        )
    for _ in range(2):
        _post_event(
            client,
            {
                "anonymous_id": anon_id,
                "event_type": "guest_article_click",
            },
        )
    _post_event(
        client,
        {
            "anonymous_id": anon_id,
            "event_type": "guest_signup_click",
            "metadata": {"location": "hero"},
        },
    )

    response = client.get(
        f"{settings.API_V1_STR}/admin/analytics/guest-funnel?range=30d",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["guest_page_view"] == 4
    assert body["counts"]["guest_article_click"] == 2
    assert body["counts"]["guest_signup_click"] == 1
    assert body["counts"]["guest_signup_completed"] == 0
    assert body["rates"]["article_click_rate"] == 0.5
    assert body["rates"]["signup_click_rate"] == 0.25
    assert body["rates"]["signup_conversion_rate"] == 0.0
    assert body["signup_cta_locations"][0]["location"] == "hero"
    assert body["signup_cta_locations"][0]["clicks"] == 1


def test_admin_funnel_returns_top_articles_and_sources(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    _clear_guest_events(db)
    popular = _create_article(db, title="Popular article")
    less_popular = _create_article(db, title="Less popular article")

    for _ in range(3):
        _post_event(
            client,
            {
                "anonymous_id": "anon-top-1",
                "event_type": "guest_article_click",
                "article_id": str(popular.id),
                "source_id": popular.source,
            },
        )
    _post_event(
        client,
        {
            "anonymous_id": "anon-top-2",
            "event_type": "guest_article_click",
            "article_id": str(less_popular.id),
            "source_id": less_popular.source,
        },
    )

    response = client.get(
        f"{settings.API_V1_STR}/admin/analytics/guest-funnel?range=all",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["top_articles"][0]["article_id"] == str(popular.id)
    assert body["top_articles"][0]["guest_clicks"] == 3
    assert body["top_articles"][0]["title"] == "Popular article"
    assert body["top_sources"][0]["source_name"] == popular.source
    assert body["top_sources"][0]["guest_clicks"] >= 4


def test_admin_funnel_returns_top_topics(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    _clear_guest_events(db)
    for _ in range(2):
        _post_event(
            client,
            {
                "anonymous_id": "anon-topic",
                "event_type": "guest_topic_click",
                "topic": "agents",
            },
        )
    _post_event(
        client,
        {
            "anonymous_id": "anon-topic",
            "event_type": "guest_topic_click",
            "topic": "rag",
        },
    )

    response = client.get(
        f"{settings.API_V1_STR}/admin/analytics/guest-funnel?range=all",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["top_topics"][0]["topic"] == "agents"
    assert body["top_topics"][0]["guest_clicks"] == 2


def test_admin_funnel_rejects_unknown_range(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/admin/analytics/guest-funnel?range=bogus",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422

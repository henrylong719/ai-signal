import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.schemas.source import SOURCES
from tests.utils.article import create_random_article


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


def test_read_sources(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/articles/sources/")
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == len(content["data"])
    assert content["count"] == len(SOURCES)
    assert all(source["topic"] != "AI source" for source in content["data"])
    assert all(source["description"] != "Curated source for AI Signal." for source in content["data"])

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
    assert len(content["data"]) >= 1
    assert "reason" in content["data"][0]


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

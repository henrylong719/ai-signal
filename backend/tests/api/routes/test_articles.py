import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
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

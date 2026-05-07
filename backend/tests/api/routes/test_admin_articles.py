import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.schemas import ArticleCreate, UserCreate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _create_article(db: Session, *, title: str = "Admin article"):
    return crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title=title,
            source="Example",
            excerpt="Admin article excerpt",
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


def test_read_admin_articles_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/admin/articles")
    assert response.status_code == 401


def test_read_admin_articles_requires_superuser(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/admin/articles",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_read_admin_articles_returns_saved_count(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    article = _create_article(db, title="Saved by two users")
    first_headers = _create_user_headers(client, db)
    second_headers = _create_user_headers(client, db)

    for headers in (first_headers, second_headers):
        response = client.post(
            f"{settings.API_V1_STR}/articles/{article.id}/save",
            headers=headers,
        )
        assert response.status_code == 201

    response = client.get(
        f"{settings.API_V1_STR}/admin/articles",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    body = response.json()
    row = next(item for item in body["data"] if item["id"] == str(article.id))
    assert row["title"] == "Saved by two users"
    assert row["saved_count"] == 2


def test_delete_admin_article_removes_article(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    article = _create_article(db, title="Delete me")
    article_id = article.id

    response = client.delete(
        f"{settings.API_V1_STR}/admin/articles/{article_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Article deleted"}
    db.expire_all()
    assert crud.get_article(session=db, article_id=article_id) is None


def test_delete_admin_article_returns_404_for_missing_article(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/admin/articles/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"

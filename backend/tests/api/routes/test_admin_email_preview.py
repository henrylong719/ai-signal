import uuid
from datetime import datetime, timezone
from html import unescape
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.schemas import ArticleCreate
from app.services.digest import DigestPublic


def _create_article(db: Session, *, title: str = "Preview article"):
    return crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title=title,
            source="Example",
            excerpt="Preview article excerpt",
            category="models",
            tags=["models"],
            published_at=datetime.now(timezone.utc),
        ),
    )


def test_digest_html_preview_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/admin/email-preview/digest-html")
    assert response.status_code == 401


def test_digest_html_preview_requires_superuser(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/admin/email-preview/digest-html",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_digest_html_preview_returns_html_with_articles(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    _create_article(db, title="Preview digest article")

    with patch(
        "app.services.digest_email.send_email_via_resend",
        side_effect=AssertionError("preview endpoint must not send email"),
    ) as mock_send:
        response = client.get(
            f"{settings.API_V1_STR}/admin/email-preview/digest-html",
            headers=superuser_token_headers,
        )

    body = unescape(response.text)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "AI Signal" in body
    assert "Today’s Signal" in body
    assert "Preview digest article" in body
    assert mock_send.call_count == 0


def test_digest_html_preview_sample_does_not_require_articles(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    with (
        patch(
            "app.api.routes.admin_email_preview.build_digest",
            side_effect=AssertionError("sample preview should not query digest"),
        ),
        patch(
            "app.services.digest_email.send_email_via_resend",
            side_effect=AssertionError("preview endpoint must not send email"),
        ) as mock_send,
    ):
        response = client.get(
            f"{settings.API_V1_STR}/admin/email-preview/digest-html?sample=true",
            headers=superuser_token_headers,
        )

    body = unescape(response.text)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "AI Signal" in body
    assert "Today’s Signal" in body
    assert "OpenAI previews faster multimodal agents" in body
    assert mock_send.call_count == 0


def test_digest_html_preview_empty_state(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    empty_digest = DigestPublic(
        generated_at=now,
        window_start=now,
        sections=[],
        is_personalized=True,
    )

    with patch("app.api.routes.admin_email_preview.build_digest", return_value=empty_digest):
        response = client.get(
            f"{settings.API_V1_STR}/admin/email-preview/digest-html",
            headers=superuser_token_headers,
        )

    body = unescape(response.text)
    assert response.status_code == 200
    assert "No articles available for today’s digest preview." in body

"""Tests for the unified email service (``app.services.email``).

The HTTP/Resend boundary is mocked everywhere — these are unit
tests that should not need network access or real env vars. Two
levels are exercised:

  - The low-level :func:`send_email_via_resend` for transport
    behavior (auth header, payload shape, error handling).
  - The high-level :func:`send_password_reset_email`,
    :func:`send_new_account_email`, and :func:`send_test_email`
    helpers for content + reset-link assembly.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import httpx
import pytest

from app.core.config import settings
from app.services import email as email_service
from app.services import resend_email
from app.services.resend_email import ResendSendResult
from app.utils import generate_password_reset_token

# --- Low-level transport ----------------------------------------------------


def test_resend_send_aborts_when_api_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No API key → ok=False with a clear error; no HTTP call attempted."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", None, raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )

    with patch("httpx.post") as mock_post:
        result = resend_email.send_email_via_resend(
            to="user@example.com", subject="Hello", html="<p>hi</p>"
        )

    assert result.ok is False
    assert result.error is not None
    assert "RESEND_API_KEY" in result.error
    assert mock_post.call_count == 0


def test_resend_send_aborts_when_from_email_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same safe-fail when EMAILS_FROM_EMAIL is unset."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", None, raising=False)

    with patch("httpx.post") as mock_post:
        result = resend_email.send_email_via_resend(
            to="user@example.com", subject="Hello", html="<p>hi</p>"
        )

    assert result.ok is False
    assert result.error is not None
    assert "EMAILS_FROM_EMAIL" in result.error
    assert mock_post.call_count == 0


def test_resend_send_posts_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: bearer auth, JSON payload with from/to/subject/html."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )
    monkeypatch.setattr(settings, "EMAILS_FROM_NAME", "AI Signal", raising=False)

    fake_response = httpx.Response(
        status_code=200,
        json={"id": "msg_123"},
        request=httpx.Request("POST", "https://api.resend.com/emails"),
    )

    with patch("httpx.post", return_value=fake_response) as mock_post:
        result = resend_email.send_email_via_resend(
            to="user@example.com",
            subject="Hello",
            html="<p>hi</p>",
            text="hi",
            headers={"X-Custom": "1"},
        )

    assert result.ok is True
    assert result.message_id == "msg_123"

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.resend.com/emails"
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    payload = kwargs["json"]
    assert payload["from"] == "AI Signal <hello@aisignal.now>"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "Hello"
    assert payload["html"] == "<p>hi</p>"
    assert payload["text"] == "hi"
    assert payload["headers"] == {"X-Custom": "1"}


def test_resend_send_uses_explicit_from_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller-supplied ``from_email`` overrides the global default."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )
    monkeypatch.setattr(settings, "EMAILS_FROM_NAME", "AI Signal", raising=False)

    fake_response = httpx.Response(
        status_code=200,
        json={"id": "mid"},
        request=httpx.Request("POST", "https://api.resend.com/emails"),
    )

    with patch("httpx.post", return_value=fake_response) as mock_post:
        resend_email.send_email_via_resend(
            to="user@example.com",
            subject="Hi",
            html="<p>hi</p>",
            from_email="digest@aisignal.now",
        )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["from"] == "AI Signal <digest@aisignal.now>"


def test_resend_send_handles_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4xx/5xx surfaces as ok=False with the response body in error."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )

    fake_response = httpx.Response(
        status_code=422,
        text="invalid sender",
        request=httpx.Request("POST", "https://api.resend.com/emails"),
    )

    with patch("httpx.post", return_value=fake_response):
        result = resend_email.send_email_via_resend(
            to="user@example.com", subject="Hi", html="<p>hi</p>"
        )

    assert result.ok is False
    assert result.error is not None
    assert "422" in result.error
    assert "invalid sender" in result.error


def test_resend_send_handles_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transport failures are caught and reported, not raised."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )

    with patch("httpx.post", side_effect=httpx.ConnectTimeout("timeout")):
        result = resend_email.send_email_via_resend(
            to="user@example.com", subject="Hi", html="<p>hi</p>"
        )

    assert result.ok is False
    assert result.error is not None
    assert "network" in result.error.lower()


# --- High-level service ----------------------------------------------------


def test_send_password_reset_email_uses_frontend_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reset link must be built from FRONTEND_HOST, not hard-coded."""
    monkeypatch.setattr(
        settings, "FRONTEND_HOST", "https://aisignal.now", raising=False
    )

    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(email_service, "send_email", fake_send)

    token = generate_password_reset_token(email="user@example.com")
    result = email_service.send_password_reset_email(
        email_to="user@example.com", token=token
    )

    assert result.ok is True
    assert captured["to"] == "user@example.com"
    expected_link = f"https://aisignal.now/reset-password?token={token}"
    assert expected_link in captured["html"]
    assert captured["subject"] == "Reset your AI Signal password"
    assert "AI Signal" in captured["html"]
    assert "Reset password" in captured["html"]
    # MJML/prettier inserts arbitrary line wraps inside paragraphs, so
    # compare against whitespace-collapsed HTML rather than the literal.
    normalized_html = re.sub(r"\s+", " ", captured["html"])
    assert "This link will expire in 48 hours." in normalized_html
    assert "Hi," in captured["html"]
    assert "Hi user@example.com," not in captured["html"]
    assert "This password will expire" not in captured["html"]
    assert "Password Recovery" not in captured["html"]


def test_send_password_reset_email_uses_first_name_greeting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When available, the reset email greets by first name only."""
    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(email_service, "send_email", fake_send)

    token = generate_password_reset_token(email="user@example.com")
    email_service.send_password_reset_email(
        email_to="user@example.com", token=token, full_name="HENRY LONG"
    )

    assert "Hi Henry," in captured["html"]
    assert "Hi HENRY," not in captured["html"]
    assert "HENRY LONG" not in captured["html"]
    assert "Hi user@example.com," not in captured["html"]


def test_send_password_reset_email_strips_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A trailing slash in FRONTEND_HOST mustn't double up in the link."""
    monkeypatch.setattr(
        settings, "FRONTEND_HOST", "https://aisignal.now/", raising=False
    )

    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(email_service, "send_email", fake_send)

    token = generate_password_reset_token(email="user@example.com")
    email_service.send_password_reset_email(
        email_to="user@example.com", token=token
    )

    assert "https://aisignal.now/reset-password?token=" in captured["html"]
    assert "https://aisignal.now//reset-password" not in captured["html"]


def test_send_password_reset_email_safe_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No API key → ok=False, no exception, no HTTP call."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", None, raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )
    monkeypatch.setattr(
        settings, "FRONTEND_HOST", "https://aisignal.now", raising=False
    )

    with patch("httpx.post") as mock_post:
        token = generate_password_reset_token(email="user@example.com")
        result = email_service.send_password_reset_email(
            email_to="user@example.com", token=token
        )

    assert result.ok is False
    assert result.error is not None
    assert "RESEND_API_KEY" in result.error
    assert mock_post.call_count == 0


def test_send_test_email_renders_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``send_test_email`` builds a real HTML body via the test template."""
    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(email_service, "send_email", fake_send)

    result = email_service.send_test_email(email_to="ops@example.com")

    assert result.ok is True
    assert captured["to"] == "ops@example.com"
    assert "Test email" in captured["subject"]
    assert "ops@example.com" in captured["html"]


def test_send_new_account_email_includes_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The admin welcome email body carries the temp credentials."""
    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(email_service, "send_email", fake_send)

    result = email_service.send_new_account_email(
        email_to="new@example.com",
        username="new@example.com",
        password="initial-pass",
    )

    assert result.ok is True
    assert captured["to"] == "new@example.com"
    assert "new@example.com" in captured["html"]
    assert "initial-pass" in captured["html"]


# --- Settings-level wiring -------------------------------------------------


def test_emails_enabled_requires_resend_not_smtp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``settings.emails_enabled`` keys off Resend, ignoring SMTP_*."""
    # SMTP_HOST being set must not flip emails_enabled to True.
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com", raising=False)
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@aisignal.now", raising=False
    )
    monkeypatch.setattr(settings, "RESEND_API_KEY", None, raising=False)
    assert settings.emails_enabled is False

    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    assert settings.emails_enabled is True


def test_email_service_reexports_digest_sender() -> None:
    """``send_digest_email`` is reachable via the unified service.

    Guards against an accidental rename leaving the digest scheduler's
    import target broken.
    """
    from app.services.digest_email import (
        send_digest_email as digest_send,
    )

    assert email_service.send_digest_email is digest_send

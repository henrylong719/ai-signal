"""Tests for the subscriber digest email sender."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.schemas import ArticleCreate
from app.services import subscriber_email
from app.services.resend_email import ResendSendResult
from app.services.subscriber_tokens import parse_subscriber_unsubscribe_token
from tests.utils.utils import random_email


def _seed_article(db: Session) -> None:
    crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title="OpenAI ships something noteworthy",
            source="Anthropic",
            category="models",
            excerpt="A short excerpt.",
            published_at=datetime.now(timezone.utc),
            tags=["test"],
        ),
    )


def _configure_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(
        settings, "DIGEST_FROM_EMAIL", "digest@example.com", raising=False
    )
    monkeypatch.setattr(
        settings, "EMAILS_FROM_EMAIL", "hello@example.com", raising=False
    )


def test_send_subscriber_digest_email_renders_and_sends(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_sender(monkeypatch)
    _seed_article(db)
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())

    captured: dict = {}

    def fake_send(**kwargs: object) -> ResendSendResult:
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid-1")

    monkeypatch.setattr(subscriber_email, "send_email_via_resend", fake_send)

    result = subscriber_email.send_subscriber_digest_email(
        session=db, subscriber=subscriber
    )

    assert result.ok is True
    assert captured["to"] == subscriber.email
    assert "List-Unsubscribe" in captured["headers"]
    # The one-click unsubscribe link must carry a token that resolves back
    # to THIS subscriber — proving the send is wired to the subscriber's
    # own token, not the user path's.
    header = captured["headers"]["List-Unsubscribe"]
    token = header.split("token=")[1].rstrip(">")
    assert parse_subscriber_unsubscribe_token(token) == subscriber.id


def test_send_subscriber_digest_email_skips_when_empty(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_sender(monkeypatch)
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())

    # Empty digest — patch the name the service actually calls.
    from app.services.digest import DigestPublic

    monkeypatch.setattr(
        subscriber_email,
        "build_digest",
        lambda **_kwargs: DigestPublic(
            generated_at=datetime.now(timezone.utc),
            window_start=datetime.now(timezone.utc),
            is_personalized=False,
            sections=[],
        ),
    )

    def fail_send(**_kwargs: object) -> ResendSendResult:
        raise AssertionError("should not send an empty digest")

    monkeypatch.setattr(subscriber_email, "send_email_via_resend", fail_send)

    result = subscriber_email.send_subscriber_digest_email(
        session=db, subscriber=subscriber
    )
    assert result.ok is False


def test_send_subscriber_digest_email_accepts_prebuilt_digest(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The scheduled job builds the digest once and reuses it; passing a
    pre-built digest must not trigger another build."""
    _configure_sender(monkeypatch)
    _seed_article(db)
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())

    prebuilt = subscriber_email.build_digest(session=db, user_id=None)

    def boom(**_kwargs: object) -> object:
        raise AssertionError("build_digest should not be called again")

    monkeypatch.setattr(subscriber_email, "build_digest", boom)
    monkeypatch.setattr(
        subscriber_email,
        "send_email_via_resend",
        lambda **_kwargs: ResendSendResult(ok=True, message_id="mid-2"),
    )

    result = subscriber_email.send_subscriber_digest_email(
        session=db, subscriber=subscriber, digest=prebuilt
    )
    assert result.ok is True

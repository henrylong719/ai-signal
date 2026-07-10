"""Tests for the scheduled subscriber digest send loop."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, delete

from app import crud
from app.core.config import settings
from app.models.subscriber import DigestSubscriber
from app.schemas import ArticleCreate, UserCreate
from app.services import subscriber_digest
from app.services.resend_email import ResendSendResult
from tests.utils.utils import random_email


@pytest.fixture(autouse=True)
def _isolate_subscribers(db: Session) -> None:
    """The send loop is global over the subscriber table, and conftest's
    cleanup doesn't touch digest_subscribers — so wipe them before each
    test here to keep the global-count assertions deterministic."""
    db.exec(delete(DigestSubscriber))
    db.commit()


def _seed_article(db: Session) -> None:
    crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title="Something worth reading today",
            source="Anthropic",
            category="models",
            excerpt="A short excerpt.",
            published_at=datetime.now(timezone.utc),
            tags=["test"],
        ),
    )


def _enable_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(
        settings, "DIGEST_FROM_EMAIL", "digest@example.com", raising=False
    )


def test_run_noop_when_email_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RESEND_API_KEY", None, raising=False)
    outcome = subscriber_digest.run_subscriber_digest_send()
    assert outcome.sent == 0
    assert outcome.candidates == 0


def test_run_sends_to_active_subscribers(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_email(monkeypatch)
    _seed_article(db)
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())

    sent_to: list[str] = []

    def fake_send(**kwargs: object) -> ResendSendResult:
        sent_to.append(kwargs["subscriber"].email)  # type: ignore[attr-defined]
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(subscriber_digest, "send_subscriber_digest_email", fake_send)

    outcome = subscriber_digest.run_subscriber_digest_send(
        now=datetime(2026, 6, 1, 6, 0, tzinfo=timezone.utc)
    )

    assert sent_to == [subscriber.email]
    assert outcome.sent == 1
    db.refresh(subscriber)
    assert subscriber.last_digest_sent_at is not None


def test_run_skips_email_matching_active_digest_user(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A person on both lists gets the personalized user digest, not a
    second generic one."""
    _enable_email(monkeypatch)
    _seed_article(db)
    shared_email = random_email()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=shared_email, password="password123"),
    )
    user.daily_digest_enabled = True
    db.add(user)
    db.commit()
    crud.upsert_subscriber(session=db, email=shared_email)

    def fail_send(**_kwargs: object) -> ResendSendResult:
        raise AssertionError("should not send to a digest-enabled user's email")

    monkeypatch.setattr(subscriber_digest, "send_subscriber_digest_email", fail_send)

    outcome = subscriber_digest.run_subscriber_digest_send(
        now=datetime(2026, 6, 1, 6, 0, tzinfo=timezone.utc)
    )
    assert outcome.sent == 0
    assert outcome.skipped == 1


def test_run_is_idempotent_within_utc_day(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_email(monkeypatch)
    _seed_article(db)
    crud.upsert_subscriber(session=db, email=random_email())
    calls = {"n": 0}

    def counting_send(**_kwargs: object) -> ResendSendResult:
        calls["n"] += 1
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(
        subscriber_digest, "send_subscriber_digest_email", counting_send
    )

    clock = datetime(2026, 6, 1, 6, 0, tzinfo=timezone.utc)
    subscriber_digest.run_subscriber_digest_send(now=clock)
    subscriber_digest.run_subscriber_digest_send(now=clock)
    assert calls["n"] == 1


def test_run_isolates_per_subscriber_failure(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_email(monkeypatch)
    _seed_article(db)
    crud.upsert_subscriber(session=db, email=random_email())
    crud.upsert_subscriber(session=db, email=random_email())

    def flaky_send(**_kwargs: object) -> ResendSendResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(subscriber_digest, "send_subscriber_digest_email", flaky_send)

    outcome = subscriber_digest.run_subscriber_digest_send(
        now=datetime(2026, 6, 1, 6, 0, tzinfo=timezone.utc)
    )
    # Both attempted, both failed, loop did not abort.
    assert outcome.failed == 2


def test_run_skips_when_digest_empty(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_email(monkeypatch)
    crud.upsert_subscriber(session=db, email=random_email())

    from app.services.digest import DigestPublic

    monkeypatch.setattr(
        subscriber_digest,
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

    monkeypatch.setattr(subscriber_digest, "send_subscriber_digest_email", fail_send)

    outcome = subscriber_digest.run_subscriber_digest_send(
        now=datetime(2026, 6, 1, 6, 0, tzinfo=timezone.utc)
    )
    assert outcome.sent == 0

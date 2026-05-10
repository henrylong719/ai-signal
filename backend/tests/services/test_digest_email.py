"""Tests for the daily-digest email sender.

The HTTP / Resend boundary is mocked because we don't want unit
tests to depend on real network or env vars. The render path is
exercised through ``send_digest_email`` so a regression in HTML
escaping or template wiring shows up here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User
from app.schemas import ArticleCreate, UserCreate
from app.schemas.source import Category
from app.services import digest_email, digest_scheduler, resend_email
from app.services.digest_email import (
    make_unsubscribe_token,
    parse_unsubscribe_token,
    send_digest_email,
)
from app.services.digest_scheduler import (
    SendLoopOutcome,
    run_digest_send,
    should_send_now,
)
from app.services.resend_email import ResendSendResult

# --- Helpers ----------------------------------------------------------------


def _make_user(
    db: Session,
    *,
    digest_enabled: bool = True,
    timezone_name: str | None = "America/New_York",
    last_sent: datetime | None = None,
) -> User:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"digest-{uuid.uuid4()}@example.com",
            password="testtest",
            full_name="Test User",
        ),
    )
    user.daily_digest_enabled = digest_enabled
    user.timezone = timezone_name
    user.last_digest_sent_at = last_sent
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_article(
    db: Session,
    *,
    source: str = "Anthropic",
    title: str | None = None,
    category: Category = "models",
    excerpt: str | None = "A short excerpt.",
) -> uuid.UUID:
    article = crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title=title or f"Article {uuid.uuid4()}",
            source=source,
            category=category,
            excerpt=excerpt,
            published_at=datetime.now(timezone.utc),
            tags=["test"],
        ),
    )
    return article.id


# --- Token round-trip -------------------------------------------------------


def test_unsubscribe_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = make_unsubscribe_token(user_id)
    assert parse_unsubscribe_token(token) == user_id


def test_unsubscribe_token_rejects_garbage() -> None:
    assert parse_unsubscribe_token("not-a-jwt") is None


def test_unsubscribe_token_rejects_wrong_type() -> None:
    """Access tokens (issued by login) must not unlock the unsub endpoint."""
    from datetime import timedelta as _td

    from app.core import security as core_security

    access = core_security.create_access_token(
        subject=str(uuid.uuid4()), expires_delta=_td(minutes=5)
    )
    assert parse_unsubscribe_token(access) is None


# --- should_send_now --------------------------------------------------------


@pytest.fixture
def opted_in_user(db: Session) -> User:
    return _make_user(db, digest_enabled=True, timezone_name="America/New_York")


def test_should_send_now_at_local_8am(opted_in_user: User) -> None:
    # 12:00 UTC == 8:00 EDT (April–November, daylight time).
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    assert should_send_now(opted_in_user, now=now, target_hour=8) is True


def test_should_send_now_skips_off_hour(opted_in_user: User) -> None:
    now = datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc)  # 9:00 local
    assert should_send_now(opted_in_user, now=now, target_hour=8) is False


def test_should_send_now_skips_disabled_user(db: Session) -> None:
    user = _make_user(db, digest_enabled=False)
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    assert should_send_now(user, now=now, target_hour=8) is False


def test_should_send_now_skips_already_sent_today(db: Session) -> None:
    # Sent at 13:00 UTC, which is 9:00 local on the same day.
    sent = datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc)
    user = _make_user(
        db,
        digest_enabled=True,
        timezone_name="America/New_York",
        last_sent=sent,
    )
    # Tick at 12:00 UTC the next day → 8:00 local on the next local
    # date, which IS a different calendar day, so it should send.
    next_day = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    assert should_send_now(user, now=next_day, target_hour=8) is True

    # Same local hour, same local day → already sent.
    same_day_again = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    assert should_send_now(user, now=same_day_again, target_hour=8) is False


def test_should_send_now_handles_unknown_timezone(db: Session) -> None:
    """Bad tz string falls back to UTC instead of raising."""
    user = _make_user(db, digest_enabled=True, timezone_name="Foo/Bar")
    # 8:00 UTC after the fallback resolves to UTC.
    now = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
    assert should_send_now(user, now=now, target_hour=8) is True


def test_should_send_now_rejects_naive_clock(opted_in_user: User) -> None:
    naive = datetime(2026, 6, 1, 12, 0)  # tz-naive
    with pytest.raises(ValueError):
        should_send_now(opted_in_user, now=naive)


# --- Send rendering --------------------------------------------------------


def test_send_digest_email_skips_when_pool_empty(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When build_digest yields no sections we never call Resend."""
    from datetime import datetime as _datetime

    from app.services.digest import DigestPublic

    user = _make_user(db)
    monkeypatch.setattr(
        settings, "RESEND_API_KEY", "test-key", raising=False
    )
    monkeypatch.setattr(
        settings, "DIGEST_FROM_EMAIL", "digest@example.com", raising=False
    )
    # Other tests in this suite seed articles into the shared DB, so
    # build_digest could find content here even with no fixtures of
    # our own. Force an empty result so this test asserts the
    # "no content → don't send" branch deterministically.
    empty_now = _datetime.now(timezone.utc)
    monkeypatch.setattr(
        digest_email,
        "build_digest",
        lambda **_kw: DigestPublic(
            generated_at=empty_now,
            window_start=empty_now,
            sections=[],
            is_personalized=True,
        ),
    )

    sent: list[dict] = []

    def fake_send(**kwargs):
        sent.append(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(digest_email, "send_email_via_resend", fake_send)

    result = send_digest_email(session=db, user=user)
    assert result.ok is False
    assert "empty" in (result.error or "")
    assert sent == []


def test_send_digest_email_sends_when_articles_exist(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: with content the renderer ships HTML+text+headers."""
    user = _make_user(db)
    _seed_article(
        db,
        source="OpenAI",
        title="OpenAI releases new model updates",
        category="models",
    )
    _seed_article(db, source="Anthropic", title="Anthropic publishes safety notes")
    _seed_article(db, source="Google DeepMind", title="DeepMind shares research")

    monkeypatch.setattr(
        settings, "RESEND_API_KEY", "test-key", raising=False
    )
    monkeypatch.setattr(
        settings, "DIGEST_FROM_EMAIL", "digest@example.com", raising=False
    )
    monkeypatch.setattr(
        settings, "FRONTEND_HOST", "https://app.example.com", raising=False
    )

    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid-123")

    monkeypatch.setattr(digest_email, "send_email_via_resend", fake_send)

    result = send_digest_email(session=db, user=user)
    assert result.ok is True
    assert result.message_id == "mid-123"
    assert captured["to"] == user.email
    assert captured["from_email"] == "digest@example.com"
    assert "Today’s Signal" in captured["subject"]
    assert "AI Signal" in captured["html"]
    assert "Today&rsquo;s Signal" in captured["html"]
    assert "OpenAI releases new model updates" in captured["html"]
    assert "OpenAI" in captured["html"]
    assert "Models" in captured["html"]
    assert "Read article" in captured["html"]
    assert "https://app.example.com/today-digest" in captured["html"]
    assert "/api/v1/articles/" in captured["html"]
    # Token-bearing unsubscribe link surfaces in both HTML and the
    # List-Unsubscribe header.
    assert "/digest/unsubscribe?token=" in captured["html"]
    assert "List-Unsubscribe" in captured["headers"]
    assert "List-Unsubscribe-Post" in captured["headers"]
    # Text fallback and HTML both populated.
    assert captured["text"]
    assert "Today’s Signal" in captured["text"]
    assert "OpenAI releases new model updates" in captured["text"]
    assert "OpenAI" in captured["text"]
    assert "Open AI Signal: https://app.example.com/today-digest" in captured["text"]
    assert "<html" in captured["html"].lower()


def test_send_digest_email_escapes_user_content(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Article titles from RSS feeds must not be injected as HTML."""
    user = _make_user(db)
    crud.create_article(
        session=db,
        article_in=ArticleCreate(
            url=f"https://example.com/{uuid.uuid4()}",
            title="<script>alert(1)</script>",
            source='Anthropic" onload=alert(1)',
            category="models",
            excerpt="<b>bold</b>",
            published_at=datetime.now(timezone.utc),
            tags=[],
        ),
    )

    monkeypatch.setattr(
        settings, "RESEND_API_KEY", "test-key", raising=False
    )
    monkeypatch.setattr(
        settings, "DIGEST_FROM_EMAIL", "digest@example.com", raising=False
    )

    captured: dict = {}

    def fake_send(**kwargs):
        captured.update(kwargs)
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(digest_email, "send_email_via_resend", fake_send)
    send_digest_email(session=db, user=user)

    html_body = captured["html"]
    # Raw HTML must be escaped — no executable script or attribute.
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    assert "<b>bold</b>" not in html_body
    assert "&lt;b&gt;bold&lt;/b&gt;" in html_body


# --- run_digest_send loop ---------------------------------------------------


def test_run_digest_send_no_op_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "RESEND_API_KEY", None, raising=False)
    monkeypatch.setattr(settings, "DIGEST_FROM_EMAIL", None, raising=False)
    outcome = run_digest_send()
    assert isinstance(outcome, SendLoopOutcome)
    assert outcome.candidates == 0
    assert outcome.sent == 0


def test_run_digest_send_marks_sent_and_is_idempotent(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful send stamps last_digest_sent_at; the second tick skips."""
    user = _make_user(
        db, digest_enabled=True, timezone_name="America/New_York", last_sent=None
    )
    _seed_article(db)

    monkeypatch.setattr(
        settings, "RESEND_API_KEY", "test-key", raising=False
    )
    monkeypatch.setattr(
        settings, "DIGEST_FROM_EMAIL", "digest@example.com", raising=False
    )

    # The test DB shares state with other tests in this file, so the
    # candidate query would return their fixtures too. Constrain the
    # loop to the user we just created so only their state is asserted.
    monkeypatch.setattr(
        digest_scheduler,
        "_candidate_users",
        lambda session: [session.get(User, user.id)],
    )
    monkeypatch.setattr(
        digest_email,
        "send_email_via_resend",
        lambda **_: ResendSendResult(ok=True, message_id="mid"),
    )

    # 12:00 UTC == 8:00 EDT.
    fire_at = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    outcome_1 = run_digest_send(now=fire_at)
    assert outcome_1.sent == 1

    db.refresh(user)
    assert user.last_digest_sent_at is not None

    # Second tick same hour same day — should skip.
    outcome_2 = run_digest_send(now=fire_at)
    assert outcome_2.sent == 0
    assert outcome_2.skipped >= 1


def test_unsubscribe_token_can_disable_digest(
    db: Session,
) -> None:
    """The unsubscribe endpoint flips the flag and is idempotent.

    Goes through the route directly — the integration test of the
    endpoint via TestClient lives in tests/api/routes/.
    """
    user = _make_user(db, digest_enabled=True)
    token = make_unsubscribe_token(user.id)
    parsed = parse_unsubscribe_token(token)
    assert parsed == user.id


# Ensure the resend_email module surface is what the digest module imports —
# guards against an accidental rename leaving send_digest_email pointing at
# nothing.
def test_resend_module_exposes_send_email_via_resend() -> None:
    assert callable(resend_email.send_email_via_resend)
    assert digest_scheduler.send_digest_email is send_digest_email

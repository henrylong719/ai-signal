"""Tests for the public digest-subscription endpoint."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.api.routes import subscription as subscription_route
from app.core.config import settings
from app.models.subscriber import DigestSubscriber
from app.services.resend_email import ResendSendResult
from app.services.subscriber_tokens import make_subscriber_unsubscribe_token
from tests.utils.utils import random_email


def test_create_subscription_persists_subscriber(
    client: TestClient, db: Session
) -> None:
    email = random_email()

    response = client.post(
        f"{settings.API_V1_STR}/subscriptions",
        json={"email": email},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert body["is_active"] is True

    stored = db.exec(
        select(DigestSubscriber).where(DigestSubscriber.email == email)
    ).one()
    assert stored.is_active is True


def test_subscribe_sends_welcome_digest_and_stamps_watermark(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new subscriber gets today's digest immediately, and the send
    stamps the watermark so the same-day scheduled run won't double-send."""
    email = random_email()
    sends: list[str] = []

    def fake_send(**kwargs: object) -> ResendSendResult:
        sends.append(kwargs["subscriber"].email)  # type: ignore[attr-defined]
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(subscription_route, "send_subscriber_digest_email", fake_send)

    response = client.post(
        f"{settings.API_V1_STR}/subscriptions", json={"email": email}
    )

    assert response.status_code == 201
    assert sends == [email]
    stored = db.exec(
        select(DigestSubscriber).where(DigestSubscriber.email == email)
    ).one()
    assert stored.last_digest_sent_at is not None


def test_subscribe_welcome_send_failure_still_returns_201(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The welcome send is best-effort — a Resend failure (or empty digest)
    must not turn the subscribe into an error, and must not stamp the
    watermark (so the scheduled run can retry)."""
    email = random_email()

    def failing_send(**_kwargs: object) -> ResendSendResult:
        return ResendSendResult(ok=False, error="empty digest")

    monkeypatch.setattr(
        subscription_route, "send_subscriber_digest_email", failing_send
    )

    response = client.post(
        f"{settings.API_V1_STR}/subscriptions", json={"email": email}
    )

    assert response.status_code == 201
    stored = db.exec(
        select(DigestSubscriber).where(DigestSubscriber.email == email)
    ).one()
    assert stored.last_digest_sent_at is None


def test_resubscribe_same_day_does_not_resend_welcome(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = random_email()
    calls = {"n": 0}

    def counting_send(**_kwargs: object) -> ResendSendResult:
        calls["n"] += 1
        return ResendSendResult(ok=True, message_id="mid")

    monkeypatch.setattr(
        subscription_route, "send_subscriber_digest_email", counting_send
    )

    client.post(f"{settings.API_V1_STR}/subscriptions", json={"email": email})
    client.post(f"{settings.API_V1_STR}/subscriptions", json={"email": email})

    assert calls["n"] == 1


def test_unsubscribe_get_deactivates_subscriber(
    client: TestClient, db: Session
) -> None:
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())
    token = make_subscriber_unsubscribe_token(subscriber.id)

    response = client.get(
        f"{settings.API_V1_STR}/subscriptions/unsubscribe",
        params={"token": token},
    )

    assert response.status_code == 200
    assert "unsubscribed" in response.text.lower()
    db.refresh(subscriber)
    assert subscriber.is_active is False


def test_unsubscribe_post_deactivates_subscriber(
    client: TestClient, db: Session
) -> None:
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())
    token = make_subscriber_unsubscribe_token(subscriber.id)

    response = client.post(
        f"{settings.API_V1_STR}/subscriptions/unsubscribe",
        params={"token": token},
    )

    assert response.status_code == 200
    db.refresh(subscriber)
    assert subscriber.is_active is False


def test_unsubscribe_bad_token_renders_page_without_changing_state(
    client: TestClient, db: Session
) -> None:
    subscriber, _ = crud.upsert_subscriber(session=db, email=random_email())

    response = client.get(
        f"{settings.API_V1_STR}/subscriptions/unsubscribe",
        params={"token": "not-a-valid-token"},
    )

    assert response.status_code == 200
    db.refresh(subscriber)
    assert subscriber.is_active is True


def test_resubscribing_same_email_returns_201(client: TestClient, db: Session) -> None:
    """The response must not reveal whether an email was already
    subscribed — a 200-vs-201 split lets anyone probe the subscriber
    list one address at a time."""
    del db
    email = random_email()

    first = client.post(
        f"{settings.API_V1_STR}/subscriptions",
        json={"email": email},
    )
    assert first.status_code == 201

    second = client.post(
        f"{settings.API_V1_STR}/subscriptions",
        json={"email": email},
    )
    assert second.status_code == 201


def test_subscription_endpoint_is_rate_limited(client: TestClient) -> None:
    """Anonymous and unauthenticated: without a quota one host can spam
    the table with unlimited rows (and subscribe strangers en masse)."""
    from app.core.rate_limit import limiter

    fresh = TestClient(client.app)  # type: ignore[arg-type]
    original_enabled = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    try:
        for _ in range(10):
            r = fresh.post(
                f"{settings.API_V1_STR}/subscriptions",
                json={"email": random_email()},
            )
            assert r.status_code == 201
        blocked = fresh.post(
            f"{settings.API_V1_STR}/subscriptions",
            json={"email": random_email()},
        )
    finally:
        limiter.enabled = original_enabled
        limiter.reset()
    assert blocked.status_code == 429

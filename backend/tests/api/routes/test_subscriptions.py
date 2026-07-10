"""Tests for the public digest-subscription endpoint."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models.subscriber import DigestSubscriber
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


def test_resubscribing_same_email_returns_201(
    client: TestClient, db: Session
) -> None:
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

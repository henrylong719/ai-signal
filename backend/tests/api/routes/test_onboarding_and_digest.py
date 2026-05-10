"""Endpoint tests for onboarding completion, digest preferences, and the
public unsubscribe link delivered via the daily-digest email.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User
from app.schemas import UserCreate
from app.services.digest_email import make_unsubscribe_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _create_authenticated_user(
    client: TestClient,
    db: Session,
) -> tuple[User, dict[str, str]]:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    return user, user_authentication_headers(
        client=client, email=email, password=password
    )


# --- /users/me/onboarding ---------------------------------------------------


def test_onboarding_requires_auth(client: TestClient) -> None:
    response = client.put(
        f"{settings.API_V1_STR}/users/me/onboarding",
        json={"timezone": "America/New_York", "daily_digest_enabled": True},
    )
    assert response.status_code == 401


def test_onboarding_marks_complete_and_persists_preferences(
    client: TestClient, db: Session
) -> None:
    user, headers = _create_authenticated_user(client, db)
    assert user.onboarded_at is None
    assert user.daily_digest_enabled is False

    response = client.put(
        f"{settings.API_V1_STR}/users/me/onboarding",
        headers=headers,
        json={"timezone": "America/Los_Angeles", "daily_digest_enabled": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "America/Los_Angeles"
    assert body["daily_digest_enabled"] is True
    assert body["onboarded_at"] is not None

    db.refresh(user)
    assert user.timezone == "America/Los_Angeles"
    assert user.daily_digest_enabled is True
    assert user.onboarded_at is not None


def test_onboarding_does_not_overwrite_completion_timestamp(
    client: TestClient, db: Session
) -> None:
    """Re-running the flow keeps the original onboarded_at."""
    user, headers = _create_authenticated_user(client, db)
    first = client.put(
        f"{settings.API_V1_STR}/users/me/onboarding",
        headers=headers,
        json={"timezone": "Europe/London", "daily_digest_enabled": False},
    ).json()
    second = client.put(
        f"{settings.API_V1_STR}/users/me/onboarding",
        headers=headers,
        json={"timezone": "Europe/London", "daily_digest_enabled": True},
    ).json()
    assert first["onboarded_at"] == second["onboarded_at"]
    assert second["daily_digest_enabled"] is True


# --- /users/me/digest-preferences ------------------------------------------


def test_digest_preferences_partial_update(
    client: TestClient, db: Session
) -> None:
    user, headers = _create_authenticated_user(client, db)
    user.timezone = "America/New_York"
    user.daily_digest_enabled = True
    db.add(user)
    db.commit()

    # Update only the toggle; tz must stay put.
    response = client.put(
        f"{settings.API_V1_STR}/users/me/digest-preferences",
        headers=headers,
        json={"daily_digest_enabled": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "America/New_York"
    assert body["daily_digest_enabled"] is False


def test_digest_preferences_disabling_resets_send_watermark(
    client: TestClient, db: Session
) -> None:
    """Re-enabling on the same day shouldn't be silently skipped by
    the loop's idempotency check."""
    user, headers = _create_authenticated_user(client, db)
    user.daily_digest_enabled = True
    user.last_digest_sent_at = None
    db.add(user)
    db.commit()

    client.put(
        f"{settings.API_V1_STR}/users/me/digest-preferences",
        headers=headers,
        json={"daily_digest_enabled": False},
    )
    db.refresh(user)
    assert user.last_digest_sent_at is not None


# --- /digest/unsubscribe ----------------------------------------------------


def test_unsubscribe_disables_digest(client: TestClient, db: Session) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string()
        ),
    )
    user.daily_digest_enabled = True
    db.add(user)
    db.commit()

    token = make_unsubscribe_token(user.id)
    response = client.get(
        f"{settings.API_V1_STR}/digest/unsubscribe",
        params={"token": token},
    )
    assert response.status_code == 200
    assert "unsubscribed" in response.text.lower()

    db.refresh(user)
    assert user.daily_digest_enabled is False


def test_unsubscribe_invalid_token_renders_friendly_page(
    client: TestClient,
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/digest/unsubscribe",
        params={"token": "garbage"},
    )
    assert response.status_code == 200
    assert "expired" in response.text.lower() or "invalid" in response.text.lower()


def test_unsubscribe_one_click_post(client: TestClient, db: Session) -> None:
    """RFC 8058 one-click target also works."""
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string()
        ),
    )
    user.daily_digest_enabled = True
    db.add(user)
    db.commit()
    token = make_unsubscribe_token(user.id)

    response = client.post(
        f"{settings.API_V1_STR}/digest/unsubscribe",
        params={"token": token},
    )
    assert response.status_code == 200
    db.refresh(user)
    assert user.daily_digest_enabled is False


def test_unsubscribe_for_deleted_user_is_idempotent(
    client: TestClient,
) -> None:
    """The token outlives the account by design (30 days). Returning
    a friendly confirmation is the right behavior — no 500."""
    token = make_unsubscribe_token(uuid.uuid4())
    response = client.get(
        f"{settings.API_V1_STR}/digest/unsubscribe",
        params={"token": token},
    )
    assert response.status_code == 200

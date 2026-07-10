"""Endpoint tests for onboarding completion, digest preferences, and the
public unsubscribe link delivered via the daily-digest email.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.models import User
from app.schemas import UserCreate
from app.services.digest_email import make_unsubscribe_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _expired_unsub_token(user_id: uuid.UUID) -> str:
    """Mint a digest-unsub JWT whose ``exp`` is already in the past."""
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "type": "digest-unsub",
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )


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


def test_onboarding_rejects_invalid_timezone(client: TestClient, db: Session) -> None:
    """A bogus IANA tz would silently fall back to UTC at send time —
    surfacing 422 tells the client to send a real zone (or omit it)."""
    _, headers = _create_authenticated_user(client, db)
    response = client.put(
        f"{settings.API_V1_STR}/users/me/onboarding",
        headers=headers,
        json={"timezone": "Not/AZone", "daily_digest_enabled": True},
    )
    assert response.status_code == 422


def test_onboarding_allows_null_timezone(client: TestClient, db: Session) -> None:
    """Omitting the timezone stays valid — browsers in privacy mode may
    not expose one, and the sender falls back to UTC by design."""
    _, headers = _create_authenticated_user(client, db)
    response = client.put(
        f"{settings.API_V1_STR}/users/me/onboarding",
        headers=headers,
        json={"daily_digest_enabled": True},
    )
    assert response.status_code == 200


# --- /users/me/digest-preferences ------------------------------------------


def test_digest_preferences_rejects_invalid_timezone(
    client: TestClient, db: Session
) -> None:
    _, headers = _create_authenticated_user(client, db)
    response = client.put(
        f"{settings.API_V1_STR}/users/me/digest-preferences",
        headers=headers,
        json={"timezone": "Mars/Phobos"},
    )
    assert response.status_code == 422


def test_digest_preferences_partial_update(client: TestClient, db: Session) -> None:
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
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
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
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
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


def test_unsubscribe_confirmation_includes_resubscribe_action(
    client: TestClient, db: Session
) -> None:
    """The success page surfaces a POST form back to /digest/resubscribe."""
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
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
    body = response.text
    assert "Resubscribe" in body
    assert 'method="post"' in body.lower()
    assert f'action="{settings.API_V1_STR}/digest/resubscribe?token={token}"' in body


# --- /digest/resubscribe ----------------------------------------------------


def test_resubscribe_enables_digest_with_valid_token(
    client: TestClient, db: Session
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    user.daily_digest_enabled = False
    db.add(user)
    db.commit()

    token = make_unsubscribe_token(user.id)
    response = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe",
        params={"token": token},
    )
    assert response.status_code == 200
    assert "subscribed again" in response.text.lower()

    db.refresh(user)
    assert user.daily_digest_enabled is True


def test_resubscribe_does_not_require_login(client: TestClient, db: Session) -> None:
    """No Authorization header is sent — the signed token is the only auth."""
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    user.daily_digest_enabled = False
    db.add(user)
    db.commit()

    token = make_unsubscribe_token(user.id)
    response = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe",
        params={"token": token},
    )
    assert response.status_code == 200


def test_resubscribe_invalid_token_renders_friendly_page(
    client: TestClient, db: Session
) -> None:
    """Garbage token must not flip any preference."""
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    user.daily_digest_enabled = False
    db.add(user)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe",
        params={"token": "garbage"},
    )
    assert response.status_code == 200
    text = response.text.lower()
    assert "invalid" in text or "expired" in text

    db.refresh(user)
    assert user.daily_digest_enabled is False


def test_resubscribe_expired_token_renders_friendly_page(
    client: TestClient, db: Session
) -> None:
    """Past-exp token must not flip any preference."""
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    user.daily_digest_enabled = False
    db.add(user)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe",
        params={"token": _expired_unsub_token(user.id)},
    )
    assert response.status_code == 200
    text = response.text.lower()
    assert "invalid" in text or "expired" in text

    db.refresh(user)
    assert user.daily_digest_enabled is False


def test_resubscribe_is_idempotent(client: TestClient, db: Session) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    user.daily_digest_enabled = False
    db.add(user)
    db.commit()

    token = make_unsubscribe_token(user.id)
    first = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe", params={"token": token}
    )
    second = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe", params={"token": token}
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert "subscribed again" in second.text.lower()

    db.refresh(user)
    assert user.daily_digest_enabled is True


def test_resubscribe_updates_same_preference_as_settings(
    client: TestClient, db: Session
) -> None:
    """The settings API and the resubscribe endpoint mutate the same field."""
    user, headers = _create_authenticated_user(client, db)
    # Disable via the settings API.
    client.put(
        f"{settings.API_V1_STR}/users/me/digest-preferences",
        headers=headers,
        json={"daily_digest_enabled": False},
    )
    db.refresh(user)
    assert user.daily_digest_enabled is False

    # Re-enable via the public resubscribe endpoint (no auth).
    token = make_unsubscribe_token(user.id)
    response = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe",
        params={"token": token},
    )
    assert response.status_code == 200

    db.refresh(user)
    assert user.daily_digest_enabled is True


def test_unsubscribe_then_resubscribe_round_trip(
    client: TestClient, db: Session
) -> None:
    """End-to-end: the same token can unsubscribe then resubscribe."""
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    user.daily_digest_enabled = True
    db.add(user)
    db.commit()

    token = make_unsubscribe_token(user.id)

    client.get(f"{settings.API_V1_STR}/digest/unsubscribe", params={"token": token})
    db.refresh(user)
    assert user.daily_digest_enabled is False

    client.post(f"{settings.API_V1_STR}/digest/resubscribe", params={"token": token})
    db.refresh(user)
    assert user.daily_digest_enabled is True


def test_resubscribe_for_deleted_user_is_safe(client: TestClient) -> None:
    """Token outlives the account; resubscribe must not 500."""
    token = make_unsubscribe_token(uuid.uuid4())
    response = client.post(
        f"{settings.API_V1_STR}/digest/resubscribe",
        params={"token": token},
    )
    assert response.status_code == 200

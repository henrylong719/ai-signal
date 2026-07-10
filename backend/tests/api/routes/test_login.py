import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, select

from app import crud
from app.api.routes.login import OAUTH_STATE_COOKIE_NAME, OAuthIdentity
from app.core.config import settings
from app.core.security import decode_token, get_password_hash, verify_password
from app.crud import create_user
from app.models import OAuthAccount, RefreshSession, User
from app.models.base import get_datetime_utc
from app.schemas import UserCreate
from app.utils import generate_password_reset_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string

REFRESH_COOKIE_PATH = "/"
LEGACY_REFRESH_COOKIE_PATHS = (
    f"{settings.API_V1_STR}/login",
    f"{settings.API_V1_STR}/login/refresh",
)
OAUTH_STATE_COOKIE_PATH = f"{settings.API_V1_STR}/login"


def _configure_google_oauth() -> Any:
    return patch.multiple(
        "app.core.config.settings",
        GOOGLE_OAUTH_CLIENT_ID="google-client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="google-client-secret",
    )


def _configure_github_oauth() -> Any:
    return patch.multiple(
        "app.core.config.settings",
        GITHUB_OAUTH_CLIENT_ID="github-client-id",
        GITHUB_OAUTH_CLIENT_SECRET="github-client-secret",
    )


def _configure_facebook_oauth() -> Any:
    return patch.multiple(
        "app.core.config.settings",
        FACEBOOK_OAUTH_CLIENT_ID="facebook-client-id",
        FACEBOOK_OAUTH_CLIENT_SECRET="facebook-client-secret",
    )


def test_get_access_token(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_start_google_oauth_redirects_and_sets_state_cookie(
    client: TestClient,
) -> None:
    with _configure_google_oauth():
        r = client.get(
            f"{settings.API_V1_STR}/login/google",
            follow_redirects=False,
        )

    assert r.status_code == 307
    assert r.headers["location"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?"
    )
    assert "client_id=google-client-id" in r.headers["location"]
    assert "scope=openid+email+profile" in r.headers["location"]
    assert _get_set_cookie_for(r, OAUTH_STATE_COOKIE_NAME) is not None


def test_start_facebook_oauth_redirects_and_sets_state_cookie(
    client: TestClient,
) -> None:
    with _configure_facebook_oauth():
        r = client.get(
            f"{settings.API_V1_STR}/login/facebook",
            follow_redirects=False,
        )

    assert r.status_code == 307
    assert r.headers["location"].startswith("https://www.facebook.com/dialog/oauth?")
    assert "client_id=facebook-client-id" in r.headers["location"]
    assert "scope=email%2Cpublic_profile" in r.headers["location"]
    assert _get_set_cookie_for(r, OAUTH_STATE_COOKIE_NAME) is not None


def test_google_oauth_callback_creates_user_and_session(
    client: TestClient,
    db: Session,
) -> None:
    state = "valid-oauth-state"
    client.cookies.set(
        OAUTH_STATE_COOKIE_NAME,
        state,
        path=OAUTH_STATE_COOKIE_PATH,
    )
    identity = OAuthIdentity(
        provider="google",
        provider_user_id="google-user-1",
        email=random_email(),
        email_verified=True,
        display_name="Google User",
        avatar_url="https://example.com/avatar.png",
    )

    with (
        _configure_google_oauth(),
        patch(
            "app.api.routes.login._fetch_oauth_identity",
            return_value=identity,
        ),
    ):
        r = client.get(
            f"{settings.API_V1_STR}/login/google/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    assert r.status_code == 303
    assert r.headers["location"] == f"{settings.FRONTEND_HOST}/"
    assert _get_set_cookie_for(r, "access_token") is not None
    assert _get_set_cookie_for(r, "refresh_token") is not None
    assert _get_set_cookie_for(r, "is_logged_in") is not None

    user = db.exec(select(User).where(User.email == identity.email)).first()
    assert user is not None
    assert user.has_password is False
    account = db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == identity.provider_user_id,
        )
    ).first()
    assert account is not None
    assert account.user_id == user.id


def test_oauth_callback_refuses_to_link_existing_password_account(
    client: TestClient,
    db: Session,
) -> None:
    """Local emails are never verified, so auto-linking a provider identity
    to an existing password account would let whoever registered the email
    first capture the real owner's social sign-in (account pre-hijack).
    The callback must bounce to /login with an error and create nothing."""
    email = random_email()
    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Existing Password User",
            password=random_lower_string(),
            is_active=True,
            is_superuser=False,
        ),
    )
    state = "valid-github-state"
    client.cookies.set(
        OAUTH_STATE_COOKIE_NAME,
        state,
        path=OAUTH_STATE_COOKIE_PATH,
    )
    identity = OAuthIdentity(
        provider="github",
        provider_user_id="evil-or-legit-99",
        email=email,
        email_verified=True,
        display_name="GitHub User",
        avatar_url=None,
    )

    with (
        _configure_github_oauth(),
        patch(
            "app.api.routes.login._fetch_oauth_identity",
            return_value=identity,
        ),
    ):
        r = client.get(
            f"{settings.API_V1_STR}/login/github/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    assert r.status_code == 303
    assert r.headers["location"].startswith(f"{settings.FRONTEND_HOST}/login")
    assert "social_error" in r.headers["location"]
    assert _get_set_cookie_for(r, "access_token") is None
    assert _get_set_cookie_for(r, "refresh_token") is None
    account = db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == "github",
            OAuthAccount.provider_user_id == identity.provider_user_id,
        )
    ).first()
    assert account is None


def test_github_oauth_callback_links_existing_user_by_email(
    client: TestClient,
    db: Session,
) -> None:
    """Cross-provider linking is allowed only when the account already has
    a provider-*verified* OAuth link for this email — proving the address
    was confirmed by a provider, not merely parked on the account."""
    email = random_email()
    existing_user = create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Existing User",
            password=random_lower_string(),
            is_active=True,
            is_superuser=False,
        ),
    )
    existing_user.has_password = False
    db.add(existing_user)
    db.flush()
    crud.create_oauth_account(
        session=db,
        user_id=existing_user.id,
        provider="google",
        provider_user_id="google-verified-1",
        email=email,
        email_verified=True,
        display_name="Existing User",
        avatar_url=None,
    )
    db.commit()
    state = "valid-github-state"
    client.cookies.set(
        OAUTH_STATE_COOKIE_NAME,
        state,
        path=OAUTH_STATE_COOKIE_PATH,
    )
    identity = OAuthIdentity(
        provider="github",
        provider_user_id="12345",
        email=email,
        email_verified=True,
        display_name="GitHub User",
        avatar_url=None,
    )

    with (
        _configure_github_oauth(),
        patch(
            "app.api.routes.login._fetch_oauth_identity",
            return_value=identity,
        ),
    ):
        r = client.get(
            f"{settings.API_V1_STR}/login/github/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    assert r.status_code == 303
    account = db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == "github",
            OAuthAccount.provider_user_id == identity.provider_user_id,
        )
    ).first()
    assert account is not None
    assert account.user_id == existing_user.id


def test_oauth_callback_refuses_link_to_parked_email_account(
    client: TestClient,
    db: Session,
) -> None:
    """An OAuth-born account whose email was later changed (parked) to a
    victim's address — with no provider-verified link for that new email —
    must NOT capture the victim's real provider sign-in. This closes the
    PATCH /users/me email-parking bypass around the has_password gate."""
    attacker_provider_email = random_email()
    victim_email = random_email()
    attacker_user = create_user(
        session=db,
        user_create=UserCreate(
            email=attacker_provider_email,
            full_name="Attacker",
            password=random_lower_string(),
            is_active=True,
            is_superuser=False,
        ),
    )
    attacker_user.has_password = False
    db.add(attacker_user)
    db.flush()
    # Attacker's real verified link is for their own address...
    crud.create_oauth_account(
        session=db,
        user_id=attacker_user.id,
        provider="google",
        provider_user_id="attacker-google-1",
        email=attacker_provider_email,
        email_verified=True,
        display_name="Attacker",
        avatar_url=None,
    )
    # ...but they parked the victim's email on the account row itself.
    attacker_user.email = victim_email
    db.add(attacker_user)
    db.commit()

    state = "valid-github-state"
    client.cookies.set(
        OAUTH_STATE_COOKIE_NAME,
        state,
        path=OAUTH_STATE_COOKIE_PATH,
    )
    identity = OAuthIdentity(
        provider="github",
        provider_user_id="victim-github-99",
        email=victim_email,
        email_verified=True,
        display_name="Victim",
        avatar_url=None,
    )

    with (
        _configure_github_oauth(),
        patch(
            "app.api.routes.login._fetch_oauth_identity",
            return_value=identity,
        ),
    ):
        r = client.get(
            f"{settings.API_V1_STR}/login/github/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    assert r.status_code == 303
    assert r.headers["location"].startswith(f"{settings.FRONTEND_HOST}/login")
    account = db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == "github",
            OAuthAccount.provider_user_id == identity.provider_user_id,
        )
    ).first()
    assert account is None


def test_facebook_oauth_callback_creates_user_and_session(
    client: TestClient,
    db: Session,
) -> None:
    state = "valid-facebook-state"
    client.cookies.set(
        OAUTH_STATE_COOKIE_NAME,
        state,
        path=OAUTH_STATE_COOKIE_PATH,
    )
    identity = OAuthIdentity(
        provider="facebook",
        provider_user_id="facebook-user-1",
        email=random_email(),
        email_verified=True,
        display_name="Facebook User",
        avatar_url="https://example.com/facebook-avatar.png",
    )

    with (
        _configure_facebook_oauth(),
        patch(
            "app.api.routes.login._fetch_oauth_identity",
            return_value=identity,
        ),
    ):
        r = client.get(
            f"{settings.API_V1_STR}/login/facebook/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    assert r.status_code == 303
    account = db.exec(
        select(OAuthAccount).where(
            OAuthAccount.provider == "facebook",
            OAuthAccount.provider_user_id == identity.provider_user_id,
        )
    ).first()
    assert account is not None
    assert account.email_verified is True


def test_oauth_callback_rejects_invalid_state(client: TestClient) -> None:
    with (
        _configure_google_oauth(),
        patch("app.api.routes.login._fetch_oauth_identity") as fetch_identity,
    ):
        r = client.get(
            f"{settings.API_V1_STR}/login/google/callback",
            params={"code": "provider-code", "state": "bad-state"},
            follow_redirects=False,
        )

    assert r.status_code == 303
    assert r.headers["location"].startswith(f"{settings.FRONTEND_HOST}/login?")
    fetch_identity.assert_not_called()


def test_get_access_token_incorrect_password(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 400


def test_use_access_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


def test_recovery_password(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    """Password recovery routes through the Resend-based email service.

    No SMTP_* settings need to be configured anymore — the Resend
    sender is patched here so no real HTTP call is made and the
    route's call into ``send_password_reset_email`` is asserted.
    """
    from app.services.resend_email import ResendSendResult

    with patch(
        "app.api.routes.login.send_password_reset_email",
        return_value=ResendSendResult(ok=True, message_id="mid"),
    ) as mock_send:
        email = "test@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link"
        }
        assert mock_send.called
        assert mock_send.call_args.kwargs["email_to"] == email
        assert isinstance(mock_send.call_args.kwargs["token"], str)


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    """Generic 200 response even when the email isn't registered."""
    from app.services.resend_email import ResendSendResult

    with patch(
        "app.api.routes.login.send_password_reset_email",
        return_value=ResendSendResult(ok=True, message_id="mid"),
    ) as mock_send:
        email = "jVgQr@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        # Should return 200 with generic message to prevent email enumeration
        # attacks. No send is attempted because there's no matching user.
        assert r.status_code == 200
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link"
        }
        assert not mock_send.called


def test_recovery_password_safe_when_resend_misconfigured(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Missing RESEND_API_KEY must not crash the recovery endpoint.

    The send returns ``ok=False`` from the service layer; the route
    logs and still returns the same generic message so the response
    body cannot be used to fingerprint deliverability state.
    """
    from app.crud import create_user
    from app.schemas import UserCreate

    email = random_email()
    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            password=random_lower_string(),
            full_name="Recovery Misconfig",
        ),
    )

    with patch("app.core.config.settings.RESEND_API_KEY", None):
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link"
        }


def test_reset_password(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        full_name="Test User",
        password=password,
        is_active=True,
        is_superuser=False,
    )
    user = create_user(session=db, user_create=user_create)
    token = generate_password_reset_token(
        email=email, hashed_password=user.hashed_password
    )
    headers = user_authentication_headers(client=client, email=email, password=password)
    data = {"new_password": new_password, "token": token}

    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=headers,
        json=data,
    )

    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    db.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified


def test_reset_password_token_is_single_use(client: TestClient, db: Session) -> None:
    """A reset token must die with the password it was issued against.
    Replaying a used token (leaked email, forwarded link) must not let
    anyone reset the password a second time."""
    email = random_email()
    first_new_password = random_lower_string()
    second_new_password = random_lower_string()
    user = create_user(
        session=db,
        user_create=UserCreate(email=email, password=random_lower_string()),
    )
    token = generate_password_reset_token(
        email=email, hashed_password=user.hashed_password
    )

    first = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        json={"new_password": first_new_password, "token": token},
    )
    assert first.status_code == 200

    replay = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        json={"new_password": second_new_password, "token": token},
    )
    assert replay.status_code == 400
    assert replay.json()["detail"] == "Invalid token"

    db.refresh(user)
    verified, _ = verify_password(first_new_password, user.hashed_password)
    assert verified


def test_reset_password_rejects_token_without_reset_type(
    client: TestClient, db: Session
) -> None:
    """Only tokens carrying the password-reset type claim may reset a
    password — an untyped (legacy-shaped) JWT with a matching sub must
    be rejected so no other signed token can be confused into this path."""
    import jwt as pyjwt

    email = random_email()
    user = create_user(
        session=db,
        user_create=UserCreate(email=email, password=random_lower_string()),
    )
    del user
    untyped_token = pyjwt.encode(
        {
            "exp": get_datetime_utc() + timedelta(hours=1),
            "nbf": get_datetime_utc(),
            "sub": email,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )

    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        json={"new_password": random_lower_string(), "token": untyped_token},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid token"


def test_reset_password_invalid_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=superuser_token_headers,
        json=data,
    )
    response = r.json()

    assert "detail" in response
    assert r.status_code == 400
    assert response["detail"] == "Invalid token"


def test_login_with_bcrypt_password_upgrades_to_argon2(
    client: TestClient, db: Session
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.hashed_password.startswith("$2")

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    # Verify the hash was upgraded to argon2
    assert user.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user.hashed_password)
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None


def test_login_with_argon2_password_keeps_hash(client: TestClient, db: Session) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    # Create an argon2 hash (current default)
    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    # Create user with argon2 hash
    user = User(email=email, hashed_password=argon2_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    original_hash = user.hashed_password

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    assert user.hashed_password == original_hash
    assert user.hashed_password.startswith("$argon2")


# ---------------------------------------------------------------------------
# Cookie-based session flow
# ---------------------------------------------------------------------------
#
# These tests verify the cookie auth path the SPA actually uses: login sets
# httpOnly cookies, protected endpoints accept the cookie, refresh rotates
# the tokens, logout clears them. The earlier tests above continue to use
# the JSON-token + Bearer-header path because that path remains valid for
# CLI / service-to-service callers.


def _get_set_cookie_for(response: object, name: str) -> str | None:
    """Return the raw Set-Cookie header value for ``name``, or None.

    Inspecting attributes (HttpOnly, Path, SameSite) requires the raw header
    string — TestClient's ``response.cookies`` only exposes parsed values.
    """
    headers: list[str] = response.headers.get_list("set-cookie")  # type: ignore[attr-defined]
    for raw in headers:
        if raw.split("=", 1)[0] == name:
            return raw
    return None


def _get_set_cookies_for(response: object, name: str) -> list[str]:
    headers: list[str] = response.headers.get_list("set-cookie")  # type: ignore[attr-defined]
    return [raw for raw in headers if raw.split("=", 1)[0] == name]


def _plant_refresh_cookie(client: TestClient, token: str) -> None:
    client.cookies.delete("refresh_token", path=REFRESH_COOKIE_PATH)
    client.cookies.set("refresh_token", token, path=REFRESH_COOKIE_PATH)


def test_login_sets_three_cookies_with_correct_attributes(
    client: TestClient,
) -> None:
    """The login endpoint must set access, refresh, and is_logged_in cookies."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200

    access_cookie = _get_set_cookie_for(r, "access_token")
    refresh_cookie = _get_set_cookie_for(r, "refresh_token")
    marker_cookie = _get_set_cookie_for(r, "is_logged_in")

    assert access_cookie is not None
    assert refresh_cookie is not None
    assert marker_cookie is not None

    # Access cookie — httpOnly so JS can't read it; site-wide path.
    assert "HttpOnly" in access_cookie
    assert "Path=/" in access_cookie
    assert "samesite=lax" in access_cookie.lower()

    # Refresh cookie — also httpOnly, set at the root path. Earlier deploys
    # scoped it under /api/v1/login as defense in depth, but iOS WebKit
    # refused to store narrow-path cookies on OAuth-callback responses, so
    # the cookie now lives at /. The JWT type=refresh claim still prevents
    # the token from being usable as an access token.
    assert "HttpOnly" in refresh_cookie
    assert f"Path={REFRESH_COOKIE_PATH}" in refresh_cookie
    # The login response must NOT emit paired Max-Age=0 Set-Cookies for the
    # legacy paths. iOS WebKit clobbers paired Set-Cookie headers that share
    # a name in the same response, dropping the just-set cookie. Legacy
    # stragglers are cleaned up on the next logout instead.
    legacy_set_cookies = [
        cookie_header
        for cookie_header in _get_set_cookies_for(r, "refresh_token")
        if any(
            f"Path={legacy}" in cookie_header for legacy in LEGACY_REFRESH_COOKIE_PATHS
        )
    ]
    assert legacy_set_cookies == []

    # Marker cookie — explicitly NOT httpOnly because the SPA reads it for
    # UI state. Has no security significance to the server.
    assert "HttpOnly" not in marker_cookie
    assert "Path=/" in marker_cookie


def test_protected_endpoint_accepts_cookie_auth(client: TestClient) -> None:
    """Once logged in, a request with no Authorization header but the
    access_token cookie should authenticate. This is the production path
    for the SPA, where the token never touches JavaScript."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200

    # No Authorization header — TestClient sends cookies automatically.
    r = fresh.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 200
    assert r.json()["email"] == settings.FIRST_SUPERUSER


def test_unauthenticated_request_returns_401(client: TestClient) -> None:
    """Auth failures must be 401, not 403. The SPA's refresh interceptor
    watches for 401 specifically — 403 means 'authenticated but not
    permitted' and is reserved for privilege checks."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    r = fresh.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 401


def test_deleted_user_token_returns_401(client: TestClient, db: Session) -> None:
    """A valid access token whose user row no longer exists must yield 401,
    not 404 — the SPA's refresh interceptor only reacts to 401, so any
    other status leaves the user stuck in a broken logged-in state."""
    email = random_email()
    password = random_lower_string()
    user = create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )
    headers = user_authentication_headers(client=client, email=email, password=password)

    db.delete(user)
    db.commit()

    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 401


def test_inactive_user_token_returns_401(client: TestClient, db: Session) -> None:
    """A valid access token for a deactivated user must yield 401, not 400,
    for the same interceptor-contract reason as the deleted-user case."""
    email = random_email()
    password = random_lower_string()
    user = create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )
    headers = user_authentication_headers(client=client, email=email, password=password)

    user.is_active = False
    db.add(user)
    db.commit()

    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 401


def test_refresh_without_cookie_returns_401(client: TestClient) -> None:
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401


def test_refresh_rotates_session(client: TestClient) -> None:
    """Each successful refresh must issue fresh access + refresh + marker
    cookies. Rotation means a stolen refresh token has limited useful life:
    the legitimate user's next refresh overwrites the cookie."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    original_access = fresh.cookies.get("access_token")
    original_refresh = fresh.cookies.get("refresh_token")
    assert original_access and original_refresh

    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 200
    rotated_refresh = fresh.cookies.get("refresh_token")
    assert _get_set_cookie_for(r, "access_token") is not None
    assert _get_set_cookie_for(r, "refresh_token") is not None
    assert rotated_refresh and rotated_refresh != original_refresh

    # The protected endpoint should still work with the rotated cookies.
    r = fresh.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 200


def test_refresh_allows_immediate_previous_token_without_extending_refresh_cookie(
    client: TestClient,
) -> None:
    """A tiny grace window prevents multi-tab refresh races from logging out
    the user, but the previous token cannot extend the refresh session."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    original_refresh = fresh.cookies.get("refresh_token")
    assert original_refresh

    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 200

    _plant_refresh_cookie(fresh, original_refresh)
    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 200
    assert _get_set_cookie_for(r, "access_token") is not None
    assert _get_set_cookie_for(r, "refresh_token") is None


def test_refresh_rejects_stale_token_after_rotation_grace(
    client: TestClient, db: Session
) -> None:
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    original_refresh = fresh.cookies.get("refresh_token")
    assert original_refresh

    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 200
    rotated_refresh = fresh.cookies.get("refresh_token")
    assert rotated_refresh

    payload = decode_token(original_refresh, expected_type="refresh")
    db_refresh_session = db.get(RefreshSession, uuid.UUID(str(payload["sid"])))
    assert db_refresh_session
    db_refresh_session.previous_token_valid_until = get_datetime_utc() - timedelta(
        seconds=1
    )
    db.add(db_refresh_session)
    db.commit()

    _plant_refresh_cookie(fresh, original_refresh)
    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401

    _plant_refresh_cookie(fresh, rotated_refresh)
    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401


def test_refresh_rejects_access_token_in_refresh_slot(client: TestClient) -> None:
    """Type-claim defense: an access token presented as a refresh token
    must be rejected. Without this check, anyone who exfiltrated the
    access cookie (despite httpOnly) could mint new sessions indefinitely."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    access_token = fresh.cookies.get("access_token")
    assert access_token

    # Plant the access token into the refresh cookie slot.
    _plant_refresh_cookie(fresh, access_token)

    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401


def test_logout_clears_all_three_cookies(client: TestClient) -> None:
    """Logout must explicitly clear all three cookies. Because cookies are
    scoped to a path, the delete must use the same path used to set them
    or the browser keeps the original."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    original_refresh = fresh.cookies.get("refresh_token")
    assert fresh.cookies.get("access_token")
    assert original_refresh

    r = fresh.post(f"{settings.API_V1_STR}/login/logout")
    assert r.status_code == 200

    # Each cookie should have a Max-Age=0 entry, which is how the browser
    # signals deletion.
    for name, expected_path in [
        ("access_token", "/"),
        ("refresh_token", REFRESH_COOKIE_PATH),
        ("is_logged_in", "/"),
    ]:
        cookie_header = _get_set_cookie_for(r, name)
        assert cookie_header is not None, f"{name} not cleared"
        assert "Max-Age=0" in cookie_header, f"{name} not deleted (Max-Age != 0)"
        assert f"Path={expected_path}" in cookie_header, (
            f"{name} cleared with wrong path"
        )
    refresh_set_cookies = _get_set_cookies_for(r, "refresh_token")
    for legacy_path in LEGACY_REFRESH_COOKIE_PATHS:
        assert any(
            f"Path={legacy_path}" in cookie_header and "Max-Age=0" in cookie_header
            for cookie_header in refresh_set_cookies
        ), f"legacy refresh cookie at {legacy_path} not cleared on logout"

    # Subsequent protected request should now 401.
    r = fresh.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 401

    # The server-side refresh session was revoked too; replaying the old
    # refresh cookie cannot mint another session.
    _plant_refresh_cookie(fresh, original_refresh)
    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401


def test_password_change_revokes_refresh_sessions(
    client: TestClient, db: Session
) -> None:
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    email = random_email()
    password = random_lower_string()
    user_create = UserCreate(email=email, password=password)
    create_user(session=db, user_create=user_create)

    r = fresh.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200
    original_refresh = fresh.cookies.get("refresh_token")
    assert original_refresh

    r = fresh.patch(
        f"{settings.API_V1_STR}/users/me/password",
        json={"current_password": password, "new_password": f"{password}1"},
    )
    assert r.status_code == 200

    _plant_refresh_cookie(fresh, original_refresh)
    r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401


@contextmanager
def _rate_limit_enabled() -> Any:
    """Temporarily enable the shared limiter (tests run with it disabled)."""
    from app.core.rate_limit import limiter

    original_enabled = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    try:
        yield
    finally:
        limiter.enabled = original_enabled
        limiter.reset()


def test_login_endpoint_is_rate_limited(client: TestClient) -> None:
    """Credential stuffing defense: repeated login attempts from one
    bucket must hit a 429 instead of allowing unlimited guesses."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    login_data = {"username": random_email(), "password": random_lower_string()}
    with _rate_limit_enabled():
        for _ in range(10):
            r = fresh.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
            assert r.status_code == 400
        blocked = fresh.post(
            f"{settings.API_V1_STR}/login/access-token", data=login_data
        )
    assert blocked.status_code == 429


def test_password_recovery_endpoint_is_rate_limited(client: TestClient) -> None:
    """Each call can trigger a real email — unlimited calls mean email
    bombing a victim and burning Resend quota."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    email = random_email()
    with _rate_limit_enabled():
        for _ in range(5):
            r = fresh.post(f"{settings.API_V1_STR}/password-recovery/{email}")
            assert r.status_code == 200
        blocked = fresh.post(f"{settings.API_V1_STR}/password-recovery/{email}")
    assert blocked.status_code == 429


def test_reset_password_endpoint_is_rate_limited(client: TestClient) -> None:
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    body = {"new_password": random_lower_string(), "token": "invalid"}
    with _rate_limit_enabled():
        for _ in range(10):
            r = fresh.post(f"{settings.API_V1_STR}/reset-password/", json=body)
            assert r.status_code == 400
        blocked = fresh.post(f"{settings.API_V1_STR}/reset-password/", json=body)
    assert blocked.status_code == 429


def test_logout_is_idempotent_when_not_logged_in(client: TestClient) -> None:
    """Calling logout without being logged in must not error — it's a no-op
    that just sets clearing headers. This matters because the SPA may call
    logout in error-recovery paths where session state is uncertain."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    r = fresh.post(f"{settings.API_V1_STR}/login/logout")
    assert r.status_code == 200

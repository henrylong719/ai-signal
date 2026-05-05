from unittest.mock import patch

from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.crud import create_user
from app.models import User
from app.schemas import UserCreate
from app.utils import generate_password_reset_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


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
    with (
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
    ):
        email = "test@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link"
        }


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "jVgQr@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    # Should return 200 with generic message to prevent email enumeration attacks
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
    token = generate_password_reset_token(email=email)
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

    # Refresh cookie — also httpOnly, but path-scoped to the refresh
    # endpoint only. This is defense in depth: the browser will never send
    # this cookie to any other endpoint.
    assert "HttpOnly" in refresh_cookie
    assert "Path=/api/v1/login/refresh" in refresh_cookie

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
    # Rotation: the new cookies must be different from the old ones.
    # (Content differs because the iat/exp claims are fresh.)
    assert _get_set_cookie_for(r, "access_token") is not None
    assert _get_set_cookie_for(r, "refresh_token") is not None

    # The protected endpoint should still work with the rotated cookies.
    r = fresh.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 200


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
    fresh.cookies.delete("refresh_token", path="/api/v1/login/refresh")
    fresh.cookies.set("refresh_token", access_token, path="/api/v1/login/refresh")

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
    assert fresh.cookies.get("access_token")

    r = fresh.post(f"{settings.API_V1_STR}/login/logout")
    assert r.status_code == 200

    # Each cookie should have a Max-Age=0 entry, which is how the browser
    # signals deletion.
    for name, expected_path in [
        ("access_token", "/"),
        ("refresh_token", "/api/v1/login/refresh"),
        ("is_logged_in", "/"),
    ]:
        cookie_header = _get_set_cookie_for(r, name)
        assert cookie_header is not None, f"{name} not cleared"
        assert "Max-Age=0" in cookie_header, f"{name} not deleted (Max-Age != 0)"
        assert f"Path={expected_path}" in cookie_header, (
            f"{name} cleared with wrong path"
        )

    # Subsequent protected request should now 401.
    r = fresh.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 401


def test_logout_is_idempotent_when_not_logged_in(client: TestClient) -> None:
    """Calling logout without being logged in must not error — it's a no-op
    that just sets clearing headers. This matters because the SPA may call
    logout in error-recovery paths where session state is uncertain."""
    fresh = TestClient(client.app)  # type: ignore[arg-type]
    r = fresh.post(f"{settings.API_V1_STR}/login/logout")
    assert r.status_code == 200

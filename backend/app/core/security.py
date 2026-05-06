import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


ALGORITHM = "HS256"

# Token kinds carried in the JWT's ``type`` claim. Checked by the auth
# dependency: presenting a refresh token in the access cookie slot (or
# vice versa) is rejected. Without this, anyone who steals the refresh
# cookie could use it as an access token directly.
TokenType = Literal["access", "refresh"]


def _create_token(
    *,
    subject: str | Any,
    expires_delta: timedelta,
    token_type: TokenType,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Encode a JWT with ``sub``, ``exp``, and ``type`` claims.

    Centralized so the claim shape and signing parameters can't drift
    between access and refresh tokens.
    """
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"exp": expire, "sub": str(subject), "type": token_type}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """Short-lived JWT used to authenticate API requests."""
    return _create_token(
        subject=subject, expires_delta=expires_delta, token_type="access"
    )


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    *,
    session_id: str | Any,
    token_id: str,
) -> str:
    """Long-lived JWT presented to the refresh endpoint to mint new access tokens.

    Defaults to ``settings.REFRESH_TOKEN_EXPIRE_DAYS`` if no delta is given.
    The refresh token's only valid use is calling /login/refresh; the path
    scoping on the refresh cookie enforces this at the browser level, and
    the ``type`` claim enforces it at the application level.
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(
        subject=subject,
        expires_delta=expires_delta,
        token_type="refresh",
        extra_claims={"sid": str(session_id), "jti": token_id},
    )


def generate_refresh_token_id() -> str:
    return secrets.token_urlsafe(32)


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Verify a JWT and assert its ``type`` claim matches.

    Raises ``jwt.InvalidTokenError`` (or a subclass) on any failure: bad
    signature, expired, or wrong type. Callers should catch the base class
    and convert to whatever the calling layer needs (HTTP 401, return None,
    etc.).
    """
    payload: dict[str, Any] = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[ALGORITHM]
    )
    if payload.get("type") != expected_type:
        # InvalidTokenError is the right base class — same handler path as
        # other JWT-validation failures, no need for a separate exception.
        raise jwt.InvalidTokenError(f"Token type mismatch: expected {expected_type!r}")
    return payload


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

"""Authentication dependencies.

Tokens are accepted from two places, in order of priority:

  1. The ``access_token`` cookie (set by /login/access-token, used by the SPA).
  2. The ``Authorization: Bearer ...`` header (used by the test suite, by
     CLI tools, and as a fallback for non-browser clients).

Both forms validate the same JWT and produce identical security properties.
The cookie path is preferred because it's the only one that survives plain
``<a href>`` navigations (see app/api/routes/article.py:go_to_article) and
because it's resistant to XSS exfiltration thanks to ``HttpOnly``.

Auth-failure status code is 401, not 403. 401 means "no valid credentials
presented" — which is what the frontend's refresh interceptor watches for.
403 is reserved for "credentials are valid but insufficient privileges"
(see ``get_current_active_superuser``).
"""

import logging
from collections.abc import Generator
from datetime import timedelta
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.cookies import ACCESS_COOKIE_NAME
from app.core.db import engine
from app.models import User
from app.models.base import get_datetime_utc

logger = logging.getLogger(__name__)

# How stale ``user.last_seen_at`` must be before we write a fresh
# timestamp on the next authenticated request. Bounded write rate is
# ~12/hour per active user worst case — invisible to admins while
# keeping the DB cost negligible.
LAST_SEEN_REFRESH_INTERVAL = timedelta(minutes=5)

# auto_error=False on both: we resolve the token manually (cookie OR header)
# rather than letting OAuth2PasswordBearer raise on missing header. The
# tokenUrl is still here so the OpenAPI docs render a working "Authorize"
# button, even though browser auth uses the cookie.
_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


def _resolve_token(
    cookie_token: str | None,
    header_token: str | None,
) -> str | None:
    """Cookie wins over header. Either is acceptable; neither is fine too."""
    return cookie_token or header_token


def _touch_last_seen(session: Session, user: User) -> None:
    """Refresh ``user.last_seen_at`` if it is older than the throttle window.

    Best-effort: a failed write must never block authentication, so any
    DB error is swallowed and logged. The next request will retry.
    """
    now = get_datetime_utc()
    if (
        user.last_seen_at is not None
        and now - user.last_seen_at < LAST_SEEN_REFRESH_INTERVAL
    ):
        return
    user.last_seen_at = now
    try:
        session.add(user)
        session.commit()
    except SQLAlchemyError:
        logger.exception("Failed to update last_seen_at for user %s", user.id)
        session.rollback()


def get_current_user(
    session: SessionDep,
    cookie_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
    header_token: Annotated[str | None, Depends(_oauth2_scheme)] = None,
) -> User:
    """Required-auth dependency. Raises 401 on any auth failure."""
    token = _resolve_token(cookie_token, header_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = security.decode_token(token, expected_type="access")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = session.get(User, subject)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    _touch_last_seen(session, user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    session: SessionDep,
    cookie_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
    header_token: Annotated[str | None, Depends(_oauth2_scheme)] = None,
) -> User | None:
    """Optional-auth variant for endpoints that work either way (e.g., the
    click redirect). Never raises — returns None on any auth failure so the
    handler can decide whether to log on behalf of the user.
    """
    token = _resolve_token(cookie_token, header_token)
    if not token:
        return None
    try:
        payload = security.decode_token(token, expected_type="access")
    except jwt.InvalidTokenError:
        return None
    subject = payload.get("sub")
    if not subject:
        return None
    user = session.get(User, subject)
    if not user or not user.is_active:
        return None
    _touch_last_seen(session, user)
    return user


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    """Privilege check, distinct from authentication. Returns 403 (the user
    is logged in, just not allowed to do this) — different from 401 above.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

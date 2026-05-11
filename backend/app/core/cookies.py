"""Cookie attribute helpers for authentication.

All cookie attribute decisions live here so they can't drift across
endpoints. Three cookies are managed:

  - ``access_token``  : httpOnly JWT, sent to all /api/* requests, short TTL
  - ``refresh_token`` : httpOnly JWT, scoped to /api/v1/login auth endpoints,
                        long TTL. Path-scoping is defense in depth — the
                        browser never sends the refresh cookie to non-login
                        API endpoints, while logout can still revoke it.
  - ``is_logged_in``  : NON-httpOnly marker, readable by JS purely as a UI
                        hint. Has no security significance — the server
                        never trusts it for authorization, only the real
                        access cookie does.

Cookie security choices:
  - ``SameSite`` is environment-dependent. Local dev runs the frontend and
    backend on the same host (``localhost``) so ``Lax`` is enough and avoids
    requiring HTTPS. Deployed environments host the frontend and backend on
    different registrable domains (Vercel ↔ Railway), which makes every
    API call cross-site — those need ``SameSite=None`` or the browser will
    refuse to send the cookies. ``None`` requires ``Secure``, which we set
    in the same branch.
  - ``Secure`` flag only in non-local environments. Browsers refuse to send
    Secure cookies over plain HTTP, which would break local dev where the
    backend runs on ``http://localhost``.
  - No ``Domain`` set. Defaults to "host that issued the cookie", which is
    correct here — we don't need cross-subdomain sharing.
"""

from typing import Final, Literal

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE_NAME: Final = "access_token"
REFRESH_COOKIE_NAME: Final = "refresh_token"
LOGGED_IN_MARKER_NAME: Final = "is_logged_in"

# Refresh cookie is only sent to login auth endpoints. This lets /login/logout
# revoke the exact DB-backed refresh session while still keeping the refresh
# token away from the rest of the API surface.
_REFRESH_COOKIE_PATH: Final = f"{settings.API_V1_STR}/login"
_LEGACY_REFRESH_COOKIE_PATH: Final = f"{settings.API_V1_STR}/login/refresh"
_DEFAULT_COOKIE_PATH: Final = "/"


def _is_secure() -> bool:
    """Whether to mark cookies Secure. False for local dev so HTTP works."""
    return settings.ENVIRONMENT != "local"


def _samesite() -> Literal["lax", "none"]:
    """SameSite attribute. ``none`` for deployed envs where the frontend
    and backend live on different registrable domains and every API call
    is cross-site; ``lax`` for local dev where they share ``localhost``.
    """
    return "none" if settings.ENVIRONMENT != "local" else "lax"


def set_access_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    """Set the short-lived access cookie used by every authenticated request."""
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        path=_DEFAULT_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite=_samesite(),
    )


def set_refresh_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    """Set the long-lived refresh cookie, scoped to login auth endpoints."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        path=_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite=_samesite(),
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=_LEGACY_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite=_samesite(),
    )


def set_logged_in_marker(response: Response, max_age_seconds: int) -> None:
    """Set the non-httpOnly marker cookie used by the frontend for UI state.

    ``httponly=False`` is intentional. The contents (literally "1") have no
    security meaning — the server never reads or trusts this cookie. It
    exists so the SPA can render its login state on first paint without
    waiting for a /users/me probe.
    """
    response.set_cookie(
        key=LOGGED_IN_MARKER_NAME,
        value="1",
        max_age=max_age_seconds,
        path=_DEFAULT_COOKIE_PATH,
        secure=_is_secure(),
        httponly=False,
        samesite=_samesite(),
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear all three auth cookies — used by the logout endpoint.

    The cookie path on a delete must match the path that was used when
    setting it, otherwise the browser treats them as different cookies and
    the original survives. That's why we explicitly pass the path here.
    """
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path=_DEFAULT_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite=_samesite(),
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite=_samesite(),
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=_LEGACY_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite=_samesite(),
    )
    response.delete_cookie(
        key=LOGGED_IN_MARKER_NAME,
        path=_DEFAULT_COOKIE_PATH,
        secure=_is_secure(),
        httponly=False,
        samesite=_samesite(),
    )

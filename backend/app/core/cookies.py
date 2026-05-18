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
   - ``SameSite=Lax`` on all three. Blocks cross-site POST CSRF (the classic
    attack) while still allowing top-level link navigations from external
    sites, which we want for OAuth callbacks and emailed links. We also
    don't have any state-changing GETs, which is the one remaining surface
    SameSite=Lax doesn't cover.


  - ``Secure`` flag only in non-local environments. Browsers refuse to send
    Secure cookies over plain HTTP, which would break local dev where the
    backend runs on ``http://localhost``.
  - No ``Domain`` set. Defaults to "host that issued the cookie", which is
    correct here — we don't need cross-subdomain sharing.
"""

from typing import Final

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


def set_access_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    """Set the short-lived access cookie used by every authenticated request."""
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        path=_DEFAULT_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite="lax",
    )


def set_refresh_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    """Set the long-lived refresh cookie, scoped to login auth endpoints.

    We deliberately do NOT also emit a Max-Age=0 Set-Cookie for the legacy
    narrow path here. iOS WebKit (Safari, and every iOS third-party browser
    since they all use WKWebView) has a bug where two ``Set-Cookie`` headers
    sharing a name in the same response clobber each other by name alone,
    ignoring the differing Path. The result is that the just-set refresh
    cookie is never stored on iPhone. The legacy cookie is cleared on the
    next logout instead (see ``clear_auth_cookies``); any straggler at the
    old path is harmless because Starlette's cookie parser keeps the last
    value when the request carries duplicates, which is the new token.
    """
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        path=_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite="lax",
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
        samesite="lax",
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
        samesite="lax",
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=_LEGACY_REFRESH_COOKIE_PATH,
        secure=_is_secure(),
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=LOGGED_IN_MARKER_NAME,
        path=_DEFAULT_COOKIE_PATH,
        secure=_is_secure(),
        httponly=False,
        samesite="lax",
    )

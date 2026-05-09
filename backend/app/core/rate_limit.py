"""Rate limiting setup.

Per-route quotas implemented with ``slowapi``. The shared ``limiter``
exported here is the one route handlers decorate; it is also wired into
the FastAPI app in ``app.main`` (state, exception handler, middleware).

Key strategy
------------
Authenticated users are limited by user id (decoded from the JWT in the
``access_token`` cookie or the ``Authorization: Bearer`` header). The
key function does *not* hit the database — it only verifies the JWT
signature and reads the ``sub`` claim, so it stays cheap enough to run
on every request without affecting steady-state latency. Anonymous
requests fall back to ``X-Forwarded-For`` / ``REMOTE_ADDR`` via
``slowapi.util.get_remote_address``.

Storage
-------
Default backend is in-process memory. That is adequate for the current
single-worker deployment (see the comment in ``services/embeddings.py``
about the embedding model load and ``--workers 1``). For multi-worker
production, set ``RATE_LIMIT_STORAGE_URI=redis://host:port`` so the
limits are shared across workers; otherwise a user could trivially
multiply their effective limit by the worker count.

Configuration
-------------
- ``RATE_LIMIT_ENABLED`` (bool, default ``True``): turn the limiter
  off entirely. Tests set this to ``False`` so they don't hit 429s.
- ``RATE_LIMIT_STORAGE_URI`` (str | None, default ``None``): pass-through
  to slowapi. ``None`` = in-memory; ``redis://...`` = shared backend.
"""

from __future__ import annotations

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core import security
from app.core.config import settings
from app.core.cookies import ACCESS_COOKIE_NAME


def _user_id_from_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = security.decode_token(token, expected_type="access")
    except jwt.InvalidTokenError:
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if not auth:
        return None
    scheme, _, value = auth.partition(" ")
    return value if scheme.lower() == "bearer" and value else None


def rate_limit_key(request: Request) -> str:
    """Per-request bucket key: ``user:<id>`` when authenticated, else ``ip:<addr>``.

    Cookie wins over header (mirrors ``api.deps._resolve_token``) so the
    SPA path is the one that decides the bucket. We never DB-lookup the
    user here — JWT verification + ``sub`` is enough to make the key
    stable across the token's lifetime.
    """
    cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
    user_id = _user_id_from_token(cookie_token) or _user_id_from_token(
        _bearer_token(request)
    )
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


# Shared limiter used by route decorators. ``enabled`` is read at module-load
# time; tests flip the env var before importing the app to keep the limiter
# from rejecting their hot loops.
#
# ``headers_enabled`` is False because the X-RateLimit-* headers slowapi
# would inject on success require either a ``response: Response`` parameter
# on every limited route or for handlers to return a Response object. None
# of our article routes currently do — they return SQLModel/Pydantic schemas
# that FastAPI serializes downstream. The Retry-After header on 429
# responses is added by ``_rate_limit_exceeded_handler`` regardless of this
# flag, so the production-required behavior (proper 429 + Retry-After) is
# unaffected.
limiter = Limiter(
    key_func=rate_limit_key,
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    headers_enabled=False,
)

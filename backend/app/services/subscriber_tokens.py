"""Signed tokens for anonymous digest subscribers.

Mirrors the user-facing ``digest-unsub`` token in ``digest_email.py`` but
keyed by ``DigestSubscriber.id`` and carrying its own ``type`` claim so it
can never be presented on the auth path or confused with the user
unsubscribe token. Possession of the signed token is the authorization for
the (no-auth) unsubscribe endpoint — the subscriber has no account to log
in with.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core import security
from app.core.config import settings

# Distinct from ``digest-unsub`` (user path) and every auth token type.
_UNSUB_TOKEN_TYPE = "subscriber-unsub"
# Long TTL: the link travels in the subscriber's mailbox archive and must
# keep working well past any session lifetime. Matches the user unsub token.
_UNSUB_TOKEN_TTL = timedelta(days=30)


def make_subscriber_unsubscribe_token(subscriber_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + _UNSUB_TOKEN_TTL
    return jwt.encode(
        {
            "sub": str(subscriber_id),
            "exp": expire,
            "type": _UNSUB_TOKEN_TYPE,
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )


def parse_subscriber_unsubscribe_token(token: str) -> uuid.UUID | None:
    """Return the subscriber id, or None on any failure (bad signature,
    expired, wrong type, malformed subject) so the caller can render a
    generic page without leaking which failure occurred."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != _UNSUB_TOKEN_TYPE:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return uuid.UUID(str(sub))
    except (ValueError, TypeError):
        return None

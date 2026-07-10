"""Tests for subscriber unsubscribe tokens."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core import security
from app.core.config import settings
from app.services import subscriber_tokens


def test_unsubscribe_token_round_trips() -> None:
    subscriber_id = uuid.uuid4()
    token = subscriber_tokens.make_subscriber_unsubscribe_token(subscriber_id)
    assert subscriber_tokens.parse_subscriber_unsubscribe_token(token) == subscriber_id


def test_parse_rejects_wrong_token_type() -> None:
    """A JWT signed with the same key but a different type claim must not
    be accepted — keeps this token off the auth and digest-unsub paths."""
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
        "type": "digest-unsub",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=security.ALGORITHM)
    assert subscriber_tokens.parse_subscriber_unsubscribe_token(token) is None


def test_parse_rejects_tampered_token() -> None:
    token = subscriber_tokens.make_subscriber_unsubscribe_token(uuid.uuid4())
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    assert subscriber_tokens.parse_subscriber_unsubscribe_token(tampered) is None


def test_parse_rejects_expired_token() -> None:
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
        "type": "subscriber-unsub",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=security.ALGORITHM)
    assert subscriber_tokens.parse_subscriber_unsubscribe_token(token) is None


def test_parse_rejects_malformed_subject() -> None:
    payload = {
        "sub": "not-a-uuid",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
        "type": "subscriber-unsub",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=security.ALGORITHM)
    assert subscriber_tokens.parse_subscriber_unsubscribe_token(token) is None

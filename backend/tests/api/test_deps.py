"""Tests for the auth dependencies' failure paths.

The happy paths are covered indirectly by every authenticated route test.
What is not exercised there is what happens when a token is malformed,
carries no subject, or names a user who no longer exists — and the
distinction that matters is that `get_current_user` raises 401 for all of
them while `get_optional_user` quietly returns None, so anonymous
browsing never 401s on a stale cookie.
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.api import deps
from app.models import User


def test_get_current_user_rejects_a_missing_token() -> None:
    with pytest.raises(HTTPException) as excinfo:
        deps.get_current_user(session=None, cookie_token=None, header_token=None)  # type: ignore[arg-type]

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"


def test_get_current_user_rejects_a_malformed_token() -> None:
    with pytest.raises(HTTPException) as excinfo:
        deps.get_current_user(
            session=None,  # type: ignore[arg-type]
            cookie_token="not-a-jwt",
            header_token=None,
        )

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Could not validate credentials"


def test_get_current_user_rejects_a_token_with_no_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        deps.security,
        "decode_token",
        lambda _token, expected_type: {"type": expected_type},
    )

    with pytest.raises(HTTPException) as excinfo:
        deps.get_current_user(
            session=None,  # type: ignore[arg-type]
            cookie_token="whatever",
            header_token=None,
        )

    assert excinfo.value.status_code == 401


def test_get_optional_user_returns_none_for_a_missing_token() -> None:
    assert (
        deps.get_optional_user(session=None, cookie_token=None, header_token=None)  # type: ignore[arg-type]
        is None
    )


def test_get_optional_user_returns_none_for_a_malformed_token() -> None:
    """A stale or corrupt cookie must not 401 an anonymous visitor."""
    assert (
        deps.get_optional_user(
            session=None,  # type: ignore[arg-type]
            cookie_token="not-a-jwt",
            header_token=None,
        )
        is None
    )


def test_get_optional_user_returns_none_when_token_has_no_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        deps.security,
        "decode_token",
        lambda _token, expected_type: {"type": expected_type},
    )

    assert (
        deps.get_optional_user(
            session=None,  # type: ignore[arg-type]
            cookie_token="whatever",
            header_token=None,
        )
        is None
    )


def test_get_optional_user_returns_none_for_an_unknown_user(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid token for a since-deleted user resolves to anonymous."""
    monkeypatch.setattr(
        deps.security,
        "decode_token",
        lambda _token, expected_type: {"sub": str(uuid.uuid4())},
    )

    assert (
        deps.get_optional_user(
            session=db,
            cookie_token="whatever",
            header_token=None,
        )
        is None
    )


def test_touch_last_seen_swallows_db_errors() -> None:
    """last_seen_at is telemetry; a write failure must not break the request."""
    rolled_back = False

    class _FailingSession:
        def add(self, _obj: object) -> None:
            pass

        def commit(self) -> None:
            raise SQLAlchemyError("db gone")

        def rollback(self) -> None:
            nonlocal rolled_back
            rolled_back = True

    user = User(
        id=uuid.uuid4(),
        email="deps@example.com",
        hashed_password="x",
        last_seen_at=None,
    )

    deps._touch_last_seen(_FailingSession(), user)  # type: ignore[arg-type]

    assert rolled_back is True


def test_touch_last_seen_skips_a_recent_write() -> None:
    """Within the refresh interval it must not touch the session at all."""

    class _ExplodingSession:
        def add(self, _obj: object) -> None:
            raise AssertionError("should not write within the refresh interval")

        def commit(self) -> None:
            raise AssertionError("should not write within the refresh interval")

    user = User(
        id=uuid.uuid4(),
        email="deps2@example.com",
        hashed_password="x",
        last_seen_at=deps.get_datetime_utc(),
    )

    deps._touch_last_seen(_ExplodingSession(), user)  # type: ignore[arg-type]

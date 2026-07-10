"""CRUD tests for refresh-session pruning."""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, delete, select

from app import crud
from app.models import RefreshSession, User
from app.models.base import get_datetime_utc
from app.schemas import UserCreate
from tests.utils.utils import random_email


def _make_user(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password="password123"),
    )


def _make_session(
    db: Session,
    user: User,
    *,
    token_id: str,
    expires_at,
    revoked_at=None,
) -> RefreshSession:
    row = crud.create_refresh_session(
        session=db,
        user_id=user.id,
        token_hash=crud.hash_refresh_token_id(token_id),
        expires_at=expires_at,
    )
    if revoked_at is not None:
        row.revoked_at = revoked_at
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_delete_stale_removes_long_dead_sessions_only(db: Session) -> None:
    # Isolate: the shared session-scoped db accumulates rows across tests.
    db.exec(delete(RefreshSession))
    db.commit()

    user = _make_user(db)
    now = get_datetime_utc()

    active = _make_session(
        db, user, token_id="active", expires_at=now + timedelta(days=10)
    )
    long_expired = _make_session(
        db, user, token_id="expired", expires_at=now - timedelta(days=40)
    )
    long_revoked = _make_session(
        db,
        user,
        token_id="revoked-old",
        expires_at=now + timedelta(days=10),
        revoked_at=now - timedelta(days=40),
    )
    recently_revoked = _make_session(
        db,
        user,
        token_id="revoked-new",
        expires_at=now + timedelta(days=10),
        revoked_at=now - timedelta(days=1),
    )

    # Capture ids before the delete+commit expires the ORM instances.
    active_id = active.id
    recently_revoked_id = recently_revoked.id
    long_expired_id = long_expired.id
    long_revoked_id = long_revoked.id

    deleted = crud.delete_stale_refresh_sessions(session=db, now=now)

    remaining = {r.id for r in db.exec(select(RefreshSession)).all()}
    assert deleted == 2
    assert active_id in remaining
    assert recently_revoked_id in remaining
    assert long_expired_id not in remaining
    assert long_revoked_id not in remaining

import hashlib
import uuid
from datetime import datetime, timedelta

from sqlalchemy import update
from sqlmodel import Session, col, select

from app.models import RefreshSession
from app.models.base import get_datetime_utc

REFRESH_REUSE_GRACE_SECONDS = 30


def hash_refresh_token_id(token_id: str) -> str:
    return hashlib.sha256(token_id.encode("utf-8")).hexdigest()


def create_refresh_session(
    *,
    session: Session,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshSession:
    db_session = RefreshSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(db_session)
    return db_session


def get_refresh_session_for_update(
    *, session: Session, session_id: uuid.UUID
) -> RefreshSession | None:
    statement = (
        select(RefreshSession).where(RefreshSession.id == session_id).with_for_update()
    )
    return session.exec(statement).first()


def refresh_session_is_active(
    *, refresh_session: RefreshSession, now: datetime
) -> bool:
    return refresh_session.revoked_at is None and refresh_session.expires_at > now


def refresh_token_matches_previous(
    *, refresh_session: RefreshSession, token_hash: str, now: datetime
) -> bool:
    return (
        refresh_session.previous_token_hash == token_hash
        and refresh_session.previous_token_valid_until is not None
        and refresh_session.previous_token_valid_until > now
    )


def rotate_refresh_session(
    *,
    refresh_session: RefreshSession,
    old_token_hash: str,
    new_token_hash: str,
    expires_at: datetime,
    now: datetime,
) -> None:
    refresh_session.previous_token_hash = old_token_hash
    refresh_session.previous_token_valid_until = now + timedelta(
        seconds=REFRESH_REUSE_GRACE_SECONDS
    )
    refresh_session.token_hash = new_token_hash
    refresh_session.expires_at = expires_at
    refresh_session.last_used_at = now


def mark_refresh_session_used(
    *, refresh_session: RefreshSession, now: datetime
) -> None:
    refresh_session.last_used_at = now


def revoke_refresh_session(
    *, refresh_session: RefreshSession, now: datetime | None = None
) -> None:
    refresh_session.revoked_at = now or get_datetime_utc()


def revoke_refresh_sessions_for_user(
    *, session: Session, user_id: uuid.UUID, now: datetime | None = None
) -> None:
    revoked_at = now or get_datetime_utc()
    statement = (
        update(RefreshSession)
        .where(
            col(RefreshSession.user_id) == user_id,
            col(RefreshSession.revoked_at).is_(None),
        )
        .values(revoked_at=revoked_at)
    )
    session.exec(statement)

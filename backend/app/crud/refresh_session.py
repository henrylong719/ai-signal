import hashlib
import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, or_, update
from sqlmodel import Session, col, select

from app.models import RefreshSession
from app.models.base import get_datetime_utc

# Window during which a just-rotated refresh token is still accepted. Sized
# to absorb realistic multi-tab races and mobile tab-resume latency, where
# one tab may finish a refresh while another is still mid-flight with the
# previous token. 30s was too tight in practice (slow cellular wake-ups).
REFRESH_REUSE_GRACE_SECONDS = 120

# How long a permanently-dead refresh session (expired or revoked) is kept
# before pruning. A dead row can never re-authenticate; the window just
# leaves a short audit trail and covers clock skew. Matches the refresh
# token TTL so anything this old is unambiguously done.
REFRESH_SESSION_RETENTION_DAYS = 30


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


def delete_stale_refresh_sessions(
    *,
    session: Session,
    now: datetime | None = None,
    retention_days: int = REFRESH_SESSION_RETENTION_DAYS,
) -> int:
    """Hard-delete refresh sessions that have been dead past the retention
    window, returning the number removed.

    A session is permanently unusable once it is revoked or expired, so
    accumulating those rows only grows the table. We delete a row when the
    moment it became dead — ``revoked_at`` if revoked, otherwise
    ``expires_at`` — is older than ``now - retention_days``. Rows that are
    still active, or dead only recently, are kept.
    """
    now = now or get_datetime_utc()
    cutoff = now - timedelta(days=retention_days)
    statement = delete(RefreshSession).where(
        or_(
            col(RefreshSession.revoked_at) < cutoff,
            col(RefreshSession.expires_at) < cutoff,
        )
    )
    result = session.exec(statement)
    session.commit()
    return int(result.rowcount or 0)

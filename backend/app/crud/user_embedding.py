"""CRUD for the cached user interest vector."""

import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from app.models.base import get_datetime_utc
from app.models.user_embedding import UserEmbedding


def get_user_embedding(*, session: Session, user_id: uuid.UUID) -> UserEmbedding | None:
    """Returns None if the user has no cached vector yet.

    The For-You service treats absence as "compute on demand" rather
    than as an error — see services/for_you.py for the fallback path.
    """
    return session.get(UserEmbedding, user_id)


def upsert_user_embedding(
    *,
    session: Session,
    user_id: uuid.UUID,
    embedding: list[float],
) -> None:
    """Atomic insert-or-replace for the user's cached interest vector.

    Used by every write path that affects what the recommender thinks
    the user wants — saving an article, clicking through, updating
    interests. Atomic upsert means concurrent writes (e.g., two saves
    in quick succession) don't race each other.
    """
    now = get_datetime_utc()
    stmt = pg_insert(UserEmbedding).values(
        user_id=user_id,
        embedding=embedding,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "embedding": embedding,
            "updated_at": now,
        },
    )
    session.exec(stmt)  # type: ignore[call-overload]
    session.commit()


def delete_user_embedding(*, session: Session, user_id: uuid.UUID) -> None:
    """Drop the cached vector. Used if we ever need to force a recompute
    on next read (e.g., after a model upgrade)."""
    row = session.get(UserEmbedding, user_id)
    if row is not None:
        session.delete(row)
        session.commit()

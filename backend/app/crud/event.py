"""CRUD for ArticleEvent — clicks and dismissals.

The headline operation is `record_event`, which uses a Postgres upsert to
atomically insert-or-increment in a single round trip. This is the right
shape for an event recorder: two concurrent clicks from the same user on
the same article must not race each other into double-inserts.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.models.article import ARTICLE_EVENT_TYPES, ArticleEvent, ArticleEventType
from app.models.base import get_datetime_utc


def record_event(
    *,
    session: Session,
    user_id: uuid.UUID,
    article_id: uuid.UUID,
    event_type: ArticleEventType,
) -> None:
    """Insert or increment an event row atomically.

    On first occurrence: inserts a row with count=1 and first_at=last_at=now.
    On subsequent occurrences: increments count and updates last_at, leaving
    first_at untouched. The composite primary key on (user_id, article_id,
    event_type) is what makes ON CONFLICT possible.

    Defensive validation against ``event_type`` not being a known value;
    SQLAlchemy/Postgres would reject it anyway via the ENUM, but raising in
    Python gives a clearer error.
    """

    if event_type not in ARTICLE_EVENT_TYPES:
        raise ValueError(f"Unknown event_type: {event_type!r}")

    now = get_datetime_utc()
    stmt = pg_insert(ArticleEvent).values(
        user_id=user_id,
        article_id=article_id,
        event_type=event_type,
        count=1,
        first_at=now,
        last_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "article_id", "event_type"],
        set_={
            "count": ArticleEvent.count + 1,
            "last_at": now,
        },
    )

    session.exec(stmt)
    session.commit()


def get_event_article_ids(
    *,
    session: Session,
    user_id: uuid.UUID,
    event_type: ArticleEventType,
) -> list[uuid.UUID]:
    """All article IDs that have an event of this type for this user.

    The recommender uses this to populate `dismissed_article_ids` (hard
    filter) and to derive `clicked_tags` / `clicked_sources` (joined with
    the articles table at the call site).
    """
    statement = select(ArticleEvent.article_id).where(
        ArticleEvent.user_id == user_id, ArticleEvent.event_type == event_type
    )
    return list(session.exec(statement).all())


def get_events(
    *,
    session: Session,
    user_id: uuid.UUID,
    event_type: ArticleEventType,
) -> Sequence[ArticleEvent]:
    """Full event rows, when count or recency are needed."""
    statement = select(ArticleEvent).where(
        ArticleEvent.user_id == user_id, ArticleEvent.event_type == event_type
    )
    return session.exec(statement).all()

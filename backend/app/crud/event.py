"""CRUD for ArticleEvent — clicks and dismissals.

The headline operation is `record_event`, which uses a Postgres upsert to
atomically insert-or-increment in a single round trip. This is the right
shape for an event recorder: two concurrent clicks from the same user on
the same article must not race each other into double-inserts.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

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
        ArticleEvent.user_id == user_id,
        ArticleEvent.event_type == event_type,
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
        ArticleEvent.user_id == user_id,
        ArticleEvent.event_type == event_type,
    )
    return session.exec(statement).all()


def get_clicked_signals(
    *, session: Session, user_id: uuid.UUID
) -> tuple[dict[str, float], dict[str, float]]:
    """Aggregate the user's clicked-article tags and sources, decay-weighted.

    Returns ``(tag_weights, source_weights)`` — same shape as
    ``crud.article.get_saved_signals``. Clicks decay faster than saves
    (see ``services.decay``) because clicks are noisier signals; an
    accidental clickthrough from last quarter shouldn't keep biasing
    the feed.

    The ``last_at`` column is used as the interaction time. A user
    who clicks an article ten times has a single ArticleEvent row
    with count=10 and last_at as the most recent click — we use the
    most recent because the question we're answering is "is this
    interest current?", not "how often did they click?".

    Done as one JOIN rather than fetch-IDs-then-fetch-articles to
    halve the round trips and let Postgres push down the filtering.
    For users with thousands of clicked articles this would benefit
    from SQL-side aggregation; at our scale Python is simpler.
    """
    from app.models import Article  # local import to avoid circular
    from app.services.decay import (
        CLICKED_HALF_LIFE_DAYS,
        aggregate_weights_by_key,
    )

    statement = (
        select(Article.source, Article.tags, ArticleEvent.last_at)
        .join(ArticleEvent, col(Article.id) == col(ArticleEvent.article_id))
        .where(
            ArticleEvent.user_id == user_id,
            ArticleEvent.event_type == "clicked",
        )
    )
    tag_pairs: list[tuple[str, datetime]] = []
    source_pairs: list[tuple[str, datetime]] = []
    for source, article_tags, last_at in session.exec(statement).all():
        source_pairs.append((source, last_at))
        if article_tags:
            for tag in article_tags:
                tag_pairs.append((tag, last_at))

    tag_weights = aggregate_weights_by_key(
        tag_pairs, half_life_days=CLICKED_HALF_LIFE_DAYS
    )
    source_weights = aggregate_weights_by_key(
        source_pairs, half_life_days=CLICKED_HALF_LIFE_DAYS
    )
    return tag_weights, source_weights


def get_clicked_article_embeddings(
    *, session: Session, user_id: uuid.UUID
) -> list[list[float]]:
    """Fetch the embeddings of every article the user has clicked through to.

    Mirror of ``crud.article.get_saved_article_embeddings`` — see there
    for the design notes. Articles without embeddings are skipped
    silently.
    """
    from app.models import Article  # local import to avoid circular

    statement = (
        select(col(Article.embedding))
        .join(ArticleEvent, col(Article.id) == col(ArticleEvent.article_id))
        .where(
            ArticleEvent.user_id == user_id,
            ArticleEvent.event_type == "clicked",
            col(Article.embedding).is_not(None),
        )
    )
    return [
        list(cast(Sequence[float], row))
        for row in session.exec(statement).all()
        if row is not None
    ]

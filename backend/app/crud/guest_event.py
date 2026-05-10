"""CRUD for anonymous guest analytics events.

Operations:

- ``record_guest_event`` — single insert. Append-only; the route layer
  has already validated the payload.
- The various ``get_*`` helpers return raw aggregations the admin
  funnel endpoint shapes into its response. Keeping each aggregation
  in its own helper means the route stays a thin orchestrator.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Article, GuestEvent


def record_guest_event(
    *,
    session: Session,
    anonymous_id: str,
    event_type: str,
    user_id: uuid.UUID | None = None,
    path: str | None = None,
    article_id: uuid.UUID | None = None,
    source_name: str | None = None,
    topic: str | None = None,
    referrer: str | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> GuestEvent:
    event = GuestEvent(
        anonymous_id=anonymous_id,
        user_id=user_id,
        event_type=event_type,
        path=path,
        article_id=article_id,
        source_name=source_name,
        topic=topic,
        referrer=referrer,
        event_metadata=event_metadata,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def get_event_counts_by_type(
    *,
    session: Session,
    since: datetime | None,
    until: datetime,
) -> dict[str, int]:
    """Return ``{event_type: count}`` over the optional window.

    ``since=None`` means "no lower bound", matching the ``range=all`` UX.
    """
    n_col = func.count().label("n")
    statement = select(GuestEvent.event_type, n_col).where(
        GuestEvent.created_at <= until
    )
    if since is not None:
        statement = statement.where(GuestEvent.created_at >= since)
    statement = statement.group_by(col(GuestEvent.event_type))
    return {row[0]: int(row[1]) for row in session.exec(statement).all()}


def get_top_clicked_articles(
    *,
    session: Session,
    since: datetime | None,
    until: datetime,
    limit: int = 10,
) -> list[tuple[uuid.UUID, int, Article | None]]:
    """Return ``[(article_id, clicks, article_or_None)]`` ordered by clicks.

    Joins against ``articles`` to surface title / source / url for the
    UI. ``LEFT JOIN`` semantics: an article that was deleted after the
    click still shows up with ``None`` for the joined row, so we can
    render a "(deleted)" placeholder rather than dropping the line.
    """
    n_col = func.count().label("n")
    statement = (
        select(GuestEvent.article_id, n_col, Article)
        .join(Article, col(Article.id) == col(GuestEvent.article_id), isouter=True)
        .where(
            GuestEvent.event_type == "guest_article_click",
            col(GuestEvent.article_id).is_not(None),
            GuestEvent.created_at <= until,
        )
    )
    if since is not None:
        statement = statement.where(GuestEvent.created_at >= since)
    statement = (
        statement.group_by(col(GuestEvent.article_id), col(Article.id))
        .order_by(n_col.desc())
        .limit(limit)
    )
    rows = session.exec(statement).all()
    # The WHERE clause filters out NULL article_ids, so the narrowing
    # cast is safe; mypy can't infer it from the predicate.
    return [
        (cast(uuid.UUID, article_id), int(count), article)
        for article_id, count, article in rows
    ]


def get_top_clicked_sources(
    *,
    session: Session,
    since: datetime | None,
    until: datetime,
    limit: int = 10,
) -> list[tuple[str, int]]:
    """Top source names by guest_source_click and guest_article_click.

    We count both ``guest_source_click`` (explicit interest in the source
    itself) and the source recorded on ``guest_article_click`` rows
    (interest via an article). Together they answer "which sources pull
    in anonymous attention?" — the original question this view exists
    to answer.
    """
    n_col = func.count().label("n")
    statement = select(GuestEvent.source_name, n_col).where(
        col(GuestEvent.source_name).is_not(None),
        col(GuestEvent.event_type).in_(("guest_source_click", "guest_article_click")),
        GuestEvent.created_at <= until,
    )
    if since is not None:
        statement = statement.where(GuestEvent.created_at >= since)
    statement = (
        statement.group_by(col(GuestEvent.source_name))
        .order_by(n_col.desc())
        .limit(limit)
    )
    rows = session.exec(statement).all()
    return [(cast(str, name), int(count)) for name, count in rows]


def get_top_clicked_topics(
    *,
    session: Session,
    since: datetime | None,
    until: datetime,
    limit: int = 10,
) -> list[tuple[str, int]]:
    n_col = func.count().label("n")
    statement = select(GuestEvent.topic, n_col).where(
        GuestEvent.event_type == "guest_topic_click",
        col(GuestEvent.topic).is_not(None),
        GuestEvent.created_at <= until,
    )
    if since is not None:
        statement = statement.where(GuestEvent.created_at >= since)
    statement = (
        statement.group_by(col(GuestEvent.topic)).order_by(n_col.desc()).limit(limit)
    )
    rows = session.exec(statement).all()
    return [(cast(str, topic), int(count)) for topic, count in rows]


def get_signup_cta_clicks_by_location(
    *,
    session: Session,
    since: datetime | None,
    until: datetime,
) -> list[tuple[str, int]]:
    """Count ``guest_signup_click`` events bucketed by ``metadata.location``.

    Events without a ``metadata.location`` are bucketed under
    ``"unknown"``. Postgres can't usefully GROUP BY a JSONB field through
    the SQLModel select API without dialect-specific casts, so we pull
    rows and group in Python. The volume is small (CTA clicks per
    window), so this is fine; revisit when we have meaningful traffic.
    """
    statement = select(GuestEvent.event_metadata).where(
        GuestEvent.event_type == "guest_signup_click",
        GuestEvent.created_at <= until,
    )
    if since is not None:
        statement = statement.where(GuestEvent.created_at >= since)

    counter: Counter[str] = Counter()
    # SQLModel's ``session.exec()`` returns scalar values (not tuples)
    # for a single-column select, so the loop variable is the JSONB
    # payload itself rather than a one-tuple.
    for metadata in session.exec(statement).all():
        location = "unknown"
        if isinstance(metadata, dict):
            raw = metadata.get("location")
            if isinstance(raw, str) and raw:
                location = raw[:64]
        counter[location] += 1

    return sorted(counter.items(), key=lambda pair: pair[1], reverse=True)

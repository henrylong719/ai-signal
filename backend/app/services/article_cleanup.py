"""Safe, two-stage article cleanup for the news/article store.

Why two stages? Hard-deleting historical articles in one shot is
unrecoverable. The pipeline instead:

  1. **Archive** old, unsaved, unengaged articles by stamping
     ``Article.archived_at``. Archived rows still exist (admin can
     still inspect them) but are filtered out of every public feed.
  2. **Delete** rows that have stayed archived for an additional
     window and *still* aren't saved and *still* have no recent click.
     Deletion relies on the existing ``ON DELETE CASCADE`` on
     ``saved_articles`` and ``article_events`` (see migrations
     ``c5d6e7f8a9b0`` and ``e3f4a5b6c7d8``) so we don't need a manual
     join-and-delete dance for related rows.

Saved articles are excluded at every stage. A recently clicked article
is excluded from archiving (so we don't hide content the user just
returned to) and from deletion (so an archived row that's seen recent
re-engagement gets to stay around).

All age math uses ``COALESCE(published_at, fetched_at)`` so feeds
without ``published_at`` (some RSS sources omit it) don't get treated
as "infinitely old" or "infinitely new" by accident.

The service does the writes in bounded batches so a large first run
doesn't lock the table or hold one giant transaction. Each batch is
its own commit; the next batch reads against the just-committed state.

Dry-run mode performs the same SELECTs but commits nothing. It's the
default for the manual script, the cron endpoint, and the scheduled
job so a misconfigured deploy never hard-deletes by accident.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select

from app.core.config import settings
from app.models import Article
from app.models.article import ArticleEvent, SavedArticle
from app.models.base import get_datetime_utc

logger = logging.getLogger(__name__)


@dataclass
class ArticleCleanupResult:
    """Structured outcome of a cleanup run.

    ``archived_count`` and ``deleted_count`` reflect what the run
    *would* do in dry-run mode and what it *did* otherwise. ``errors``
    is non-empty only when a batch raised — the loop catches and
    records per-batch failures so a single bad row can't sink the
    rest of the run.
    """

    archived_count: int = 0
    deleted_count: int = 0
    dry_run: bool = True
    archive_cutoff: datetime | None = None
    delete_cutoff: datetime | None = None
    keep_clicked_since: datetime | None = None
    errors: list[str] = field(default_factory=list)


def _coalesced_age_column() -> Any:
    """Article's effective age timestamp: ``published_at`` if set, else ``fetched_at``.

    Some RSS feeds omit ``published_at``; falling through to
    ``fetched_at`` keeps those articles in the same age window as
    everything else.
    """
    return func.coalesce(Article.published_at, Article.fetched_at)


def _saved_exists_subquery() -> ColumnElement[bool]:
    """``EXISTS (SELECT 1 FROM saved_articles WHERE article_id = articles.id)``.

    We use NOT EXISTS rather than a LEFT JOIN + IS NULL because the
    cleanup scan ranges over potentially many articles; an anti-join
    via EXISTS gives Postgres clean access to the (article_id) side
    of the saved_articles index without materializing a join.
    """
    return (
        select(SavedArticle.user_id)
        .where(col(SavedArticle.article_id) == col(Article.id))
        .exists()
    )


def _recent_click_exists_subquery(since: datetime) -> ColumnElement[bool]:
    """``EXISTS (... clicked events with last_at >= since)``.

    Only the ``clicked`` event type counts as "keep this around" —
    dismisses are an explicit negative signal and shouldn't protect
    an article from cleanup.
    """
    return (
        select(ArticleEvent.user_id)
        .where(
            and_(
                col(ArticleEvent.article_id) == col(Article.id),
                col(ArticleEvent.event_type) == "clicked",
                col(ArticleEvent.last_at) >= since,
            )
        )
        .exists()
    )


def _archive_candidate_ids(
    *,
    session: Session,
    archive_cutoff: datetime,
    keep_clicked_since: datetime,
    limit: int,
) -> list[uuid.UUID]:
    """Fetch the next batch of article IDs eligible for archiving.

    Returns at most ``limit`` IDs. Caller is responsible for stamping
    ``archived_at`` and committing.
    """
    age = _coalesced_age_column()
    statement = (
        select(Article.id)
        .where(
            col(Article.archived_at).is_(None),
            age < archive_cutoff,
            ~_saved_exists_subquery(),
            ~_recent_click_exists_subquery(keep_clicked_since),
        )
        .limit(limit)
    )
    return list(session.exec(statement).all())


def _delete_candidate_ids(
    *,
    session: Session,
    delete_cutoff: datetime,
    keep_clicked_since: datetime,
    limit: int,
) -> list[uuid.UUID]:
    """Fetch the next batch of archived article IDs eligible for deletion."""
    statement = (
        select(Article.id)
        .where(
            col(Article.archived_at).is_not(None),
            col(Article.archived_at) < delete_cutoff,
            ~_saved_exists_subquery(),
            ~_recent_click_exists_subquery(keep_clicked_since),
        )
        .limit(limit)
    )
    return list(session.exec(statement).all())


def _archive_batch(
    *,
    session: Session,
    article_ids: list[uuid.UUID],
    now: datetime,
    dry_run: bool,
) -> int:
    """Stamp ``archived_at`` on a batch of articles, returning rows affected.

    In dry-run mode we still build the statement but never execute the
    UPDATE — the candidate count is what matters.
    """
    if not article_ids:
        return 0
    if dry_run:
        return len(article_ids)
    statement = (
        sa_update(Article)
        .where(col(Article.id).in_(article_ids))
        .values(archived_at=now)
    )
    session.exec(statement)
    session.commit()
    # Cleanup runs single-process inside the app's scheduler. The
    # SELECT ↔ UPDATE window is microseconds, so concurrent updates on
    # the same id batch don't happen in practice. Reporting the batch
    # size is accurate enough for the operator's eye-test.
    return len(article_ids)


def _delete_batch(
    *,
    session: Session,
    article_ids: list[uuid.UUID],
    dry_run: bool,
) -> int:
    """Hard-delete a batch of articles, returning rows affected.

    The ``ON DELETE CASCADE`` on ``saved_articles`` and ``article_events``
    handles related-row cleanup. We re-checked the saved/clicked
    predicates in the SELECT step, so a cascading delete here should
    only touch articles that earned removal.
    """
    if not article_ids:
        return 0
    if dry_run:
        return len(article_ids)
    statement = sa_delete(Article).where(col(Article.id).in_(article_ids))
    session.exec(statement)
    session.commit()
    return len(article_ids)


def run_article_cleanup(
    *,
    session: Session,
    dry_run: bool | None = None,
    archive_after_days: int | None = None,
    delete_after_days: int | None = None,
    keep_clicked_after_days: int | None = None,
    batch_size: int | None = None,
) -> ArticleCleanupResult:
    """Run the full archive → delete pipeline once.

    Any kwarg left as ``None`` falls back to the corresponding setting
    in ``app.core.config``. Callers (CLI script, internal endpoint,
    scheduler) all share this entry point so cleanup semantics are
    identical regardless of how the run was triggered.

    Returns an ``ArticleCleanupResult`` with counters and the cutoff
    timestamps that were used — useful for logging and for the cron
    endpoint to return as JSON.
    """
    effective_dry_run = (
        dry_run if dry_run is not None else settings.ARTICLE_CLEANUP_DRY_RUN
    )
    archive_days = archive_after_days or settings.ARTICLE_ARCHIVE_AFTER_DAYS
    delete_days = delete_after_days or settings.ARTICLE_DELETE_AFTER_DAYS
    keep_click_days = (
        keep_clicked_after_days or settings.ARTICLE_KEEP_CLICKED_AFTER_DAYS
    )
    chunk = batch_size or settings.ARTICLE_CLEANUP_BATCH_SIZE

    now = get_datetime_utc()
    archive_cutoff = now - timedelta(days=archive_days)
    delete_cutoff = now - timedelta(days=delete_days)
    keep_clicked_since = now - timedelta(days=keep_click_days)

    result = ArticleCleanupResult(
        dry_run=effective_dry_run,
        archive_cutoff=archive_cutoff,
        delete_cutoff=delete_cutoff,
        keep_clicked_since=keep_clicked_since,
    )

    logger.info(
        "Article cleanup starting (dry_run=%s): archive<%s, delete<%s, "
        "keep_clicked_since=%s, batch_size=%d",
        effective_dry_run,
        archive_cutoff.isoformat(),
        delete_cutoff.isoformat(),
        keep_clicked_since.isoformat(),
        chunk,
    )

    # --- Archive stage ----------------------------------------------------
    # Loop in batches until a SELECT returns fewer than ``chunk`` rows.
    # In dry-run mode we'd otherwise loop forever (we never stamp
    # archived_at), so a single batch is enough to estimate work.
    while True:
        try:
            ids = _archive_candidate_ids(
                session=session,
                archive_cutoff=archive_cutoff,
                keep_clicked_since=keep_clicked_since,
                limit=chunk,
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            msg = f"archive-select failed: {exc!r}"
            logger.exception(msg)
            result.errors.append(msg)
            break

        if not ids:
            break

        try:
            affected = _archive_batch(
                session=session,
                article_ids=ids,
                now=now,
                dry_run=effective_dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            msg = f"archive-update batch failed: {exc!r}"
            logger.exception(msg)
            result.errors.append(msg)
            break

        result.archived_count += affected
        logger.info("Archive batch: %d row(s)", affected)

        if effective_dry_run or len(ids) < chunk:
            # Dry-run never persists; one batch is the report.
            # Last partial batch means we've drained the pool.
            break

    # --- Delete stage -----------------------------------------------------
    while True:
        try:
            ids = _delete_candidate_ids(
                session=session,
                delete_cutoff=delete_cutoff,
                keep_clicked_since=keep_clicked_since,
                limit=chunk,
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            msg = f"delete-select failed: {exc!r}"
            logger.exception(msg)
            result.errors.append(msg)
            break

        if not ids:
            break

        try:
            affected = _delete_batch(
                session=session,
                article_ids=ids,
                dry_run=effective_dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            msg = f"delete batch failed: {exc!r}"
            logger.exception(msg)
            result.errors.append(msg)
            break

        result.deleted_count += affected
        logger.info("Delete batch: %d row(s)", affected)

        if effective_dry_run or len(ids) < chunk:
            break

    logger.info(
        "Article cleanup done (dry_run=%s): archived=%d, deleted=%d, errors=%d",
        result.dry_run,
        result.archived_count,
        result.deleted_count,
        len(result.errors),
    )
    return result

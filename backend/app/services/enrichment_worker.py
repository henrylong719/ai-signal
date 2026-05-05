"""Async worker that picks pending articles off the DB queue and enriches them.

Design:
    - One poll = one batch of up to N rows.
    - Rows are fetched newest-first so fresh content gets enriched ahead
      of any backfill backlog.
    - Each row is processed concurrently under a semaphore so we can scale
      throughput without hammering the Anthropic API.
    - The DB connection is NOT held while the LLM call is in flight. We
      open a quick transaction to fetch IDs, close it, run the LLM calls,
      then open another to write results back.

What this module does NOT do:
    - It does not run on a schedule. The scheduler (Step 6) calls
      `run_enrichment_poll()` on a timer.
    - It does not claim rows for multi-worker safety. We're single-worker
      for now; if we ever run multiple worker processes, see the comment
      in `_fetch_pending_ids` for where the SELECT...FOR UPDATE SKIP LOCKED
      pattern would slot in.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.db import async_engine
from app.models import Article
from app.models.base import get_datetime_utc
from app.services.enrichment import (
    EnrichmentError,
    EnrichmentResult,
    enrich_article,
    enrichment_enabled,
)

logger = logging.getLogger(__name__)


# How many rows we try to enrich per poll. Cheap to tune; the cost ceiling
# is mostly governed by how often the scheduler runs the poll and your
# actual ingestion volume.
_BATCH_SIZE = 20

# How many concurrent LLM calls to allow. Haiku is fast and Anthropic's
# rate limits are generous, but pushing this too high invites 429s.
_CONCURRENCY = 5

# After this many failed attempts on a single row, we give up and mark it
# 'failed'. Reset manually with: UPDATE articles SET summary_status='pending',
# summary_attempts=0 WHERE summary_status='failed'.
_MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class PollResult:
    """Summary of one worker poll, for logging and tests."""

    fetched: int
    succeeded: int
    failed: int
    gave_up: int  # rows that hit _MAX_ATTEMPTS this pass


# ---------------------------------------------------------------------------
# DB helpers — these mirror the inline-SQL style of crud/ingest.py rather
# than going through crud/article.py, since the queries here are specific
# to the worker's queue management and not generally useful elsewhere.
# ---------------------------------------------------------------------------


async def _fetch_pending_ids(session: AsyncSession, limit: int) -> list[uuid.UUID]:
    """Get the next batch of article IDs needing enrichment.

    Newest-first so that if we're behind, fresh content takes priority over
    backfilling old rows.

    NOTE: For multi-worker safety, replace this query with:

        SELECT id FROM articles
        WHERE summary_status = 'pending'
        ORDER BY published_at DESC NULLS LAST
        LIMIT :limit
        FOR UPDATE SKIP LOCKED

    and add an UPDATE to flip those rows to 'in_progress' inside the same
    transaction. The current implementation is single-worker only.
    """
    stmt = (
        select(col(Article.id))
        .where(col(Article.summary_status) == "pending")
        .where(col(Article.summary_attempts) < _MAX_ATTEMPTS)
        .order_by(
            col(Article.published_at).desc().nullslast(),
            col(Article.fetched_at).desc(),
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def _load_article(session: AsyncSession, article_id: uuid.UUID) -> Article | None:
    """Load a full Article row by ID."""
    return await session.get(Article, article_id)


async def _write_success(
    session: AsyncSession, article_id: uuid.UUID, enrichment: EnrichmentResult
) -> None:
    """Apply enrichment results to a row and mark it done."""
    stmt = (
        update(Article)
        .where(col(Article.id) == article_id)
        .values(
            summary=enrichment.summary,
            why_it_matters=enrichment.why_it_matters,
            difficulty=enrichment.difficulty,
            summary_status="done",
            summary_prompt_version=enrichment.prompt_version,
            summary_generated_at=get_datetime_utc(),
        )
    )
    await session.execute(stmt)


async def _write_failure(
    session: AsyncSession, article_id: uuid.UUID, current_attempts: int
) -> bool:
    """Increment attempts on a failed row. Returns True if we gave up.

    Uses an atomic SQL increment rather than read-modify-write so the
    counter is correct even if the row was touched between fetch and
    write (defensive; matters once we go multi-worker).
    """
    new_attempts = current_attempts + 1
    new_status = "failed" if new_attempts >= _MAX_ATTEMPTS else "pending"
    stmt = (
        update(Article)
        .where(col(Article.id) == article_id)
        .values(
            summary_attempts=col(Article.summary_attempts) + 1,
            summary_status=new_status,
        )
    )
    await session.execute(stmt)
    return new_status == "failed"


# ---------------------------------------------------------------------------
# Per-row processing — one of these runs per row, concurrently, under a
# semaphore. Keeps DB writes inside the same transaction the caller passes in.
# ---------------------------------------------------------------------------


@dataclass
class _RowOutcome:
    """Result of processing one row, used by the poll to tally counts."""

    succeeded: bool
    gave_up: bool


async def _process_one(
    article_id: uuid.UUID, semaphore: asyncio.Semaphore
) -> _RowOutcome:
    """Enrich one article and persist the result.

    Each call gets its own DB session. The session lifetime is short:
    one read at the start, one write at the end, with the LLM call
    happening between (with no DB connection held).
    """
    # Load the article.
    async with AsyncSession(async_engine) as session:
        article = await _load_article(session, article_id)
        if article is None:
            # Row vanished between fetch and load — extremely unlikely but
            # not impossible. Treat as a no-op success.
            return _RowOutcome(succeeded=False, gave_up=False)
        current_attempts = article.summary_attempts

    # Run the LLM call OUTSIDE any DB session, under the concurrency cap.
    async with semaphore:
        try:
            enrichment = await enrich_article(article)
        except EnrichmentError as e:
            logger.warning(
                "Enrichment failed for article %s (attempt %d/%d): %s",
                article_id,
                current_attempts + 1,
                _MAX_ATTEMPTS,
                e,
            )
            async with AsyncSession(async_engine) as session:
                gave_up = await _write_failure(session, article_id, current_attempts)
                await session.commit()
            return _RowOutcome(succeeded=False, gave_up=gave_up)

    # Write the result back.
    async with AsyncSession(async_engine) as session:
        await _write_success(session, article_id, enrichment)
        await session.commit()

    return _RowOutcome(succeeded=True, gave_up=False)


# ---------------------------------------------------------------------------
# The poll — public entry point. Scheduler calls this on a timer.
# ---------------------------------------------------------------------------


async def run_enrichment_poll(batch_size: int = _BATCH_SIZE) -> PollResult:
    """Run one batch of enrichment.

    Safe to call when ANTHROPIC_API_KEY is unset — short-circuits without
    touching the DB.
    """
    if not enrichment_enabled():
        logger.debug("Enrichment disabled (no API key); skipping poll.")
        return PollResult(fetched=0, succeeded=0, failed=0, gave_up=0)

    # Step 1: claim work. Quick read, no LLM calls held inside this session.
    async with AsyncSession(async_engine) as session:
        article_ids = await _fetch_pending_ids(session, batch_size)

    if not article_ids:
        return PollResult(fetched=0, succeeded=0, failed=0, gave_up=0)

    logger.info("Enrichment poll picked up %d articles", len(article_ids))

    # Step 2: process concurrently. Each task manages its own DB sessions.
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    outcomes = await asyncio.gather(
        *(_process_one(aid, semaphore) for aid in article_ids),
        return_exceptions=False,  # _process_one already swallows errors
    )

    # Step 3: tally.
    succeeded = sum(1 for o in outcomes if o.succeeded)
    gave_up = sum(1 for o in outcomes if o.gave_up)
    failed = len(outcomes) - succeeded  # includes gave_up

    logger.info(
        "Enrichment poll done: %d succeeded, %d failed (%d gave up)",
        succeeded,
        failed,
        gave_up,
    )

    return PollResult(
        fetched=len(article_ids),
        succeeded=succeeded,
        failed=failed,
        gave_up=gave_up,
    )

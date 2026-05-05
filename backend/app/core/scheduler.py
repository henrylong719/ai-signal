"""Background scheduler that periodically runs ingest and enrichment.

Owns two recurring jobs:
    - ingest_job: pulls fresh RSS articles into the DB queue.
    - enrichment_job: drains pending articles by calling the LLM.

The scheduler is started on FastAPI app startup and stopped on shutdown
via the lifespan handler in app/main.py.

Single-replica only. If you ever run multiple backend replicas, every
replica will run its own scheduler — meaning ingest and enrichment will
fire multiple times in parallel. To support multi-replica deployments,
either move scheduling to an external cron hitting webhook endpoints,
or add a job store with leader election (e.g., a Postgres-backed
APScheduler store with row locking).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.crud.ingest import ingest_all
from app.services.enrichment import enrichment_enabled
from app.services.enrichment_worker import run_enrichment_poll

logger = logging.getLogger(__name__)


# How often each job runs. Tune as needed.
#
# Ingest every 4 hours — RSS feeds don't update faster than that for
# most sources, and we don't want to be a bad citizen hammering them.
_INGEST_INTERVAL = timedelta(hours=4)

# Enrichment every 5 minutes — frequent enough that fresh articles get
# summaries within minutes of ingestion. Cheap because the worker
# short-circuits if there's nothing pending.
_ENRICHMENT_INTERVAL = timedelta(minutes=5)

# How long after a missed run we'll still execute it. Useful for the
# ingest job: if the app was restarted at 3:55 and the next ingest was
# scheduled for 4:00, we want it to still run at 4:30 once the app is
# back up rather than waiting until 8:00.
_MISFIRE_GRACE_SECONDS = 60 * 30  # 30 minutes


# Module-level singleton. Created on first call to start_scheduler(),
# stopped on stop_scheduler(). Module-level rather than passed around
# because there's only ever one in this process.
_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# Job wrappers — these exist so we can log around each invocation. The
# actual work happens in ingest_all() and run_enrichment_poll().
# ---------------------------------------------------------------------------


async def _ingest_job() -> None:
    """Wrap ingest_all() with logging."""
    logger.info("Scheduled ingest starting")
    try:
        result = await ingest_all()
        logger.info("Scheduled ingest done: %s", result)
    except Exception:
        # APScheduler logs job exceptions itself, but we want our own
        # message so it's findable in our logs by job name.
        logger.exception("Scheduled ingest failed")


async def _enrichment_job() -> None:
    """Wrap run_enrichment_poll() with logging."""
    if not enrichment_enabled():
        # Quietly skip — already logged at debug in the worker itself.
        return
    try:
        result = await run_enrichment_poll()
        # Only log when the poll actually did something. With 5-minute
        # cadence and an empty queue, we'd otherwise spam logs.
        if result.fetched > 0:
            logger.info("Scheduled enrichment poll: %s", result)
    except Exception:
        logger.exception("Scheduled enrichment poll failed")


# ---------------------------------------------------------------------------
# Lifecycle — called from app startup/shutdown.
# ---------------------------------------------------------------------------


def start_scheduler() -> None:
    """Create and start the scheduler. Idempotent."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler already started; ignoring start_scheduler() call")
        return

    scheduler = AsyncIOScheduler()

    # Ingest. We schedule the first run for ~30 seconds after startup so
    # a freshly-deployed app populates its DB without anyone clicking
    # anything. After that, every 4 hours.
    scheduler.add_job(
        _ingest_job,
        trigger=IntervalTrigger(seconds=int(_INGEST_INTERVAL.total_seconds())),
        id="ingest",
        name="Fetch articles from RSS sources",
        coalesce=True,  # collapse missed runs into one
        max_instances=1,  # never run two ingests in parallel
        misfire_grace_time=_MISFIRE_GRACE_SECONDS,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
    )

    # Enrichment. First run after 1 minute (gives ingest time to land
    # some rows on a fresh start). Then every 5 minutes.
    scheduler.add_job(
        _enrichment_job,
        trigger=IntervalTrigger(seconds=int(_ENRICHMENT_INTERVAL.total_seconds())),
        id="enrichment",
        name="Enrich pending articles via LLM",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=_MISFIRE_GRACE_SECONDS,
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=1),
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Scheduler started: ingest every %s, enrichment every %s",
        _INGEST_INTERVAL,
        _ENRICHMENT_INTERVAL,
    )


def stop_scheduler() -> None:
    """Stop the scheduler. Idempotent."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Scheduler stopped")

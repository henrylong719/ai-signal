"""APScheduler-based cron for the ingest pipeline.

Runs ``services.ingest_runner.run_tracked_ingest`` on an interval. Lives
inside the FastAPI process because:
  - We're single-replica for the foreseeable future.
  - The job is short (tens of seconds for 44 RSS feeds).
  - Adding a separate worker container is the right move once we're
    multi-replica or once the job grows past ~5 minutes; both are
    over-engineering today.

The scheduler is started in ``app.main``'s lifespan and stopped on
shutdown. Two concurrency safeguards on the job:

  - ``coalesce=True``: if multiple fires queue up while the process
    was paused (laptop sleep, container migration), only one runs on
    resume. Without this, waking from a long sleep would trigger
    every missed tick at once.
  - ``max_instances=1``: a single run already in flight blocks the
    next tick from starting. ``ingest_all`` opens its own DB sessions
    and is internally idempotent (ON CONFLICT DO NOTHING on the URL
    unique index), so two overlapping runs would be *correct* but
    wasteful — duplicate HTTP fetches and embedding work.

Local development gating: ``settings.ingest_scheduler_enabled`` is
False by default in ENVIRONMENT=local because uvicorn's --reload would
otherwise re-trigger ingestion on every file save. Set
``INGEST_SCHEDULER_ENABLED=True`` in your .env to test the scheduled
path locally.
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped]
    AsyncIOScheduler,
)

from app.core.config import settings
from app.services.ingest_runner import run_tracked_ingest

logger = logging.getLogger(__name__)

# Module-level singleton. The scheduler is owned by main.py's lifespan;
# this module exposes start/stop helpers so main.py doesn't need to
# import APScheduler directly.
_scheduler: AsyncIOScheduler | None = None

_INGEST_JOB_ID = "ingest_all"


def start_scheduler() -> None:
    """Start the ingestion scheduler if enabled in settings.

    Idempotent — calling twice in the same process is a no-op on the
    second call. This matters because uvicorn workers can re-import
    main.py in some configurations.
    """
    global _scheduler

    if not settings.ingest_scheduler_enabled:
        logger.info(
            "Ingest scheduler disabled (ENVIRONMENT=%s, "
            "INGEST_SCHEDULER_ENABLED=%s); skipping start",
            settings.ENVIRONMENT,
            settings.INGEST_SCHEDULER_ENABLED,
        )
        return

    if _scheduler is not None and _scheduler.running:
        logger.debug("Ingest scheduler already running; skipping start")
        return

    _scheduler = AsyncIOScheduler(timezone=timezone.utc)

    # First run is delayed so DB, embedding model load, and other
    # startup work settles before 44 RSS feeds get hit.
    next_run_time = datetime.now(timezone.utc) + timedelta(
        seconds=settings.INGEST_INITIAL_DELAY_SECONDS
    )

    _scheduler.add_job(
        run_tracked_ingest,
        trigger="interval",
        minutes=settings.INGEST_INTERVAL_MINUTES,
        id=_INGEST_JOB_ID,
        next_run_time=next_run_time,
        coalesce=True,
        max_instances=1,
        # Misfire grace: if a tick fires more than 5 minutes late
        # (because the event loop was blocked), drop it rather than
        # running stale. Coalesce already handles most of this, but
        # the grace is a backstop.
        misfire_grace_time=300,
    )

    _scheduler.start()
    logger.info(
        "Ingest scheduler started: interval=%dmin, first run at %s",
        settings.INGEST_INTERVAL_MINUTES,
        next_run_time.isoformat(),
    )


def shutdown_scheduler() -> None:
    """Stop the scheduler cleanly on application shutdown.

    ``wait=False`` so a long-running ingest doesn't block process exit.
    The in-flight job continues but the scheduler stops accepting new
    fires; the job's lifecycle write at the end will still happen.
    """
    global _scheduler

    if _scheduler is None or not _scheduler.running:
        return

    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Ingest scheduler stopped")

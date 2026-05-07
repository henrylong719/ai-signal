"""CRUD for ingest_runs.

Three lifecycle write paths plus a list query:
  - start_run: insert a row with status="running"
  - finish_run: update row to "succeeded" with counts
  - fail_run: update row to "failed" with the exception's message
  - list_runs: most-recent-first listing for the admin page

Each lifecycle write opens its own short-lived session. The wrapper
service in ``services/ingest_runner.py`` is responsible for keeping
the run id between calls — we don't pass session objects across the
async ingest_all boundary because that boundary uses AsyncSession
while this module uses sync Session, matching the rest of crud/.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, desc, select

from app.models import IngestRun, IngestRunStatus


def _expire_stale_runs(*, session: Session, max_age_minutes: int = 5) -> int:
    """Mark any lingering "running" rows as "failed".

    If a process dies mid-run the row stays "running" forever. This
    sweeps them up before each new run so the admin page stays clean.
    Returns the number of rows expired.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    statement = select(IngestRun).where(
        IngestRun.status == "running",
        IngestRun.started_at < cutoff,
    )
    stale = list(session.exec(statement).all())
    for run in stale:
        now = datetime.now(timezone.utc)
        run.finished_at = now
        run.duration_ms = _duration_ms(run.started_at, now)
        run.status = "failed"
        run.errors = ["process terminated before completion"]
        session.add(run)
    if stale:
        session.commit()
    return len(stale)


def start_ingest_run(*, session: Session) -> IngestRun:
    """Insert a fresh ``running`` row and return it.

    Also expires any stale "running" rows from previous runs that
    never completed (e.g., the process was killed mid-run).
    """
    expired = _expire_stale_runs(session=session)
    if expired:
        import logging
        logging.getLogger(__name__).warning(
            "Expired %d stale ingest run(s) stuck in 'running'", expired
        )

    run = IngestRun(
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def finish_ingest_run(
    *,
    session: Session,
    run_id: uuid.UUID,
    inserted: int,
    skipped: int,
    embedded: int,
    errors: list[str],
) -> IngestRun | None:
    """Mark a run as completed and write its result counts.

    Returns None if the row vanished (would only happen if an admin
    deleted it mid-run; not a state we expect). Status is set to
    ``failed`` when the errors list is non-empty even though the run
    didn't raise — partial source failures are still failures from
    the operator's perspective.
    """
    run = session.get(IngestRun, run_id)
    if run is None:
        return None

    finished_at = datetime.now(timezone.utc)
    run.finished_at = finished_at
    run.duration_ms = _duration_ms(run.started_at, finished_at)
    run.inserted = inserted
    run.skipped = skipped
    run.embedded = embedded
    run.errors = list(errors)
    run.status = "failed" if errors else "succeeded"

    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def fail_ingest_run(
    *,
    session: Session,
    run_id: uuid.UUID,
    error: str,
) -> IngestRun | None:
    """Mark a run as failed when the wrapper caught an exception.

    Distinct from a partial-error finish: this path is taken when
    ingest_all itself raised (DB connection lost, scheduler
    misconfigured, etc.) and we have no per-source counts to record.
    The error message is stored as a single-element errors list so
    the wire shape stays uniform.
    """
    run = session.get(IngestRun, run_id)
    if run is None:
        return None

    finished_at = datetime.now(timezone.utc)
    run.finished_at = finished_at
    run.duration_ms = _duration_ms(run.started_at, finished_at)
    run.errors = [error]
    run.status = "failed"

    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def list_ingest_runs(
    *,
    session: Session,
    limit: int = 50,
    status: IngestRunStatus | None = None,
) -> list[IngestRun]:
    """Most-recent-first listing for the admin page.

    Capped server-side at the route layer; this function trusts its
    caller. Optional status filter is for future use (e.g., a "failed
    runs" tab); the admin page in this round just shows all runs.
    """
    statement = select(IngestRun).order_by(desc(IngestRun.started_at)).limit(limit)
    if status is not None:
        statement = (
            select(IngestRun)
            .where(IngestRun.status == status)
            .order_by(desc(IngestRun.started_at))
            .limit(limit)
        )
    return list(session.exec(statement).all())


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    """Compute duration in milliseconds, clamped to >= 0.

    The clamp guards against clock skew between the started_at write
    and finished_at write — extremely unlikely on a single host but
    free to defend against. Zero is the floor, not negative.
    """
    delta = finished_at - started_at
    return max(int(delta.total_seconds() * 1000), 0)

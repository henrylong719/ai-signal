"""Run-tracking wrapper around ``crud.ingest.ingest_all``.

This module exists because:
  - ``ingest_all`` is async and uses AsyncSession; the run-tracking
    writes are sync and use Session. Mixing them inside ingest_all
    would force every test of the underlying ingest path to also
    deal with run-tracking, which is the wrong coupling.
  - The wrapper is the single entry point for *every* ingestion —
    both the scheduled cron and the manual superuser POST. Any future
    triggers (a CLI command, a webhook) should also go through this
    wrapper so every run shows up in the admin page.

Session lifecycle: each lifecycle write (start, finish, fail) opens
its own short-lived sync Session against ``app.core.db.engine``.
Sessions are not reused across writes because the writes happen at
boundaries that may be seconds or minutes apart (the run itself runs
in between), and holding a connection idle across that span is wasteful.
"""

import logging
from typing import Any

from sqlmodel import Session

from app import crud
from app.core.db import engine
from app.crud.ingest import ingest_all

logger = logging.getLogger(__name__)


async def run_tracked_ingest() -> dict[str, Any]:
    """Run ``ingest_all`` and record the result in ``ingest_runs``.

    Returns the same dict shape ``ingest_all`` returns, plus a ``run_id``
    key so callers (the manual POST endpoint) can correlate the response
    with the row in the admin page.

    Failure modes:
      - ``ingest_all`` raises: the run row is updated with status="failed"
        and the exception's str() as the single error. The exception is
        re-raised so the caller (or scheduler) sees it.
      - ``ingest_all`` returns errors but doesn't raise: the run row is
        finished with status="failed" and the errors list. No re-raise —
        partial source failures are an expected operational state, not
        an exception.
      - The run-tracking writes themselves fail: logged, swallowed. The
        underlying ingestion succeeded, and we'd rather lose visibility
        on one run than fail an otherwise-successful ingestion.
    """
    with Session(engine) as session:
        run = crud.start_ingest_run(session=session)
    run_id = run.id

    try:
        result = await ingest_all()
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_all raised; recording failed run")
        try:
            with Session(engine) as session:
                crud.fail_ingest_run(
                    session=session,
                    run_id=run_id,
                    error=f"{type(exc).__name__}: {exc}",
                )
        except Exception:  # noqa: BLE001
            # Don't let a logging-table write failure mask the real
            # exception. The original exception is what callers need.
            logger.exception("Failed to record run failure for run_id=%s", run_id)
        raise

    inserted_raw = result.get("inserted", 0)
    skipped_raw = result.get("skipped", 0)
    embedded_raw = result.get("embedded", 0)
    errors_raw = result.get("errors", [])

    # Defensive coercion: ingest_all's return type is loosely typed
    # (IngestResult = dict[str, int | list[str]]). The DB columns are
    # typed; we'd rather coerce here with a sane fallback than let a
    # surprise value crash the lifecycle write.
    inserted = int(inserted_raw) if isinstance(inserted_raw, int) else 0
    skipped = int(skipped_raw) if isinstance(skipped_raw, int) else 0
    embedded = int(embedded_raw) if isinstance(embedded_raw, int) else 0
    errors = list(errors_raw) if isinstance(errors_raw, list) else []

    try:
        with Session(engine) as session:
            crud.finish_ingest_run(
                session=session,
                run_id=run_id,
                inserted=inserted,
                skipped=skipped,
                embedded=embedded,
                errors=[str(e) for e in errors],
            )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to record run completion for run_id=%s; ingestion itself succeeded",
            run_id,
        )

    return {**result, "run_id": str(run_id)}

"""CRUD tests for ingest_runs.

Exercises the lifecycle: start_run → finish_run (success and partial-fail
paths) → fail_run → list_runs ordering.
"""

import time

from sqlmodel import Session

from app import crud
from app.models import IngestRun


def test_start_ingest_run_creates_running_row(db: Session) -> None:
    run = crud.start_ingest_run(session=db)

    assert run.id is not None
    assert run.status == "running"
    assert run.finished_at is None
    assert run.duration_ms is None
    assert run.inserted == 0
    assert run.skipped == 0
    assert run.embedded == 0
    assert run.errors == []


def test_finish_ingest_run_success_path(db: Session) -> None:
    run = crud.start_ingest_run(session=db)

    # Tiny sleep so duration_ms is observably > 0.
    time.sleep(0.01)

    finished = crud.finish_ingest_run(
        session=db,
        run_id=run.id,
        inserted=12,
        skipped=3,
        embedded=12,
        errors=[],
    )

    assert finished is not None
    assert finished.id == run.id
    assert finished.status == "succeeded"
    assert finished.finished_at is not None
    assert finished.duration_ms is not None
    assert finished.duration_ms >= 0
    assert finished.inserted == 12
    assert finished.skipped == 3
    assert finished.embedded == 12
    assert finished.errors == []


def test_finish_ingest_run_with_errors_marks_failed(db: Session) -> None:
    """A finished run with non-empty errors is status="failed".

    This covers the partial-source-failure case: ingest_all returned
    cleanly but reported per-source errors. From an operator's view
    that's still a failed run.
    """
    run = crud.start_ingest_run(session=db)

    finished = crud.finish_ingest_run(
        session=db,
        run_id=run.id,
        inserted=5,
        skipped=0,
        embedded=5,
        errors=["source-a: timeout", "source-b: 500"],
    )

    assert finished is not None
    assert finished.status == "failed"
    assert finished.errors == ["source-a: timeout", "source-b: 500"]
    # Counts are still recorded — we want to know the partial result.
    assert finished.inserted == 5


def test_fail_ingest_run_records_exception(db: Session) -> None:
    run = crud.start_ingest_run(session=db)

    failed = crud.fail_ingest_run(
        session=db,
        run_id=run.id,
        error="ConnectionError: db unreachable",
    )

    assert failed is not None
    assert failed.status == "failed"
    assert failed.errors == ["ConnectionError: db unreachable"]
    assert failed.finished_at is not None
    assert failed.duration_ms is not None


def test_finish_ingest_run_returns_none_for_unknown_id(db: Session) -> None:
    """Defensive: a missing row shouldn't crash the lifecycle write."""
    import uuid

    result = crud.finish_ingest_run(
        session=db,
        run_id=uuid.uuid4(),
        inserted=0,
        skipped=0,
        embedded=0,
        errors=[],
    )
    assert result is None


def test_list_ingest_runs_orders_most_recent_first(db: Session) -> None:
    # Clean slate — other tests in this module may have written rows.
    from sqlmodel import delete

    db.exec(delete(IngestRun))
    db.commit()

    first = crud.start_ingest_run(session=db)
    time.sleep(0.01)
    second = crud.start_ingest_run(session=db)
    time.sleep(0.01)
    third = crud.start_ingest_run(session=db)

    runs = crud.list_ingest_runs(session=db, limit=10)

    assert len(runs) == 3
    assert [r.id for r in runs] == [third.id, second.id, first.id]


def test_list_ingest_runs_filters_by_status(db: Session) -> None:
    from sqlmodel import delete

    db.exec(delete(IngestRun))
    db.commit()

    succeeded = crud.start_ingest_run(session=db)
    crud.finish_ingest_run(
        session=db,
        run_id=succeeded.id,
        inserted=1,
        skipped=0,
        embedded=1,
        errors=[],
    )

    failed = crud.start_ingest_run(session=db)
    crud.fail_ingest_run(session=db, run_id=failed.id, error="boom")

    crud.start_ingest_run(session=db)  # leave one running

    succeeded_runs = crud.list_ingest_runs(session=db, status="succeeded")
    assert len(succeeded_runs) == 1
    assert succeeded_runs[0].id == succeeded.id

    failed_runs = crud.list_ingest_runs(session=db, status="failed")
    assert len(failed_runs) == 1
    assert failed_runs[0].id == failed.id

    running_runs = crud.list_ingest_runs(session=db, status="running")
    assert len(running_runs) == 1

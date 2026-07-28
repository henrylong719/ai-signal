"""Tests for the run-tracked ingest wrapper.

We don't run the real ingest_all here (no live RSS feeds in tests).
Instead we monkeypatch ingest_all to return canned results or raise,
and assert the wrapper records the right row in ingest_runs.

These tests use ``asyncio.run`` rather than pytest-asyncio. The wrapper
is the only async surface in this file and the test suite doesn't use
pytest-asyncio elsewhere; pulling it in for one file isn't worth the
dep.
"""

import asyncio

import pytest
from sqlmodel import Session, delete, select

from app import crud  # noqa: F401  (kept for symmetry with other test files)
from app.models import IngestRun
from app.services import ingest_runner


@pytest.fixture(autouse=True)
def _clean_runs(db: Session):  # type: ignore[no-untyped-def]
    """Each test starts with no ingest_runs rows.

    Module-scoped DB fixture means cleanup in teardown is symmetric —
    we don't want runs from a previous test polluting the next list.
    """
    db.exec(delete(IngestRun))
    db.commit()
    yield
    db.exec(delete(IngestRun))
    db.commit()


def test_run_tracked_ingest_success(monkeypatch, db: Session) -> None:  # type: ignore[no-untyped-def]
    async def fake_ingest_all() -> dict[str, object]:
        return {"inserted": 7, "skipped": 2, "embedded": 7, "errors": []}

    monkeypatch.setattr(ingest_runner, "ingest_all", fake_ingest_all)

    result = asyncio.run(ingest_runner.run_tracked_ingest())

    assert result["inserted"] == 7
    assert result["skipped"] == 2
    assert result["embedded"] == 7
    assert result["errors"] == []
    assert "run_id" in result

    # Exactly one row was written, in the succeeded state.
    runs = list(db.exec(select(IngestRun)).all())
    assert len(runs) == 1
    run = runs[0]
    assert str(run.id) == result["run_id"]
    assert run.status == "succeeded"
    assert run.inserted == 7
    assert run.skipped == 2
    assert run.embedded == 7
    assert run.errors == []
    assert run.finished_at is not None


def test_run_tracked_ingest_partial_errors(monkeypatch, db: Session) -> None:  # type: ignore[no-untyped-def]
    """ingest_all returned errors but didn't raise → status=degraded,
    counts still recorded, no exception propagated."""

    async def fake_ingest_all() -> dict[str, object]:
        return {
            "inserted": 3,
            "skipped": 1,
            "embedded": 3,
            "errors": ["source-a: timeout"],
        }

    monkeypatch.setattr(ingest_runner, "ingest_all", fake_ingest_all)

    result = asyncio.run(ingest_runner.run_tracked_ingest())
    assert result["errors"] == ["source-a: timeout"]

    runs = list(db.exec(select(IngestRun)).all())
    assert len(runs) == 1
    assert runs[0].status == "degraded"
    assert runs[0].inserted == 3
    assert runs[0].errors == ["source-a: timeout"]


def test_run_tracked_ingest_reraises_and_records_failure(  # type: ignore[no-untyped-def]
    monkeypatch, db: Session
) -> None:
    """ingest_all itself raised → wrapper records failed row and re-raises.

    Re-raising matters for the scheduler: APScheduler logs unhandled
    job exceptions, which is the visibility we want for catastrophic
    failures (DB down, model load errors, etc.)."""

    async def fake_ingest_all() -> dict[str, object]:
        raise RuntimeError("db connection lost")

    monkeypatch.setattr(ingest_runner, "ingest_all", fake_ingest_all)

    with pytest.raises(RuntimeError, match="db connection lost"):
        asyncio.run(ingest_runner.run_tracked_ingest())

    runs = list(db.exec(select(IngestRun)).all())
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].errors == ["RuntimeError: db connection lost"]
    assert runs[0].inserted == 0
    assert runs[0].skipped == 0


def test_run_tracked_ingest_coerces_unexpected_value_types(  # type: ignore[no-untyped-def]
    monkeypatch, db: Session
) -> None:
    """The wrapper defends against ingest_all returning surprise types.

    The ingest_all return type is loosely typed; if a future change
    accidentally returns a string for a count, we don't want the
    lifecycle write to crash. Defensive coercion lives in the wrapper."""

    async def fake_ingest_all() -> dict[str, object]:
        return {
            "inserted": "not-an-int",  # nonsense
            "skipped": 5,
            "embedded": None,
            "errors": [],
        }

    monkeypatch.setattr(ingest_runner, "ingest_all", fake_ingest_all)

    asyncio.run(ingest_runner.run_tracked_ingest())

    runs = list(db.exec(select(IngestRun)).all())
    assert len(runs) == 1
    # Bad types coerced to 0; good types preserved.
    assert runs[0].inserted == 0
    assert runs[0].skipped == 5
    assert runs[0].embedded == 0
    assert runs[0].status == "succeeded"

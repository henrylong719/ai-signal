"""Admin endpoint for ingestion run history.

Superuser-only. Returns the most recent ingestion runs with status,
counts, duration, and any errors. Powers the admin /ingest-runs page
in the frontend.

GET /admin/ingest-runs
  Optional query params:
    limit  (default 50, max 200) — number of runs to return
    status (optional)            — filter to "running" / "succeeded" / "failed"
  Returns: { data: list[IngestRunPublic], count: int }
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import SQLModel

from app import crud
from app.api.deps import SessionDep, get_current_active_superuser
from app.models import IngestRunStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


class IngestRunPublic(BaseModel):
    """Wire shape of one run.

    Fields mirror the IngestRun model with two adjustments:
      - id is serialized as a string (UUID) for the JS client.
      - errors is always a list of strings; the model's JSONB column
        could hold richer structures in the future, but the current
        contract is "human-readable error messages."
    """

    id: str
    started_at: str
    finished_at: str | None
    status: IngestRunStatus
    inserted: int
    skipped: int
    embedded: int
    duration_ms: int | None
    errors: list[str]


class IngestRunsPublic(SQLModel):
    """Paginated wrapper. ``count`` is the page size, not a total —
    listing is bounded and the admin page doesn't paginate yet."""

    data: list[IngestRunPublic]
    count: int


@router.get("/ingest-runs", response_model=IngestRunsPublic)
def read_ingest_runs(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    status: IngestRunStatus | None = Query(default=None),
) -> Any:
    """List recent ingestion runs, most recent first.

    No total-count query: the admin page renders a flat list of recent
    runs and doesn't paginate. If we ever need full pagination, add a
    count query alongside the listing.
    """

    print("runnnnnnnnnn")
    runs = crud.list_ingest_runs(session=session, limit=limit, status=status)
    data = [
        IngestRunPublic(
            id=str(run.id),
            started_at=run.started_at.isoformat(),
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
            status=run.status,
            inserted=run.inserted,
            skipped=run.skipped,
            embedded=run.embedded,
            duration_ms=run.duration_ms,
            errors=list(run.errors) if run.errors else [],
        )
        for run in runs
    ]
    return IngestRunsPublic(data=data, count=len(data))

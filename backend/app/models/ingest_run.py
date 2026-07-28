"""IngestRun: one row per ingestion run.

The row is written at the *start* of a run with status="running" and
updated at the end to "succeeded", "degraded", or "failed". This shape lets the
admin UI distinguish "currently running" from "never finished" — the
latter being a process that died mid-run, which we don't auto-recover
but do want to surface.

The table is append-only from the application's perspective: there's no
update path other than the lifecycle finish_run / fail_run write. Old
rows can be pruned by an operator with a one-off SQL when the table
gets unwieldy; we don't ship a retention policy because at one row per
30 minutes we accumulate ~17k rows/year, which Postgres handles fine.

Column choices worth noting:
  - status is a Postgres ENUM, matching the article_event_type pattern.
    ``degraded`` distinguishes a completed ingest with per-source or
    embedding errors from a catastrophic failure that aborted the run.
  - errors is JSONB, not Text. We store a list of error strings; if we
    later want structured per-source errors with stack traces, JSONB
    accommodates without a schema migration.
  - duration_ms is a derived field (finished_at - started_at) but we
    persist it because reading it sorted is useful for spotting slow
    runs and the alternative — computing in SQL on every read — is
    less ergonomic from SQLModel.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc

# Allowed values for IngestRun.status. Kept in lockstep with the
# Postgres ENUM created in the migration.
IngestRunStatus = Literal["running", "succeeded", "degraded", "failed"]
INGEST_RUN_STATUSES: tuple[IngestRunStatus, ...] = (
    "running",
    "succeeded",
    "degraded",
    "failed",
)


class IngestRun(SQLModel, table=True):
    __tablename__ = "ingest_runs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
    started_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    status: IngestRunStatus = Field(
        sa_column=Column(
            ENUM(
                "running",
                "succeeded",
                "degraded",
                "failed",
                name="ingest_run_status",
                create_type=False,
            ),
            nullable=False,
        )
    )
    inserted: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    skipped: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    embedded: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    duration_ms: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    # JSONB list of error strings. Empty list (not null) is the
    # expected shape for a successful run with no errors.
    errors: Any = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

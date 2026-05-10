"""Anonymous guest funnel events.

Append-only log of high-level product events from logged-out visitors.
Distinct from ``ArticleEvent`` (which is aggregated, per-user, used for
personalization). The guest log answers product questions instead:
"did anyone click an article before signing up?", "which CTA converts?".

Design notes
------------
- One row per event. We *don't* dedupe-then-count like ArticleEvent
  because we want raw time-series totals over a window, and the volume
  is bounded by how many guests visit (small).
- ``anonymous_id`` is a client-generated UUID kept in localStorage. We
  store it as Text rather than UUID because the column should accept
  malformed input gracefully (we validate length but not exact shape) —
  see the route validator.
- ``user_id`` is optional and only set on ``guest_signup_completed`` to
  attribute conversions. We deliberately don't backfill prior events
  with the new user_id; the link via anonymous_id is enough for funnel
  analysis and keeps the model simple.
- ``metadata`` is JSONB with a hard size cap at the route layer. Used
  primarily for ``{"location": "hero"}`` on CTA events.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import Text
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc
from app.schemas.guest_analytics import GUEST_EVENT_TYPES, GuestEventType

# Re-export so existing imports (``from app.models import GuestEvent,
# GUEST_EVENT_TYPES``) keep working without callers needing to know that
# the literal source-of-truth lives in schemas.
__all__ = ["GUEST_EVENT_TYPES", "GuestEvent", "GuestEventType"]


class GuestEvent(SQLModel, table=True):
    __tablename__ = "guest_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    anonymous_id: str = Field(sa_column=Column(String(64), nullable=False))
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    event_type: str = Field(sa_column=Column(String(40), nullable=False))
    path: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    article_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("articles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    source_name: str | None = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    topic: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))
    referrer: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    event_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
    )

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    __table_args__ = (
        # Primary read shape: "give me counts by event_type in a date window".
        Index("ix_guest_events_event_type_created_at", "event_type", "created_at"),
        # Used by admin "is this anonymous_id active today" lookups + the
        # signup-completion attribution path.
        Index("ix_guest_events_anonymous_id_created_at", "anonymous_id", "created_at"),
    )

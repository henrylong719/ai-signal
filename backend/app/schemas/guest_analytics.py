"""Pydantic schemas for the guest analytics feature.

Two surfaces:

- ``GuestEventCreate`` — payload accepted by the public POST endpoint.
  Validation is strict by design: unknown ``event_type`` is rejected,
  the anonymous_id format is bounded, and metadata is size-limited so
  a malicious caller can't grow the table with a few JSON kilobytes per
  call.

- ``GuestFunnelResponse`` and friends — admin dashboard payload. Keep
  the shape flat and self-describing; the admin UI maps these straight
  into cards and tables.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import SQLModel

# Allowed values for ``GuestEvent.event_type``. Mirrored on the route
# validator and on the model so the source of truth lives in one place.
GuestEventType = Literal[
    "guest_page_view",
    "guest_article_click",
    "guest_source_click",
    "guest_topic_click",
    "guest_signup_click",
    "guest_login_click",
    "guest_signup_completed",
]
GUEST_EVENT_TYPES: tuple[GuestEventType, ...] = (
    "guest_page_view",
    "guest_article_click",
    "guest_source_click",
    "guest_topic_click",
    "guest_signup_click",
    "guest_login_click",
    "guest_signup_completed",
)

# Hard cap on serialized metadata. 2 KiB is plenty for ``{"location": "..."}``
# and similar small bags, but small enough that flooding the table is not
# attractive.
_MAX_METADATA_BYTES = 2048
_MAX_METADATA_KEYS = 20
_MAX_ANONYMOUS_ID_LENGTH = 64
_MAX_PATH_LENGTH = 512
_MAX_TOPIC_LENGTH = 64
_MAX_SOURCE_NAME_LENGTH = 64
_MAX_REFERRER_LENGTH = 1024

DateRange = Literal["7d", "30d", "90d", "all"]
ALLOWED_RANGES: tuple[DateRange, ...] = ("7d", "30d", "90d", "all")


def _is_flat_json_scalar(value: Any) -> bool:
    """True for JSON values we allow inside ``metadata`` (no nesting)."""

    if value is None:
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return True
    return isinstance(value, str)


class GuestEventCreate(BaseModel):
    """Payload for the public guest-event intake endpoint.

    Defined as a plain ``pydantic.BaseModel`` rather than ``SQLModel``
    because SQLModel reserves the ``metadata`` attribute for SQLAlchemy's
    ``MetaData`` binding; a field called ``metadata`` on a SQLModel
    subclass is silently shadowed at instance-access time.
    """

    model_config = ConfigDict(populate_by_name=True)

    anonymous_id: str = Field(min_length=1, max_length=_MAX_ANONYMOUS_ID_LENGTH)
    event_type: GuestEventType
    path: str | None = Field(default=None, max_length=_MAX_PATH_LENGTH)
    article_id: uuid.UUID | None = None
    source_id: str | None = Field(
        default=None,
        max_length=_MAX_SOURCE_NAME_LENGTH,
        description=(
            "Logical source identifier. In AI Signal sources are keyed by "
            "their display name (see ``schemas.source.SOURCES``), so this "
            "accepts a string rather than a UUID."
        ),
    )
    topic: str | None = Field(default=None, max_length=_MAX_TOPIC_LENGTH)
    referrer: str | None = Field(default=None, max_length=_MAX_REFERRER_LENGTH)
    user_id: uuid.UUID | None = None
    # Stored as ``event_metadata`` on the instance because ``metadata`` is
    # reserved on SQLAlchemy/SQLModel parents and would be shadowed on a
    # SQLModel; the wire-level JSON key stays ``metadata`` via alias.
    event_metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("event_type")
    @classmethod
    def _event_type_known(cls, value: str) -> str:
        # Pydantic Literal validation rejects unknowns first; explicit
        # check duplicated here for a clearer error message.
        if value not in GUEST_EVENT_TYPES:
            raise ValueError(f"Unknown event_type: {value!r}")
        return value

    @field_validator("event_metadata")
    @classmethod
    def _metadata_size_capped(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        if len(value) > _MAX_METADATA_KEYS:
            raise ValueError(f"metadata accepts at most {_MAX_METADATA_KEYS} keys")
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            if not _is_flat_json_scalar(nested):
                raise ValueError(
                    "metadata values must be flat scalars (str, number, bool, null); "
                    "nested objects and arrays are not accepted"
                )
        serialized = json.dumps(value, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _MAX_METADATA_BYTES:
            raise ValueError(f"metadata exceeds {_MAX_METADATA_BYTES}-byte limit")
        return value


class FunnelCounts(SQLModel):
    """Raw event counts inside the selected window."""

    guest_page_view: int = 0
    guest_article_click: int = 0
    guest_source_click: int = 0
    guest_topic_click: int = 0
    guest_signup_click: int = 0
    guest_login_click: int = 0
    guest_signup_completed: int = 0


class FunnelRates(SQLModel):
    """Derived conversion ratios. 0.0 when the denominator is zero."""

    article_click_rate: float = 0.0
    signup_click_rate: float = 0.0
    signup_conversion_rate: float = 0.0


class TopArticleRow(SQLModel):
    article_id: uuid.UUID
    title: str | None = None
    source_name: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    guest_clicks: int


class TopSourceRow(SQLModel):
    source_name: str
    guest_clicks: int


class TopTopicRow(SQLModel):
    topic: str
    guest_clicks: int


class CtaLocationRow(SQLModel):
    location: str
    clicks: int
    # NOTE: completed_signups by-location attribution is left for a
    # follow-up. The MVP returns CTA click counts only, with completion
    # totals shown in the summary cards. Add per-location attribution by
    # joining on ``anonymous_id`` once we have meaningful guest traffic.
    completed_signups: int | None = None
    conversion_rate: float | None = None


class GuestFunnelResponse(SQLModel):
    range: DateRange
    range_start: datetime | None = None
    range_end: datetime
    counts: FunnelCounts
    rates: FunnelRates
    top_articles: list[TopArticleRow]
    top_sources: list[TopSourceRow]
    top_topics: list[TopTopicRow]
    signup_cta_locations: list[CtaLocationRow]

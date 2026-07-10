"""Pydantic schemas for user feedback submissions."""

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator
from sqlmodel import SQLModel

FeedbackCategory = Literal[
    "general",
    "missing_topic_source_tag",
    "bad_recommendation",
    "feature_request",
    "bug_report",
]
FEEDBACK_CATEGORIES: tuple[FeedbackCategory, ...] = (
    "general",
    "missing_topic_source_tag",
    "bad_recommendation",
    "feature_request",
    "bug_report",
)

_MIN_MESSAGE_LENGTH = 10
_MAX_MESSAGE_LENGTH = 2000

# Same caps as guest-event metadata (see ``schemas.guest_analytics``):
# ``context`` is a small bag of UI breadcrumbs ({"path": ..., "source":
# ...}), not a dumping ground — without a ceiling any account can grow
# the JSONB column by megabytes per request.
_MAX_CONTEXT_BYTES = 2048
_MAX_CONTEXT_KEYS = 20


def _is_flat_json_scalar(value: Any) -> bool:
    """True for JSON values we allow inside ``context`` (no nesting)."""
    return value is None or isinstance(value, bool | int | float | str)


class FeedbackCreate(SQLModel):
    category: FeedbackCategory
    message: str = Field(min_length=_MIN_MESSAGE_LENGTH, max_length=_MAX_MESSAGE_LENGTH)
    context: dict[str, Any] | None = None

    @field_validator("message", mode="before")
    @classmethod
    def _strip_message(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("context")
    @classmethod
    def _context_size_capped(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        if len(value) > _MAX_CONTEXT_KEYS:
            raise ValueError(f"context accepts at most {_MAX_CONTEXT_KEYS} keys")
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError("context keys must be strings")
            if not _is_flat_json_scalar(nested):
                raise ValueError(
                    "context values must be flat scalars (str, number, bool, "
                    "null); nested objects and arrays are not accepted"
                )
        serialized = json.dumps(value, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _MAX_CONTEXT_BYTES:
            raise ValueError(f"context exceeds {_MAX_CONTEXT_BYTES}-byte limit")
        return value


class FeedbackPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category: FeedbackCategory
    message: str
    context: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

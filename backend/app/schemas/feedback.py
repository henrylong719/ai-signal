"""Pydantic schemas for user feedback submissions."""

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


class FeedbackPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category: FeedbackCategory
    message: str
    context: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

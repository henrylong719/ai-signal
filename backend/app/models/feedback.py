"""User-submitted product feedback and suggestions."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import Text
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc
from app.schemas.feedback import FeedbackCategory


class UserFeedback(SQLModel, table=True):
    __tablename__ = "user_feedback"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    category: FeedbackCategory = Field(sa_column=Column(String(40), nullable=False))
    message: str = Field(sa_column=Column(Text, nullable=False))
    context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

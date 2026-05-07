"""User interest preferences (explicit onboarding signal)."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.types import Text
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class UserInterest(SQLModel, table=True):
    """One row per user, holding their selected categories, tags, and preferred sources.

    Stored as TEXT[] arrays rather than a normalized join table because:
      - the row is always read whole by the recommender;
      - writes are full-replace from the settings UI;
      - interests are bounded to ~10 items in practice.

    See migration f4a5b6c7d8e9 for the original design rationale, and
    migration g5b6c7d8e9f1 for the preferred_sources addition.
    """

    __tablename__ = "user_interests"

    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )

    categories: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
    )

    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
    )

    preferred_sources: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
    )

    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

"""Cached user interest vector for the semantic-similarity layer."""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

from app.models.article import EMBEDDING_DIM
from app.models.base import get_datetime_utc


class UserEmbedding(SQLModel, table=True):
    """Precomputed semantic representation of a user's interests.

    Recomputed at write time — when the user saves/unsaves an article,
    clicks through to read one, or updates their stated interests.
    Read by the For-You service to avoid recomputing on every feed
    request. See migration b6c7d8e9f0a1 for the design rationale.

    Missing row = no vector cached yet. The For-You service falls back
    to a live build (and writes the cache) on first read, so cold-start
    users self-warm without any separate backfill step.
    """

    __tablename__ = "user_embeddings"

    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    embedding: Any = Field(
        sa_column=Column(Vector(EMBEDDING_DIM), nullable=False),
        exclude=True,
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

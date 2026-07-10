"""Anonymous email subscribers for the daily digest newsletter."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class DigestSubscriber(SQLModel, table=True):
    __tablename__ = "digest_subscribers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(
        sa_column=Column(String(320), nullable=False, unique=True, index=True)
    )
    is_active: bool = Field(default=True, nullable=False)
    # When the last digest send to this subscriber completed. Idempotency
    # key for the daily scheduled job (same UTC calendar day → skip), same
    # role as ``User.last_digest_sent_at``. NULL means never sent.
    last_digest_sent_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

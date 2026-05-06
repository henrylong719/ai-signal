import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class OAuthAccount(SQLModel, table=True):
    __tablename__ = "oauth_accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    provider: str = Field(sa_column=Column(String(32), nullable=False))
    provider_user_id: str = Field(sa_column=Column(String(255), nullable=False))
    email: str = Field(sa_column=Column(String(255), nullable=False))
    email_verified: bool = Field(default=False)
    display_name: str | None = Field(
        default=None, sa_column=Column(String(255), nullable=True)
    )
    avatar_url: str | None = Field(
        default=None, sa_column=Column(String(2048), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_accounts_provider_provider_user_id",
        ),
        Index("ix_oauth_accounts_user_id", "user_id"),
    )

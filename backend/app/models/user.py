import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field

from app.models.base import get_datetime_utc
from app.schemas.user import UserBase


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    has_password: bool = True
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    # IANA timezone string (e.g. "America/New_York"). Captured from the
    # browser at sign-up and used by the daily-digest scheduler to fire
    # the email at the user's local 6am rather than a single global UTC
    # hour. NULL means "not yet known" — sender treats unset as UTC.
    timezone: str | None = Field(
        default=None,
        sa_column=Column(String(64), nullable=True),
    )
    # Whether the user has opted in to the recurring daily-digest email.
    # Default False so we never auto-subscribe an account on creation;
    # the onboarding flow flips this on if the user accepts.
    daily_digest_enabled: bool = Field(default=False, nullable=False)
    # When the last successful digest send completed. The hourly job
    # uses this as an idempotency key (same calendar day → skip) so a
    # restart or duplicate fire can't deliver two emails.
    last_digest_sent_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # When first-run onboarding finished. NULL ⇒ the welcome modal
    # still shows on next sign-in. We never back-fill, so accounts that
    # predate the feature get the modal once.
    onboarded_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # Updated by get_current_user on each authenticated request, throttled
    # to ~5 minutes to avoid writing on every API call. NULL means the
    # user has never been seen since the column was added — admins read
    # this to gauge who is still active.
    last_seen_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

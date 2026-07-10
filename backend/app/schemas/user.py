import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import EmailStr, field_validator
from sqlmodel import Field, SQLModel


def _validate_optional_timezone(value: Any) -> Any:
    """Reject non-IANA timezone strings so we don't silently store a value
    that falls back to UTC at digest-send time. ``None``/empty stays valid
    (the sender treats unset as UTC by design)."""
    if value is None or value == "":
        return value
    if isinstance(value, str):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"Unknown timezone: {value!r}")
    return value


def _lowercase_email(value: Any) -> Any:
    """Canonicalize inbound emails so the password and OAuth signup paths
    can't create two accounts for one person differing only by case.
    Applied on the *input* schemas only — stored values are returned as-is.
    """
    if isinstance(value, str):
        return value.strip().lower()
    return value


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    _normalize_email = field_validator("email", mode="before")(_lowercase_email)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    _normalize_email = field_validator("email", mode="before")(_lowercase_email)


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)

    _normalize_email = field_validator("email", mode="before")(_lowercase_email)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)

    _normalize_email = field_validator("email", mode="before")(_lowercase_email)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserPublic(UserBase):
    id: uuid.UUID
    has_password: bool = True
    created_at: datetime | None = None
    # Surfaced to the client so the SPA can: open the onboarding modal
    # when ``onboarded_at`` is null, render the digest toggle in
    # /settings, and decide which timezone label to show.
    timezone: str | None = None
    daily_digest_enabled: bool = False
    onboarded_at: datetime | None = None
    # Read by the admin user table to flag dormant accounts. NULL ⇒
    # never seen since the column was introduced.
    last_seen_at: datetime | None = None


class OnboardingComplete(SQLModel):
    """Payload submitted at the end of the first-run onboarding flow.

    The client sends the timezone it detected from the browser plus
    whether the user accepted the daily digest opt-in. The endpoint
    sets ``onboarded_at = now()`` so the modal does not reopen.
    """

    # IANA timezone string. Optional — older browsers or privacy modes
    # may not expose it; in that case the sender falls back to UTC.
    timezone: str | None = Field(default=None, max_length=64)
    daily_digest_enabled: bool = False

    _validate_timezone = field_validator("timezone")(_validate_optional_timezone)


class DigestPreferencesUpdate(SQLModel):
    """Body for the settings-page digest toggle.

    Allows changing the opt-in flag and the cached timezone independent
    of the onboarding flow. Both fields are optional so the client can
    update only what changed.
    """

    daily_digest_enabled: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)

    _validate_timezone = field_validator("timezone")(_validate_optional_timezone)


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class OAuthAccountPublic(SQLModel):
    provider: str
    email: str
    email_verified: bool
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class OAuthAccountsPublic(SQLModel):
    data: list[OAuthAccountPublic]

"""Pydantic schemas for digest subscriptions."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel


class SubscriptionCreate(SQLModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class SubscriptionPublic(SQLModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

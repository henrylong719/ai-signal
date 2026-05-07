import uuid
from datetime import datetime

from sqlalchemy import DateTime
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

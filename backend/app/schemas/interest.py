"""Pydantic schemas for the user interests endpoints."""

from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from app.schemas.source import CATEGORIES, Category

# Tags are user-supplied free text. We cap quantity and length at the schema
# layer so the storage column can't be DOS'd by a malicious or buggy client.
_MAX_TAGS = 20
_MAX_TAG_LENGTH = 32
_MAX_CATEGORIES = len(CATEGORIES)


class UserInterestPublic(SQLModel):
    """Wire shape returned to the client.

    A user with no interests row in the DB still gets a valid response
    with empty lists — the frontend treats absence and emptiness as the
    same thing.
    """

    categories: list[Category] = []
    tags: list[str] = []
    updated_at: datetime | None = None


class UserInterestUpdate(SQLModel):
    """PUT body for /users/me/interests.

    Validation:
      - categories must be drawn from the Category Literal (Pydantic enforces).
      - tags are length- and count-bounded.
    """

    categories: list[Category] = Field(default_factory=list, max_length=_MAX_CATEGORIES)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_TAGS)

    def normalized_tags(self) -> list[str]:
        """Lowercase, strip, drop empties, drop duplicates, enforce length."""
        seen: set[str] = set()
        out: list[str] = []
        for raw in self.tags:
            tag: str = raw.strip().lower()
            if not tag or len(tag) > _MAX_TAG_LENGTH:
                continue
            if tag in seen:
                continue
            seen.add(tag)
            out.append(tag)
        return out

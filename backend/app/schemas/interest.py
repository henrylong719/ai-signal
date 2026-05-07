"""Pydantic schemas for the user interests endpoints."""

from datetime import datetime

from pydantic import Field, field_validator
from sqlmodel import SQLModel

from app.schemas.source import CATEGORIES, SOURCES, Category

# Tags are user-supplied free text. We cap quantity and length at the schema
# layer so the storage column can't be DOS'd by a malicious or buggy client.
_MAX_TAGS = 20
_MAX_TAG_LENGTH = 32
_MAX_CATEGORIES = len(CATEGORIES)
# Preferred sources are picked from a fixed, server-known list. We cap at
# the size of that list — picking every source is a meaningful "opt into
# everything" signal, but more than that is a bug or abuse.
_MAX_PREFERRED_SOURCES = len(SOURCES)

# Cached set of valid source names for fast membership checks. Built once
# at import time from the canonical SOURCES tuple.
_VALID_SOURCE_NAMES: frozenset[str] = frozenset(s.name for s in SOURCES)


class UserInterestPublic(SQLModel):
    """Wire shape returned to the client.

    A user with no interests row in the DB still gets a valid response
    with empty lists — the frontend treats absence and emptiness as the
    same thing.
    """

    categories: list[Category] = []
    tags: list[str] = []
    preferred_sources: list[str] = []
    updated_at: datetime | None = None


class UserInterestUpdate(SQLModel):
    """PUT body for /users/me/interests.

    Validation:
      - categories must be drawn from the Category Literal (Pydantic enforces).
      - tags are length- and count-bounded; normalized in `normalized_tags`.
      - preferred_sources must each be a known source name (validator below).
    """

    categories: list[Category] = Field(default_factory=list, max_length=_MAX_CATEGORIES)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_TAGS)
    preferred_sources: list[str] = Field(
        default_factory=list, max_length=_MAX_PREFERRED_SOURCES
    )

    @field_validator("preferred_sources")
    @classmethod
    def _validate_preferred_sources(cls, value: list[str]) -> list[str]:
        """Strip, dedupe (preserving first-seen order), and validate against SOURCES.

        Source names are case-sensitive matches against the canonical
        SOURCES list — display name is the identifier, no slug layer.
        Unknown names raise ValueError so FastAPI returns 422 with a
        precise message about which name was rejected.
        """
        seen: set[str] = set()
        out: list[str] = []
        for raw in value:
            name = raw.strip()
            if not name:
                continue
            if name in seen:
                continue
            if name not in _VALID_SOURCE_NAMES:
                raise ValueError(f"Unknown source: {name!r}")
            seen.add(name)
            out.append(name)
        return out

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

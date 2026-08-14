"""Pydantic schemas for the user interests endpoints."""

from collections.abc import Iterable
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


def known_source_names(names: Iterable[str]) -> list[str]:
    """Strip, dedupe (first-seen order), and keep only names still in SOURCES.

    Shared by the write path (validator below) and the read path
    (`app.api.routes.interest.read_interests`) so both agree on what
    counts as a live source.

    Unknown names are dropped rather than rejected. Sources get retired
    from SOURCES as curation changes, and a stored preference outlives the
    source it points at: the client faithfully echoes back the list the
    server gave it, so raising here would 422 the entire save and lock the
    user out of changing *any* source until their row was hand-edited.
    Dropping makes the round-trip self-healing — the stale name disappears
    on the user's next save.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in names:
        name = raw.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        if name in _VALID_SOURCE_NAMES:
            out.append(name)
    return out


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
      - preferred_sources are filtered to known source names (validator below).
    """

    categories: list[Category] = Field(default_factory=list, max_length=_MAX_CATEGORIES)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_TAGS)
    preferred_sources: list[str] = Field(
        default_factory=list, max_length=_MAX_PREFERRED_SOURCES
    )

    @field_validator("preferred_sources", mode="before")
    @classmethod
    def _validate_preferred_sources(cls, value: object) -> object:
        """Strip, dedupe, and drop names no longer in SOURCES.

        Source names are case-sensitive matches against the canonical
        SOURCES list — display name is the identifier, no slug layer. See
        `known_source_names` for why unknown names are dropped instead of
        rejected.

        Runs in "before" mode so the `max_length` cap applies to the
        filtered list rather than the raw payload. In "after" mode, a user
        following (nearly) every source who also carried a few retired
        names would blow the cap on the raw list and get rejected before
        the filter could drop the dead names — reintroducing the lockout
        this filtering exists to prevent. The cap's job is to bound what
        we *store*, and filtering already guarantees that ceiling.

        Non-list input is passed through untouched so Pydantic's own type
        error surfaces instead of a confusing one from here.
        """
        # Intentional, in both early returns below: hand malformed input
        # straight back to Pydantic so it reports the real type error
        # against the declared list[str]. Do not "fix" this into a raise or
        # a coercion — a client sending {"preferred_sources": "OpenAI"}
        # should be told it sent a string where a list belongs, not get a
        # bespoke message from here or a silently wrapped value.
        if not isinstance(value, list):
            return value

        # Accumulate into an annotated list rather than testing with
        # all(isinstance(...) for ...). The generator form asserts the
        # element type without establishing it: `value` stays list[object]
        # to a type checker, so passing it to known_source_names(Iterable[str])
        # is an error rather than something narrowing can discharge. Building
        # the list makes the guarantee real at the point of use.
        names: list[str] = []
        for item in value:
            if not isinstance(item, str):
                return value
            names.append(item)
        return known_source_names(names)

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

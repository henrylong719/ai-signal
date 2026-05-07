"""CRUD for UserInterest — explicit onboarding signals.

`set_interests` is an upsert: the user picks their interests in the settings
UI and we full-replace whatever was stored before. This matches the UX (a
form, not a queue of "add" / "remove" actions) and avoids the
get-then-create-or-update dance at the API layer.
"""

import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from app.models.base import get_datetime_utc
from app.models.interest import UserInterest


def get_interests(*, session: Session, user_id: uuid.UUID) -> UserInterest | None:
    """Returns None if the user has never set interests.

    The API layer treats absence as "empty" rather than "missing" — a fresh
    user with no preferences is a valid state, not an error.
    """
    return session.get(UserInterest, user_id)


def set_interests(
    *,
    session: Session,
    user_id: uuid.UUID,
    categories: list[str],
    tags: list[str],
    preferred_sources: list[str],
) -> UserInterest:
    """Full-replace the user's stored interests.

    Validation of category/tag/source values against the allowed sets is
    the API layer's job — this function trusts its inputs. We normalize
    tags to lowercase here because tags come from free-form text input
    upstream. Categories and preferred_sources are sorted to keep storage
    deterministic (helpful for tests and for cache-key stability).
    """
    normalized_tags = sorted({t.strip().lower() for t in tags if t.strip()})
    normalized_categories = sorted(set(categories))
    # Preferred sources are case-sensitive display names from SOURCES;
    # the API-layer validator already deduped and stripped them. We sort
    # for storage determinism.
    normalized_sources = sorted(set(preferred_sources))
    now = get_datetime_utc()

    stmt = pg_insert(UserInterest).values(
        user_id=user_id,
        categories=normalized_categories,
        tags=normalized_tags,
        preferred_sources=normalized_sources,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "categories": normalized_categories,
            "tags": normalized_tags,
            "preferred_sources": normalized_sources,
            "updated_at": now,
        },
    )
    session.exec(stmt)
    session.commit()

    # Re-fetch so the caller gets the canonical row, not a stale snapshot.
    refreshed = session.get(UserInterest, user_id)
    assert refreshed is not None  # we just upserted it
    return refreshed

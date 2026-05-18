"""GET / PUT /users/me/interests — explicit onboarding signal management."""

import logging
import uuid
from datetime import datetime
from typing import cast

from fastapi import APIRouter
from sqlmodel import Session

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.schemas import UserInterestPublic, UserInterestUpdate
from app.schemas.source import Category
from app.services.embeddings import compute_and_save_user_vector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me/interests", tags=["interests"])


def _stored_categories_to_public(categories: list[str]) -> list[Category]:
    return [cast(Category, category) for category in categories]


def _refresh_user_vector(session: Session, user_id: uuid.UUID) -> None:
    """Best-effort recompute of the cached user interest vector.

    Mirrors ``app.api.routes.article._refresh_user_vector``. Duplication
    is intentional: embedding-pipeline failures here must not break the
    interest-update operation, and centralising the helper would mean
    importing it across modules where the import graph is already busy.

    Note: preferred_sources do NOT flow into the user embedding (they
    affect the source-affinity component of the score, not the semantic
    component). When only preferred_sources change, this recompute is
    effectively a no-op at the embedding level — but we still call it to
    keep the trigger-on-any-change contract simple.
    """
    try:
        compute_and_save_user_vector(session=session, user_id=user_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to refresh user interest vector for %s after interests "
            "update; will fall back to live recompute on next /for-you request",
            user_id,
        )


def _to_public(
    *,
    categories: list[Category] | None,
    tags: list[str] | None,
    preferred_sources: list[str] | None,
    updated_at: datetime | None,
) -> UserInterestPublic:
    """Construct the public response shape from arbitrary inputs.

    Centralized so empty/missing rows and existing rows produce identical
    shapes — the frontend should never need to special-case "no row yet".
    """
    return UserInterestPublic(
        categories=list(categories or []),
        tags=list(tags or []),
        preferred_sources=list(preferred_sources or []),
        updated_at=updated_at,
    )


@router.get("", response_model=UserInterestPublic)
def read_interests(
    session: SessionDep,
    current_user: CurrentUser,
) -> UserInterestPublic:
    """Current user's stored interests, or empty defaults if none set."""
    row = crud.get_interests(session=session, user_id=current_user.id)
    if row is None:
        return _to_public(categories=[], tags=[], preferred_sources=[], updated_at=None)
    # The DB stores categories as TEXT[]; we trust the stored values to
    # already match the Category Literal because the writer validates them.
    return _to_public(
        categories=_stored_categories_to_public(row.categories),
        tags=row.tags,
        preferred_sources=row.preferred_sources,
        updated_at=row.updated_at,
    )


@router.put("", response_model=UserInterestPublic)
def update_interests(
    session: SessionDep,
    current_user: CurrentUser,
    body: UserInterestUpdate,
) -> UserInterestPublic:
    """Replace the current user's interests with the provided lists.

    Pydantic enforces that `body.categories` is a subset of the Category
    Literal and that `body.preferred_sources` is a subset of SOURCES.
    Tag normalization (lowercase, trim, dedupe, length cap) happens in
    `body.normalized_tags()` before reaching the DB layer.
    """
    previous = crud.get_interests(session=session, user_id=current_user.id)
    row = crud.set_interests(
        session=session,
        user_id=current_user.id,
        categories=list(body.categories),
        tags=body.normalized_tags(),
        preferred_sources=list(body.preferred_sources),
    )
    # Only categories and tags flow into the user vector — recomputing on
    # preferred_sources-only changes is wasted work that blocks the PUT
    # response (the follow button stays in a "Saving" state until it
    # returns). Skip the refresh unless the embedding-relevant inputs
    # actually changed.
    prev_categories = set(previous.categories) if previous else set()
    prev_tags = set(previous.tags) if previous else set()
    if prev_categories != set(row.categories) or prev_tags != set(row.tags):
        _refresh_user_vector(session, current_user.id)
    return _to_public(
        categories=_stored_categories_to_public(row.categories),
        tags=row.tags,
        preferred_sources=row.preferred_sources,
        updated_at=row.updated_at,
    )

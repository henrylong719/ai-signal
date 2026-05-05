"""GET / PUT /users/me/interests — explicit onboarding signal management."""

from datetime import datetime
from typing import cast

from fastapi import APIRouter

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.schemas import UserInterestPublic, UserInterestUpdate
from app.schemas.source import Category

router = APIRouter(prefix="/users/me/interests", tags=["interests"])


def _stored_categories_to_public(categories: list[str]) -> list[Category]:
    return [cast(Category, category) for category in categories]


def _to_public(
    *,
    categories: list[Category] | None,
    tags: list[str] | None,
    updated_at: datetime | None,
) -> UserInterestPublic:
    """Construct the public response shape from arbitrary inputs.

    Centralized so empty/missing rows and existing rows produce identical
    shapes — the frontend should never need to special-case "no row yet".
    """
    return UserInterestPublic(
        categories=list(categories or []),
        tags=list(tags or []),
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
        return _to_public(categories=[], tags=[], updated_at=None)
    # The DB stores categories as TEXT[]; we trust the stored values to
    # already match the Category Literal because the writer validates them.
    return _to_public(
        categories=_stored_categories_to_public(row.categories),
        tags=row.tags,
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
    Literal; tag normalization (lowercase, trim, dedupe, length cap) happens
    in `body.normalized_tags()` before reaching the DB layer.
    """
    row = crud.set_interests(
        session=session,
        user_id=current_user.id,
        categories=list(body.categories),
        tags=body.normalized_tags(),
    )
    return _to_public(
        categories=_stored_categories_to_public(row.categories),
        tags=row.tags,
        updated_at=row.updated_at,
    )

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from sqlmodel import SQLModel

from app.api.deps import OptionalCurrentUser, SessionDep
from app.schemas import ArticlePublic
from app.services.digest import DigestPublic, DigestSection, build_digest

router = APIRouter(prefix="/digest", tags=["digest"])


# --- Wire schemas -----------------------------------------------------------
#
# These mirror the dataclasses in services.digest but project Article
# rows down to ArticlePublic (the same shape /articles/ returns) and
# attach the per-article `reason` inline — same pattern as
# ForYouArticlePublic in services/for_you.


class DigestArticlePublic(ArticlePublic):
    """ArticlePublic plus the recommender's reason string.

    Matches ForYouArticlePublic's shape so the frontend can reuse the
    same article-card rendering and reason-badge component.
    """

    reason: str | None = None


class DigestSectionPublic(SQLModel):
    key: str
    title: str
    articles: list[DigestArticlePublic]


class DigestPublicSchema(SQLModel):
    generated_at: datetime
    window_start: datetime
    is_personalized: bool
    sections: list[DigestSectionPublic]


# --- Serialization ----------------------------------------------------------


def _serialize_section(section: DigestSection) -> DigestSectionPublic:
    articles = [
        DigestArticlePublic(
            **ArticlePublic.model_validate(article).model_dump(),
            reason=section.reasons.get(article.id),
        )
        for article in section.articles
    ]
    return DigestSectionPublic(
        key=section.key,
        title=section.title,
        articles=articles,
    )


def _serialize_digest(digest: DigestPublic) -> DigestPublicSchema:
    return DigestPublicSchema(
        generated_at=digest.generated_at,
        window_start=digest.window_start,
        is_personalized=digest.is_personalized,
        sections=[_serialize_section(s) for s in digest.sections],
    )


# --- Route ------------------------------------------------------------------


@router.get("/today-digest", response_model=DigestPublicSchema)
def read_today_digest(
    session: SessionDep,
    user: OptionalCurrentUser,
) -> Any:
    """Today's digest. Personalized when signed in, generic when not."""
    digest = build_digest(
        session=session,
        user_id=user.id if user is not None else None,
    )
    return _serialize_digest(digest)

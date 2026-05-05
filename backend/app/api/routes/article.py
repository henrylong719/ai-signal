import uuid
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel

from app import crud
from app.api.deps import CurrentUser, OptionalCurrentUser, SessionDep
from app.schemas import (
    ArticlePublic,
    ArticlesPublic,
    ForYouArticlePublic,
    ForYouArticlesPublic,
)
from app.schemas.source import (
    SOURCES,
    Category,
    SourcePublic,
    SourcesPublic,
    SourceType,
)
from app.services.for_you import rank_for_you

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/", response_model=ArticlesPublic)
def read_articles(
    session: SessionDep,
    category: Category | None = Query(default=None),
    search: str | None = Query(default=None),
    source: str | None = Query(default=None, max_length=64),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """
    Retrieve articles.
    """
    count = crud.count_articles(
        session=session, category=category, search=search, source=source
    )
    articles = crud.get_articles(
        session=session,
        category=category,
        search=search,
        source=source,
        skip=skip,
        limit=limit,
    )
    articles_public = [ArticlePublic.model_validate(article) for article in articles]
    return ArticlesPublic(data=articles_public, count=count)


@router.get("/sources/", response_model=SourcesPublic)
def read_sources(
    source_type: SourceType | None = Query(default=None),
) -> Any:
    """
    Retrieve configured article sources.
    """
    sources = [
        SourcePublic(
            name=source.name,
            default_category=source.default_category,
            source_type=source.source_type,
            topic=source.topic,
            description=source.description,
        )
        for source in SOURCES
        if source_type is None or source.source_type == source_type
    ]
    return SourcesPublic(data=sources, count=len(sources))


@router.get("/for-you", response_model=ForYouArticlesPublic)
def read_for_you_articles(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Get current user's personalized article feed."""
    items, count = rank_for_you(
        session=session,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    articles = []
    for item in items:
        article = crud.get_article(session=session, article_id=item.scored.article.id)
        if article:
            article_public = ForYouArticlePublic.model_validate(article)
            article_public.reason = item.reason
            articles.append(article_public)
    return ForYouArticlesPublic(data=articles, count=count)


# --- Saved articles ---


class SavedArticlesPublic(SQLModel):
    data: list[ArticlePublic]
    count: int


class SavedArticleIdsPublic(SQLModel):
    article_ids: list[uuid.UUID]


@router.get("/saved/", response_model=SavedArticlesPublic)
def read_saved_articles(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Get current user's saved articles."""
    count = crud.count_saved_articles(session=session, user_id=current_user.id)
    saved = crud.get_saved_articles(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    articles = []
    for s in saved:
        article = crud.get_article(session=session, article_id=s.article_id)
        if article:
            articles.append(ArticlePublic.model_validate(article))
    return SavedArticlesPublic(data=articles, count=count)


@router.get("/saved/ids", response_model=SavedArticleIdsPublic)
def read_saved_article_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get IDs of all articles saved by current user (for UI state)."""
    ids = crud.get_saved_article_ids(session=session, user_id=current_user.id)
    return SavedArticleIdsPublic(article_ids=ids)


@router.post("/{article_id}/save", status_code=201)
def save_article(
    session: SessionDep,
    current_user: CurrentUser,
    article_id: uuid.UUID,
) -> Any:
    """Save an article for the current user."""
    article = crud.get_article(session=session, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    existing = crud.get_saved_article(
        session=session, user_id=current_user.id, article_id=article_id
    )
    if existing:
        raise HTTPException(status_code=409, detail="Article already saved")
    crud.save_article(session=session, user_id=current_user.id, article_id=article_id)
    return {"message": "Article saved"}


@router.delete("/{article_id}/save")
def unsave_article(
    session: SessionDep,
    current_user: CurrentUser,
    article_id: uuid.UUID,
) -> Any:
    """Remove article from saved list."""
    existing = crud.get_saved_article(
        session=session, user_id=current_user.id, article_id=article_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Saved article not found")
    crud.unsave_article(session=session, saved_article=existing)
    return {"message": "Article unsaved"}


# --- Behavioral events ---


_ALLOWED_REDIRECT_SCHEMES = {"http", "https"}


@router.get("/{article_id}/go")
def go_to_article(
    session: SessionDep,
    user: OptionalCurrentUser,
    article_id: uuid.UUID,
) -> RedirectResponse:
    """Log a click and 302-redirect to the article's external URL.

    Auth is optional: anonymous users get the redirect with no logging,
    signed-in users get the click recorded as a behavioral signal for the
    recommender. Logging is best-effort — navigation is the contract.

    The destination URL comes from the article row in the DB (never from a
    query parameter), which means this endpoint cannot be repurposed as an
    open redirect by an attacker. The scheme is whitelisted defensively.
    """
    article = crud.get_article(session=session, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    parsed = urlparse(article.url)
    if parsed.scheme not in _ALLOWED_REDIRECT_SCHEMES or not parsed.netloc:
        # Should never happen for ingested articles, but defense in depth.
        raise HTTPException(status_code=400, detail="Article URL is invalid")

    if user is not None:
        # Best-effort: a logging failure must not block the redirect.
        try:
            crud.record_event(
                session=session,
                user_id=user.id,
                article_id=article_id,
                event_type="clicked",
            )
        except Exception:  # noqa: BLE001
            session.rollback()

    return RedirectResponse(url=article.url, status_code=302)


@router.post("/{article_id}/dismiss", status_code=204)
def dismiss_article(
    session: SessionDep,
    current_user: CurrentUser,
    article_id: uuid.UUID,
) -> None:
    """Mark an article as dismissed by the current user.

    Dismissed articles are hard-filtered out of the For-You feed (see
    `recommender.filter_candidates`). Idempotent — a second dismiss just
    bumps the count and last_at.
    """
    article = crud.get_article(session=session, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    crud.record_event(
        session=session,
        user_id=current_user.id,
        article_id=article_id,
        event_type="dismissed",
    )


@router.get("/{id}", response_model=ArticlePublic)
def read_article(session: SessionDep, id: uuid.UUID) -> Any:
    """
    Get article by ID.
    """
    article = crud.get_article(session=session, article_id=id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

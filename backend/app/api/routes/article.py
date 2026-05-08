import logging
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlmodel import Session, SQLModel

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
from app.services.article_search import search_articles
from app.services.embeddings import compute_and_save_user_vector
from app.services.for_you import _CANDIDATE_POOL_SIZE, rank_for_you

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


def _refresh_user_vector(session: Session, user_id: uuid.UUID) -> None:
    """Recompute the cached user interest vector.

    Called from every write path that changes user signal (save/unsave
    article, click through, dismiss is excluded — see the
    user_embeddings migration for why). Failures propagate; callers own
    the policy for whether to swallow/log or fail the user-facing
    operation. The next read either rebuilds the cache or falls back to
    live computation, so a missed cache update is recoverable.
    """
    compute_and_save_user_vector(session=session, user_id=user_id)


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
    articles, count = search_articles(
        session=session,
        category=category,
        search=search,
        source=source,
        skip=skip,
        limit=limit,
    )
    articles_public = [ArticlePublic.model_validate(article) for article in articles]
    return ArticlesPublic(data=articles_public, count=count)


@router.get("/for-you", response_model=ForYouArticlesPublic)
def read_for_you(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Personalized feed for the current user.

    The candidate pool is the most-recent N articles minus already-saved
    and dismissed ones (see ``services.for_you.rank_for_you``). Scoring
    happens in Python; only the requested page slice is returned.

    The ``count`` returned is the total scored pool size — the number of
    articles the recommender would have ranked for this user — not the
    DB-wide article count. This is the right shape for the frontend's
    infinite-scroll pagination.
    """
    items, total = rank_for_you(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    article_ids = [item.scored.article.id for item in items]
    articles_by_id = {
        article.id: article
        for article in crud.get_articles_by_ids(
            session=session, article_ids=article_ids
        )
    }
    data = [
        ForYouArticlePublic(
            **ArticlePublic.model_validate(
                articles_by_id[item.scored.article.id]
            ).model_dump(),
            reason=item.reason,
        )
        for item in items
    ]
    return ForYouArticlesPublic(
        data=data,
        count=total,
        candidate_pool_cap=_CANDIDATE_POOL_SIZE,
    )


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
    articles_by_id = {
        article.id: article
        for article in crud.get_articles_by_ids(
            session=session,
            article_ids=[s.article_id for s in saved],
        )
    }
    articles = [
        ArticlePublic.model_validate(articles_by_id[s.article_id])
        for s in saved
        if s.article_id in articles_by_id
    ]
    return SavedArticlesPublic(data=articles, count=count)


@router.get("/saved/ids", response_model=SavedArticleIdsPublic)
def read_saved_article_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get IDs of all articles saved by current user (for UI state)."""
    ids = crud.get_saved_article_ids(session=session, user_id=current_user.id)
    return SavedArticleIdsPublic(article_ids=ids)


@router.get("/{id}", response_model=ArticlePublic)
def read_article(session: SessionDep, id: uuid.UUID) -> Any:
    """
    Get article by ID.
    """
    article = crud.get_article(session=session, article_id=id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


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
    # Saving an article is the strongest behavioral signal we have —
    # update the cached user vector so the next /for-you request
    # reflects this new interest immediately.
    try:
        _refresh_user_vector(session, current_user.id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to refresh user interest vector for %s; will fall back to "
            "live recompute on next /for-you request",
            current_user.id,
        )
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
    # Unsaving is the inverse signal — the user is telling us they no
    # longer want this article weighted toward their interests.
    try:
        _refresh_user_vector(session, current_user.id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to refresh user interest vector for %s; will fall back to "
            "live recompute on next /for-you request",
            current_user.id,
        )
    return {"message": "Article unsaved"}


# --- Behavioral events ---


_ALLOWED_REDIRECT_SCHEMES = {"http", "https"}
_NO_PRIORS_DEAD_HOSTS = {"no-priors.com", "www.no-priors.com"}
_NO_PRIORS_AUDIO_HOSTS = {"traffic.megaphone.fm", "dcs-cached.megaphone.fm"}
_NO_PRIORS_FALLBACK_URL = (
    "https://podcasts.apple.com/us/podcast/"
    "no-priors-artificial-intelligence-technology-startups/id1668002688"
)
_NO_PRIORS_APPLE_SEARCH_URL = "https://itunes.apple.com/search"
_NO_PRIORS_APPLE_COLLECTION_ID = 1668002688


def _is_no_priors_raw_audio_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.netloc.lower() in _NO_PRIORS_AUDIO_HOSTS
        and parsed.path.lower().endswith(".mp3")
    )


def _no_priors_apple_episode_url(title: str) -> str | None:
    try:
        response = httpx.get(
            _NO_PRIORS_APPLE_SEARCH_URL,
            params={
                "term": f"No Priors {title}",
                "media": "podcast",
                "entity": "podcastEpisode",
                "limit": 5,
            },
            timeout=2.0,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (httpx.HTTPError, ValueError, TypeError):
        return None

    for result in results:
        if not isinstance(result, dict):
            continue
        if result.get("collectionId") != _NO_PRIORS_APPLE_COLLECTION_ID:
            continue
        episode_url = result.get("trackViewUrl")
        parsed = urlparse(str(episode_url or ""))
        if parsed.scheme in _ALLOWED_REDIRECT_SCHEMES and parsed.netloc.lower() in {
            "podcasts.apple.com",
            "itunes.apple.com",
        }:
            return str(episode_url)
    return None


def _article_redirect_url(article: Any) -> str:
    parsed = urlparse(article.url)
    if article.source == "No Priors" and parsed.netloc.lower() in _NO_PRIORS_DEAD_HOSTS:
        return _NO_PRIORS_FALLBACK_URL
    if article.source == "No Priors" and _is_no_priors_raw_audio_url(article.url):
        return _no_priors_apple_episode_url(article.title) or _NO_PRIORS_FALLBACK_URL
    return article.url


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

    destination_url = _article_redirect_url(article)
    parsed = urlparse(destination_url)
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
            # Click is now part of the user's behavioral signal — refresh
            # the cached interest vector. This is also wrapped in the
            # outer try/except so any failure here is swallowed too;
            # navigation is still the contract.
            _refresh_user_vector(session, user.id)
        except Exception:  # noqa: BLE001
            session.rollback()
            logger.exception(
                "Failed to record click signal or refresh user vector for %s; "
                "redirecting anyway",
                user.id,
            )

    return RedirectResponse(url=destination_url, status_code=302)


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

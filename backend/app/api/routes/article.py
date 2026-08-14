import logging
import uuid
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, SQLModel

from app import crud
from app.api.deps import CurrentUser, OptionalCurrentUser, SessionDep
from app.core.rate_limit import limiter
from app.schemas import (
    ArticlePublic,
    ArticlesPublic,
    ForYouArticlePublic,
    ForYouArticlesPublic,
    ScoringWeightsPublic,
)
from app.schemas.interest import known_source_names
from app.schemas.source import (
    SOURCES,
    Category,
    SourcePublic,
    SourcesPublic,
    SourceType,
)
from app.services.article_redirects import (
    ALLOWED_REDIRECT_SCHEMES,
    resolve_redirect_url,
)
from app.services.article_search import search_articles
from app.services.embeddings import compute_and_save_user_vector
from app.services.for_you import _CANDIDATE_POOL_SIZE, build_debug_payload, rank_for_you

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
@limiter.limit("60/minute")
def read_articles(
    request: Request,  # noqa: ARG001  # consumed by @limiter.limit
    session: SessionDep,
    category: Category | None = Query(default=None),
    search: str | None = Query(default=None),
    source: str | None = Query(default=None, max_length=64),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Retrieve articles.

    Rate-limited to 60 requests/minute per bucket (per-user when
    authenticated, per-IP otherwise — see ``app.core.rate_limit``).
    Semantic / keyword search shares this bucket; if search ever moves
    to its own endpoint, give it a stricter quota (~30/min).
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
@limiter.limit("100/minute")
def read_for_you(
    request: Request,  # noqa: ARG001  # consumed by @limiter.limit
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    debug: bool = Query(
        default=False,
        description=(
            "Admin diagnostic: include per-article scoring breakdown and "
            "exploration-injection flags. Silently ignored for non-superusers."
        ),
    ),
) -> Any:
    """Personalized feed for the current user.

    [... see full docstring in /home/claude/ai-signal-main/backend/app/api/routes/article.py ...]
    """
    # Effective debug = requested AND privileged. Silent ignore on the
    # privilege check, deliberate — see route docstring above.
    effective_debug = debug and current_user.is_superuser

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
    # An article can be deleted (admin action / cleanup) between the
    # ranking pass and this refetch, in which case it's absent from
    # articles_by_id. Skip it rather than KeyError into a 500 — the feed
    # is a best-effort snapshot, so a just-removed item simply doesn't
    # appear.
    data = [
        ForYouArticlePublic(
            **ArticlePublic.model_validate(article).model_dump(),
            reason=item.reason,
            debug=build_debug_payload(item) if effective_debug else None,
        )
        for item in items
        if (article := articles_by_id.get(item.scored.article.id)) is not None
    ]

    weights_public: ScoringWeightsPublic | None = None
    if effective_debug and items:
        active_weights = items[0].scored.breakdown.weights
        weights_public = ScoringWeightsPublic(
            semantic=active_weights.semantic,
            explicit=active_weights.explicit,
            source=active_weights.source,
            recency=active_weights.recency,
        )

    return ForYouArticlesPublic(
        data=data,
        count=total,
        candidate_pool_cap=_CANDIDATE_POOL_SIZE,
        weights=weights_public,
    )


@router.get("/following", response_model=ArticlesPublic)
@limiter.limit("100/minute")
def read_following(
    request: Request,  # noqa: ARG001  # consumed by @limiter.limit
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Articles from sources the current user follows.

    Authenticated-only. Reads the user's preferred_sources from
    UserInterest and returns matching articles in published_at desc
    order — no scoring, no diversity rerank, just chronological from
    the followed-source set. This is intentionally simpler than For-You:
    users come here when they want exactly what their trusted sources
    published, not a personalized blend.

    A user with no preferred_sources gets an empty page; the route
    still 200's so the client renders the "Follow sources to build
    your trusted AI reading list" empty state instead of a generic
    error. The crud helpers short-circuit on an empty `sources` list,
    so this is a constant-time response.

    Stored names are filtered against the live SOURCES list. Retiring a
    source does not delete the articles it already produced, so without
    this a retired source keeps feeding this list while the Sources UI
    (which filters on read) shows it as unfollowed — visible articles
    from a source the user has no way to unfollow.
    """
    interests = crud.get_interests(session=session, user_id=current_user.id)
    preferred_sources = known_source_names(
        interests.preferred_sources if interests else []
    )
    count = crud.count_articles(session=session, sources=preferred_sources)
    articles = crud.get_articles(
        session=session,
        sources=preferred_sources,
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


# --- Saved articles ---


class SavedArticlesPublic(SQLModel):
    data: list[ArticlePublic]
    count: int


class SavedArticleIdsPublic(SQLModel):
    article_ids: list[uuid.UUID]


@router.get("/saved/", response_model=SavedArticlesPublic)
@limiter.limit("100/minute")
def read_saved_articles(
    request: Request,  # noqa: ARG001  # consumed by @limiter.limit
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Get current user's saved articles.

    Reads articles via a single JOIN against ``saved_articles`` so the
    page comes back in one query rather than the two-query (saved IDs,
    then articles by ID) pattern. Ordering is by ``saved_at desc`` so
    the most recently saved article is first.
    """
    count = crud.count_saved_articles(session=session, user_id=current_user.id)
    articles = crud.get_saved_articles_with_articles(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return SavedArticlesPublic(
        data=[ArticlePublic.model_validate(article) for article in articles],
        count=count,
    )


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
    saved = crud.save_article(
        session=session, user_id=current_user.id, article_id=article_id
    )
    if saved is None:
        # Lost a race with a concurrent save — same outcome as the
        # pre-check catching it.
        raise HTTPException(status_code=409, detail="Article already saved")
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


@router.api_route("/{article_id}/go", methods=["GET", "HEAD"])
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
    Per-source rewrites (e.g. No Priors) live in
    ``services.article_redirects`` so the route stays a thin lookup.
    """
    article = crud.get_article(session=session, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    destination_url = resolve_redirect_url(article)
    parsed = urlparse(destination_url)
    if parsed.scheme not in ALLOWED_REDIRECT_SCHEMES or not parsed.netloc:
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

    # noindex/nofollow tells search engines this is a tracking redirect,
    # not a page. Without it Googlebot indexes these URLs and reports
    # them as "Page with redirect" in Search Console.
    return RedirectResponse(
        url=destination_url,
        status_code=302,
        headers={
            "X-Robots-Tag": "noindex, nofollow",
            "Referrer-Policy": "no-referrer",
        },
    )


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

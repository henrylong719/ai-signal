"""For-You feed orchestration.

Pulls together the recommender's inputs from three CRUD layers (articles,
events, interests), assembles a ``UserProfile``, and scores a candidate
pool. Lives in the services layer so the API route stays thin and so the
orchestration is unit-testable independent of FastAPI.

The semantic-similarity layer is intentionally absent from v1 — it would
be added here as an extra step that fetches embeddings and computes
cosine similarities against a user-interest vector. Until then, the
``score_candidates`` call passes ``semantic_similarities=None`` and the
recommender quietly skips that term. All other signals (explicit
interests, saved/clicked tag and source affinity, recency) are live.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlmodel import Session

from app import crud
from app.models import Article
from app.services.recommender import (
    CandidateArticle,
    ScoredArticle,
    UserProfile,
    filter_candidates,
    reason_for,
    score_candidates,
)

# Size of the candidate pool we score in Python. See
# ``crud.article.get_recent_articles_excluding`` for the trade-off.
_CANDIDATE_POOL_SIZE = 200


@dataclass(frozen=True)
class ForYouItem:
    """One ranked article plus its explainability metadata.

    Carries enough breakdown for the API layer to render reason badges
    and to surface debug info if we ever want a "why am I seeing this?"
    affordance for users.
    """

    scored: ScoredArticle
    reason: str | None


def build_user_profile(*, session: Session, user_id: uuid.UUID) -> UserProfile:
    """Read every signal we have for the user and assemble a profile.

    Five DB queries — explicit interests, saved signals, clicked signals,
    saved-article IDs (for filtering), dismissed article IDs (also for
    filtering). Each query is small; total round-trip overhead is what
    we trade for keeping the recommender input shape clean and testable.
    """
    interests_row = crud.get_interests(session=session, user_id=user_id)
    saved_tags, saved_sources = crud.get_saved_signals(session=session, user_id=user_id)
    clicked_tags, clicked_sources = crud.get_clicked_signals(
        session=session, user_id=user_id
    )
    saved_article_ids = set(
        crud.get_saved_article_ids(session=session, user_id=user_id)
    )
    dismissed_article_ids = set(
        crud.get_event_article_ids(
            session=session, user_id=user_id, event_type="dismissed"
        )
    )

    return UserProfile(
        interest_categories=frozenset(
            interests_row.categories if interests_row else []
        ),
        interest_tags=frozenset(interests_row.tags if interests_row else []),
        saved_tags=saved_tags,
        saved_sources=saved_sources,
        clicked_tags=clicked_tags,
        clicked_sources=clicked_sources,
        saved_article_ids=frozenset(saved_article_ids),
        dismissed_article_ids=frozenset(dismissed_article_ids),
    )


def _to_candidate(article: Article) -> CandidateArticle:
    """Project an SQLModel Article down to the recommender's input shape."""
    return CandidateArticle(
        id=article.id,
        title=article.title,
        source=article.source,
        category=article.category,
        tags=tuple(article.tags or ()),
        published_at=article.published_at,
    )


def rank_for_you(
    *,
    session: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[ForYouItem], int]:
    """Build the personalized feed for one user.

    Returns ``(items, total_candidate_count)``. The total is the size of
    the *scored* pool, not the pool returned — pagination is over the
    scored output. Note this means total is bounded by
    ``_CANDIDATE_POOL_SIZE``; for our scale that's the right trade-off.
    """
    profile = build_user_profile(session=session, user_id=user_id)

    # Fetch candidate pool: recent articles, hard-filter saved + dismissed.
    # The recommender's filter_candidates step is a defense-in-depth pass
    # in case the IDs have drifted between query and score.
    excluded = set(profile.saved_article_ids) | set(profile.dismissed_article_ids)
    db_articles: Sequence[Article] = crud.get_recent_articles_excluding(
        session=session,
        excluded_ids=excluded,
        limit=_CANDIDATE_POOL_SIZE,
    )

    candidates = [_to_candidate(a) for a in db_articles]
    candidates = filter_candidates(candidates, profile)

    scored = score_candidates(candidates, profile)
    total = len(scored)

    page = scored[skip : skip + limit]
    return [
        ForYouItem(scored=item, reason=reason_for(item, profile)) for item in page
    ], total

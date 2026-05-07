"""For-You feed orchestration.

Pulls together the recommender's inputs from CRUD (articles, events,
interests, embeddings), assembles a ``UserProfile`` and a user interest
vector, and scores a candidate pool. Lives in the services layer so the
API route stays thin and so the orchestration is unit-testable
independent of FastAPI.

The semantic-similarity layer reads the cached user embedding from
``user_embeddings`` (written by every endpoint that changes user
signal — see ``services/embeddings.py:compute_and_save_user_vector``).
If the cache is empty, we recompute live and write through. If the user
has no signal at all (no interests, no saves, no clicks), we skip the
semantic step entirely — the scorer falls back to the explicit, source,
and recency layers exactly as it did before embeddings existed.
"""

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlmodel import Session

from app import crud
from app.services.embeddings import (
    compute_and_save_user_vector,
    cosine_similarities,
)
from app.services.recommender import (
    CandidateArticle,
    ScoredArticle,
    UserProfile,
    filter_candidates,
    reason_for,
    score_candidates,
)

logger = logging.getLogger(__name__)

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

    Five DB queries — explicit interests (which now also carries
    preferred_sources), saved signals, clicked signals, saved-article IDs
    (for filtering), dismissed article IDs (also for filtering). Each
    query is small; total round-trip overhead is what we trade for
    keeping the recommender input shape clean and testable.
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
        preferred_sources=frozenset(
            interests_row.preferred_sources if interests_row else []
        ),
        saved_tags=saved_tags,
        saved_sources=saved_sources,
        clicked_tags=clicked_tags,
        clicked_sources=clicked_sources,
        saved_article_ids=frozenset(saved_article_ids),
        dismissed_article_ids=frozenset(dismissed_article_ids),
    )


def _to_candidate(article) -> CandidateArticle:  # type: ignore[no-untyped-def]
    """Project an SQLModel Article down to the recommender's input shape."""
    return CandidateArticle(
        id=article.id,
        title=article.title,
        source=article.source,
        category=article.category,
        tags=tuple(article.tags or ()),
        published_at=article.published_at,
    )


def _resolve_user_vector(*, session: Session, user_id: uuid.UUID) -> list[float] | None:
    """Read the cached user vector, falling back to live recompute on miss.

    The cache is populated at write time (save / unsave / click /
    update interests). A miss here means either:
      - The user existed before the user_embeddings table did
      - The user has zero signal (no saves, clicks, or interests)
      - A write-time recompute failed and the row was dropped

    We try a live build to handle case 1. Cases 2 and 3 produce None
    from the live build too, which the caller handles by skipping the
    semantic step entirely.

    The live build writes through to the cache so subsequent requests
    hit the fast path. Failures here log and return None — the For-You
    feed must keep working even if the embedding model is unavailable.
    """
    cached = crud.get_user_embedding(session=session, user_id=user_id)
    if cached is not None:
        return list(cached.embedding)

    try:
        return compute_and_save_user_vector(session=session, user_id=user_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Live user-vector recompute failed for %s; semantic layer "
            "will be skipped for this request",
            user_id,
        )
        return None


def _candidate_similarities(
    *,
    user_vector: list[float],
    db_articles: Sequence,  # type: ignore[type-arg]
) -> dict[uuid.UUID, float]:
    """Cosine similarity for every candidate that has an embedding.

    Articles without embeddings (not yet backfilled) are absent from the
    returned dict. ``score_candidates`` looks up by ID and treats
    missing entries as 0 — those articles still get ranked by the
    other signals, just without semantic contribution.
    """
    article_vecs: dict[uuid.UUID, list[float]] = {}
    for article in db_articles:
        embedding = getattr(article, "embedding", None)
        if embedding is None:
            continue
        # pgvector returns numpy arrays; convert to plain lists so the
        # math helpers in services.embeddings stay numpy-free.
        article_vecs[article.id] = list(embedding)
    return cosine_similarities(user_vector, article_vecs)


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

    Semantic-similarity layer:
      1. Resolve the user vector (cache → live recompute → None).
      2. If we have one, compute cosine similarities against every
         candidate article that has an embedding.
      3. Pass the {id: similarity} map to ``score_candidates``; the
         scorer clamps to [0, 1] (negative similarity becomes 0) and
         applies the semantic weight.

    If the user vector is None (cold-start, no signal), the semantic
    map is None and the scorer skips that term — exactly the v0
    behavior.
    """
    profile = build_user_profile(session=session, user_id=user_id)

    # Fetch candidate pool: recent articles, hard-filter saved + dismissed.
    # The recommender's filter_candidates step is a defense-in-depth pass
    # in case the IDs have drifted between query and score.
    excluded = set(profile.saved_article_ids) | set(profile.dismissed_article_ids)
    db_articles: Sequence = crud.get_recent_articles_excluding(
        session=session,
        excluded_ids=excluded,
        limit=_CANDIDATE_POOL_SIZE,
    )

    # Semantic layer. Skipped entirely when the user has no signal —
    # we don't even fetch embeddings in that case.
    user_vector = _resolve_user_vector(session=session, user_id=user_id)
    if user_vector is not None:
        similarities = _candidate_similarities(
            user_vector=user_vector, db_articles=db_articles
        )
    else:
        similarities = None

    candidates = [_to_candidate(a) for a in db_articles]
    candidates = filter_candidates(candidates, profile)

    scored = score_candidates(candidates, profile, semantic_similarities=similarities)
    total = len(scored)

    page = scored[skip : skip + limit]
    return [
        ForYouItem(scored=item, reason=reason_for(item, profile)) for item in page
    ], total

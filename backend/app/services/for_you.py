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

# Add this import near the other service imports:

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlmodel import Session

from app import crud
from app.models import Article
from app.services.diversity import (
    DEFAULT_LAMBDA_FOR_YOU,
    RerankItem,
    diversity_rerank,
)
from app.services.embeddings import (
    compute_and_save_user_vector,
    cosine_similarities,
    cosine_similarity,
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
    db_articles: Sequence[Article],
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


def _most_similar_saved_titles(
    *,
    db_articles: Sequence[Article],
    saved: list[tuple[uuid.UUID, str, list[float]]],
) -> dict[uuid.UUID, str]:
    """For each candidate, the title of the saved article it's closest to.

    Powers the "Similar to: <title>" reason label. Computed pairwise
    against the user's individual saved articles — *not* against the
    centroid user vector — because the centroid can't tell us which
    individual save a candidate is most similar to. (The centroid is
    what the recommender's semantic-similarity score uses; this lookup
    is a parallel computation purely for explainability.)

    Cost: O(C × S) cosine sims, where C ≤ candidate pool size (~200)
    and S = number of saved articles with embeddings. With 384-dim
    vectors and S=50, that's 10k × 384 ≈ 4M float ops per request —
    well under 50ms. We intentionally don't cache this between
    requests; it's cheap enough to recompute and keeps the data path
    simple (no cache invalidation when saves change).

    Returns a {candidate_id: best_saved_title} map. Candidates without
    an embedding don't appear (no way to compute similarity); the
    caller falls back to the generic semantic label for those. If the
    user has no saved articles with embeddings, returns an empty map.
    """
    if not saved:
        return {}

    result: dict[uuid.UUID, str] = {}
    for article in db_articles:
        embedding = getattr(article, "embedding", None)
        if embedding is None:
            continue
        candidate_vec = list(embedding)
        best_title: str | None = None
        best_sim = -1.0  # cosine ranges in [-1, 1]; any real sim beats this
        for _saved_id, title, saved_vec in saved:
            sim = cosine_similarity(candidate_vec, saved_vec)
            if sim > best_sim:
                best_sim = sim
                best_title = title
        if best_title is not None:
            result[article.id] = best_title
    return result


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
    db_articles: Sequence[Article] = crud.get_recent_articles_excluding(
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
        # For the "Similar to: <title>" reason label. Only fetched when
        # we have a user vector — otherwise the semantic component is
        # zero across the board and the personalized label can never
        # fire. The lookup is pairwise against individual saved
        # articles (not against the centroid user vector) because the
        # centroid can't tell us which save a candidate is closest to.
        saved_with_titles = crud.get_saved_articles_with_embeddings_and_titles(
            session=session, user_id=user_id
        )
        most_similar_titles = _most_similar_saved_titles(
            db_articles=db_articles, saved=saved_with_titles
        )
    else:
        similarities = None
        most_similar_titles = {}

    candidates = [_to_candidate(a) for a in db_articles]
    candidates = filter_candidates(candidates, profile)

    scored = score_candidates(candidates, profile, semantic_similarities=similarities)

    # Diversity rerank between scoring and pagination. Without this, a
    # source-rich pool can fill the head of the feed with one source
    # (e.g. arXiv burst, weekly newsletter dump). The reranker uses the
    # user's preferred_sources to bypass the cap for explicitly opted-
    # in sources — if the user said "show me OpenAI," seeing OpenAI
    # cluster is correct, not a bug. Lambda is high (0.85) because
    # personalized scores are already meaningful and we don't want
    # diversity to undermine personalization — it's a tiebreaker.
    #
    # The reranker reads `source` and `category` off the wrapped item,
    # so we wrap the CandidateArticle (not ScoredArticle, which only
    # exposes those via `.article`). After reranking, we map back to
    # the original ScoredArticle by id so reason_for() still gets the
    # full breakdown.
    scored_by_id = {s.article.id: s for s in scored}
    rerank_items = [RerankItem(item=s.article, score=s.score) for s in scored]
    reranked = diversity_rerank(
        rerank_items,
        lambda_=DEFAULT_LAMBDA_FOR_YOU,
        preferred_sources=profile.preferred_sources,
    )
    scored = [scored_by_id[it.item.id] for it in reranked]
    total = len(scored)

    page = scored[skip : skip + limit]
    return [
        ForYouItem(
            scored=item,
            reason=reason_for(
                item,
                profile,
                most_similar_saved_title=most_similar_titles.get(item.article.id),
            ),
        )
        for item in page
    ], total

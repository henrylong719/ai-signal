"""Shared ranking pipeline.

The personalized scoring pipeline used by both the For-You feed and the
Today's Digest: resolve the user's interest vector, project articles to
the recommender's input shape, compute semantic similarities, filter,
and score.

Lives in its own module so digest and for_you don't share underscore-
prefixed internals across files. Both surfaces wrap this core with their
own surface-specific concerns (For-You adds diversity rerank +
exploration injection + saved-title reasons; digest adds section
slicing). What's *common* — "score this pool of articles for this
user" — lives here.

The function takes the ``UserProfile`` as input rather than building it,
so callers control the cost of profile assembly (digest fetches the
profile once and reuses it across the fetch-window-fallback loop in
principle; in practice they fetch once each).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlmodel import Session

from app import crud
from app.models import Article
from app.services.embeddings import (
    compute_and_save_user_vector,
    cosine_similarities,
)
from app.services.recommender import (
    CandidateArticle,
    ScoredArticle,
    UserProfile,
    filter_candidates,
    score_candidates,
)

logger = logging.getLogger(__name__)


def to_candidate(article: Article) -> CandidateArticle:
    """Project an SQLModel ``Article`` to the recommender's input shape."""
    return CandidateArticle(
        id=article.id,
        title=article.title,
        source=article.source,
        category=article.category,
        tags=tuple(article.tags or ()),
        published_at=article.published_at,
    )


def resolve_user_vector(*, session: Session, user_id: uuid.UUID) -> list[float] | None:
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
    hit the fast path. Failures here log and return None — the
    personalized layer must keep working even if the embedding model is
    unavailable.
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


def candidate_similarities(
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


@dataclass(frozen=True)
class RankingResult:
    """Output of ``rank_articles``.

    ``scored`` is the ranked list. ``used_semantic`` reports whether
    the user vector was available — when False, all semantic
    components are 0 and the caller can skip semantic-dependent work
    (e.g. fetching saved-article titles for "Similar to: <title>"
    reasons).
    """

    scored: list[ScoredArticle]
    used_semantic: bool


def rank_articles(
    *,
    session: Session,
    user_id: uuid.UUID,
    profile: UserProfile,
    db_articles: Sequence[Article],
) -> RankingResult:
    """Score and order a pool of articles for one user.

    Pipeline:

      1. Resolve the user's interest vector (cache → live recompute →
         None). When None (cold-start, no signal), the semantic layer is
         skipped entirely; the scorer still produces a useful ranking
         from explicit + source + recency signals.
      2. Compute candidate→user cosine similarities, where embeddings
         exist.
      3. Project articles to ``CandidateArticle``.
      4. Hard-filter saved + dismissed (defense-in-depth — the CRUD
         caller should already exclude these).
      5. Score against the user profile, applying the semantic
         similarities map.

    Returns a ``RankingResult`` with the scored list (sorted by
    descending total score) and a flag indicating whether the
    semantic layer was used. Surface-specific concerns (diversity
    rerank, exploration injection, section slicing, reason-label
    rendering) live in the caller.
    """
    user_vector = resolve_user_vector(session=session, user_id=user_id)
    similarities = (
        candidate_similarities(user_vector=user_vector, db_articles=db_articles)
        if user_vector is not None
        else None
    )

    candidates = filter_candidates([to_candidate(a) for a in db_articles], profile)
    scored = score_candidates(candidates, profile, semantic_similarities=similarities)
    return RankingResult(scored=scored, used_semantic=user_vector is not None)

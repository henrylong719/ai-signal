"""Article-search and Latest-feed orchestration.

This service backs three different surfaces from one entry point:

- The Latest feed (no search query) — chronological browse with
  diversity reranking applied.
- Keyword search (search query, embeddings unavailable or failed).
- Semantic search (search query with a working embedder).

Diversity reranking is intentionally only applied to the Latest case.
Searches return whatever matches the query — reranking a search result
to be "diverse" makes the result confusing ("I searched for 'OpenAI',
why am I seeing Anthropic?"). Latest is the only surface where the
ordering is purely a presentation choice rather than a relevance signal.

For Latest, we fetch a larger candidate pool than the user's page size,
rerank the whole pool, then slice to the requested page. Reranking a
single page would break the diversity guarantee at page boundaries
(page 2 doesn't know what was selected for page 1). The pool size is
bounded — for very deep pagination we fall back to chronological tail,
which is fine because no real user scrolls 200+ articles deep.
"""

import logging
from collections.abc import Sequence

from sqlmodel import Session

from app import crud
from app.models import Article
from app.schemas.source import Category
from app.services.diversity import (
    DEFAULT_LAMBDA_LATEST,
    RerankItem,
    diversity_rerank,
)
from app.services.embeddings import embed_text

logger = logging.getLogger(__name__)

# Pool size for diversity reranking on the Latest feed. Large enough
# that the first 5–10 pages all come from a reranked pool; small
# enough that the rerank stays well under 50ms. Past this offset, deep
# pagination falls through to chronological tail.
_LATEST_RERANK_POOL_SIZE = 200


def _rerank_latest_pool(
    *,
    session: Session,
    category: Category | None,
    source: str | None,
) -> list[Article]:
    """Fetch the top-of-feed pool and apply the diversity reranker.

    Cached per-request only; called once per request from
    `search_articles` for chronological browses. The result is sliced
    by the route layer to produce the response page.

    `source` is unusual here: when the user is filtering to a single
    source (e.g. /article-sources/openai), there's nothing to diversify
    — every candidate is the same source. We still call the reranker
    for shape consistency but it short-circuits to score order.
    """
    pool = list(
        crud.get_articles(
            session=session,
            category=category,
            source=source,
            skip=0,
            limit=_LATEST_RERANK_POOL_SIZE,
        )
    )
    if not pool:
        return []

    # Score = recency-only proxy. We don't have a real recency_score
    # function exposed here (it lives in recommender.py), but for the
    # rerank's normalization step the *order* matters more than the
    # absolute values. Use a simple monotonically-decreasing rank
    # score so that newer articles have higher relevance.
    items = [
        RerankItem(item=article, score=float(len(pool) - idx))
        for idx, article in enumerate(pool)
    ]

    reranked = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)
    return [it.item for it in reranked]


def search_articles(
    *,
    session: Session,
    search: str | None,
    category: Category | None = None,
    source: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[Sequence[Article], int]:
    query = search.strip() if search else None
    if not query:
        # Chronological browse — apply diversity reranking to the head
        # of the feed. For deep pagination beyond the rerank pool, fall
        # through to plain chronological (rare in practice; nobody
        # scrolls past 200 articles).
        count = crud.count_articles(session=session, category=category, source=source)
        if skip >= _LATEST_RERANK_POOL_SIZE:
            articles = crud.get_articles(
                session=session,
                category=category,
                source=source,
                skip=skip,
                limit=limit,
            )
            return articles, count
        reranked_pool = _rerank_latest_pool(
            session=session, category=category, source=source
        )
        page = reranked_pool[skip : skip + limit]
        return page, count

    try:
        query_embedding = embed_text(query)
        count = crud.count_semantic_search_articles(
            session=session,
            query_embedding=query_embedding,
            category=category,
            source=source,
        )
        if count > 0:
            articles = crud.get_semantic_search_articles(
                session=session,
                query_embedding=query_embedding,
                category=category,
                source=source,
                skip=skip,
                limit=limit,
            )
            return articles, count
    except Exception:  # noqa: BLE001
        logger.exception("Semantic article search failed; falling back to keyword")

    count = crud.count_articles(
        session=session,
        category=category,
        search=query,
        source=source,
    )
    articles = crud.get_articles(
        session=session,
        category=category,
        search=query,
        source=source,
        skip=skip,
        limit=limit,
    )
    return articles, count

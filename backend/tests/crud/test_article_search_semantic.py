"""Relevance-threshold contract for semantic search.

Without a distance cutoff, semantic search "matches" the entire corpus
(every article has *some* distance to the query) and ``count`` reports
the total number of embedded articles — so the frontend paginates a
user through the whole database for any query.
"""

import uuid

from sqlmodel import Session

from app import crud
from app.models.article import EMBEDDING_DIM
from tests.utils.article import create_random_article


def _unit_vector(direction: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[direction] = 1.0
    return vector


def _embedded_article(db: Session, *, direction: int) -> uuid.UUID:
    article = create_random_article(db)
    article.embedding = _unit_vector(direction)
    db.add(article)
    db.commit()
    return article.id


def test_semantic_search_excludes_irrelevant_articles(db: Session) -> None:
    """An article orthogonal to the query (cosine distance 1.0) must not
    appear in the results, no matter how few real matches exist."""
    relevant_id = _embedded_article(db, direction=380)
    irrelevant_id = _embedded_article(db, direction=381)

    results = crud.get_semantic_search_articles(
        session=db,
        query_embedding=_unit_vector(380),
        limit=1000,
    )
    result_ids = {article.id for article in results}

    assert relevant_id in result_ids
    assert irrelevant_id not in result_ids


def test_semantic_search_count_matches_thresholded_results(db: Session) -> None:
    """``count`` must describe the same thresholded set the page queries
    return — not the size of the whole embedded corpus."""
    _embedded_article(db, direction=380)
    _embedded_article(db, direction=381)

    query_embedding = _unit_vector(380)
    results = crud.get_semantic_search_articles(
        session=db,
        query_embedding=query_embedding,
        limit=1000,
    )
    count = crud.count_semantic_search_articles(
        session=db,
        query_embedding=query_embedding,
    )

    assert count == len(results)


def test_semantic_search_count_is_zero_for_unrelated_query(db: Session) -> None:
    """A query far from everything must count zero matches so the search
    layer falls back to keyword search instead of serving the corpus."""
    _embedded_article(db, direction=380)

    count = crud.count_semantic_search_articles(
        session=db,
        query_embedding=_unit_vector(382),
    )

    assert count == 0

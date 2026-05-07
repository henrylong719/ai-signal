import logging
from collections.abc import Sequence

from sqlmodel import Session

from app import crud
from app.models import Article
from app.schemas.source import Category
from app.services.embeddings import embed_text

logger = logging.getLogger(__name__)


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
        count = crud.count_articles(session=session, category=category, source=source)
        articles = crud.get_articles(
            session=session,
            category=category,
            source=source,
            skip=skip,
            limit=limit,
        )
        return articles, count

    try:
        query_embedding = embed_text(query)
        count = crud.count_semantic_search_articles(
            session=session,
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

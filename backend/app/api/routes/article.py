import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app import crud
from app.api.deps import SessionDep
from app.schemas import ArticlePublic, ArticlesPublic
from app.schemas.source import Category

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/", response_model=ArticlesPublic)
def read_articles(
    session: SessionDep,
    category: Category | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """
    Retrieve articles.
    """
    count = crud.count_articles(session=session, category=category)
    articles = crud.get_articles(
        session=session, category=category, skip=skip, limit=limit
    )
    articles_public = [ArticlePublic.model_validate(article) for article in articles]
    return ArticlesPublic(data=articles_public, count=count)


@router.get("/{id}", response_model=ArticlePublic)
def read_article(session: SessionDep, id: uuid.UUID) -> Any:
    """
    Get article by ID.
    """
    article = crud.get_article(session=session, article_id=id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

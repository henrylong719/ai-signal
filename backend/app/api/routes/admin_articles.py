"""Admin endpoints for article inventory and cleanup."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import SQLModel

from app import crud
from app.api.deps import SessionDep, get_current_active_superuser
from app.schemas import ArticlePublic, Message

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


class AdminArticlePublic(ArticlePublic):
    saved_count: int


class AdminArticlesPublic(SQLModel):
    data: list[AdminArticlePublic]
    count: int


@router.get("/articles", response_model=AdminArticlesPublic)
def read_admin_articles(
    session: SessionDep,
    search: str | None = Query(default=None),
    source: str | None = Query(default=None, max_length=64),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> Any:
    """List articles for operators, including how many users saved each one."""
    count = crud.count_articles(session=session, search=search, source=source)
    rows = crud.get_articles_with_saved_counts(
        session=session,
        search=search,
        source=source,
        skip=skip,
        limit=limit,
    )
    return AdminArticlesPublic(
        data=[
            AdminArticlePublic(
                **ArticlePublic.model_validate(article).model_dump(),
                saved_count=saved_count,
            )
            for article, saved_count in rows
        ],
        count=count,
    )


@router.delete("/articles/{article_id}", response_model=Message)
def delete_admin_article(session: SessionDep, article_id: uuid.UUID) -> Any:
    """Delete an article and its saved/event rows via database cascades."""
    article = crud.get_article(session=session, article_id=article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    crud.delete_article(session=session, db_article=article)
    return Message(message="Article deleted")

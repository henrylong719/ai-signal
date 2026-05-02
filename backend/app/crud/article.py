import uuid
from collections.abc import Sequence

from sqlmodel import Session, col, func, select

from app.models import Article
from app.schemas import ArticleCreate, ArticleUpdate
from app.schemas.source import Category


def count_articles(*, session: Session, category: Category | None = None) -> int:
    statement = select(func.count()).select_from(Article)
    if category is not None:
        statement = statement.where(Article.category == category)
    return session.exec(statement).one()


def get_articles(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 50,
    category: Category | None = None,
) -> Sequence[Article]:
    statement = select(Article)
    if category is not None:
        statement = statement.where(Article.category == category)
    statement = (
        statement.order_by(
            col(Article.published_at).desc().nullslast(),
            col(Article.fetched_at).desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return session.exec(statement).all()


def get_article(*, session: Session, article_id: uuid.UUID) -> Article | None:
    return session.get(Article, article_id)


def get_article_by_url(*, session: Session, url: str) -> Article | None:
    statement = select(Article).where(Article.url == url)
    return session.exec(statement).first()


def create_article(*, session: Session, article_in: ArticleCreate) -> Article:
    db_article = Article.model_validate(article_in)
    session.add(db_article)
    session.commit()
    session.refresh(db_article)
    return db_article


def update_article(
    *, session: Session, db_article: Article, article_in: ArticleUpdate
) -> Article:
    update_dict = article_in.model_dump(exclude_unset=True)
    db_article.sqlmodel_update(update_dict)
    session.add(db_article)
    session.commit()
    session.refresh(db_article)
    return db_article


def delete_article(*, session: Session, db_article: Article) -> None:
    session.delete(db_article)
    session.commit()

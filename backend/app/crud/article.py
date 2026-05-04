import uuid
from collections.abc import Sequence

from sqlmodel import Session, col, func, or_, select

from app.models import Article
from app.models.article import SavedArticle
from app.schemas import ArticleCreate, ArticleUpdate
from app.schemas.source import Category


def count_articles(
    *,
    session: Session,
    category: Category | None = None,
    search: str | None = None,
    source: str | None = None,
) -> int:
    statement = select(func.count()).select_from(Article)
    if category is not None:
        statement = statement.where(Article.category == category)
    if source:
        statement = statement.where(Article.source == source)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(col(Article.title).ilike(pattern), col(Article.excerpt).ilike(pattern))  # type: ignore[union-attr]
        )
    return session.exec(statement).one()


def get_articles(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 50,
    category: Category | None = None,
    search: str | None = None,
    source: str | None = None,
) -> Sequence[Article]:
    statement = select(Article)
    if category is not None:
        statement = statement.where(Article.category == category)
    if source:
        statement = statement.where(Article.source == source)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(col(Article.title).ilike(pattern), col(Article.excerpt).ilike(pattern))  # type: ignore[union-attr]
        )
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


# --- Saved articles ---


def get_saved_articles(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 50
) -> Sequence[SavedArticle]:
    statement = (
        select(SavedArticle)
        .where(SavedArticle.user_id == user_id)
        .order_by(SavedArticle.saved_at.desc())  # type: ignore
        .offset(skip)
        .limit(limit)
    )
    return session.exec(statement).all()


def count_saved_articles(*, session: Session, user_id: uuid.UUID) -> int:
    statement = (
        select(func.count()).select_from(SavedArticle).where(SavedArticle.user_id == user_id)
    )
    return session.exec(statement).one()


def get_saved_article(
    *, session: Session, user_id: uuid.UUID, article_id: uuid.UUID
) -> SavedArticle | None:
    statement = select(SavedArticle).where(
        SavedArticle.user_id == user_id,
        SavedArticle.article_id == article_id,
    )
    return session.exec(statement).first()


def save_article(
    *, session: Session, user_id: uuid.UUID, article_id: uuid.UUID
) -> SavedArticle:
    saved = SavedArticle(user_id=user_id, article_id=article_id)
    session.add(saved)
    session.commit()
    session.refresh(saved)
    return saved


def unsave_article(*, session: Session, saved_article: SavedArticle) -> None:
    session.delete(saved_article)
    session.commit()


def get_saved_article_ids(
    *, session: Session, user_id: uuid.UUID
) -> list[uuid.UUID]:
    statement = select(SavedArticle.article_id).where(SavedArticle.user_id == user_id)
    return list(session.exec(statement).all())

import uuid
from datetime import datetime
from typing import Any, Literal

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc
from app.schemas.article import ArticleBase
from app.schemas.source import Category

_published_at_column = Column(DateTime(timezone=True), nullable=True)
_archived_at_column = Column(DateTime(timezone=True), nullable=True)

# Allowed values for ArticleEvent.event_type. Kept in lockstep with the
# Postgres ENUM created in migration e3f4a5b6c7d8.
ArticleEventType = Literal["clicked", "dismissed"]
ARTICLE_EVENT_TYPES: tuple[ArticleEventType, ...] = ("clicked", "dismissed")

# Embedding dimension. Matches sentence-transformers/all-MiniLM-L6-v2 and
# the migration in a5b6c7d8e9f0_add_pgvector_and_article_embedding.py.
# If we ever swap embedding models, this constant + the migration are
# the two places to change.
EMBEDDING_DIM = 384


class Article(ArticleBase, table=True):
    __tablename__ = "articles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    url: str = Field(sa_type=Text, unique=True, nullable=False)
    title: str = Field(sa_type=Text, nullable=False)
    source: str = Field(sa_column=Column(String(64), nullable=False, index=True))

    excerpt: str | None = Field(default=None, sa_type=Text, nullable=True)
    image_url: str | None = Field(default=None, sa_type=Text, nullable=True)
    author: str | None = Field(default=None, sa_type=Text, nullable=True)

    category: Category = Field(sa_column=Column(String(32), nullable=False, index=True))
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False),
    )

    published_at: datetime | None = Field(
        default=None,
        sa_column=_published_at_column,
    )
    fetched_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Soft-archive timestamp written by the cleanup pipeline (see
    # ``services.article_cleanup``). NULL means the article is live and
    # shows in user-facing feeds; non-NULL hides it from public queries
    # but keeps the row around so we can confirm the cleanup looks
    # sensible before any hard delete fires later.
    archived_at: datetime | None = Field(
        default=None,
        sa_column=_archived_at_column,
    )

    # 384-dim semantic embedding. Nullable: not every article needs an
    # embedding immediately. The For-You scorer skips articles without
    # one in its semantic-similarity term and lets the other signals
    # (interests, recency, source affinity) handle them.
    #
    # `exclude=True` on the Field keeps embeddings out of every Pydantic
    # serialization — clients should never see 384 floats in API
    # responses. The DB column still exists and is queryable in CRUD code.
    embedding: Any | None = Field(
        default=None,
        sa_column=Column(Vector(EMBEDDING_DIM), nullable=True),
        exclude=True,
    )

    __table_args__ = (
        Index("ix_articles_published_at_desc", _published_at_column.desc()),
        # Cleanup + feed-filter index. Public queries filter
        # ``archived_at IS NULL`` and the cleanup service scans for rows
        # with ``archived_at < cutoff``; a plain b-tree on the column
        # serves both with the same shape.
        Index("ix_articles_archived_at", _archived_at_column),
    )


_saved_articles_user_id_column = Column(
    UUID(as_uuid=True),
    ForeignKey("user.id", ondelete="CASCADE"),
    primary_key=True,
)
_saved_articles_saved_at_column = Column(DateTime(timezone=True), nullable=False)


class SavedArticle(SQLModel, table=True):
    __tablename__ = "saved_articles"

    user_id: uuid.UUID = Field(sa_column=_saved_articles_user_id_column)
    article_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    saved_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=_saved_articles_saved_at_column,
    )

    # Compound (user_id, saved_at desc) index added in migration
    # 4c5d6e7f8a9b. The /articles/saved/ endpoint and the saved-articles
    # JOIN both read by user_id ordered by saved_at desc — without this
    # index Postgres has to sort on the fly per request.
    __table_args__ = (
        Index(
            "ix_saved_articles_user_saved_at",
            _saved_articles_user_id_column,
            _saved_articles_saved_at_column.desc(),
        ),
    )


class ArticleEvent(SQLModel, table=True):
    """Aggregated user-article behavioral events.

    One row per (user, article, event_type). `count` increments on each
    repeat event; `last_at` tracks recency. See migration e3f4a5b6c7d8 for
    the full design rationale.

    `create_type=False` on the ENUM column tells SQLAlchemy to not auto-create
    the type — the migration already manages its lifecycle.
    """

    __tablename__ = "article_events"

    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    article_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    event_type: ArticleEventType = Field(
        sa_column=Column(
            ENUM(
                "clicked",
                "dismissed",
                name="article_event_type",
                create_type=False,
            ),
            primary_key=True,
            nullable=False,
        )
    )
    count: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default="1"),
    )
    first_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    last_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

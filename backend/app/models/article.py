import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc
from app.schemas.article import ArticleBase
from app.schemas.source import Category, ContentQuality, Difficulty, SummaryStatus

_published_at_column = Column(DateTime(timezone=True), nullable=True)


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

    content_quality: ContentQuality = Field(
        default="excerpt",
        sa_column=Column(String(16), nullable=False),
    )

    summary: str | None = Field(default=None, sa_type=Text, nullable=True)
    why_it_matters: str | None = Field(default=None, sa_type=Text, nullable=True)
    difficulty: Difficulty | None = Field(
        default=None,
        sa_column=Column(String(16), nullable=True),
    )

    summary_status: SummaryStatus = Field(
        default="pending",
        sa_column=Column(String(16), nullable=False),
    )
    summary_attempts: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
    )
    summary_prompt_version: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    summary_generated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    __table_args__ = (
        Index("ix_articles_published_at_desc", _published_at_column.desc()),
    )


class SavedArticle(SQLModel, table=True):
    __tablename__ = "saved_articles"

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
    saved_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

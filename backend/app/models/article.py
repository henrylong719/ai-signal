import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field

from app.models.base import get_datetime_utc
from app.schemas.article import ArticleBase
from app.schemas.source import Category

_published_at_column = Column(DateTime(timezone=True), nullable=True)


class Article(ArticleBase, table=True):
    __tablename__ = "articles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    url: str = Field(sa_type=Text, unique=True, nullable=False)
    title: str = Field(sa_type=Text, nullable=False)
    source: str = Field(sa_column=Column(String(64), nullable=False, index=True))

    excerpt: str | None = Field(default=None, sa_type=Text, nullable=True)
    author: str | None = Field(
        default=None, sa_column=Column(String(128), nullable=True)
    )

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

    __table_args__ = (
        Index("ix_articles_published_at_desc", _published_at_column.desc()),
    )

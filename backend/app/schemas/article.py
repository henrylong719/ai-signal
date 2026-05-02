import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.schemas.source import Category


class ArticleBase(SQLModel):
    url: str
    title: str
    source: str = Field(max_length=64)

    excerpt: str | None = None
    image_url: str | None = None
    author: str | None = Field(default=None, max_length=128)

    category: Category
    tags: list[str] = Field(default_factory=list)

    published_at: datetime | None = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(SQLModel):
    url: str | None = None
    title: str | None = None
    source: str | None = Field(default=None, max_length=64)
    excerpt: str | None = None
    image_url: str | None = None
    author: str | None = Field(default=None, max_length=128)
    category: Category | None = None
    tags: list[str] | None = None
    published_at: datetime | None = None


class ArticlePublic(ArticleBase):
    id: uuid.UUID
    fetched_at: datetime


class ArticlesPublic(SQLModel):
    data: list[ArticlePublic]
    count: int

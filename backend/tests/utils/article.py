import uuid

from sqlmodel import Session

from app import crud
from app.models import Article
from app.schemas import ArticleCreate
from app.schemas.source import Category
from tests.utils.utils import random_lower_string


def create_random_article(
    db: Session,
    category: Category = "models",
    image_url: str | None = None,
    source: str = "Example",
) -> Article:
    title = random_lower_string()
    article_in = ArticleCreate(
        url=f"https://example.com/{uuid.uuid4()}",
        title=title,
        source=source,
        excerpt=random_lower_string(),
        image_url=image_url,
        author=random_lower_string(),
        category=category,
        tags=[category],
    )
    return crud.create_article(session=db, article_in=article_in)

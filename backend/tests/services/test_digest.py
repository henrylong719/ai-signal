from datetime import datetime, timezone
from uuid import uuid4

from app.models import Article
from app.schemas.source import Category
from app.services.digest import _build_sections

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


def _article(
    *,
    title: str,
    source: str,
    category: Category = "models",
) -> Article:
    return Article(
        id=uuid4(),
        url=f"https://example.com/{uuid4()}",
        title=title,
        source=source,
        excerpt="excerpt",
        category=category,
        tags=[category],
        published_at=NOW,
    )


def test_top_stories_prefer_distinct_sources() -> None:
    articles = [
        _article(title="Highest ranked", source="Source A"),
        _article(title="Second from same source", source="Source A"),
        _article(title="Best from source B", source="Source B"),
        _article(title="Best from source C", source="Source C"),
    ]

    sections = _build_sections(articles, reasons={})

    assert [article.title for article in sections[0].articles] == [
        "Highest ranked",
        "Best from source B",
        "Best from source C",
    ]


def test_top_stories_fill_from_ranked_articles_when_sources_are_limited() -> None:
    articles = [
        _article(title="Highest ranked", source="Source A"),
        _article(title="Second from same source", source="Source A"),
        _article(title="Best from source B", source="Source B"),
        _article(title="Third from source A", source="Source A"),
    ]

    sections = _build_sections(articles, reasons={})

    assert [article.title for article in sections[0].articles] == [
        "Highest ranked",
        "Best from source B",
        "Second from same source",
    ]

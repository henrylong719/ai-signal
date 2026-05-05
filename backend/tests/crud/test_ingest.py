import asyncio
import uuid
from typing import Any

import pytest
from sqlmodel import Session

from app import crud
from app.crud import ingest
from app.schemas.source import Source


def test_ingest_stores_article_image_url(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    article_url = f"https://example.com/{uuid.uuid4()}"
    article_title = "RSS article with image"
    image_url = "https://example.com/rss-image.png"
    source = Source("Example", "https://example.com/feed.xml", "models")

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]]]:
        del client
        return source, [
            {
                "link": article_url,
                "title": article_title,
                "summary": f'<img src="{image_url}">',
            }
        ]

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 1
    assert result["skipped"] == 0

    article = crud.get_article_by_url(session=db, url=article_url)
    assert article is not None
    assert article.image_url == image_url


def test_ingest_decodes_article_title_html_entities(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    article_url = f"https://example.com/{uuid.uuid4()}"
    source = Source("Example", "https://example.com/feed.xml", "models")

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]]]:
        del client
        return source, [
            {
                "link": article_url,
                "title": "Google Home&#8217;s Gemini AI",
            }
        ]

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 1

    article = crud.get_article_by_url(session=db, url=article_url)
    assert article is not None
    assert article.title == "Google Home\u2019s Gemini AI"


def test_ingest_stores_long_article_author(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    article_url = f"https://example.com/{uuid.uuid4()}"
    long_author = ", ".join(f"Author {index}" for index in range(30))
    source = Source("Example", "https://example.com/feed.xml", "models")

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]]]:
        del client
        return source, [
            {
                "link": article_url,
                "title": "RSS article with long author list",
                "author": long_author,
            }
        ]

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 1
    assert result["skipped"] == 0

    article = crud.get_article_by_url(session=db, url=article_url)
    assert article is not None
    assert article.author == long_author

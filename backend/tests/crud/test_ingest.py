import asyncio
import uuid
from typing import Any

import httpx
import pytest
from sqlmodel import Session

from app import crud
from app.crud import ingest
from app.schemas.source import SOURCES, Source


def test_ingest_stores_article_image_url(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    article_url = f"https://example.com/{uuid.uuid4()}"
    article_title = "RSS article with image"
    image_url = "https://example.com/rss-image.png"
    source = Source("Example", "https://example.com/feed.xml", "models")

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]], str | None]:
        del client
        return (
            source,
            [
                {
                    "link": article_url,
                    "title": article_title,
                    "summary": f'<img src="{image_url}">',
                }
            ],
            None,
        )

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
    ) -> tuple[Source, list[dict[str, Any]], str | None]:
        del client
        return (
            source,
            [
                {
                    "link": article_url,
                    "title": "Google Home&#8217;s Gemini AI",
                }
            ],
            None,
        )

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
    ) -> tuple[Source, list[dict[str, Any]], str | None]:
        del client
        return (
            source,
            [
                {
                    "link": article_url,
                    "title": "RSS article with long author list",
                    "author": long_author,
                }
            ],
            None,
        )

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 1
    assert result["skipped"] == 0

    article = crud.get_article_by_url(session=db, url=article_url)
    assert article is not None
    assert article.author == long_author


def test_ingest_uses_no_priors_audio_enclosure_for_dead_homepage_link(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio_url = f"https://traffic.megaphone.fm/{uuid.uuid4()}.mp3"
    source = Source(
        "No Priors",
        "https://feeds.megaphone.fm/nopriors",
        "business",
        "podcast",
    )

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]], str | None]:
        del client
        return (
            source,
            [
                {
                    "link": "https://no-priors.com/",
                    "title": "Podcast episode with stale homepage link",
                    "links": [
                        {
                            "href": audio_url,
                            "type": "audio/mpeg",
                            "rel": "enclosure",
                        }
                    ],
                }
            ],
            None,
        )

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 1
    article = crud.get_article_by_url(session=db, url=audio_url)
    assert article is not None
    assert article.source == "No Priors"


def test_ingest_records_fetch_error_for_failed_source(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dead feed must land in the run's ``errors`` list. Without this,
    the run tracker records a clean success and dead sources rot invisibly."""
    del db
    source = Source("Example", "https://example.com/feed.xml", "models")

    class FailingClient:
        async def __aenter__(self) -> "FailingClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest.httpx, "AsyncClient", FailingClient)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 0
    errors = result["errors"]
    assert isinstance(errors, list)
    assert any("Example" in error and "ConnectError" in error for error in errors)


def test_ingest_skips_malformed_entry_and_keeps_rest(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One entry with garbage data (here: month 0 in published_parsed)
    must be skipped and reported — not abort the whole run and lose every
    other article from every source."""
    import time

    good_url = f"https://example.com/{uuid.uuid4()}"
    source = Source("Example", "https://example.com/feed.xml", "models")
    bad_time = time.struct_time((2026, 0, 1, 0, 0, 0, 0, 0, 0))

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]], str | None]:
        del client
        return (
            source,
            [
                {
                    "link": f"https://example.com/bad-{uuid.uuid4()}",
                    "title": "Entry with broken date",
                    "published_parsed": bad_time,
                },
                {
                    "link": good_url,
                    "title": "Healthy entry after the broken one",
                },
            ],
            None,
        )

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["inserted"] == 1
    assert crud.get_article_by_url(session=db, url=good_url) is not None
    errors = result["errors"]
    assert isinstance(errors, list)
    assert any("Example" in error for error in errors)


def test_fetch_one_sends_rss_reader_headers() -> None:
    source = Source("Example", "https://example.com/feed.xml", "models")

    class FakeClient:
        request_headers: dict[str, str] | None = None

        async def get(self, _url: str, **kwargs: Any) -> httpx.Response:
            self.request_headers = kwargs.get("headers")
            request = httpx.Request("GET", source.rss_url)
            return httpx.Response(
                200,
                request=request,
                text="""<?xml version="1.0"?>
                <rss version="2.0">
                  <channel>
                    <item>
                      <title>Article</title>
                      <link>https://example.com/article</link>
                    </item>
                  </channel>
                </rss>""",
            )

    client = FakeClient()

    _, entries, error = asyncio.run(ingest._fetch_one(source, client))  # type: ignore[arg-type]

    assert client.request_headers == ingest.RSS_REQUEST_HEADERS
    assert len(entries) == 1
    assert error is None


def test_anthropic_source_uses_production_feed_url() -> None:
    source = next(source for source in SOURCES if source.name == "Anthropic")

    assert "rsshub.app" not in source.rss_url

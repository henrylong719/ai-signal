import asyncio
import uuid
from typing import Any, cast

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from app import crud
from app.crud import ingest
from app.models import Article
from app.schemas.source import SOURCES, Source
from app.services import embeddings


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
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "FailingClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(ingest, "SOURCES", (source,))
    monkeypatch.setattr(ingest.httpx, "AsyncClient", FailingClient)
    monkeypatch.setattr(ingest, "RSS_FETCH_RETRY_BASE_DELAY_SECONDS", 0)

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

    _, entries, error = asyncio.run(
        ingest._fetch_one(source, cast(httpx.AsyncClient, client))
    )

    assert client.request_headers == ingest.RSS_REQUEST_HEADERS
    assert len(entries) == 1
    assert error is None


def test_fetch_one_retries_transient_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Source("Example", "https://example.com/feed.xml", "models")

    class FlakyClient:
        calls = 0

        async def get(self, _url: str, **kwargs: Any) -> httpx.Response:
            del kwargs
            self.calls += 1
            if self.calls < 3:
                raise httpx.ConnectError("temporary outage")
            request = httpx.Request("GET", source.rss_url)
            return httpx.Response(
                200,
                request=request,
                text="<rss><channel><item><title>Recovered</title></item></channel></rss>",
            )

    client = FlakyClient()
    monkeypatch.setattr(ingest, "RSS_FETCH_RETRY_BASE_DELAY_SECONDS", 0)

    _, entries, error = asyncio.run(
        ingest._fetch_one(source, cast(httpx.AsyncClient, client))
    )

    assert client.calls == 3
    assert len(entries) == 1
    assert error is None


def test_fetch_one_does_not_retry_permanent_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Source("Example", "https://example.com/feed.xml", "models")

    class MissingClient:
        calls = 0

        async def get(self, _url: str, **kwargs: Any) -> httpx.Response:
            del kwargs
            self.calls += 1
            request = httpx.Request("GET", source.rss_url)
            return httpx.Response(404, request=request)

    client = MissingClient()
    monkeypatch.setattr(ingest, "RSS_FETCH_RETRY_BASE_DELAY_SECONDS", 0)

    _, entries, error = asyncio.run(
        ingest._fetch_one(source, cast(httpx.AsyncClient, client))
    )

    assert client.calls == 1
    assert entries == []
    assert error == "Example: fetch failed (HTTPStatusError)"


def test_ingest_bounds_source_fetch_concurrency(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del db
    active = 0
    peak = 0
    sources = tuple(
        Source(f"Source {index}", f"https://example.com/{index}.xml", "models")
        for index in range(12)
    )

    async def fake_fetch_one(
        source: Source, client: object
    ) -> tuple[Source, list[dict[str, Any]], str | None]:
        nonlocal active, peak
        del client
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return source, [], None

    monkeypatch.setattr(ingest, "SOURCES", sources)
    monkeypatch.setattr(ingest, "RSS_FETCH_CONCURRENCY", 3)
    monkeypatch.setattr(ingest, "_fetch_one", fake_fetch_one)

    result = asyncio.run(ingest.ingest_all())

    assert result["errors"] == []
    assert peak == 3


def test_embed_inserted_articles_batches_and_reports_provider_errors(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles = [
        Article(
            url=f"https://example.com/embed-{uuid.uuid4()}",
            title=f"Article {index}",
            source="Example",
            category="models",
            tags=["models"],
        )
        for index in range(5)
    ]
    db.add_all(articles)
    db.commit()
    article_ids = [article.id for article in articles]
    batch_sizes: list[int] = []

    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        batch_sizes.append(len(texts))
        if len(batch_sizes) == 2:
            raise httpx.ReadTimeout("provider timeout")
        return [[1.0] + [0.0] * 383 for _ in texts]

    monkeypatch.setattr(ingest, "EMBEDDING_BATCH_SIZE", 2)
    monkeypatch.setattr(embeddings, "embed_texts", fake_embed_texts)

    async def run_embedding() -> tuple[int, list[str]]:
        async with AsyncSession(ingest.async_engine, expire_on_commit=False) as session:
            return await ingest._embed_inserted_articles(session, article_ids)

    try:
        embedded, errors = asyncio.run(run_embedding())

        assert batch_sizes == [2, 2, 1]
        assert embedded == 3
        assert errors == ["Embeddings batch 2/3: failed (ReadTimeout)"]
    finally:
        # This suite shares a session-scoped database. Remove these deliberately
        # pending rows so they do not affect backfill or recency tests.
        db.expire_all()
        for article_id in article_ids:
            article = db.get(Article, article_id)
            if article is not None:
                db.delete(article)
        db.commit()


def test_anthropic_source_uses_production_feed_url() -> None:
    source = next(source for source in SOURCES if source.name == "Anthropic")

    assert "rsshub.app" not in source.rss_url


def test_sources_exclude_confirmed_dead_youtube_feeds() -> None:
    removed = {
        "3Blue1Brown",
        "Two Minute Papers",
        "Yannic Kilcher",
        "Andrej Karpathy (YouTube)",
        "DeepLearningAI",
        "Computerphile",
        "AI Coffee Break",
        "sentdex",
    }

    assert removed.isdisjoint(source.name for source in SOURCES)

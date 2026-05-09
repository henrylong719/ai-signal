import asyncio
import html
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser  # type: ignore[import-untyped]
import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.db import async_engine
from app.models import Article
from app.models.base import get_datetime_utc
from app.schemas.source import SOURCES, Source
from app.services.article_tagging import normalize_excerpt, tag_article
from app.services.rss_images import extract_image_url

logger = logging.getLogger(__name__)

IngestResult = dict[str, int | list[str]]

RSS_REQUEST_HEADERS = {
    "User-Agent": "AI Signal RSS Reader/1.0",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
}
_NO_PRIORS_DEAD_HOSTS = {"no-priors.com", "www.no-priors.com"}


def _clean_text(value: Any) -> str:
    return html.unescape(str(value)).strip()


def _audio_enclosure_url(entry: dict[str, Any]) -> str | None:
    for link in entry.get("links", []) or []:
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        link_type = str(link.get("type") or "")
        if href and link_type.startswith("audio/"):
            return str(href)
    for enclosure in entry.get("enclosures", []) or []:
        if not isinstance(enclosure, dict):
            continue
        href = enclosure.get("href")
        enclosure_type = str(enclosure.get("type") or "")
        if href and enclosure_type.startswith("audio/"):
            return str(href)
    return None


def _entry_url(source: Source, entry: dict[str, Any]) -> str | None:
    url = entry.get("link")

    if source.name == "No Priors":
        parsed = urlparse(str(url or ""))
        if not url or parsed.netloc.lower() in _NO_PRIORS_DEAD_HOSTS:
            return _audio_enclosure_url(entry) or (str(url) if url else None)

    return str(url) if url else None


async def _fetch_one(
    source: Source, client: httpx.AsyncClient
) -> tuple[Source, list[dict[str, Any]]]:
    try:
        resp = await client.get(
            source.rss_url,
            timeout=10.0,
            follow_redirects=True,
            headers=RSS_REQUEST_HEADERS,
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        return source, list(feed.entries)
    except Exception:  # noqa: BLE001
        # One failed source must never break the whole ingest run, but we
        # still want to know *which* source failed and why — silent fetch
        # failures hide chronically dead feeds. Log at warning since this
        # is operational signal, not a correctness bug.
        logger.warning(
            "RSS fetch failed for source %s (%s); skipping this run",
            source.name,
            source.rss_url,
            exc_info=True,
        )
        return source, []


def _published_at(entry: dict[str, Any]) -> datetime | None:
    published = entry.get("published_parsed")
    if not published:
        return None
    return datetime(
        published.tm_year,
        published.tm_mon,
        published.tm_mday,
        published.tm_hour,
        published.tm_min,
        published.tm_sec,
        tzinfo=timezone.utc,
    )


async def _embed_inserted_articles(
    session: AsyncSession, article_ids: list[uuid.UUID]
) -> int:
    """Encode the just-inserted articles inline. Best-effort.

    Bridges the async ingest path to the sync embedding service via
    ``asyncio.to_thread`` so the event loop stays responsive while the
    encoder is busy. Failures are logged and swallowed: the backfill
    will pick up any articles that didn't get embedded here, so an
    embedding failure must never block ingestion of fresh content.

    Returns the count of articles that were successfully embedded.
    """
    if not article_ids:
        return 0

    # Local import keeps torch/sentence-transformers off the ingest
    # module-load path, matching the pattern in services/embeddings.py.
    from app.services.embeddings import article_embedding_text, embed_texts

    # Re-fetch the just-inserted rows so we have the canonical text
    # fields (post any DB-side normalization). Since we have the IDs
    # this is a single bounded query.
    stmt = select(Article).where(col(Article.id).in_(article_ids))
    result = await session.execute(stmt)
    articles = list(result.scalars().all())

    if not articles:
        return 0

    texts = [article_embedding_text(a) for a in articles]
    # Encode in a worker thread — torch is sync and CPU-bound. Without
    # to_thread, encoding hundreds of articles would block the event
    # loop and stall any concurrent ingestion of other sources.
    vectors = await asyncio.to_thread(embed_texts, texts)

    # Write the embeddings back. We use the same async session — the
    # per-row UPDATEs join the open transaction and commit together.
    for article, vector in zip(articles, vectors, strict=True):
        article.embedding = vector
        session.add(article)
    await session.commit()

    return len(articles)


async def ingest_all() -> IngestResult:
    inserted = 0
    skipped = 0
    errors: list[str] = []
    inserted_ids: list[uuid.UUID] = []
    article_table = Article.metadata.tables["articles"]

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_fetch_one(s, client) for s in SOURCES])

    async with AsyncSession(async_engine) as session:
        for source, entries in results:
            for entry in entries:
                url = _entry_url(source, entry)
                title = entry.get("title")
                if not url or not title:
                    continue

                title = _clean_text(title)
                excerpt = normalize_excerpt(entry.get("summary")) or None
                image_url = extract_image_url(entry, feed_url=source.rss_url)
                author = (
                    _clean_text(entry.get("author")) if entry.get("author") else None
                )
                published_at = _published_at(entry)

                category, tags = tag_article(
                    title=title, excerpt=excerpt or "", fallback=source.default_category
                )

                stmt = (
                    insert(article_table)
                    .values(
                        url=url,
                        title=title,
                        source=source.name,
                        excerpt=excerpt,
                        image_url=image_url,
                        author=author,
                        category=category,
                        tags=tags,
                        published_at=published_at,
                        fetched_at=get_datetime_utc(),
                    )
                    .on_conflict_do_nothing(index_elements=["url"])
                    .returning(article_table.c.id)
                )

                result: Result[tuple[Any]] = await session.execute(stmt)
                new_id = result.scalar_one_or_none()
                if new_id is not None:
                    inserted += 1
                    inserted_ids.append(new_id)
                else:
                    skipped += 1

        await session.commit()

        # Inline embedding of just-inserted rows. Wrapped in try/except
        # so any failure here (model load error, OOM, etc.) doesn't fail
        # the ingest run — the new articles are already durably stored,
        # they just won't have embeddings until backfill picks them up.
        embedded = 0
        try:
            embedded = await _embed_inserted_articles(session, inserted_ids)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Inline embedding failed for %d article(s); they will be "
                "embedded on the next backfill run",
                len(inserted_ids),
            )

    return {
        "inserted": inserted,
        "skipped": skipped,
        "embedded": embedded,
        "errors": errors,
    }

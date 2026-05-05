import asyncio
from datetime import datetime, timezone
from typing import Any

import feedparser  # type: ignore[import-untyped]
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_engine
from app.models import Article
from app.models.base import get_datetime_utc
from app.schemas.source import SOURCES, Source
from app.services.article_tagging import normalize_excerpt, tag_article
from app.services.content_quality import classify_content_quality
from app.services.rss_images import extract_image_url

IngestResult = dict[str, int | list[str]]


async def _fetch_one(
    source: Source, client: httpx.AsyncClient
) -> tuple[Source, list[dict[str, Any]]]:
    try:
        resp = await client.get(source.rss_url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        return source, list(feed.entries)
    except Exception:
        return source, []  # one failed source must never break the run


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


async def ingest_all() -> IngestResult:
    inserted = 0
    skipped = 0
    errors: list[str] = []
    article_table = Article.metadata.tables["articles"]

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_fetch_one(s, client) for s in SOURCES])

    async with AsyncSession(async_engine) as session:
        for source, entries in results:
            for entry in entries:
                url = entry.get("link")
                title = entry.get("title")
                if not url or not title:
                    continue

                excerpt = normalize_excerpt(entry.get("summary")) or None
                image_url = extract_image_url(entry, feed_url=source.rss_url)
                author = entry.get("author") or None
                published_at = _published_at(entry)

                category, tags = tag_article(
                    title=title, excerpt=excerpt or "", fallback=source.default_category
                )

                # Decide whether this article is worth sending to the
                # enrichment LLM later. The classifier looks at the title
                # and the normalized excerpt; the worker uses the result
                # via summary_status below.
                content_quality = classify_content_quality(
                    title=title, excerpt=excerpt or ""
                )

                # Articles with usable content go into the worker's queue
                # ('pending'). Title-only and insufficient rows are marked
                # 'skipped' so the worker leaves them alone — no LLM cost,
                # no retries, no wasted attempts.
                if content_quality in ("full", "excerpt"):
                    summary_status = "pending"
                else:
                    summary_status = "skipped"

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
                        content_quality=content_quality,
                        summary_status=summary_status,
                        summary_attempts=0,
                    )
                    .on_conflict_do_nothing(index_elements=["url"])
                    .returning(article_table.c.id)
                )

                result: Result[tuple[Any]] = await session.execute(stmt)
                if result.scalar_one_or_none() is not None:
                    inserted += 1
                else:
                    skipped += 1

        await session.commit()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}

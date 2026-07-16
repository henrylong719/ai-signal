"""Check that every configured Source's rss_url is reachable and parses as a feed.

Uses the same fetch settings as the real ingest path (see app/crud/ingest.py)
so a pass here means ingest_all() will actually get entries from it. Run this
from an environment with normal internet access — sandboxes with a
restrictive egress allowlist will report false failures for every blocked
host.

Usage: uv run python scripts/check_sources.py
"""

import asyncio
import logging
import sys

import feedparser  # type: ignore[import-untyped]
import httpx

from app.schemas.source import SOURCES, Source

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "AI Signal RSS Reader/1.0",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
}
CONCURRENCY = 10
TIMEOUT_SECONDS = 15.0


async def _check_one(
    source: Source, client: httpx.AsyncClient, sem: asyncio.Semaphore
) -> tuple[str, bool, str]:
    async with sem:
        try:
            resp = await client.get(
                source.rss_url,
                timeout=TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=HEADERS,
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            if feed.bozo and not feed.entries:
                return source.name, False, f"unparseable feed ({feed.bozo_exception})"
            if not feed.entries:
                return source.name, False, "parsed but zero entries"
            return source.name, True, f"{len(feed.entries)} entries"
        except Exception as exc:  # noqa: BLE001
            return source.name, False, f"{type(exc).__name__}: {exc}"


async def main() -> None:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_check_one(s, client, sem) for s in SOURCES]
        )

    failures = [r for r in results if not r[1]]
    logger.info("%d/%d sources OK\n", len(results) - len(failures), len(results))

    if failures:
        logger.info("Failing sources:")
        for name, _, detail in failures:
            logger.info("  - %s: %s", name, detail)

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())

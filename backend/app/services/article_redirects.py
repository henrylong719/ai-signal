"""Source-specific outbound redirect resolution.

The `/articles/{id}/go` endpoint normally redirects to the article's stored
URL. A small number of sources need rewriting at click time — most commonly
because the original feed pointed at a now-dead host or at a raw audio
file that browsers can't usefully render.

Per-source workarounds live here rather than inside the route handler so:
  - The hot path (the redirect) stays a thin lookup.
  - Each rewrite has a single named entry point that is easy to test
    in isolation and easy to unhook when the upstream feed is fixed.
  - Successful external lookups (Apple Podcasts) can be cached at the
    process level so a popular episode resolves once instead of paying
    a 2s timeout on every click.

Currently only "No Priors" needs this treatment. New sources should add
their own helper here and a single ``if`` arm in ``resolve_redirect_url``.
"""

from __future__ import annotations

import logging
from typing import Any, cast
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# --- Allow-list of redirect schemes ----------------------------------------
#
# Used by the route handler to defend against open-redirect even though
# destinations come from the DB. Re-exported so callers don't reach into
# this module and the route together.
ALLOWED_REDIRECT_SCHEMES: frozenset[str] = frozenset({"http", "https"})


# --- No Priors --------------------------------------------------------------
#
# The original feed URL points at no-priors.com which intermittently 404s,
# and many episodes are emitted as raw .mp3 hosts that browsers download
# rather than play. We rewrite both cases to Apple Podcasts.

_NO_PRIORS_DEAD_HOSTS = frozenset({"no-priors.com", "www.no-priors.com"})
_NO_PRIORS_AUDIO_HOSTS = frozenset({"traffic.megaphone.fm", "dcs-cached.megaphone.fm"})
_NO_PRIORS_FALLBACK_URL = (
    "https://podcasts.apple.com/us/podcast/"
    "no-priors-artificial-intelligence-technology-startups/id1668002688"
)
_NO_PRIORS_APPLE_SEARCH_URL = "https://itunes.apple.com/search"
_NO_PRIORS_APPLE_COLLECTION_ID = 1668002688
_NO_PRIORS_APPLE_LOOKUP_TIMEOUT_S = 2.0
_NO_PRIORS_APPLE_HOSTS = frozenset({"podcasts.apple.com", "itunes.apple.com"})

# Process-level cache of *successful* title → episode-URL resolutions.
# Failed lookups (network error, no match) are deliberately NOT cached so a
# transient iTunes outage doesn't pin every No Priors click to the show
# landing page until the worker restarts. Per-worker, which is fine: the
# cost of a cache miss is one HTTP call; the cache is best-effort.
_apple_episode_url_cache: dict[str, str] = {}


def _is_no_priors_raw_audio_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.netloc.lower() in _NO_PRIORS_AUDIO_HOSTS
        and parsed.path.lower().endswith(".mp3")
    )


def _no_priors_apple_episode_url(title: str) -> str | None:
    """Resolve a No Priors episode title to its Apple Podcasts URL.

    Calls the iTunes Search API once per unique title; on success the
    result is cached for the lifetime of the process. On any failure
    (timeout, parse error, no episode match) returns None so the caller
    can fall back to the show-landing URL — and skips the cache so the
    next click retries.
    """
    cached = _apple_episode_url_cache.get(title)
    if cached is not None:
        return cached

    try:
        response = httpx.get(
            _NO_PRIORS_APPLE_SEARCH_URL,
            params={
                "term": f"No Priors {title}",
                "media": "podcast",
                "entity": "podcastEpisode",
                "limit": 5,
            },
            timeout=_NO_PRIORS_APPLE_LOOKUP_TIMEOUT_S,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (httpx.HTTPError, ValueError, TypeError):
        # Transient lookup failure. Caller falls back to the show
        # landing URL, so this isn't user-visible. Logged at info so
        # chronic failures show up in operational metrics without
        # alarming on transient timeouts.
        logger.info(
            "Apple Podcasts lookup failed for No Priors title %r; "
            "falling back to show landing",
            title,
        )
        return None

    for result in results:
        if not isinstance(result, dict):
            continue
        if result.get("collectionId") != _NO_PRIORS_APPLE_COLLECTION_ID:
            continue
        episode_url = result.get("trackViewUrl")
        parsed = urlparse(str(episode_url or ""))
        if (
            parsed.scheme in ALLOWED_REDIRECT_SCHEMES
            and parsed.netloc.lower() in _NO_PRIORS_APPLE_HOSTS
        ):
            resolved = str(episode_url)
            _apple_episode_url_cache[title] = resolved
            return resolved
    return None


def resolve_redirect_url(article: Any) -> str:
    """Return the URL the click handler should send the user to.

    For most articles this is the stored URL, untouched. Per-source
    rewrites are evaluated first and only when the article matches —
    we don't pay any extra cost for non-rewritten sources.
    """
    if article.source == "No Priors":
        parsed = urlparse(article.url)
        if parsed.netloc.lower() in _NO_PRIORS_DEAD_HOSTS:
            return _NO_PRIORS_FALLBACK_URL
        if _is_no_priors_raw_audio_url(article.url):
            return (
                _no_priors_apple_episode_url(article.title)
                or _NO_PRIORS_FALLBACK_URL
            )
    # ``article`` is ``Any`` so we can accept either the SQLModel Article
    # row or a SimpleNamespace from tests; ``.url`` on either is a str.
    return cast(str, article.url)

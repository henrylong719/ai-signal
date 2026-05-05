"""Classify how much usable content an article has.

This module decides, before any LLM call, whether an article is worth
sending to the enrichment worker. It is pure, deterministic, and cheap —
no I/O, no async, no external services.

The output drives the `content_quality` column on Article and, by extension,
whether the worker enriches the row or marks it `skipped`.

Inputs are expected to be:
  - title: the raw article title (RSS feeds don't put HTML in titles in
    practice; we don't strip it here either way)
  - excerpt: the *already-normalized* plain-text excerpt produced by
    `app.services.article_tagging.normalize_excerpt`

Categories returned:
  - "full":         >= 1500 informative chars after boilerplate stripping
  - "excerpt":      >= 200 informative chars
  - "title_only":   excerpt is thin/boilerplate, but title is descriptive
  - "insufficient": neither title nor excerpt carry useful signal
"""

from __future__ import annotations

import re

from app.schemas.source import ContentQuality

# Threshold for declaring an excerpt "full content" rather than just an excerpt.
# Most RSS feeds that ship full posts put thousands of chars in <content:encoded>
# (Simon Willison, Lilian Weng, arXiv abstracts, etc.). 1500 is comfortably
# above what a short paragraph excerpt would contain.
_FULL_THRESHOLD = 1500

# Threshold for "this is a real excerpt we can summarize."
# An arXiv abstract is typically 800-2000 chars. A Medium-style RSS preview
# is often 200-400. Below 200 there's not much to work with beyond the title.
_EXCERPT_THRESHOLD = 200

# Below this title length, we don't even trust the title to carry signal.
# (E.g. a title like "Update" or "News" tells us almost nothing.)
_MIN_TITLE_LENGTH = 20

# Patterns that should be stripped before measuring informative content.
# Each is a regex that matches a known boilerplate fragment found in the
# wild across the feeds we ingest. Order doesn't matter — we apply them all.
_BOILERPLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # WordPress "appeared first on" footer. Matches the Microsoft AI feed
    # pattern in particular: "The post TITLE appeared first on FEEDNAME."
    re.compile(r"The post .*? appeared first on .*?\.", re.IGNORECASE | re.DOTALL),
    # Generic "read more" / "continue reading" tails.
    re.compile(
        r"\b(read|continue reading|read the full article)\b[\s\.\u2026\u2192>]*",
        re.IGNORECASE,
    ),
    re.compile(r"\bread more\b[\s\.\u2026\u2192>]*", re.IGNORECASE),
    # Trailing arrow/ellipsis-only fragments left after stripping.
    re.compile(r"[\u2192\u2026\.>\s]+$"),
)


def _strip_boilerplate(text: str) -> str:
    """Remove known boilerplate fragments. Returns trimmed result."""
    for pattern in _BOILERPLATE_PATTERNS:
        text = pattern.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_title_repetition(excerpt: str, title: str) -> str:
    """If the excerpt starts with (or mostly is) the title, remove that copy.

    Many feeds construct the excerpt by repeating the title verbatim before
    the actual preview text. That repetition isn't informative content —
    it's the same signal we already have from the title field.
    """
    if not title:
        return excerpt
    # Case-insensitive prefix removal. We don't try to find the title
    # mid-excerpt; that's rarer and risks false positives.
    if excerpt.lower().startswith(title.lower()):
        return excerpt[len(title) :].lstrip(" \t-:|\u2013\u2014.")
    return excerpt


def _informative_length(title: str, excerpt: str) -> int:
    """How many characters of usable signal does the excerpt carry?

    'Usable' means: after stripping known boilerplate and any verbatim
    repetition of the title.
    """
    if not excerpt:
        return 0
    cleaned = _strip_title_repetition(excerpt, title)
    cleaned = _strip_boilerplate(cleaned)
    return len(cleaned)


def classify_content_quality(*, title: str, excerpt: str) -> ContentQuality:
    """Decide whether an article is worth sending to the enrichment LLM.

    See module docstring for the four possible return values.
    """
    title = (title or "").strip()
    excerpt = (excerpt or "").strip()

    informative = _informative_length(title, excerpt)
    title_ok = len(title) >= _MIN_TITLE_LENGTH

    if informative >= _FULL_THRESHOLD:
        return "full"
    if informative >= _EXCERPT_THRESHOLD:
        return "excerpt"
    if title_ok:
        return "title_only"
    return "insufficient"

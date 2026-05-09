"""Today's Digest assembly.

A digest is a fixed, time-bounded snapshot of the day's articles
organized into sections. Personalized when we have signal, with a
sensible non-personalized fallback for cold-start users.

Two design choices worth noting:

1. Sections are computed, not editorial. We don't curate "Top Story"
   manually — the highest-scored article in each category is the
   section lead. This keeps the digest a deterministic projection
   over the article table.

2. The window is "since the start of today, user-local". For a v0
   that doesn't track user timezone, UTC is fine — switch later when
   we add a tz field to user.
"""

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app import crud
from app.models import Article
from app.schemas.source import Category
from app.services.for_you import build_user_profile
from app.services.ranking import rank_articles
from app.services.recommender import ScoringWeights, UserProfile, reason_for

# Candidate pool size for digest scoring. Smaller than For You's 200
# because the time window already constrains the input set.
_DIGEST_POOL_SIZE = 100

# Digest-specific scoring weights. Compared to the For-You defaults
# (semantic=0.30, explicit=0.40, source=0.15, recency=0.15):
#
# - Semantic bumped to 0.35: the digest is a curated snapshot, so
#   "articles like what you've saved" is a stronger quality signal.
# - Explicit stays at 0.40: stated interests are the strongest signal.
# - Source stays at 0.15: unchanged.
# - Recency dropped to 0.10 with a 12h half-life: everything in the
#   digest is already from today, so recency is mostly a tiebreaker.
#   The shorter half-life (12h vs 7d) makes morning-vs-evening articles
#   meaningfully different within the narrow window.
_DIGEST_WEIGHTS = ScoringWeights(
    semantic=0.35,
    explicit=0.40,
    source=0.15,
    recency=0.10,
    recency_half_life_days=0.5,  # 12 hours
)

# Max articles per section in the rendered digest.
_PER_SECTION_LIMIT = 5

# How far back "today" reaches if the day is quiet. The digest should
# never be empty — if there are no articles in the last 24h we widen
# to 48h. Past that we render an empty state.
_PRIMARY_WINDOW = timedelta(hours=24)
_FALLBACK_WINDOW = timedelta(hours=48)

# Stable section order. Tweak to taste. "top" is built separately.
_CATEGORY_ORDER: tuple[Category, ...] = (
    "research",
    "engineering",
    "models",
    "infrastructure",
    "agents",
    "rag",
    "applications",
    "business",
    "policy",
    "safety",
    "other",
)


@dataclass(frozen=True)
class DigestSection:
    key: str  # "top", "research", "engineering", ...
    title: str  # display string
    articles: list[Article]  # ArticlePublic conversion happens at API boundary.
    reasons: dict[uuid.UUID, str | None]


@dataclass(frozen=True)
class DigestPublic:
    generated_at: datetime
    window_start: datetime
    sections: list[DigestSection]
    is_personalized: bool


def _window_start(now: datetime, window: timedelta) -> datetime:
    return now - window


def _fetch_pool_with_fallback(
    *,
    session: Session,
    now: datetime,
    excluded: set[uuid.UUID],
) -> tuple[Sequence[Article], datetime]:
    """Fetch the candidate pool, widening the window once if today is quiet.

    Returns ``(articles, window_start)``. ``window_start`` reflects which
    window actually produced the pool, so the caller can surface it in
    the response without re-deriving it.
    """
    window_start = _window_start(now, _PRIMARY_WINDOW)
    db_articles = crud.get_articles_in_window(
        session=session,
        since=window_start,
        excluded_ids=excluded,
        limit=_DIGEST_POOL_SIZE,
    )
    if db_articles:
        return db_articles, window_start

    # Day was quiet — widen the window once before giving up.
    window_start = _window_start(now, _FALLBACK_WINDOW)
    db_articles = crud.get_articles_in_window(
        session=session,
        since=window_start,
        excluded_ids=excluded,
        limit=_DIGEST_POOL_SIZE,
    )
    return db_articles, window_start


def _fetch_pool_with_popularity_fallback(
    *,
    session: Session,
    now: datetime,
) -> tuple[Sequence[tuple[Article, int]], datetime]:
    """Like ``_fetch_pool_with_fallback`` but returns ``(article, save_count)`` tuples.

    Used by the anonymous digest path where popularity drives ranking.
    """
    window_start = _window_start(now, _PRIMARY_WINDOW)
    rows = crud.get_articles_in_window_with_popularity(
        session=session,
        since=window_start,
        limit=_DIGEST_POOL_SIZE,
    )
    if rows:
        return rows, window_start

    window_start = _window_start(now, _FALLBACK_WINDOW)
    rows = crud.get_articles_in_window_with_popularity(
        session=session,
        since=window_start,
        limit=_DIGEST_POOL_SIZE,
    )
    return rows, window_start


def _rank_personalized(
    *,
    session: Session,
    user_id: uuid.UUID,
    profile: UserProfile,
    db_articles: Sequence[Article],
) -> tuple[list[Article], dict[uuid.UUID, str | None]]:
    """Score the pool for a signed-in user and return articles in scored order.

    Delegates the actual scoring to ``ranking.rank_articles`` and then
    attaches the digest's reason labels (the simpler "Because you
    follow X" form — the For-You feed adds the "Similar to: <title>"
    refinement, which the digest doesn't surface).
    """
    result = rank_articles(
        session=session,
        user_id=user_id,
        profile=profile,
        db_articles=db_articles,
        weights=_DIGEST_WEIGHTS,
    )
    scored = result.scored

    reasons: dict[uuid.UUID, str | None] = {
        s.article.id: reason_for(s, profile) for s in scored
    }
    # Map back to DB articles in scored order. filter_candidates may
    # drop entries, so we iterate the scored list rather than db_articles.
    by_id = {a.id: a for a in db_articles}
    ordered_articles = [by_id[s.article.id] for s in scored if s.article.id in by_id]
    return ordered_articles, reasons


def _rank_anonymous(
    db_articles: Sequence[tuple[Article, int]],
    now: datetime,
) -> tuple[list[Article], dict[uuid.UUID, str | None]]:
    """Order the pool for an anonymous request using popularity + recency.

    Without a user profile we blend two signals:

      - **Popularity (0.6):** How many users have saved this article.
        Log-scaled and normalized so a few saves matter a lot but
        viral articles don't completely dominate.
      - **Recency (0.4):** Exponential decay with a 12-hour half-life,
        same as the personalized digest. Within a single day's window
        this still creates meaningful spread between morning and
        evening articles.

    This replaces the old pure-recency ordering, which made the
    anonymous digest identical to the Latest feed.

    Reasons surface the popularity signal when it's meaningful
    ("Popular in the community") so anonymous users still see *why*
    an article appears high in the digest.
    """
    if not db_articles:
        return [], {}

    # Unpack and compute raw scores.
    scored: list[tuple[Article, int, float]] = []
    max_saves = max((count for _, count in db_articles), default=0)

    for article, save_count in db_articles:
        # Log-scaled popularity in [0, 1]. log1p(0)=0, log1p(max)=1.
        if max_saves > 0:
            pop = math.log1p(save_count) / math.log1p(max_saves)
        else:
            pop = 0.0

        # Recency: 12-hour half-life decay.
        if article.published_at is not None:
            pub = article.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            age_days = max((now - pub).total_seconds() / 86400.0, 0.0)
            rec = 0.5 ** (age_days / 0.5)  # 12h half-life
        else:
            rec = 0.0

        blended = 0.6 * pop + 0.4 * rec
        scored.append((article, save_count, blended))

    scored.sort(key=lambda t: t[2], reverse=True)

    articles = [a for a, _, _ in scored]
    reasons: dict[uuid.UUID, str | None] = {}
    for article, save_count, _ in scored:
        if save_count >= 3:
            reasons[article.id] = "Popular in the community"
        elif save_count >= 1:
            reasons[article.id] = "Trending today"
        else:
            reasons[article.id] = None

    return articles, reasons


def build_digest(
    *,
    session: Session,
    user_id: uuid.UUID | None,
    now: datetime | None = None,
) -> DigestPublic:
    """Assemble today's digest.

    If user_id is None (anonymous), we return a non-personalized
    digest ranked by source authority + recency. Same sections, same
    shape — just no semantic layer and no behavioral filters.
    """
    now = now or datetime.now(timezone.utc)

    # Personalization inputs. Anonymous requests skip profile + semantic
    # layer entirely; the recommender's other terms (recency, source
    # weight) still produce a sensible order via _rank_anonymous.
    profile = (
        build_user_profile(session=session, user_id=user_id)
        if user_id is not None
        else None
    )
    excluded: set[uuid.UUID] = (
        set(profile.saved_article_ids) | set(profile.dismissed_article_ids)
        if profile is not None
        else set()
    )

    if profile is not None:
        db_articles, window_start = _fetch_pool_with_fallback(
            session=session, now=now, excluded=excluded
        )
        assert user_id is not None
        ordered_articles, reasons = _rank_personalized(
            session=session,
            user_id=user_id,
            profile=profile,
            db_articles=db_articles,
        )
    else:
        db_articles_with_pop, window_start = _fetch_pool_with_popularity_fallback(
            session=session, now=now
        )
        ordered_articles, reasons = _rank_anonymous(db_articles_with_pop, now)

    sections = _build_sections(ordered_articles, reasons)

    return DigestPublic(
        generated_at=now,
        window_start=window_start,
        sections=sections,
        is_personalized=profile is not None,
    )


def _build_sections(
    articles: list[Article],
    reasons: dict[uuid.UUID, str | None],
) -> list[DigestSection]:
    """Slice the ranked list into display sections.

    'Top' prefers distinct sources when possible. Then per-category
    sections, each capped at _PER_SECTION_LIMIT, with articles already
    used in 'Top' filtered out so we don't double-show.
    """
    if not articles:
        return []

    top = _top_stories(articles, limit=3)
    used = {a.id for a in top}
    sections: list[DigestSection] = [
        DigestSection(
            key="top",
            title="Top stories",
            articles=top,
            reasons={a.id: reasons.get(a.id) for a in top},
        )
    ]

    by_category: dict[Category, list[Article]] = {}
    for article in articles:
        if article.id in used:
            continue
        by_category.setdefault(article.category, []).append(article)

    for cat in _CATEGORY_ORDER:
        bucket = by_category.get(cat, [])[:_PER_SECTION_LIMIT]
        if not bucket:
            continue
        sections.append(
            DigestSection(
                key=cat,
                title=_section_title(cat),
                articles=bucket,
                reasons={a.id: reasons.get(a.id) for a in bucket},
            )
        )
    return sections


def _top_stories(articles: list[Article], *, limit: int) -> list[Article]:
    """Pick the top stories, preferring distinct sources AND categories.

    Three passes, each filling remaining slots:
      1. Pick articles with both a new source and a new category — gives
         the broadest overview of the day.
      2. Pick articles with at least a new source or a new category —
         still adds diversity on one dimension.
      3. Fill any remaining slots from the ranked order regardless.
    """
    selected: list[Article] = []
    selected_ids: set[uuid.UUID] = set()
    seen_sources: set[str] = set()
    seen_categories: set[str] = set()

    # Pass 1: both source and category are new.
    for article in articles:
        source_key = article.source.strip().casefold()
        cat_key = article.category.strip().casefold()
        if source_key not in seen_sources and cat_key not in seen_categories:
            selected.append(article)
            selected_ids.add(article.id)
            seen_sources.add(source_key)
            seen_categories.add(cat_key)
            if len(selected) >= limit:
                return selected

    # Pass 2: at least one of source or category is new.
    for article in articles:
        if article.id in selected_ids:
            continue
        source_key = article.source.strip().casefold()
        cat_key = article.category.strip().casefold()
        if source_key not in seen_sources or cat_key not in seen_categories:
            selected.append(article)
            selected_ids.add(article.id)
            seen_sources.add(source_key)
            seen_categories.add(cat_key)
            if len(selected) >= limit:
                return selected

    # Pass 3: fill remaining slots from ranked order.
    for article in articles:
        if article.id in selected_ids:
            continue
        selected.append(article)
        selected_ids.add(article.id)
        if len(selected) >= limit:
            break

    return selected


def _section_title(category: Category) -> str:
    return {
        "research": "Research",
        "engineering": "Engineering",
        "models": "Models",
        "infrastructure": "Infrastructure",
        "agents": "Agents",
        "rag": "RAG",
        "applications": "Applications",
        "business": "Business",
        "policy": "Policy",
        "safety": "Safety",
        "other": "Other",
    }.get(category, category.title())

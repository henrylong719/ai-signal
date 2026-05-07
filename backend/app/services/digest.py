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

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app import crud
from app.models import Article
from app.schemas.source import Category
from app.services.for_you import (
    _candidate_similarities,
    _resolve_user_vector,
    _to_candidate,
    build_user_profile,
)
from app.services.recommender import (
    filter_candidates,
    reason_for,
    score_candidates,
)

# Candidate pool size for digest scoring. Smaller than For You's 200
# because the time window already constrains the input set.
_DIGEST_POOL_SIZE = 100

# Max articles per section in the rendered digest.
_PER_SECTION_LIMIT = 5

# How far back "today" reaches if the day is quiet. The digest should
# never be empty — if there are no articles in the last 24h we widen
# to 48h. Past that we render an empty state.
_PRIMARY_WINDOW = timedelta(hours=24)
_FALLBACK_WINDOW = timedelta(hours=48)


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
    window_start = _window_start(now, _PRIMARY_WINDOW)

    # Personalization inputs. If anonymous, we synthesize an empty
    # profile and skip the semantic layer — the recommender's other
    # terms (recency, source weight) still produce a sensible order.
    profile = (
        build_user_profile(session=session, user_id=user_id)
        if user_id is not None
        else None
    )
    excluded = (
        set(profile.saved_article_ids) | set(profile.dismissed_article_ids)
        if profile is not None
        else set()
    )

    db_articles = crud.get_articles_in_window(
        session=session,
        since=window_start,
        excluded_ids=excluded,
        limit=_DIGEST_POOL_SIZE,
    )
    if not db_articles:
        # Day was quiet — widen the window once before giving up.
        window_start = _window_start(now, _FALLBACK_WINDOW)
        db_articles = crud.get_articles_in_window(
            session=session,
            since=window_start,
            excluded_ids=excluded,
            limit=_DIGEST_POOL_SIZE,
        )

    # Score the pool. Personalized path uses the full For-You scorer;
    # anonymous path skips semantic and uses a stub profile.
    if profile is not None:
        assert user_id is not None
        user_vec = _resolve_user_vector(session=session, user_id=user_id)
        sims = (
            _candidate_similarities(user_vector=user_vec, db_articles=db_articles)
            if user_vec is not None
            else None
        )
        candidates = filter_candidates([_to_candidate(a) for a in db_articles], profile)
        scored = score_candidates(candidates, profile, semantic_similarities=sims)
        reasons = {s.article.id: reason_for(s, profile) for s in scored}
        # Map back to DB articles in scored order.
        by_id = {a.id: a for a in db_articles}
        ordered_articles = [
            by_id[s.article.id] for s in scored if s.article.id in by_id
        ]
    else:
        # Anonymous: just rely on published_at order from CRUD.
        ordered_articles = list(db_articles)
        reasons = {}

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

    # Stable section order. Tweak to taste.
    category_order: list[Category] = [
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
    ]
    for cat in category_order:
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
    selected: list[Article] = []
    selected_ids: set[uuid.UUID] = set()
    seen_sources: set[str] = set()

    for article in articles:
        source_key = article.source.strip().casefold()

        if source_key in seen_sources:
            continue

        selected.append(article)
        selected_ids.add(article.id)
        seen_sources.add(source_key)

        if len(selected) >= limit:
            return selected

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

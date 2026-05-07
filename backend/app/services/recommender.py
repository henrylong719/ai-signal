"""Recommendation scoring.

This module is intentionally framework-free: no FastAPI, no SQLModel, no
embeddings library imports. It operates on plain dataclasses so it can be
unit-tested in isolation and reused across endpoints, batch jobs, and offline
evaluation scripts.

The scoring pipeline is a weighted linear combination of normalized signals:

    score = w_sem * semantic_similarity
          + w_exp * explicit_interest_match
          + w_src * source_affinity
          + w_rec * recency

Each component is normalized to [0, 1] so weights are meaningfully comparable
and the final score is bounded and explainable. The ``ScoreBreakdown`` returned
alongside each scored article exposes every component, which is what powers the
"Because you follow X" reason labels on the frontend: we pick the dominant
positive contributor rather than generating a plausible-sounding string after
the fact.

Negative signals are handled by hard-filtering, not soft-penalizing. Articles
the user has saved (already on the Saved tab) or dismissed are removed before
scoring; this avoids the failure mode where a high enough match resurfaces a
dismissed article. There is no soft "viewed" penalty because in this app a
card scrolling into an infinite-scroll viewport is not a reliable signal of
attention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateArticle:
    """Article data needed for scoring.

    Decoupled from the SQLModel ``Article`` so the scorer can be tested with
    plain dicts and so the DB layer can project only the columns it needs.
    """

    id: UUID
    title: str
    source: str
    category: str
    tags: tuple[str, ...]
    published_at: datetime | None


@dataclass(frozen=True)
class UserProfile:
    """Aggregated state used to score candidates for one user.

    ``saved_article_ids`` and ``dismissed_article_ids`` are used by
    ``filter_candidates`` to remove candidates entirely. There is intentionally
    no soft "viewed" penalty: in this app cards in an infinite-scroll feed
    can't be reliably distinguished as "seen but ignored" vs "not yet
    scrolled to," so a soft penalty would be built on noise.

    ``interest_categories`` and ``interest_tags`` come from explicit
    onboarding choices.

    ``preferred_sources`` are sources the user has explicitly opted into
    via the personalization page — the strongest possible source signal.
    They feed the source-affinity term only; they do not flow into the
    user embedding (semantic similarity is built from saved/clicked
    article embeddings plus stated interest text).

    ``saved_tags`` / ``saved_sources`` are derived from saved articles
    (strongest behavioral positive). ``clicked_tags`` / ``clicked_sources``
    are derived from outbound-link clicks recorded by the redirect endpoint
    (weaker positive — a click means interest, but not necessarily that the
    user actually read the article). Both feed the explicit-match and
    source-affinity terms, with saves weighted above clicks.
    """

    interest_categories: frozenset[str] = field(default_factory=frozenset)
    interest_tags: frozenset[str] = field(default_factory=frozenset)
    preferred_sources: frozenset[str] = field(default_factory=frozenset)
    saved_tags: frozenset[str] = field(default_factory=frozenset)
    saved_sources: frozenset[str] = field(default_factory=frozenset)
    clicked_tags: frozenset[str] = field(default_factory=frozenset)
    clicked_sources: frozenset[str] = field(default_factory=frozenset)
    saved_article_ids: frozenset[UUID] = field(default_factory=frozenset)
    dismissed_article_ids: frozenset[UUID] = field(default_factory=frozenset)

    @property
    def has_any_signal(self) -> bool:
        """Whether the user has enough signal for personalized ranking."""
        return bool(
            self.interest_categories
            or self.interest_tags
            or self.preferred_sources
            or self.saved_tags
            or self.saved_sources
            or self.clicked_tags
            or self.clicked_sources
        )


@dataclass(frozen=True)
class ScoringWeights:
    """Tunable weights for the linear combination.

    Defaults reflect a content-based bias appropriate for a news feed where
    explicit interests and saved-article signal are the strongest predictors.
    Semantic similarity gets meaningful weight but is intentionally not the
    dominant term — embeddings of short titles are noisy.

    Adjust ``recency`` upward for fresher feeds; it currently uses a 7-day
    half-life decay (see ``recency_score``).
    """

    # Defaults tuned so personalization dominates recency on the For-You feed
    # (the Latest tab already shows pure recency). Sum to 1.0 so the final
    # score is bounded in [0, 1]. Adjust via constructor in tests or via
    # env-driven config in the API layer.
    semantic: float = 0.30
    explicit: float = 0.40
    source: float = 0.15
    recency: float = 0.15

    # Recency half-life in days. With t_half=7 an article published today
    # scores 1.0, one a week old scores 0.5, two weeks 0.25, etc.
    recency_half_life_days: float = 7.0


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreBreakdown:
    """Per-article scoring components, for ranking and for reason labels.

    The breakdown is the source of truth: ``total`` is computed from the
    components (not stored independently), and ``reason()`` picks the
    dominant positive contributor. This guarantees the reason shown to
    the user actually drove the ranking.
    """

    semantic: float
    explicit: float
    source: float
    recency: float
    weights: ScoringWeights

    @property
    def total(self) -> float:
        return (
            self.weights.semantic * self.semantic
            + self.weights.explicit * self.explicit
            + self.weights.source * self.source
            + self.weights.recency * self.recency
        )

    def dominant_signal(self) -> str | None:
        """Name of the highest-contributing positive term, or None if all zero.

        Used to render reason labels. We compare *weighted* contributions, not
        raw component values, so a high-weight small term beats a low-weight
        large one — which matches the actual ranking impact.
        """
        contributions = {
            "semantic": self.weights.semantic * self.semantic,
            "explicit": self.weights.explicit * self.explicit,
            "source": self.weights.source * self.source,
            "recency": self.weights.recency * self.recency,
        }
        best_name, best_value = max(contributions.items(), key=lambda kv: kv[1])
        return best_name if best_value > 0 else None


@dataclass(frozen=True)
class ScoredArticle:
    article: CandidateArticle
    breakdown: ScoreBreakdown

    @property
    def score(self) -> float:
        return self.breakdown.total


# ---------------------------------------------------------------------------
# Component scorers — each returns a value in [0, 1].
# ---------------------------------------------------------------------------


def explicit_match_score(article: CandidateArticle, profile: UserProfile) -> float:
    """How well the article matches the user's stated and behavioral interests.

    Combines:
      - category match against onboarding-selected categories
      - tag overlap (Jaccard) against three sources, weighted by signal
        strength: saved tags (strongest) > clicked tags > onboarding tags.

    Returns 0 if the user has provided no interest signal at all.

    Tag-source weights are 1:2:3 (stated:clicked:saved), normalized to sum
    to 1. Saving an article is a stronger commitment than clicking through
    to read it, which is in turn stronger than picking a topic checkbox.
    """
    if not (
        profile.interest_categories
        or profile.interest_tags
        or profile.saved_tags
        or profile.clicked_tags
    ):
        return 0.0

    category_score = 1.0 if article.category in profile.interest_categories else 0.0

    article_tags = set(article.tags)
    started_overlap = _jaccard(article_tags, profile.interest_tags)
    clicked_overlap = _jaccard(article_tags, profile.clicked_tags)
    saved_overlap = _jaccard(article_tags, profile.saved_tags)
    # Weights 1:2:3 normalized to /6. Saved > clicked > started.
    tag_score = (
        (1 / 6) * started_overlap + (2 / 6) * clicked_overlap + (3 / 6) * saved_overlap
    )

    # Average category and tag signals; both already in [0,1]
    return 0.5 * category_score + 0.5 * tag_score


def source_affinity_score(
    article: CandidateArticle,
    profile: UserProfile,
) -> float:
    """Affinity for the article's source.

    Four-level scale, highest applicable level wins:
      1.0  — user has explicitly opted into this source via the
             personalization page (strongest, user told us directly)
      0.7  — user has saved an article from this source (strong behavioral)
      0.4  — user has clicked through but never saved (weaker behavioral)
      0.0  — no signal for this source

    Discrete levels rather than continuous (e.g., proportion of saves
    from this source) because graduated source-affinity tends to
    over-recommend whatever the user engaged with most recently and
    reduces feed diversity.

    The 1.0 ceiling for explicit preference is what makes
    "Because you follow X" labels meaningful: the user actually said so.
    """
    if article.source in profile.preferred_sources:
        return 1.0
    if article.source in profile.saved_sources:
        return 0.7
    if article.source in profile.clicked_sources:
        return 0.4
    return 0.0


def recency_score(
    article: CandidateArticle,
    *,
    weights: ScoringWeights,
    now: datetime,
) -> float:
    """Exponential decay on age, half-life set in ``weights``.

    Articles without a ``published_at`` get 0 — we'd rather not surface
    timestamp-less articles in a "for you" feed where freshness matters.
    """
    if article.published_at is None:
        return 0.0

    published = article.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)

    age_days = max((now - published).total_seconds() / 86400.0, 0.0)
    # 0.5 ** (age / half_life). Equivalent to exp(-ln(2) * age / half_life).
    return float(0.5 ** (age_days / weights.recency_half_life_days))


# ---------------------------------------------------------------------------
# Filtering and main entry point
# ---------------------------------------------------------------------------


def filter_candidates(
    candidates: list[CandidateArticle], profile: UserProfile
) -> list[CandidateArticle]:
    """Hard-filter saved and dismissed articles before scoring.

    Saved articles already live on a dedicated tab so re-recommending them
    wastes feed space. Dismissed articles are an explicit "don't show me this"
    signal — soft-penalizing them lets a high enough match resurface them,
    which is the wrong behavior.
    """

    excluded = profile.saved_article_ids | profile.dismissed_article_ids
    if not excluded:
        return list(candidates)
    return [c for c in candidates if c.id not in excluded]


def score_candidates(
    candidates: list[CandidateArticle],
    profile: UserProfile,
    *,
    semantic_similarities: dict[UUID, float] | None = None,
    weights: ScoringWeights | None = None,
    now: datetime | None = None,
) -> list[ScoredArticle]:
    """Score and rank candidates for one user.

    ``semantic_similarities`` maps article_id -> cosine similarity in [0, 1]
    against the user's interest vector. When None (e.g., before pgvector is
    wired up, or for users without an interest vector) the semantic term is
    skipped — the scorer remains useful with explicit + source + recency
    signals alone.

    Returns articles sorted by descending score. Filtering is the caller's
    responsibility — call ``filter_candidates`` first if the input list may
    contain saved or dismissed items.
    """
    weights = weights or ScoringWeights()
    now = now or datetime.now(timezone.utc)
    sims = semantic_similarities or {}

    scored: list[ScoredArticle] = []
    for article in candidates:
        breakdown = ScoreBreakdown(
            semantic=_clamp(sims.get(article.id, 0.0)),
            explicit=_clamp(explicit_match_score(article, profile)),
            source=_clamp(source_affinity_score(article, profile)),
            recency=_clamp(recency_score(article, weights=weights, now=now)),
            weights=weights,
        )
        scored.append(ScoredArticle(article=article, breakdown=breakdown))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Reason labels — small enough to live here, used by API layer.
# ---------------------------------------------------------------------------


def reason_for(scored: ScoredArticle, profile: UserProfile) -> str | None:
    """Human-readable explanation of why an article was ranked high.

    Returns None when no positive signal contributed (pure recency-only
    rankings get no badge — the UI can decide whether to show one).
    """
    dominant = scored.breakdown.dominant_signal()
    if dominant is None:
        return None

    article = scored.article
    if dominant == "semantic":
        return "Similar to articles you saved"
    if dominant == "explicit":
        # Prefer naming the matched category if there is one — it reads better
        # than naming a tag like "rag-evals".
        if article.category in profile.interest_categories:
            return f"Because you follow {_humanize_category(article.category)}"
        matched_tags = set(article.tags) & (
            profile.interest_tags | profile.saved_tags | profile.clicked_tags
        )
        if matched_tags:
            tag = sorted(matched_tags)[0]
            return f"Matches your interest in {tag}"
        return "Matches your interest"
    if dominant == "source":
        # Explicit preference > saved > clicked, mirroring the score levels.
        # The phrasing differs to reflect *why* the source matters: explicit
        # preference is a direct opt-in ("you follow"), saved is a strong
        # behavioral signal ("you saved articles from"), clicked is a
        # weaker one ("you read").
        if article.source in profile.preferred_sources:
            return f"Because you follow {article.source}"
        if article.source in profile.saved_sources:
            return f"Because you saved articles from {article.source}"
        if article.source in profile.clicked_sources:
            return f"Because you read {article.source}"
        # Source dominant but no source membership shouldn't happen in
        # practice — source_affinity_score returns 0 in that case, so it
        # can't dominate. Defensive None.
        return None
    if dominant == "recency":
        return "Fresh from your feed"

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jaccard(a: set[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    if math.isnan(x):
        return low
    return max(low, min(high, x))


def _humanize_category(category: str) -> str:
    """Render a category code as a user-facing label.

    Kept local rather than pulled from the Category Literal to avoid coupling
    the scorer to source.py's schema.
    """
    overrides = {"rag": "RAG"}
    return overrides.get(category, category.capitalize())

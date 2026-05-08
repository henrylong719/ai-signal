"""Tests for the recommendation scorer.

These tests double as a spec: each test name states a property the scorer
guarantees. The fixtures stay deliberately small and explicit so each test
reads top-to-bottom without jumping around.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.services.recommender import (
    CandidateArticle,
    ScoringWeights,
    UserProfile,
    explicit_match_score,
    filter_candidates,
    reason_for,
    recency_score,
    score_candidates,
    source_affinity_score,
)

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


def _article(
    *,
    id: UUID | None = None,
    title: str = "Some article",
    source: str = "Anthropic",
    category: str = "engineering",
    tags: tuple[str, ...] = (),
    age_days: float | None = 0.0,
) -> CandidateArticle:
    """Compact article factory keeping per-test fixtures readable."""
    published = NOW - timedelta(days=age_days) if age_days is not None else None
    return CandidateArticle(
        id=id or uuid4(),
        title=title,
        source=source,
        category=category,
        tags=tags,
        published_at=published,
    )


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------


def test_explicit_match_returns_zero_when_user_has_no_interests() -> None:
    article = _article(category="agents", tags=("agents", "tools"))
    profile = UserProfile()  # no interests, no saves, no clicks

    assert explicit_match_score(article, profile) == 0.0


def test_explicit_match_rewards_matching_category() -> None:
    article = _article(category="agents", tags=())
    profile = UserProfile(interest_categories=frozenset({"agents"}))

    # Category match contributes 0.5 (the category half of the score), tags 0.
    assert explicit_match_score(article, profile) == 0.5


def test_explicit_match_with_only_stated_tags_is_nonzero() -> None:
    """A user with only stated interest tags (no categories, no saves, no
    clicks) should still get a nonzero explicit-match score for an article
    whose tags overlap. This guards the bug where stated tags were
    accidentally compared against interest_categories instead of
    interest_tags."""
    article = _article(category="other", tags=("rag", "evals"))
    profile = UserProfile(interest_tags=frozenset({"rag", "evals"}))

    score = explicit_match_score(article, profile)

    # No category match (category="other" not in empty interest_categories).
    # Full Jaccard overlap on tags = 1.0, weighted by the stated weight 1/6.
    # Tag-side total = 1/6, then halved with the (zero) category half = 1/12.
    assert score > 0
    assert abs(score - (0.5 * 0.0 + 0.5 * (1 / 6))) < 1e-9


def test_explicit_match_weights_saved_above_clicked_above_stated() -> None:
    """Strength order: saved > clicked > stated. Each Jaccard-overlaps fully."""
    article = _article(category="other", tags=("rag", "evals"))

    only_stated = UserProfile(interest_tags=frozenset({"rag", "evals"}))
    only_clicked = UserProfile(clicked_tags={"rag": 1.0, "evals": 1.0})
    only_saved = UserProfile(saved_tags={"rag": 1.0, "evals": 1.0})

    stated_score = explicit_match_score(article, only_stated)
    clicked_score = explicit_match_score(article, only_clicked)
    saved_score = explicit_match_score(article, only_saved)

    # All three are nonzero (the bug-guard above ensures stated > 0).
    assert 0 < stated_score < clicked_score < saved_score


def test_source_affinity_is_one_for_explicitly_preferred_source() -> None:
    """Explicit preference is the strongest possible source signal — 1.0."""
    article = _article(source="OpenAI")
    profile = UserProfile(preferred_sources=frozenset({"OpenAI"}))

    assert source_affinity_score(article, profile) == 1.0


def test_source_affinity_prefers_explicit_over_saved() -> None:
    """When a source is both explicitly preferred and saved-from, explicit wins
    (1.0, not the saved 0.7) — the user told us directly."""
    article = _article(source="LangChain")
    profile = UserProfile(
        preferred_sources=frozenset({"LangChain"}),
        saved_sources={"LangChain": 1.0},
    )

    assert source_affinity_score(article, profile) == 1.0


def test_source_affinity_levels_ordered() -> None:
    """preferred (1.0) > saved (0.7) > clicked (0.4) > none (0.0)."""
    article = _article(source="LangChain")

    only_preferred = UserProfile(preferred_sources=frozenset({"LangChain"}))
    only_saved = UserProfile(saved_sources={"LangChain": 1.0})
    only_clicked = UserProfile(clicked_sources={"LangChain": 1.0})
    none_set = UserProfile()

    preferred_score = source_affinity_score(article, only_preferred)
    saved_score = source_affinity_score(article, only_saved)
    clicked_score = source_affinity_score(article, only_clicked)
    none_score = source_affinity_score(article, none_set)

    assert preferred_score == 1.0
    assert saved_score == 0.7
    assert clicked_score == 0.4
    assert none_score == 0.0
    assert preferred_score > saved_score > clicked_score > none_score


def test_source_affinity_attenuates_with_decay_for_saved_sources() -> None:
    """Saved-source affinity is `0.7 * decay_weight`. A fresh save
    contributes the full 0.7; an old save contributes proportionally
    less. The CRUD layer is responsible for computing the decay
    weight; the scorer just consumes it."""
    article = _article(source="LangChain")

    fresh = UserProfile(saved_sources={"LangChain": 1.0})
    half_decayed = UserProfile(saved_sources={"LangChain": 0.5})
    nearly_dead = UserProfile(saved_sources={"LangChain": 0.05})

    assert source_affinity_score(article, fresh) == 0.7
    assert abs(source_affinity_score(article, half_decayed) - 0.35) < 1e-9
    assert abs(source_affinity_score(article, nearly_dead) - 0.035) < 1e-9


def test_explicit_match_attenuates_with_decay_for_saved_tags() -> None:
    """Saved-tag overlap is decay-attenuated. With identical tag
    overlap structure, a freshly-saved tag contributes more than a
    decayed one."""
    article = _article(category="other", tags=("rag", "evals"))

    fresh = UserProfile(saved_tags={"rag": 1.0, "evals": 1.0})
    decayed = UserProfile(saved_tags={"rag": 0.3, "evals": 0.3})

    fresh_score = explicit_match_score(article, fresh)
    decayed_score = explicit_match_score(article, decayed)

    assert fresh_score > 0
    assert decayed_score > 0
    # Decayed score should be ~30% of fresh (the attenuation factor).
    assert abs(decayed_score / fresh_score - 0.3) < 1e-6


def test_source_affinity_is_seven_tenths_for_freshly_saved_sources() -> None:
    """Freshly saved (decay weight 1.0) yields the full saved-level
    ceiling of 0.7 — same value the discrete-level scorer used to
    return before decay was added."""
    article = _article(source="LangChain")
    profile = UserProfile(saved_sources={"LangChain": 1.0})

    assert source_affinity_score(article, profile) == 0.7


def test_source_affinity_is_four_tenths_for_clicked_only_sources() -> None:
    """Clicking through is meaningful but weaker than saving."""
    article = _article(source="LangChain")
    profile = UserProfile(clicked_sources={"LangChain": 1.0})

    assert source_affinity_score(article, profile) == 0.4


def test_source_affinity_prefers_saved_over_clicked_when_both_present() -> None:
    article = _article(source="LangChain")
    profile = UserProfile(
        saved_sources={"LangChain": 1.0},
        clicked_sources={"LangChain": 1.0},
    )

    assert source_affinity_score(article, profile) == 0.7


def test_source_affinity_is_zero_for_unknown_source() -> None:
    article = _article(source="RandomBlog")
    profile = UserProfile(saved_sources={"LangChain": 1.0})

    assert source_affinity_score(article, profile) == 0.0


def test_has_any_signal_true_with_only_preferred_sources() -> None:
    """A user with only explicit source preferences (no topics, tags, saves,
    or clicks) should still count as having signal — the recommender will
    rank by source-affinity + recency only."""
    profile = UserProfile(preferred_sources=frozenset({"OpenAI"}))

    assert profile.has_any_signal is True


def test_has_any_signal_false_for_completely_empty_profile() -> None:
    profile = UserProfile()

    assert profile.has_any_signal is False


def test_recency_decays_with_seven_day_half_life() -> None:
    weights = ScoringWeights(recency_half_life_days=7.0)
    today = _article(age_days=0)
    week_old = _article(age_days=7)
    two_weeks_old = _article(age_days=14)

    assert recency_score(today, weights=weights, now=NOW) == 1.0
    assert abs(recency_score(week_old, weights=weights, now=NOW) - 0.5) < 1e-9
    assert abs(recency_score(two_weeks_old, weights=weights, now=NOW) - 0.25) < 1e-9


def test_recency_is_zero_for_articles_without_published_at() -> None:
    weights = ScoringWeights()
    article = _article(age_days=None)

    assert recency_score(article, weights=weights, now=NOW) == 0.0


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_filter_removes_saved_and_dismissed_articles() -> None:
    """Negative signals are hard filters, not soft penalties.

    Saved articles already live on a dedicated tab; dismissed articles are
    an explicit "don't show me this" — soft-penalizing either lets a high
    enough match resurface them, which is the wrong behavior.
    """
    keep = _article()
    saved = _article()
    dismissed = _article()

    profile = UserProfile(
        saved_article_ids=frozenset({saved.id}),
        dismissed_article_ids=frozenset({dismissed.id}),
    )

    result = filter_candidates([keep, saved, dismissed], profile)

    assert [c.id for c in result] == [keep.id]


def test_filter_is_a_noop_when_profile_has_no_exclusions() -> None:
    articles = [_article(), _article(), _article()]
    profile = UserProfile()

    result = filter_candidates(articles, profile)

    assert [c.id for c in result] == [a.id for a in articles]


# ---------------------------------------------------------------------------
# End-to-end scoring
# ---------------------------------------------------------------------------


def test_scored_articles_are_returned_in_descending_score_order() -> None:
    # Three candidates: one matches everything, one matches source, one nothing.
    perfect = _article(
        category="rag", tags=("rag", "evals"), source="LangChain", age_days=0
    )
    source_only = _article(category="other", tags=(), source="LangChain", age_days=20)
    nothing = _article(category="other", tags=(), source="RandomBlog", age_days=30)

    profile = UserProfile(
        interest_categories=frozenset({"rag"}),
        saved_tags={"rag": 1.0, "evals": 1.0},
        saved_sources={"LangChain": 1.0},
    )

    result = score_candidates([nothing, source_only, perfect], profile, now=NOW)

    assert [s.article.id for s in result] == [
        perfect.id,
        source_only.id,
        nothing.id,
    ]


def test_clicks_alone_produce_personalized_ranking_above_unmatched() -> None:
    """A user with only click-history (no saves, no stated interests) should
    still get personalized ranking — clicks are real positive signal."""
    matched = _article(category="other", tags=("rag",), source="LangChain", age_days=10)
    unmatched = _article(
        category="other", tags=("kubernetes",), source="DevOpsBlog", age_days=10
    )

    profile = UserProfile(
        clicked_tags={"rag": 1.0},
        clicked_sources={"LangChain": 1.0},
    )

    result = score_candidates([unmatched, matched], profile, now=NOW)

    assert result[0].article.id == matched.id


def test_score_handles_articles_without_embeddings_gracefully() -> None:
    """When an article isn't in the semantic_similarities map, the semantic
    component is 0 and the article is still ranked by the other signals."""
    article = _article(category="rag", tags=("rag",))
    profile = UserProfile(interest_categories=frozenset({"rag"}))

    # Should not raise and should still produce a meaningful ranking.
    result = score_candidates([article], profile, now=NOW)

    assert len(result) == 1
    assert result[0].breakdown.semantic == 0.0
    assert result[0].breakdown.explicit > 0


# ---------------------------------------------------------------------------
# Reason labels
# ---------------------------------------------------------------------------


def test_reason_uses_category_label_when_explicit_category_drives_score() -> None:
    article = _article(category="rag", tags=())
    profile = UserProfile(interest_categories=frozenset({"rag"}))

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Because you follow RAG"


def test_reason_for_explicit_source_says_because_you_follow() -> None:
    """When source-affinity dominates and the source is explicitly preferred,
    the label should be 'Because you follow X' — direct opt-in phrasing."""
    article = _article(category="other", tags=(), source="OpenAI", age_days=30)
    profile = UserProfile(preferred_sources=frozenset({"OpenAI"}))

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Because you follow OpenAI"


def test_reason_for_saved_source_says_because_you_saved() -> None:
    """Behavioral source affinity (saved-from) gets 'Because you saved
    articles from X' — distinct from explicit preference."""
    article = _article(category="other", tags=(), source="LangChain", age_days=30)
    profile = UserProfile(saved_sources={"LangChain": 1.0})

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Because you saved articles from LangChain"


def test_reason_for_clicked_source_says_because_you_read() -> None:
    """Click-only source affinity gets 'Because you read X' — weakest of the
    three source phrasings."""
    article = _article(category="other", tags=(), source="LangChain", age_days=30)
    profile = UserProfile(clicked_sources={"LangChain": 1.0})

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Because you read LangChain"


def test_reason_explicit_source_wins_over_saved_when_both_set() -> None:
    """When a source is both preferred and saved-from, the reason should
    reflect explicit preference (the dominant signal level)."""
    article = _article(category="other", tags=(), source="LangChain", age_days=30)
    profile = UserProfile(
        preferred_sources=frozenset({"LangChain"}),
        saved_sources={"LangChain": 1.0},
    )

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Because you follow LangChain"


def test_reason_recognizes_clicked_tags_in_explicit_path() -> None:
    """Reason for an article matched via clicked_tags should still be the
    explicit-match label, not the source label."""
    article = _article(
        category="other", tags=("rag",), source="UnseenSource", age_days=30
    )
    profile = UserProfile(clicked_tags={"rag": 1.0})

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Matches your interest in rag"


def test_reason_is_fresh_when_only_recency_contributes() -> None:
    """Cold-start user: no interests, no saves, no clicks. Recency alone
    produces a 'Fresh from your feed' label."""
    article = _article(age_days=0)
    profile = UserProfile()

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Fresh from your feed"


def test_reason_uses_semantic_label_when_embedding_similarity_dominates() -> None:
    article = _article(category="other", source="Other", age_days=30)
    profile = UserProfile()

    scored = score_candidates(
        [article],
        profile,
        semantic_similarities={article.id: 0.95},
        now=NOW,
    )[0]

    assert reason_for(scored, profile) == "Similar to articles you saved"

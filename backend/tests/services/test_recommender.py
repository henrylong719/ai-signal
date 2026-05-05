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


def test_explicit_match_weights_saved_above_clicked_above_stated() -> None:
    """Strength order: saved > clicked > stated. Each Jaccard-overlaps fully."""
    article = _article(category="other", tags=("rag", "evals"))

    only_stated = UserProfile(interest_tags=frozenset({"rag", "evals"}))
    only_clicked = UserProfile(clicked_tags=frozenset({"rag", "evals"}))
    only_saved = UserProfile(saved_tags=frozenset({"rag", "evals"}))

    stated_score = explicit_match_score(article, only_stated)
    clicked_score = explicit_match_score(article, only_clicked)
    saved_score = explicit_match_score(article, only_saved)

    assert stated_score < clicked_score < saved_score


def test_source_affinity_is_one_for_saved_sources() -> None:
    article = _article(source="LangChain")
    profile = UserProfile(saved_sources=frozenset({"LangChain"}))

    assert source_affinity_score(article, profile) == 1.0


def test_source_affinity_is_half_for_clicked_only_sources() -> None:
    """Clicking through is meaningful but weaker than saving."""
    article = _article(source="LangChain")
    profile = UserProfile(clicked_sources=frozenset({"LangChain"}))

    assert source_affinity_score(article, profile) == 0.5


def test_source_affinity_prefers_saved_over_clicked_when_both_present() -> None:
    article = _article(source="LangChain")
    profile = UserProfile(
        saved_sources=frozenset({"LangChain"}),
        clicked_sources=frozenset({"LangChain"}),
    )

    assert source_affinity_score(article, profile) == 1.0


def test_source_affinity_is_zero_for_unknown_source() -> None:
    article = _article(source="RandomBlog")
    profile = UserProfile(saved_sources=frozenset({"LangChain"}))

    assert source_affinity_score(article, profile) == 0.0


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
        saved_tags=frozenset({"rag", "evals"}),
        saved_sources=frozenset({"LangChain"}),
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
    unmatched = _article(category="other", tags=(), source="RandomBlog", age_days=10)

    profile = UserProfile(
        clicked_tags=frozenset({"rag"}),
        clicked_sources=frozenset({"LangChain"}),
    )

    result = score_candidates([unmatched, matched], profile, now=NOW)

    assert result[0].article.id == matched.id


def test_semantic_similarity_contributes_when_provided() -> None:
    article = _article()
    profile = UserProfile()  # no other signal — isolate semantic

    no_sim = score_candidates([article], profile, now=NOW)
    with_sim = score_candidates(
        [article], profile, semantic_similarities={article.id: 1.0}, now=NOW
    )

    assert with_sim[0].score > no_sim[0].score


def test_semantic_similarity_defaults_to_zero_when_omitted() -> None:
    """Scorer is usable before pgvector is wired up."""
    article = _article(category="rag", age_days=0)
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


def test_reason_uses_source_label_when_source_affinity_dominates() -> None:
    # No category or tag match — only source affinity should fire.
    article = _article(category="other", tags=(), source="LangChain", age_days=30)
    profile = UserProfile(saved_sources=frozenset({"LangChain"}))

    scored = score_candidates([article], profile, now=NOW)[0]

    assert reason_for(scored, profile) == "Popular from LangChain"


def test_reason_recognizes_clicked_tags_in_explicit_path() -> None:
    """Reason for an article matched via clicked_tags should still be the
    explicit-match label, not the source label."""
    article = _article(
        category="other", tags=("rag",), source="UnseenSource", age_days=30
    )
    profile = UserProfile(clicked_tags=frozenset({"rag"}))

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

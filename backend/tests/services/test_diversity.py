"""Tests for the diversity-aware reranker.

These tests double as a spec: each test name states a property the
reranker guarantees. Fixtures stay deliberately small so each test
reads top-to-bottom without jumping around.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.diversity import (
    DEFAULT_LAMBDA_FOR_YOU,
    DEFAULT_LAMBDA_LATEST,
    RerankItem,
    diversity_rerank,
)


@dataclass(frozen=True)
class _Article:
    """Minimal duck-typed article for reranker tests.

    The reranker accepts anything with `source` and `category` fields,
    so we don't need the full Article SQLModel here.
    """

    source: str
    category: str


def _items(*specs: tuple[str, str, float]) -> list[RerankItem[_Article]]:
    """Compact factory: list of (source, category, score) triples."""
    return [
        RerankItem(_Article(source=s, category=c), score=score) for s, c, score in specs
    ]


def _sources(items: list[RerankItem[_Article]]) -> list[str]:
    return [it.item.source for it in items]


def _max_consecutive_run(items: list[RerankItem[_Article]]) -> int:
    """Longest streak of identical-source picks in a row."""
    if not items:
        return 0
    best = current = 1
    for i in range(1, len(items)):
        if items[i].item.source == items[i - 1].item.source:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_pool_returns_empty_list() -> None:
    assert diversity_rerank([], lambda_=DEFAULT_LAMBDA_LATEST) == []


def test_small_pool_skips_rerank_and_sorts_by_score() -> None:
    """Pools smaller than the rerank threshold are returned sorted by
    score — diversity terms dominate on small inputs and produce odd
    orderings, so we bail early."""
    items = _items(
        ("A", "x", 0.1),
        ("B", "y", 0.9),
        ("C", "x", 0.5),
    )

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    # Sorted by score descending: B, C, A
    assert _sources(result) == ["B", "C", "A"]


def test_returned_list_preserves_input_length() -> None:
    """Every candidate gets placed somewhere — the reranker chooses
    where, but doesn't drop or duplicate items."""
    items = _items(*[(f"src{i % 5}", f"cat{i % 3}", 1.0 - i * 0.01) for i in range(40)])

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    assert len(result) == len(items)
    # No duplicates: every input id appears exactly once.
    input_ids = {id(it) for it in items}
    output_ids = {id(it) for it in result}
    assert input_ids == output_ids


def test_lambda_one_preserves_score_order_for_large_pools() -> None:
    """λ=1.0 means pure relevance, no diversity penalty — should
    return items sorted by score."""
    items = _items(
        *[("arXiv", "research", 1.0 - i * 0.001) for i in range(40)],
    )

    result = diversity_rerank(items, lambda_=1.0)

    # All identical sources, monotonically decreasing scores → same order.
    scores = [it.score for it in result]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Core diversity behavior
# ---------------------------------------------------------------------------


def test_breaks_up_a_burst_from_one_dominant_source() -> None:
    """The headline use case: arXiv drops 60 papers, 9 other sources
    have ~14 articles each. The first window of the reranked feed
    should not be 100% arXiv."""
    items: list[RerankItem[_Article]] = []
    # Highest-scoring 60 are all arXiv — chronological would put all
    # of these first.
    for i in range(60):
        items.append(RerankItem(_Article("arXiv", "research"), 1.0 - i * 0.001))
    # Lower-scoring articles from 9 other sources (so we have a
    # candidate pool well above the rerank threshold).
    for src_idx in range(9):
        for i in range(14):
            items.append(
                RerankItem(
                    _Article(f"src{src_idx}", "applications"),
                    0.85 - i * 0.001,
                )
            )

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    first_20 = result[:20]
    arxiv_count = sum(1 for it in first_20 if it.item.source == "arXiv")
    distinct_sources = len({it.item.source for it in first_20})

    # arXiv shouldn't dominate the head; distinct sources should be high.
    assert arxiv_count < 10, (
        f"arXiv took {arxiv_count}/20 of the head — burst not broken up"
    )
    assert distinct_sources >= 7, (
        f"only {distinct_sources} distinct sources in first 20"
    )


def test_top_scoring_item_still_wins_first_position() -> None:
    """Whatever scored highest goes first — diversity reranking only
    affects how *subsequent* items are chosen relative to what's
    already placed."""
    items = _items(
        ("arXiv", "research", 1.0),  # winner
        *[("arXiv", "research", 0.9 - i * 0.001) for i in range(15)],
        *[(f"src{i % 8}", f"cat{i % 3}", 0.5 - i * 0.001) for i in range(40)],
    )

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    assert result[0].item.source == "arXiv"
    assert result[0].score == 1.0


def test_no_more_than_two_consecutive_articles_from_same_source() -> None:
    """The consecutive-source cap guarantees at most 2 in a row, even
    when the soft penalty would otherwise let a third through."""
    # Pool with several sources represented enough to satisfy the cap
    # without falling back to "everyone is capped, pick something".
    items: list[RerankItem[_Article]] = []
    sources = ["A", "B", "C", "D"]
    for src in sources:
        for i in range(15):
            items.append(RerankItem(_Article(src, "x"), 1.0 - i * 0.01))

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    # Across the full output, no source should ever appear 3+ in a row
    # while alternatives remain available.
    assert _max_consecutive_run(result) <= 2


def test_window_share_cap_limits_burst_in_visible_window() -> None:
    """No single source should occupy more than ~30% of any 20-window
    while alternatives are available."""
    items: list[RerankItem[_Article]] = []
    # arXiv has many high-scoring items
    for i in range(40):
        items.append(RerankItem(_Article("arXiv", "research"), 1.0 - i * 0.001))
    # Plenty of other sources to fill in
    for src_idx in range(8):
        for i in range(15):
            items.append(
                RerankItem(
                    _Article(f"other{src_idx}", "x"),
                    0.6 - i * 0.001,
                )
            )

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    # Check every rolling 20-window in the first 60 picks
    for start in range(0, 40):
        window = result[start : start + 20]
        arxiv_count = sum(1 for it in window if it.item.source == "arXiv")
        # 30% of 20 = 6. Floor of cap is the threshold.
        assert arxiv_count <= 6, (
            f"window {start}..{start + 20} has {arxiv_count} arXiv, expected ≤6"
        )


# ---------------------------------------------------------------------------
# Preferred source behavior
# ---------------------------------------------------------------------------


def test_preferred_sources_bypass_consecutive_cap() -> None:
    """If a user explicitly preferred OpenAI, they shouldn't see OpenAI
    articles artificially split up. The 2-consecutive cap doesn't apply
    to preferred sources."""
    # 10 OpenAI articles (all preferred), 30 other articles
    items = _items(
        *[("OpenAI", "engineering", 1.0 - i * 0.001) for i in range(10)],
        *[("Other", "research", 0.5 - i * 0.001) for i in range(30)],
    )

    result = diversity_rerank(
        items,
        lambda_=DEFAULT_LAMBDA_FOR_YOU,
        preferred_sources=frozenset({"OpenAI"}),
    )

    # First several picks should be the preferred source — it has the
    # highest scores AND is exempt from the cap.
    first_10 = _sources(result[:10])
    openai_count = sum(1 for s in first_10 if s == "OpenAI")
    assert openai_count >= 8, (
        f"only {openai_count}/10 preferred-source articles in head"
    )


def test_non_preferred_source_with_same_dominance_gets_capped() -> None:
    """The mirror of the previous test: an unpreferred source with the
    same score profile *should* get capped. Confirms the bypass is
    actually doing something, not just coincidental ordering."""
    # Same 10 high-scoring articles from "Other" instead of "OpenAI"
    items = _items(
        *[("Other", "engineering", 1.0 - i * 0.001) for i in range(10)],
        *[("Filler", "research", 0.5 - i * 0.001) for i in range(30)],
    )

    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_FOR_YOU)

    first_10 = _sources(result[:10])
    other_count = sum(1 for s in first_10 if s == "Other")
    # With no preference, Other must be broken up by the consecutive
    # cap and the soft penalty.
    assert other_count < 8, f"unpreferred source took {other_count}/10 — cap not firing"


# ---------------------------------------------------------------------------
# Score normalization
# ---------------------------------------------------------------------------


def test_handles_identical_scores_without_dividing_by_zero() -> None:
    """If every candidate has the same score, span = 0 and the
    normalization fallback should kick in (treating all as equal)."""
    items = _items(*[(f"src{i % 5}", "x", 0.5) for i in range(40)])

    # Should not raise.
    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    assert len(result) == 40
    # With identical scores, only diversity drives ordering — so
    # consecutive runs should be at most 2.
    assert _max_consecutive_run(result) <= 2


def test_handles_negative_scores() -> None:
    """Recency decay can produce values close to zero; explicit-match
    can be 0; some edge cases produce negative scores. The normalizer
    handles arbitrary ranges."""
    items = _items(
        *[(f"src{i % 4}", "x", -10.0 + i * 0.1) for i in range(40)],
    )

    # Should not raise; should still produce a length-40 result.
    result = diversity_rerank(items, lambda_=DEFAULT_LAMBDA_LATEST)

    assert len(result) == 40

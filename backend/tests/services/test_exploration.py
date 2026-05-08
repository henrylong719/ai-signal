"""Tests for the exploration injection service.

These are pure-function tests on ``inject_exploration``: no DB, no
session, no FastAPI. The integration with ``rank_for_you`` lives in
``test_for_you.py``; here we exercise the contract in isolation.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.services.exploration import (
    EXPLORATION_OFFSET,
    EXPLORATION_REASON,
    EXPLORATION_STEP,
    ExplorationResult,
    inject_exploration,
    is_exploration_candidate,
)
from app.services.recommender import (
    CandidateArticle,
    ScoreBreakdown,
    ScoredArticle,
    ScoringWeights,
    UserProfile,
)

NOW = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 5, 8)
TOMORROW = date(2026, 5, 9)
WEIGHTS = ScoringWeights()


def _candidate(
    *,
    title: str = "x",
    source: str = "Source",
    category: str = "models",
    tags: tuple[str, ...] = (),
    age_days: int = 0,
) -> CandidateArticle:
    return CandidateArticle(
        id=uuid4(),
        title=title,
        source=source,
        category=category,
        tags=tags,
        published_at=NOW - timedelta(days=age_days),
    )


def _scored(
    article: CandidateArticle | None = None,
    *,
    semantic: float = 0.0,
    explicit: float = 0.0,
    source: float = 0.0,
    recency: float = 0.5,
) -> ScoredArticle:
    """Build a ScoredArticle with the given component values.

    Recency defaults to 0.5 so the article has *some* score (otherwise
    the breakdown total is 0 and the article would be filtered upstream
    in practice). The exploration logic only inspects semantic /
    explicit / source, never recency.
    """
    return ScoredArticle(
        article=article or _candidate(),
        breakdown=ScoreBreakdown(
            semantic=semantic,
            explicit=explicit,
            source=source,
            recency=recency,
            weights=WEIGHTS,
        ),
    )


def _profile_with_signal() -> UserProfile:
    """Profile that returns True from has_any_signal."""
    return UserProfile(interest_categories=frozenset({"models"}))


# ---------------------------------------------------------------------------
# is_exploration_candidate
# ---------------------------------------------------------------------------


def test_exploration_candidate_when_all_personalization_zero() -> None:
    assert is_exploration_candidate(_scored(recency=0.9)) is True


def test_not_exploration_when_semantic_nonzero() -> None:
    assert is_exploration_candidate(_scored(semantic=0.1)) is False


def test_not_exploration_when_explicit_nonzero() -> None:
    assert is_exploration_candidate(_scored(explicit=0.2)) is False


def test_not_exploration_when_source_nonzero() -> None:
    assert is_exploration_candidate(_scored(source=0.05)) is False


# ---------------------------------------------------------------------------
# inject_exploration: determinism
# ---------------------------------------------------------------------------


def _build_pool(n_exploit: int, n_explore: int) -> list[ScoredArticle]:
    """Reranked input: n_exploit personalized items, then n_explore zero-
    personalization items mixed in at every position past EXPLORATION_OFFSET.

    The exploit items get explicit=1.0 so they're clearly *not*
    exploration candidates. The explore items are pure recency.
    """
    items: list[ScoredArticle] = []
    for i in range(n_exploit):
        items.append(
            _scored(
                _candidate(title=f"exploit-{i}", source=f"ExploitSrc{i % 3}"),
                explicit=1.0,
                recency=0.5,
            )
        )
    for i in range(n_explore):
        items.append(
            _scored(
                _candidate(title=f"explore-{i}", source=f"ExploreSrc{i % 4}"),
                recency=0.5,
            )
        )
    return items


def test_same_user_same_day_produces_identical_picks() -> None:
    user_id = uuid4()
    pool = _build_pool(n_exploit=20, n_explore=15)
    profile = _profile_with_signal()

    first = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)
    second = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    assert first.injected_ids == second.injected_ids
    assert [it.article.id for it in first.items] == [
        it.article.id for it in second.items
    ]


def test_different_days_produce_different_picks() -> None:
    """Same user, different day → different exploration picks.

    With a pool of 15 exploration candidates and ~3 slots in a 20-item
    list, the chance two random days produce identical first picks is
    1/15 ≈ 7%. We pick three days to drive that vanishingly low.
    """
    user_id = uuid4()
    pool = _build_pool(n_exploit=20, n_explore=15)
    profile = _profile_with_signal()

    picks_by_day: list[frozenset[UUID]] = []
    for offset in range(3):
        day = TODAY + timedelta(days=offset)
        result = inject_exploration(pool, profile=profile, user_id=user_id, today=day)
        picks_by_day.append(result.injected_ids)

    # At least one pair should differ — collision across all three days
    # would mean determinism is broken (constant-seeded shuffle).
    assert len(set(picks_by_day)) > 1


def test_different_users_same_day_produce_different_picks() -> None:
    pool = _build_pool(n_exploit=20, n_explore=15)
    profile = _profile_with_signal()

    picks_by_user: list[frozenset[UUID]] = []
    for _ in range(3):
        result = inject_exploration(pool, profile=profile, user_id=uuid4(), today=TODAY)
        picks_by_user.append(result.injected_ids)

    assert len(set(picks_by_user)) > 1


# ---------------------------------------------------------------------------
# inject_exploration: slot positions
# ---------------------------------------------------------------------------


def test_injection_lands_only_at_fixed_slot_positions() -> None:
    user_id = uuid4()
    pool = _build_pool(n_exploit=10, n_explore=10)
    profile = _profile_with_signal()

    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    expected_slots = set(range(EXPLORATION_OFFSET, len(pool), EXPLORATION_STEP))
    actual_slots = {
        i
        for i, item in enumerate(result.items)
        if item.article.id in result.injected_ids
    }
    assert actual_slots.issubset(expected_slots)


def test_non_injected_positions_keep_original_exploit_items() -> None:
    """Positions that aren't slots and aren't the source of a swap stay put.

    With the swap-by-index implementation, three position categories
    exist after injection:
      - Slot positions where injection happened: contain an exploration
        item; the displaced exploit was swapped *down* to where the
        exploration item used to sit.
      - The "swap source" positions (where the exploration items
        originally sat): now contain the displaced exploit items.
      - All other positions: unchanged from input.

    This test asserts only the third category. It also asserts the
    bijection — every input id appears exactly once in the output.
    """
    user_id = uuid4()
    pool = _build_pool(n_exploit=10, n_explore=10)
    profile = _profile_with_signal()

    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    # Bijection check.
    assert {it.article.id for it in result.items} == {it.article.id for it in pool}

    # Compute the set of "involved" positions: slots where an injection
    # happened, plus the original positions of the injected items.
    pool_position_by_id = {it.article.id: i for i, it in enumerate(pool)}
    slot_positions = set(range(EXPLORATION_OFFSET, len(pool), EXPLORATION_STEP))
    swap_origin_positions = {pool_position_by_id[id_] for id_ in result.injected_ids}
    involved = (
        # Slots that actually received an injection.
        {i for i in slot_positions if result.items[i].article.id in result.injected_ids}
        | swap_origin_positions
    )

    for i, original in enumerate(pool):
        if i in involved:
            continue
        assert result.items[i].article.id == original.article.id, (
            f"uninvolved position {i} unexpectedly changed"
        )


def test_output_length_matches_input_length() -> None:
    user_id = uuid4()
    pool = _build_pool(n_exploit=20, n_explore=10)
    profile = _profile_with_signal()

    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    assert len(result.items) == len(pool)


# ---------------------------------------------------------------------------
# inject_exploration: fallbacks and edges
# ---------------------------------------------------------------------------


def test_cold_start_user_gets_no_injection() -> None:
    """Cold-start: profile has no signal → no exploration."""
    user_id = uuid4()
    pool = _build_pool(n_exploit=0, n_explore=20)
    cold_profile = UserProfile()  # no interests, no saves, no clicks
    assert cold_profile.has_any_signal is False

    result = inject_exploration(
        pool, profile=cold_profile, user_id=user_id, today=TODAY
    )

    assert result.injected_ids == frozenset()
    assert [it.article.id for it in result.items] == [it.article.id for it in pool]


def test_empty_exploration_pool_preserves_exploit_ordering() -> None:
    """Every item is personalized → no exploration candidates → no swaps."""
    user_id = uuid4()
    pool = _build_pool(n_exploit=20, n_explore=0)
    profile = _profile_with_signal()

    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    assert result.injected_ids == frozenset()
    assert [it.article.id for it in result.items] == [it.article.id for it in pool]


def test_partial_pool_fills_slots_in_order_then_stops() -> None:
    """Fewer exploration candidates than slots → fill what we can."""
    user_id = uuid4()
    # Long output (50 items) → many slots, but only 2 exploration candidates.
    pool = _build_pool(n_exploit=48, n_explore=2)
    profile = _profile_with_signal()

    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    # Exactly 2 injections happened, no more.
    assert len(result.injected_ids) == 2

    # The injections landed at the first two slot positions.
    expected_slots = list(range(EXPLORATION_OFFSET, len(pool), EXPLORATION_STEP))
    injected_slots = sorted(
        i
        for i, item in enumerate(result.items)
        if item.article.id in result.injected_ids
    )
    assert injected_slots == expected_slots[:2]


def test_empty_input_returns_empty_output() -> None:
    """Defensive: zero-length input shouldn't crash."""
    user_id = uuid4()
    profile = _profile_with_signal()

    result = inject_exploration([], profile=profile, user_id=user_id, today=TODAY)

    assert result.items == []
    assert result.injected_ids == frozenset()


# ---------------------------------------------------------------------------
# inject_exploration: source diversity within injected slots
# ---------------------------------------------------------------------------


def test_consecutive_injected_slots_avoid_same_source_when_possible() -> None:
    """If exploration pool has variety, adjacent injections shouldn't share source.

    We construct a pool with 5 different sources for exploration and
    check that across many days, we don't see same-source adjacencies
    in the injected positions when alternatives exist.
    """
    user_id = uuid4()
    profile = _profile_with_signal()

    # 21 exploit items + 10 exploration items spread across 5 sources.
    exploit = [
        _scored(
            _candidate(title=f"e-{i}", source=f"ExploitSrc{i % 3}"),
            explicit=1.0,
        )
        for i in range(21)
    ]
    explore = [
        _scored(
            _candidate(title=f"x-{i}", source=f"ExploreSrc{i % 5}"),
        )
        for i in range(10)
    ]
    pool = exploit + explore

    # Pool of 31 → slots at 2, 9, 16, 23, 30 → 5 injections.
    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)
    injected_in_order = [
        item for item in result.items if item.article.id in result.injected_ids
    ]
    assert len(injected_in_order) >= 4, (
        "expected at least 4 injections to test adjacency"
    )

    # No two consecutive injected items should share a source. With 5
    # sources and ~5 picks, this is reliably achievable when variety
    # exists.
    sources = [it.article.source for it in injected_in_order]
    consecutive_dupes = sum(
        1 for a, b in zip(sources, sources[1:], strict=False) if a == b
    )
    assert consecutive_dupes == 0, (
        f"injected sources {sources} have consecutive dupes despite available variety"
    )


def test_same_source_dominates_pool_falls_back_gracefully() -> None:
    """All exploration items from one source → still inject, no crash."""
    user_id = uuid4()
    profile = _profile_with_signal()

    exploit = [
        _scored(_candidate(title=f"e-{i}", source="Exploit"), explicit=1.0)
        for i in range(20)
    ]
    explore = [_scored(_candidate(title=f"x-{i}", source="OnlySrc")) for i in range(5)]
    pool = exploit + explore

    result = inject_exploration(pool, profile=profile, user_id=user_id, today=TODAY)

    # We should still inject when the pool exists, even if diversity
    # within the pool is impossible.
    assert len(result.injected_ids) > 0


# ---------------------------------------------------------------------------
# Module constants sanity
# ---------------------------------------------------------------------------


def test_exploration_constants_match_target_density() -> None:
    """Sanity check: with 25-item page, we get ~14% injection density."""
    page_size = 25
    n_slots = sum(
        1
        for i in range(page_size)
        if (i - EXPLORATION_OFFSET) % EXPLORATION_STEP == 0 and i >= EXPLORATION_OFFSET
    )
    assert n_slots == 4  # positions 2, 9, 16, 23 → 4 of 25 = 16%
    assert EXPLORATION_REASON == "Outside your usual interests"

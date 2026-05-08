"""Diversity-aware reranking for feed surfaces.

The chronological-or-personalized score is a great *first* ordering, but
both Latest and For-You suffer the same failure mode: a single source
(arXiv cs.CL drops 50 papers; a newsletter publishes a weekly digest
of 8 articles) can flood the visible window and drown out everything
else. Pure chronological treats this as "neutral" but it isn't —
chronological is an opinion that ranks bursty publishers above everyone
else.

This module implements a Maximum Marginal Relevance (MMR) reranker
adapted for feed contexts. The classic MMR formulation (Carbonell &
Goldstein, SIGIR 1998) is:

    MMR(item) = λ · relevance(item)
              − (1 − λ) · max_similarity(item, already_selected)

We adapt this in three ways:

1. **Categorical similarity, not embedding similarity.** Two articles
   from the same source = 1.0; same category but different source =
   0.5; otherwise 0.0. This captures most of what semantic MMR gives
   us at a fraction of the cost — and avoids a feedback loop with the
   For-You scorer's own semantic-similarity term.

2. **Preferred-source bypass.** If a user has explicitly opted into a
   source via the personalization page, that source gets a reduced
   diversity penalty. The user told us they want it; clustering their
   preferred-source articles together is correct behavior, not a bug
   to suppress.

3. **A hard share cap on top of the soft penalty.** No source may
   occupy more than `max_share` of any rolling window in the visible
   feed. The MMR penalty alone is sometimes too gentle when one source
   has 50+ candidates queued — the cap is a backstop that guarantees
   we never display a screen entirely from one source.

The reranker is intentionally framework-free (no SQLModel, no FastAPI)
so it can be unit-tested in isolation and reused across feed surfaces.
It operates on tuples of `(article, score)` rather than full
``ScoredArticle`` instances, which keeps it usable from both the Latest
feed (where the "score" is just a recency proxy) and the For-You feed
(where the score is a `ScoreBreakdown.total`).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

# ---------------------------------------------------------------------------
# Inputs and outputs
# ---------------------------------------------------------------------------


class _HasSourceAndCategory(Protocol):
    """Shape any rerankable item must satisfy.

    Both ``Article`` (SQLModel) and ``CandidateArticle`` (recommender
    dataclass) satisfy this implicitly — duck typing keeps this module
    decoupled from the rest of the codebase.
    """

    @property
    def source(self) -> str: ...
    @property
    def category(self) -> str: ...


T = TypeVar("T", bound=_HasSourceAndCategory)


@dataclass(frozen=True)
class RerankItem(Generic[T]):
    """One candidate for reranking, paired with its base relevance score.

    `score` is whatever the upstream ranker produced — recency for
    Latest, weighted breakdown total for For-You. The reranker
    normalizes these to [0, 1] internally so the lambda trade-off has
    consistent semantics regardless of the input range.
    """

    item: T
    score: float


# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

# Default lambda values for the two feed surfaces. Higher lambda means
# more weight on the original relevance, less on diversity. Latest is
# tuned lower because chronological burstiness is the worst there;
# For-You is tuned higher because a personalized score is already
# meaningful and aggressive reranking would undermine personalization.
DEFAULT_LAMBDA_LATEST = 0.7
DEFAULT_LAMBDA_FOR_YOU = 0.85

# Source-clustering signal weights. Same source = full penalty; same
# category but different source = half penalty; otherwise no penalty.
# Discrete levels rather than continuous similarity because the goal
# is to break up bursts, not to enforce some abstract notion of "topic
# diversity" — which the explicit-match score already handles.
_SIMILARITY_SAME_SOURCE = 1.0
_SIMILARITY_SAME_CATEGORY = 0.5

# When a source is in the user's `preferred_sources`, its same-source
# similarity is reduced from 1.0 to this value. The user explicitly
# asked for this source, so two of its articles in a row is fine; we
# still apply *some* penalty to avoid an entire screen of one source
# even when preferred.
_SIMILARITY_SAME_SOURCE_PREFERRED = 0.3

# Hard cap parameters. Two layers of protection:
#   1. **Window share**: no source may exceed `max_share` of the most
#      recent `window_size` selections. This is the primary cap.
#   2. **Consecutive cap**: regardless of the window-share math, no more
#      than `_MAX_CONSECUTIVE_SAME_SOURCE` articles from the same source
#      may appear in a row. This catches the bootstrap case where the
#      window-share cap hasn't kicked in yet but a source is dominating
#      the head of the feed.
# The window-share cap requires `_MIN_WINDOW_FOR_CAP` items in the
# window before it activates — otherwise it fires on trivially small
# windows where one repeat is mathematically forced.
_DEFAULT_WINDOW_SIZE = 20
_DEFAULT_MAX_SHARE = 0.30
_MIN_WINDOW_FOR_CAP = 5
_MAX_CONSECUTIVE_SAME_SOURCE = 2

# Reranking small candidate pools makes the diversity terms dominate
# and produces odd orderings. Below this threshold we return the input
# unchanged — there's not enough material for diversity to be
# meaningful anyway.
_MIN_POOL_FOR_RERANK = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def diversity_rerank(
    items: list[RerankItem[T]],
    *,
    lambda_: float,
    preferred_sources: frozenset[str] = frozenset(),
    window_size: int = _DEFAULT_WINDOW_SIZE,
    max_share: float = _DEFAULT_MAX_SHARE,
) -> list[RerankItem[T]]:
    """MMR-style rerank with a per-source share cap.

    Greedy O(N·K) algorithm where N is the candidate pool size and K
    is the number selected. For our pool sizes (~200 candidates,
    ~50–200 selected) this completes in a few milliseconds.

    Returns a new list; does not mutate the input. The returned list
    has the same length as the input — every candidate gets placed
    somewhere, the algorithm just decides where.

    The caller is responsible for slicing the returned list down to a
    page size; pagination cannot meaningfully happen below this layer
    because page N depends on what was selected for pages 1..N-1.

    Args:
        items: Candidates with their base relevance scores. Order does
            not matter — the reranker chooses its own.
        lambda_: Trade-off between relevance and diversity, in [0, 1].
            1.0 = pure relevance (no reranking). 0.0 = pure diversity
            (relevance ignored). Sensible values are 0.6–0.9.
        preferred_sources: Sources the user has explicitly opted into.
            Articles from these sources get a reduced diversity penalty
            and are exempt from the hard share cap.
        window_size: Size of the rolling window used by the hard cap.
            The cap looks at the most recent `window_size` selections
            when deciding whether to skip a candidate.
        max_share: Maximum fraction of the rolling window any single
            source may occupy. 0.30 = 6 out of 20 with the default
            window.
    """
    if not items:
        return []

    # Below the threshold, reranking does more harm than good — return
    # the input sorted by base relevance instead.
    if len(items) < _MIN_POOL_FOR_RERANK:
        return sorted(items, key=lambda it: it.score, reverse=True)

    # Min-max normalize scores to [0, 1] so the lambda trade-off has
    # consistent semantics regardless of whether the input is recency
    # (could be tiny floats from a decay function), unbounded scores,
    # or already-normalized [0, 1] values.
    scores = [it.score for it in items]
    s_min, s_max = min(scores), max(scores)
    span = s_max - s_min
    if span <= 0:
        # All scores identical — diversity wins by default.
        normalized: dict[int, float] = {i: 0.0 for i in range(len(items))}
    else:
        normalized = {i: (it.score - s_min) / span for i, it in enumerate(items)}

    remaining: list[tuple[int, RerankItem[T]]] = list(enumerate(items))
    selected: list[RerankItem[T]] = []

    while remaining:
        # Compute the trailing-window source distribution once per
        # iteration. Window grows until it hits window_size, then
        # slides as we keep picking.
        window = selected[-window_size:] if selected else []
        window_counts: Counter[str] = Counter(it.item.source for it in window)
        cap_active = len(window) >= _MIN_WINDOW_FOR_CAP
        # Threshold *count* in the window above which a source is
        # capped. Computing count rather than ratio avoids floating-
        # point edge cases.
        cap_threshold = max_share * len(window)

        # Trailing run of the same source — used by the consecutive cap.
        # Computed bottom-up so an empty trail returns an empty string
        # which compares-unequal to any real source.
        trailing_source = ""
        trailing_count = 0
        for prev in reversed(selected):
            if not trailing_source:
                trailing_source = prev.item.source
                trailing_count = 1
            elif prev.item.source == trailing_source:
                trailing_count += 1
            else:
                break

        best_local_idx = -1  # index into `remaining`, not original
        best_mmr = -float("inf")
        # Track best non-capped pick AND best overall pick separately.
        # If the cap eliminates everyone (rare but possible at very
        # high concentrations), we fall back to picking by MMR alone.
        best_mmr_uncapped = -float("inf")
        best_local_idx_uncapped = -1

        for local_idx, (orig_idx, candidate) in enumerate(remaining):
            src = candidate.item.source
            cat = candidate.item.category
            is_preferred_src = src in preferred_sources

            # Diversity penalty: maximum similarity to anything we've
            # already selected. We can short-circuit at 1.0 (or at the
            # preferred-source ceiling 0.3 for preferred sources).
            penalty = 0.0
            same_source_penalty = (
                _SIMILARITY_SAME_SOURCE_PREFERRED
                if is_preferred_src
                else _SIMILARITY_SAME_SOURCE
            )
            for chosen in selected:
                sim: float
                if chosen.item.source == src:
                    sim = same_source_penalty
                elif chosen.item.category == cat:
                    sim = _SIMILARITY_SAME_CATEGORY
                else:
                    sim = 0.0
                if sim > penalty:
                    penalty = sim
                    # Can't get higher than the same-source cap from
                    # any further iteration; bail early.
                    if penalty >= same_source_penalty:
                        break

            mmr = lambda_ * normalized[orig_idx] - (1 - lambda_) * penalty

            # Track the best overall pick (used as a fallback if the
            # cap eliminates every candidate).
            if mmr > best_mmr:
                best_mmr = mmr
                best_local_idx = local_idx

            # Apply the caps. Preferred sources bypass both caps —
            # the user asked for them.
            if not is_preferred_src:
                # Consecutive cap: don't allow more than N in a row.
                if (
                    src == trailing_source
                    and trailing_count >= _MAX_CONSECUTIVE_SAME_SOURCE
                ):
                    continue
                # Window-share cap (primary).
                if cap_active and window_counts.get(src, 0) >= cap_threshold:
                    continue

            if mmr > best_mmr_uncapped:
                best_mmr_uncapped = mmr
                best_local_idx_uncapped = local_idx

        # Prefer the cap-respecting pick; fall back to overall best
        # only when every remaining candidate is capped.
        pick_idx = (
            best_local_idx_uncapped if best_local_idx_uncapped != -1 else best_local_idx
        )
        _, picked = remaining.pop(pick_idx)
        selected.append(picked)

    return selected

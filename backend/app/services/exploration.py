"""Exploration injection for the For-You feed.

The recommender is good at "more of what you already like" but that's
also its failure mode: a user who interacts with three RAG-evals
articles ends up with a feed that's 80% RAG-evals, which compounds —
their saves and clicks reinforce the same narrow interest, the
embedding centroid drifts further into one corner of vector space,
and adjacent topics they'd plausibly enjoy never surface.

The standard fix is ε-greedy exploration: reserve a fixed fraction of
slots for items the recommender thinks the user *won't* like, and let
the user discover things outside their current profile. This module
implements that as a post-rerank injection step.

# Design choices worth knowing about

**Injected after diversity rerank, at fixed slot positions.** The
exploit ordering (post-rerank) is preserved everywhere except at
positions 2, 9, 16, 23... (0-indexed; every 7th slot starting at the
3rd position), where exploration items overwrite the exploit pick.
This keeps exploration density at ~14% — close enough to the ε=0.15
target — and gives users a predictable rhythm.

**"Outside your usual interests" defined structurally, not by
threshold.** A candidate qualifies for exploration only if all three
personalization components of its breakdown are zero (semantic,
explicit, source). What's left is pure recency. This is more honest
than "bottom-quartile of total score": those items are *literally*
outside the user's bubble by every signal we have, which is what the
"Outside your usual interests" reason label actually claims.

**Deterministic per (user_id, today_utc_date).** Refreshing the page
must produce the same exploration picks within the same UTC day,
otherwise the feed feels broken ("where did that article go?"). We
seed a per-request RNG with a hash of (user_id, today). New ingests
during the day can change the candidate pool, which can shift picks
slightly — that's expected and matches user mental model ("the feed
updated").

**Source diversity within the exploration pool itself.** Without this,
two adjacent injected slots could both land on arXiv burst items and
re-create the very flooding the diversity reranker is meant to
prevent. We apply a simple no-consecutive-same-source rule when
ordering the exploration pool, then take items off the front.

**Cold-start opt-out.** If the user has no signal at all, every item
is "outside their bubble" by definition and exploration has no
meaning — the chronological feed *is* the exploration. We detect
this via ``profile.has_any_signal`` and return the input unchanged.

**Graceful degradation when the pool is small.** If we have fewer
exploration candidates than slots in the requested page, slots fill
in order and the rest stay as exploit picks. We don't backfill with
"close to exploration" items because that would dilute the honesty
of the reason label.
"""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import date

from app.services.recommender import ScoredArticle, UserProfile

# Slot positions: 0-indexed, every 7th starting at index 2. So in a
# 25-item page the user sees exploration at items 3, 10, 17, 24 (1-
# indexed) — 4 of 25 = 16%, close to the ε=0.15 target.
EXPLORATION_OFFSET = 2
EXPLORATION_STEP = 7

# Reason label shown on exploration items. Different from any label
# ``reason_for`` produces, so the call site can branch cleanly on
# membership in the injected-id set rather than parsing strings.
EXPLORATION_REASON = "Outside your usual interests"


@dataclass(frozen=True)
class ExplorationResult:
    """Output of ``inject_exploration``.

    Carries both the new ordered list and the set of article ids that
    were injected as exploration. The caller (``for_you.rank_for_you``)
    uses the id set to decide which reason label to apply: exploration
    items get ``EXPLORATION_REASON``, everything else goes through
    ``reason_for``.

    Returning the id set rather than a per-position flag matches how
    pagination works downstream: after slicing, position indices change
    but ids don't.
    """

    items: list[ScoredArticle]
    injected_ids: frozenset[uuid.UUID]


def is_exploration_candidate(scored: ScoredArticle) -> bool:
    """True iff every personalization component is zero.

    Semantic, explicit, and source must all be 0 — the article has no
    overlap with anything the user has signaled. What's left in its
    score is pure recency. This makes the "Outside your usual
    interests" reason label literally accurate: by every signal the
    recommender has, this is outside the user's profile.

    Note: cold-start users (``profile.has_any_signal == False``) make
    *every* candidate qualify, which is meaningless. The caller is
    responsible for the cold-start short-circuit; this predicate
    doesn't know about the profile.
    """
    breakdown = scored.breakdown
    return (
        breakdown.semantic == 0.0
        and breakdown.explicit == 0.0
        and breakdown.source == 0.0
    )


def _seed_for(user_id: uuid.UUID, today: date) -> int:
    """Stable 64-bit seed from (user_id, today).

    Python's built-in ``hash()`` is salted per process, so it would
    produce different seeds across worker restarts and break the
    "refresh shows the same picks" guarantee. SHA-256 of the joined
    string is overkill for collision resistance but cheap and gives
    us cross-process stability for free.
    """
    payload = f"{user_id}:{today.isoformat()}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


def _order_exploration_pool(
    pool: list[ScoredArticle],
    rng: random.Random,
) -> list[ScoredArticle]:
    """Shuffle the pool, then reorder to avoid consecutive same-source.

    Two-step process:
      1. Random shuffle (deterministic given the rng) — produces the
         per-day variety that's the whole point of exploration.
      2. Greedy pass: walk the shuffled list and, when the next item's
         source matches the previous *injected* source, swap it with
         the next non-matching item further down. If no non-matching
         item exists, accept the duplicate (the pool ran out of
         diversity; injecting in source order is still better than
         skipping).

    This is much weaker than running the full diversity reranker over
    the exploration pool, but it's enough for the failure mode we
    care about: two arXiv burst items landing in adjacent injected
    slots. Full MMR here would be over-engineering for a 4-item-per-
    page injection.
    """
    items = list(pool)
    rng.shuffle(items)

    # Greedy de-duplication of consecutive same-source items.
    for i in range(1, len(items)):
        if items[i].article.source != items[i - 1].article.source:
            continue
        # Find the next item with a different source and swap it in.
        for j in range(i + 1, len(items)):
            if items[j].article.source != items[i - 1].article.source:
                items[i], items[j] = items[j], items[i]
                break
        # If no swap candidate found, leave items[i] as-is and move on.
        # We've done our best — the rest of the pool is the same source.

    return items


def inject_exploration(
    reranked: list[ScoredArticle],
    *,
    profile: UserProfile,
    user_id: uuid.UUID,
    today: date,
) -> ExplorationResult:
    """Overwrite fixed slots in the reranked list with exploration picks.

    The contract:
      - Returns a list of the same length as ``reranked``.
      - Items at positions ``EXPLORATION_OFFSET + k * EXPLORATION_STEP``
        (for k = 0, 1, 2, ...) are replaced with exploration picks
        when available; other positions are untouched.
      - Replaced exploit picks are dropped, not shifted — the new list
        has the same length and the same items at non-injected
        positions. We're swapping, not inserting.
      - Determinism: same ``(user_id, today)`` and same input list →
        identical output.

    Why swap and not insert? The reranked list is already at most
    pool size (~200), and we're paginating from it. Inserting would
    push items out of the tail, which complicates the
    "all candidates eventually paginate to" guarantee. Swapping keeps
    the bijection clean: every input id appears exactly once in the
    output. The exploration item moves *up* (from its natural rerank
    position to the slot); the displaced exploit item moves *down*
    (to where the exploration item used to sit). This preserves the
    invariant `set(input_ids) == set(output_ids)` and avoids the bug
    where a naive overwrite would leave the exploration item at both
    its original position and the injected slot.

    Cold-start short-circuit: a user with no signals would have every
    item qualify as exploration, which is meaningless. We return the
    input unchanged in that case.
    """
    # Cold-start: all candidates qualify, exploration is a no-op.
    if not profile.has_any_signal:
        return ExplorationResult(items=list(reranked), injected_ids=frozenset())

    # Build the exploration candidate pool from the reranked list. Doing
    # it after rerank (rather than from the raw scored list) means
    # exploration items have already been considered for diversity
    # ordering — even if we don't use that ordering, the pool itself
    # was filtered through the same hard filters (saved, dismissed)
    # via ``filter_candidates`` upstream.
    candidates = [s for s in reranked if is_exploration_candidate(s)]
    if not candidates:
        return ExplorationResult(items=list(reranked), injected_ids=frozenset())

    rng = random.Random(_seed_for(user_id, today))
    ordered_pool = _order_exploration_pool(candidates, rng)

    # Compute injection slot indices over the full reranked length.
    # We do this globally so pagination slices stably: page 2's slot
    # indices are relative to the start of the global list, not the
    # start of the page.
    slots = list(range(EXPLORATION_OFFSET, len(reranked), EXPLORATION_STEP))

    # Index by id so we can find each exploration item's current
    # position in the output list quickly. We update positions as we
    # swap, so this map stays in sync with `output`.
    output = list(reranked)
    position_by_id: dict[uuid.UUID, int] = {
        item.article.id: i for i, item in enumerate(output)
    }
    injected_ids: set[uuid.UUID] = set()

    pool_iter = iter(ordered_pool)
    for slot in slots:
        # Find the next pool item that:
        #   - isn't already injected at an earlier slot, and
        #   - isn't currently at this exact slot (defensive — its
        #     natural rerank position would have to coincide with a
        #     slot, which can happen if the exploit pool is small).
        replacement = None
        for candidate in pool_iter:
            cand_id = candidate.article.id
            if cand_id in injected_ids:
                continue
            if position_by_id[cand_id] == slot:
                # Already at the slot — no swap needed, but still mark
                # as injected so the reason label fires.
                injected_ids.add(cand_id)
                replacement = None
                break
            replacement = candidate
            break

        if replacement is None:
            # Either pool exhausted or candidate was already at slot.
            # Continue to the next slot — pool_iter will be empty if
            # we've run out, ending the loop on the next iteration.
            continue

        # Swap: move exploration item up to `slot`, move whatever was
        # at `slot` down to where the exploration item came from.
        explore_id = replacement.article.id
        explore_pos = position_by_id[explore_id]
        displaced = output[slot]
        displaced_id = displaced.article.id

        output[slot], output[explore_pos] = output[explore_pos], output[slot]
        position_by_id[explore_id] = slot
        position_by_id[displaced_id] = explore_pos
        injected_ids.add(explore_id)

    return ExplorationResult(items=output, injected_ids=frozenset(injected_ids))

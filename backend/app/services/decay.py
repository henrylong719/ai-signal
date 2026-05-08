"""Recency decay for behavioral signals.

When a user saves or clicks an article, that interaction is informative
about their interests *now* — but the informativeness fades. A save
from yesterday is a much stronger signal of current interest than a
save from a year ago. Without decay, the For-You feed gets dragged
backwards by old behavior that no longer reflects the user.

We use exponential decay with a half-life: signal at time t has weight
``0.5 ** (age_days / half_life_days)``. This is the same shape as
``recency_score`` in ``recommender.py`` but applied to user-side
signals rather than article-side recency.

Half-life choices:
  - Saved actions: 60 days. Saving is a deliberate, committed action;
    a save from two months ago is still meaningful.
  - Clicked actions: 21 days. Clicks are noisier (one-tap, often
    interest-of-the-moment); we want them to fade faster so an
    accidental clickthrough from last quarter doesn't keep biasing
    the feed.

These values are exposed as constants so they can be swapped or A/B
tested cleanly. They do not depend on user properties; everyone gets
the same decay curve.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Half-life parameters. See module docstring for the rationale.
SAVED_HALF_LIFE_DAYS = 60.0
CLICKED_HALF_LIFE_DAYS = 21.0


def decay_weight(
    interaction_at: datetime,
    *,
    half_life_days: float,
    now: datetime | None = None,
) -> float:
    """Exponential decay weight in (0, 1] for a single interaction.

    Returns 1.0 for an interaction that just happened, 0.5 at the
    half-life, ~0.25 at two half-lives, and so on. Always > 0 — even
    very old interactions contribute *something* (the floor is set by
    Python's float precision rather than a hard cutoff).

    The caller is responsible for combining multiple interactions into
    a per-tag or per-source weight; this helper is the per-interaction
    primitive. See ``aggregate_weights_by_key`` for the common pattern
    of "tag/source -> highest decay weight across its interactions."
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if interaction_at.tzinfo is None:
        interaction_at = interaction_at.replace(tzinfo=timezone.utc)
    age_days = max((now - interaction_at).total_seconds() / 86400.0, 0.0)
    return float(0.5 ** (age_days / half_life_days))


def aggregate_weights_by_key(
    pairs: list[tuple[str, datetime]],
    *,
    half_life_days: float,
    now: datetime | None = None,
) -> dict[str, float]:
    """Collapse (key, interaction_at) pairs into a key -> max-weight dict.

    The "right" aggregation function for behavioral decay is *max*
    rather than *sum*: a tag that appeared in 5 saves a year ago plus
    1 save yesterday should weight close to 1.0 (because the recent
    save is a strong current signal), not pile up to a number that
    suggests overwhelming preference. Sum would over-credit users who
    happened to save many articles with the same tag historically.

    The same key can appear many times in the input — once per
    interaction. We compute each interaction's decay weight and keep
    the maximum per key.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    weights: dict[str, float] = {}
    for key, interaction_at in pairs:
        w = decay_weight(interaction_at, half_life_days=half_life_days, now=now)
        if w > weights.get(key, 0.0):
            weights[key] = w
    return weights

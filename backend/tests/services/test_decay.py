"""Tests for the recency decay helpers.

These are the primitive functions that turn (key, interaction_at)
pairs into per-key decay weights. The CRUD layer uses them to build
the weighted dicts that flow into UserProfile, but the helpers
themselves know nothing about saves vs clicks vs articles — they're
pure decay math.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.decay import (
    CLICKED_HALF_LIFE_DAYS,
    SAVED_HALF_LIFE_DAYS,
    aggregate_weights_by_key,
    decay_weight,
)

NOW = datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc)


def test_decay_weight_is_one_for_just_now_interactions() -> None:
    assert decay_weight(NOW, half_life_days=30, now=NOW) == 1.0


def test_decay_weight_halves_at_one_half_life() -> None:
    interaction = NOW - timedelta(days=30)
    weight = decay_weight(interaction, half_life_days=30, now=NOW)
    assert abs(weight - 0.5) < 1e-9


def test_decay_weight_quarters_at_two_half_lives() -> None:
    interaction = NOW - timedelta(days=60)
    weight = decay_weight(interaction, half_life_days=30, now=NOW)
    assert abs(weight - 0.25) < 1e-9


def test_decay_weight_handles_naive_datetime_as_utc() -> None:
    """Defensively normalize timezone-naive datetimes — Postgres
    returns aware datetimes, but defensive normalisation prevents
    failures if the column type changes."""
    naive_now = NOW.replace(tzinfo=None)
    assert decay_weight(naive_now, half_life_days=30, now=NOW) == 1.0


def test_decay_weight_clamps_future_timestamps_to_zero_age() -> None:
    """Clock skew can produce 'future' interactions. They should weight
    1.0 (treated as just-now) rather than producing weight > 1."""
    future = NOW + timedelta(hours=1)
    weight = decay_weight(future, half_life_days=30, now=NOW)
    assert weight == 1.0


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def test_aggregate_keeps_max_weight_when_key_appears_multiple_times() -> None:
    """A user who saved 5 articles tagged 'rag' over time gets the
    weight from the *most recent* one — not the sum, which would
    over-credit users who saved many old articles with the same tag."""
    pairs = [
        ("rag", NOW - timedelta(days=120)),  # quite old
        ("rag", NOW - timedelta(days=60)),  # half-life ago
        ("rag", NOW),  # just now -> should win
        ("evals", NOW - timedelta(days=30)),
    ]
    weights = aggregate_weights_by_key(pairs, half_life_days=60, now=NOW)
    assert weights["rag"] == 1.0
    assert abs(weights["evals"] - 0.5 ** (30 / 60)) < 1e-9


def test_aggregate_returns_empty_dict_for_empty_input() -> None:
    assert aggregate_weights_by_key([], half_life_days=60, now=NOW) == {}


def test_aggregate_uses_default_half_lives_consistently() -> None:
    """Sanity check that the published constants give the curve we
    designed for. Saves: 60-day half-life. Clicks: 21-day."""
    interaction = NOW - timedelta(days=60)

    save_weight = decay_weight(
        interaction, half_life_days=SAVED_HALF_LIFE_DAYS, now=NOW
    )
    click_weight = decay_weight(
        interaction, half_life_days=CLICKED_HALF_LIFE_DAYS, now=NOW
    )

    # 60 days is exactly one save half-life -> 0.5
    assert abs(save_weight - 0.5) < 1e-9
    # 60 days is ~2.86 click half-lives -> much smaller
    assert click_weight < 0.15

from datetime import datetime, timezone

import pytest

from app.services import scheduler


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # Plenty of room before :55 this hour.
        ((10, 0, 0), (10, 55)),
        # Exactly the delay before :55 still makes this hour.
        ((10, 54, 0), (10, 55)),
        # Inside the delay window, so roll to next hour.
        ((10, 54, 30), (11, 55)),
        ((10, 58, 0), (11, 55)),
        # Rolls over midnight.
        ((23, 59, 0), (0, 55)),
    ],
)
def test_next_ingest_start_lands_on_hh55_after_delay(
    monkeypatch: pytest.MonkeyPatch,
    now: tuple[int, int, int],
    expected: tuple[int, int],
) -> None:
    monkeypatch.setattr(scheduler.settings, "INGEST_INITIAL_DELAY_SECONDS", 60)
    start = scheduler._next_ingest_start(
        datetime(2026, 10, 31, *now, tzinfo=timezone.utc)
    )
    assert (start.hour, start.minute, start.second) == (*expected, 0)

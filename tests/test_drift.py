"""
F5 drift logic tests (M1).

Focus: the "baseline x 1.5 for N consecutive days" rule fires at exactly the
required number of days — not one fewer.
"""

import datetime

from core.drift import compute_drift_status, daily_red_rates

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)

# baseline 0.20 -> threshold 0.30. A day at 0.50 RED exceeds; a day at 0.0 does not.
BASELINE = 0.20


def _art(days_ago: int, level: str, hour: int = 9) -> dict:
    ts = (NOW - datetime.timedelta(days=days_ago)).replace(hour=hour)
    return {"timestamp": ts.isoformat(), "routing_classification": level}


def _day(days_ago: int, red: int, green: int) -> list[dict]:
    """A day's worth of artifacts with `red` RED and `green` GREEN decisions."""
    return [_art(days_ago, "RED") for _ in range(red)] + [
        _art(days_ago, "GREEN") for _ in range(green)
    ]


def test_fires_at_exactly_three_consecutive_days():
    # Days 0,1,2 each at 0.5 RED (> 0.30 threshold) -> drift.
    arts = _day(0, 1, 1) + _day(1, 1, 1) + _day(2, 1, 1)
    status = compute_drift_status(arts, BASELINE, now=NOW)
    assert status["threshold"] == 0.3
    assert status["days_exceeded"] == 3
    assert status["is_drifting"] is True


def test_two_consecutive_days_does_not_fire():
    # Only days 0,1 exceed; day 2 is all GREEN -> streak breaks at 2.
    arts = _day(0, 1, 1) + _day(1, 1, 1) + _day(2, 0, 2)
    status = compute_drift_status(arts, BASELINE, now=NOW)
    assert status["days_exceeded"] == 2
    assert status["is_drifting"] is False


def test_streak_breaks_on_most_recent_day():
    # Newest day below threshold breaks the streak regardless of older spikes.
    arts = _day(0, 0, 2) + _day(1, 1, 1) + _day(2, 1, 1) + _day(3, 1, 1)
    status = compute_drift_status(arts, BASELINE, now=NOW)
    assert status["days_exceeded"] == 0
    assert status["is_drifting"] is False


def test_window_excludes_old_artifacts():
    # A RED-heavy day 10 days ago must not count (outside 7-day window).
    arts = _day(10, 5, 0) + _day(0, 1, 3)  # today: 1 RED / 4 total = 0.25
    status = compute_drift_status(arts, BASELINE, now=NOW)
    assert status["total_decisions"] == 4
    assert status["current_red_rate"] == 0.25


def test_current_red_rate_over_window():
    # 3 RED + 1 GREEN across two in-window days -> 0.75.
    arts = _day(0, 2, 0) + _day(1, 1, 1)
    status = compute_drift_status(arts, BASELINE, now=NOW)
    assert status["total_decisions"] == 4
    assert status["current_red_rate"] == 0.75


def test_empty_is_safe():
    status = compute_drift_status([], BASELINE, now=NOW)
    assert status["is_drifting"] is False
    assert status["current_red_rate"] == 0.0
    assert status["total_decisions"] == 0
    assert status["daily"] == []


def test_daily_is_newest_first():
    arts = _day(0, 1, 1) + _day(2, 1, 1)
    rows = daily_red_rates(arts, now=NOW)
    assert [r["date"] for r in rows] == ["2026-06-13", "2026-06-11"]

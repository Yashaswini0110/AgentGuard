"""
AgentGuard v2 — F5: Data Drift Detection (M1)

Pure, side-effect-free drift math. Callers pass in a list of artifact dicts
(filesystem today, Supabase later via F9) and the training baseline; this module
computes the rolling RED rate and the consecutive-day drift signal.

Drift definition (PRD F5):
    rolling `window_days`-day RED rate exceeds (baseline_red_rate * MULTIPLIER)
    for `DAYS_REQUIRED` consecutive most-recent days.

"RED rate" here means the *router's* RED classifications (routing_classification
== "RED"), to stay apples-to-apples with the training baseline, which is the
model's RED fraction on its training labels.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Optional

# Tunable constants (kept here so the contract and tests share one source).
WINDOW_DAYS = 7
DAYS_REQUIRED = 3
MULTIPLIER = 1.5


def _parse_ts(ts) -> Optional[datetime.datetime]:
    """Parse an ISO-8601 artifact timestamp to an aware UTC datetime, or None."""
    if not isinstance(ts, str) or not ts:
        return None
    raw = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def _is_red(artifact: dict) -> bool:
    level = artifact.get("routing_classification")
    return isinstance(level, str) and level.strip().upper() == "RED"


def daily_red_rates(
    artifacts: list[dict],
    window_days: int = WINDOW_DAYS,
    now: Optional[datetime.datetime] = None,
) -> list[dict]:
    """
    Per-calendar-day RED rate within the trailing window, newest day first.

    Returns a list of {date: 'YYYY-MM-DD', red_rate: float, total: int} for each
    UTC day in the window that has at least one decision.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    window_start = now - datetime.timedelta(days=window_days)

    buckets: dict[str, list[bool]] = defaultdict(list)
    for art in artifacts:
        dt = _parse_ts(art.get("timestamp"))
        if dt is None or dt <= window_start or dt > now:
            continue
        day = dt.date().isoformat()
        buckets[day].append(_is_red(art))

    rows: list[dict] = []
    for day in sorted(buckets.keys(), reverse=True):
        flags = buckets[day]
        total = len(flags)
        red = sum(1 for f in flags if f)
        rows.append(
            {
                "date": day,
                "red_rate": round(red / total, 4) if total else 0.0,
                "total": total,
            }
        )
    return rows


def compute_drift_status(
    artifacts: list[dict],
    baseline_red_rate: float,
    window_days: int = WINDOW_DAYS,
    days_required: int = DAYS_REQUIRED,
    multiplier: float = MULTIPLIER,
    now: Optional[datetime.datetime] = None,
) -> dict:
    """
    Compute the drift status object (matches contracts/drift-status.md).

    is_drifting is True when the most-recent `days_required` days (that have
    decisions) each have a daily RED rate strictly above baseline * multiplier.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    window_start = now - datetime.timedelta(days=window_days)

    threshold = round(float(baseline_red_rate) * multiplier, 6)

    in_window = [
        a
        for a in artifacts
        if (dt := _parse_ts(a.get("timestamp"))) is not None
        and window_start < dt <= now
    ]
    total = len(in_window)
    red = sum(1 for a in in_window if _is_red(a))
    current_red_rate = round(red / total, 4) if total else 0.0

    daily = daily_red_rates(artifacts, window_days=window_days, now=now)

    # Count consecutive most-recent days strictly above threshold.
    days_exceeded = 0
    for row in daily:  # newest first
        if row["red_rate"] > threshold:
            days_exceeded += 1
        else:
            break

    return {
        "is_drifting": days_exceeded >= days_required,
        "current_red_rate": current_red_rate,
        "baseline_red_rate": round(float(baseline_red_rate), 6),
        "threshold": threshold,
        "days_exceeded": days_exceeded,
        "days_required": days_required,
        "window_days": window_days,
        "total_decisions": total,
        "daily": daily,
    }

"""F5 drift-alert: edge detection + fire-once semantics."""

import datetime

from core import drift_alert
from core.drift_alert import detect_transition

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)


def _drifting_artifacts() -> list[dict]:
    """3 recent days at 0.5 RED — drift under baseline 0.20 (threshold 0.30)."""
    arts = []
    for days_ago in (0, 1, 2):
        ts = (NOW - datetime.timedelta(days=days_ago)).replace(hour=9)
        arts.append({"timestamp": ts.isoformat(), "routing_classification": "RED"})
        arts.append({"timestamp": ts.isoformat(), "routing_classification": "GREEN"})
    return arts


def test_detect_transition_only_on_rising_edge():
    assert detect_transition(False, True) is True
    assert detect_transition(True, True) is False
    assert detect_transition(False, False) is False
    assert detect_transition(True, False) is False


def test_alert_fires_exactly_once(tmp_path, monkeypatch):
    monkeypatch.setattr(drift_alert, "STATE_PATH", str(tmp_path / "drift_state.json"))
    fired: list[dict] = []
    monkeypatch.setattr(drift_alert, "_subscribers", [lambda s: fired.append(s)])

    arts = _drifting_artifacts()
    first = drift_alert.evaluate_and_notify(arts, 0.20, now=NOW)
    second = drift_alert.evaluate_and_notify(arts, 0.20, now=NOW)

    assert first["is_drifting"] is True
    assert first["alert_fired"] is True       # rising edge
    assert second["alert_fired"] is False     # already drifting -> no re-fire
    assert len(fired) == 1                     # subscriber called exactly once


def test_no_alert_when_not_drifting(tmp_path, monkeypatch):
    monkeypatch.setattr(drift_alert, "STATE_PATH", str(tmp_path / "drift_state.json"))
    fired: list[dict] = []
    monkeypatch.setattr(drift_alert, "_subscribers", [lambda s: fired.append(s)])

    calm = [{"timestamp": NOW.replace(hour=9).isoformat(), "routing_classification": "GREEN"}]
    result = drift_alert.evaluate_and_notify(calm, 0.20, now=NOW)

    assert result["is_drifting"] is False
    assert result["alert_fired"] is False
    assert fired == []

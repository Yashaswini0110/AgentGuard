"""
AgentGuard v2 — F5: drift-alert transition + notifier hook (M1)

This is the seam between M1's drift detection and M3's F6 email. M1 owns
detecting when drift is *newly raised* (a False -> True edge) and invoking
registered subscribers exactly once; M3 registers an email notifier via
register_drift_alert().

Subscribers are fire-and-forget: a failing subscriber is logged and never
propagates, so a drift alert (or a broken email integration) can never affect
the governance pipeline.
"""

from __future__ import annotations

import datetime
import glob
import json
import logging
import os
import threading
from typing import Callable

from core import drift, risk_router

logger = logging.getLogger("agentguard.drift")

_ROOT = os.path.dirname(os.path.dirname(__file__))
ARTIFACTS_DIR = os.path.join(_ROOT, "artifacts")
STATE_PATH = os.path.join(_ROOT, "models", "drift_state.json")

_LOCK = threading.Lock()
_subscribers: list[Callable[[dict], None]] = []


def register_drift_alert(fn: Callable[[dict], None]) -> None:
    """
    Subscribe a callback invoked once when drift is newly raised. The callback
    receives the drift status dict (contracts/drift-status.md). M3 wires the
    Admin email notification here.
    """
    _subscribers.append(fn)


def detect_transition(prev_drifting: bool, now_drifting: bool) -> bool:
    """True only on a False -> True edge (drift newly raised)."""
    return bool(now_drifting) and not bool(prev_drifting)


def _load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"is_drifting": False}


def _save_state(is_drifting: bool) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"is_drifting": is_drifting, "updated_at": _now()}, f
            )
    except OSError as exc:
        logger.warning("could not persist drift state: %s", exc)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _notify(status: dict) -> None:
    for fn in list(_subscribers):
        try:
            fn(status)
        except Exception as exc:  # a subscriber must never break the caller
            logger.warning("drift alert subscriber failed: %s", exc)


def evaluate_and_notify(
    artifacts: list[dict], baseline_red_rate: float, now=None
) -> dict:
    """
    Compute drift, fire subscribers once on a newly-raised alert, persist state.
    Returns the drift status with an added ``alert_fired`` flag.
    """
    status = drift.compute_drift_status(artifacts, baseline_red_rate, now=now)
    with _LOCK:
        prev = bool(_load_state().get("is_drifting", False))
        fired = detect_transition(prev, status["is_drifting"])
        _save_state(status["is_drifting"])
    if fired:
        logger.warning(
            "DRIFT ALERT raised: red_rate=%.3f threshold=%.3f days_exceeded=%d",
            status["current_red_rate"], status["threshold"], status["days_exceeded"],
        )
        _notify(status)
    status["alert_fired"] = fired
    return status


def _load_artifacts() -> list[dict]:
    arts: list[dict] = []
    files = sorted(
        glob.glob(os.path.join(ARTIFACTS_DIR, "*.json")),
        key=os.path.getmtime,
        reverse=True,
    )[:2000]
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                arts.append(json.load(f))
        except Exception:
            pass
    return arts


def run_drift_check() -> dict:
    """Background entrypoint: load artifacts + baseline, evaluate, notify."""
    baseline = float(risk_router.load_model_meta().get("baseline_red_rate", 0.15))
    return evaluate_and_notify(_load_artifacts(), baseline)

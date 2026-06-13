"""
AgentGuard v2 — F5.2: Router retraining (M1)

Background retrain of the Layer-2 risk router. Trains a challenger on the
synthetic baseline PLUS accumulated real decisions (artifacts that carry the
raw router_features), cross-validates, and hot-swaps the live model ONLY if the
challenger's accuracy matches or beats the incumbent on the same held-out split.
The incumbent is archived first, so a swap is always reversible.

Guardrails (PRD §5.1): the live model is only replaced on the final atomic step;
any failure leaves it untouched. Email/UI never block on this.

Contract: contracts/admin-retrain.md
"""

from __future__ import annotations

import datetime
import os
import threading
import uuid

import pandas as pd

from core import risk_router

_ROOT = os.path.dirname(os.path.dirname(__file__))
SYNTHETIC_CSV = os.path.join(_ROOT, "data", "synthetic_hr_dataset.csv")

_LOCK = threading.Lock()
_STATUS: dict = {
    "job_id": None,
    "status": "IDLE",          # IDLE | RUNNING | DONE | FAILED
    "started_at": None,
    "finished_at": None,
    "old_accuracy": None,
    "new_accuracy": None,
    "swapped": False,
    "model_version_hash": None,
    "message": "No retrain has run yet.",
}


def should_swap(new_acc: float, old_acc: float | None) -> bool:
    """Swap iff there is no incumbent, or the challenger matches/beats it."""
    return old_acc is None or new_acc >= old_acc


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_status() -> dict:
    with _LOCK:
        return dict(_STATUS)


def _update(**fields) -> None:
    with _LOCK:
        _STATUS.update(fields)


def _artifact_training_rows() -> list[dict]:
    """Rows from real decisions that persisted their router_features + label."""
    from core import artifact_store
    rows: list[dict] = []
    for art in artifact_store.load_all():
        feats = art.get("router_features")
        label = art.get("routing_classification")
        if (
            isinstance(feats, dict)
            and label in ("GREEN", "YELLOW", "RED")
            and all(k in feats for k in risk_router.SAFE_FEATURES)
        ):
            row = {k: feats[k] for k in risk_router.SAFE_FEATURES}
            row["risk_label"] = label
            rows.append(row)
    return rows


def build_training_frame() -> tuple[pd.DataFrame, int, int]:
    """Synthetic baseline + retrainable real artifacts, aligned on the model columns."""
    cols = risk_router.SAFE_FEATURES + ["risk_label"]
    base = pd.read_csv(SYNTHETIC_CSV)
    base = base[[c for c in cols if c in base.columns]]
    n_synth = len(base)

    art_rows = _artifact_training_rows()
    if art_rows:
        combined = pd.concat([base, pd.DataFrame(art_rows)], ignore_index=True)
    else:
        combined = base
    return combined, n_synth, len(art_rows)


def _run(job_id: str) -> None:
    """Heavy work — executed as a background task."""
    try:
        df, n_synth, n_art = build_training_frame()
        _update(message=f"Training challenger on {n_synth} synthetic + {n_art} real rows")

        result = risk_router.fit_router_from_frame(df)
        new_acc = result["test_acc"]

        # Evaluate the incumbent on the SAME held-out split for a fair comparison.
        old_acc = None
        try:
            old_acc = risk_router.evaluate_bundle(
                risk_router._load_model(), result["X_test"], result["y_test"]
            )
        except Exception:
            old_acc = None  # no incumbent -> challenger wins by default

        if should_swap(new_acc, old_acc):
            risk_router.archive_current_model()
            meta = risk_router.persist_router_bundle(result, source="retrain")
            _update(
                status="DONE",
                finished_at=_now(),
                old_accuracy=old_acc,
                new_accuracy=round(new_acc, 6),
                swapped=True,
                model_version_hash=meta["model_version_hash"],
                message=f"Swapped: challenger {new_acc:.4f} >= incumbent "
                        f"{('n/a' if old_acc is None else f'{old_acc:.4f}')}.",
            )
        else:
            _update(
                status="DONE",
                finished_at=_now(),
                old_accuracy=round(old_acc, 6),
                new_accuracy=round(new_acc, 6),
                swapped=False,
                model_version_hash=risk_router._load_hash(),
                message=f"Kept incumbent: challenger {new_acc:.4f} < incumbent {old_acc:.4f}.",
            )
    except Exception as exc:  # live model untouched on any failure
        _update(status="FAILED", finished_at=_now(), message=f"Retrain failed: {exc}")


def start_retrain(background) -> dict | None:
    """
    Reserve the single retrain slot and schedule the background job. Returns the
    job descriptor, or None if a retrain is already running (caller -> 409).
    """
    with _LOCK:
        if _STATUS["status"] == "RUNNING":
            return None
        job_id = uuid.uuid4().hex[:8]
        _STATUS.update(
            job_id=job_id,
            status="RUNNING",
            started_at=_now(),
            finished_at=None,
            old_accuracy=None,
            new_accuracy=None,
            swapped=False,
            model_version_hash=None,
            message="Retrain started.",
        )
    background.add_task(_run, job_id)
    return {"job_id": job_id, "status": "STARTED"}

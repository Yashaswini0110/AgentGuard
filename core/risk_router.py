"""
AgentGuard v3 — Layer 2: ML Risk Router
Classifies hiring decisions into GREEN / YELLOW / RED risk categories.
Uses only safe, non-discriminatory features and produces SHAP explainability scores.
Target latency: < 50ms per inference call.
"""

import os
import time
import json
import shutil
import datetime
import hashlib
from typing import Optional

import numpy as np
import pandas as pd
import joblib
import shap
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SAFE_FEATURES = [
    "years_of_experience",
    "skill_match_score",
    "interview_score",
    "assessment_score",
    "decision_confidence",
    "feature_count",
]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "router_model.pkl")
HASH_PATH = os.path.join(MODEL_DIR, "model_version_hash.txt")
META_PATH = os.path.join(MODEL_DIR, "model_meta.json")

# Fallback RED baseline used when no model_meta.json exists yet (F5 drift).
DEFAULT_BASELINE_RED_RATE = 0.15

# Module-level cache: avoids rebuilding PermutationExplainer on every call.
_EXPLAINER_CACHE: dict = {}

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _derive_risk_label(row: pd.Series) -> str:
    """Deterministic rule-based fallback for labelling unlabelled datasets."""
    conf = row.get("decision_confidence", 0.5)
    fc = row.get("feature_count", 0)

    if conf < 0.4 or fc > 8:
        return "RED"
    if (0.4 <= conf <= 0.65) or (5 <= fc <= 8):
        return "YELLOW"
    return "GREEN"


def _sha256_file(path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_model_dir() -> None:
    os.makedirs(MODEL_DIR, exist_ok=True)


def _load_model() -> dict:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Trained model not found at '{MODEL_PATH}'. "
            "Run train_router() first."
        )
    return joblib.load(MODEL_PATH)


def _load_hash() -> str:
    if not os.path.exists(HASH_PATH):
        return "unknown"
    with open(HASH_PATH, "r") as f:
        return f.read().strip()


def load_model_meta() -> dict:
    """
    Read models/model_meta.json (training baseline + provenance for F5 drift).

    Falls back to a safe default if the file is missing or unreadable so callers
    (e.g. /drift/status) never crash on a fresh or partially-set-up install.
    """
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if isinstance(meta, dict) and "baseline_red_rate" in meta:
            return meta
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {
        "baseline_red_rate": DEFAULT_BASELINE_RED_RATE,
        "model_version_hash": _load_hash(),
        "source": "default",
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART A — Training
# ─────────────────────────────────────────────────────────────────────────────

def fit_router_from_frame(df: pd.DataFrame) -> dict:
    """
    Fit a GradientBoostingClassifier on a feature frame and return the trained
    bundle, evaluation metrics, the training baseline, and the held-out test
    split. Exposing the test split lets a retrain compare a challenger model
    against the incumbent on identical data.
    """
    if "risk_label" not in df.columns:
        df = df.copy()
        df["risk_label"] = df.apply(_derive_risk_label, axis=1)

    missing = [c for c in SAFE_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")

    X = df[SAFE_FEATURES].astype(float)
    y_raw = df["risk_label"].astype(str).str.strip().str.upper()

    label_order = ["GREEN", "YELLOW", "RED"]
    le = LabelEncoder()
    le.fit(label_order)
    y = le.transform(y_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Regularisation: shallow trees + leaf/ split floors generalise on noisy labels.
    clf = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        min_samples_leaf=20,
        min_samples_split=40,
        random_state=42,
    )
    clf.fit(X_train, y_train)

    test_acc = accuracy_score(y_test, clf.predict(X_test))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X_train, y_train, cv=cv, scoring="accuracy")

    # Small SHAP background sample keeps the PermutationExplainer fast.
    bg_size = min(10, len(X_train))
    background = X_train.sample(n=bg_size, random_state=42)
    bundle = {"classifier": clf, "label_encoder": le, "shap_background": background}

    return {
        "bundle": bundle,
        "test_acc": float(test_acc),
        "cv_acc": float(cv_scores.mean()),
        "baseline_red_rate": float((y_raw == "RED").mean()),
        "n_samples": int(len(df)),
        "label_distribution": {
            "GREEN": int((y_raw == "GREEN").sum()),
            "YELLOW": int((y_raw == "YELLOW").sum()),
            "RED": int((y_raw == "RED").sum()),
        },
        "X_test": X_test,
        "y_test": y_test,
    }


def persist_router_bundle(fit_result: dict, source: str = "train_router") -> dict:
    """
    Write model + hash + metadata (drift baseline) from a fit_router_from_frame
    result. This is the atomic swap step: callers archive the incumbent first.
    """
    _ensure_model_dir()
    joblib.dump(fit_result["bundle"], MODEL_PATH)
    model_hash = _sha256_file(MODEL_PATH)
    with open(HASH_PATH, "w") as f:
        f.write(model_hash)

    meta = {
        "baseline_red_rate": round(fit_result["baseline_red_rate"], 6),
        "model_version_hash": model_hash,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "train_accuracy": round(fit_result["test_acc"], 6),
        "cv_accuracy": round(fit_result["cv_acc"], 6),
        "n_samples": fit_result["n_samples"],
        "label_distribution": fit_result["label_distribution"],
        "source": source,
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def archive_current_model() -> Optional[str]:
    """
    Copy the live model to models/archive/<old_hash>.pkl so a swap is reversible.
    Returns the archive path, or None if there is no current model.
    """
    if not os.path.exists(MODEL_PATH):
        return None
    archive_dir = os.path.join(MODEL_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    dest = os.path.join(archive_dir, f"{_load_hash()}.pkl")
    shutil.copy2(MODEL_PATH, dest)
    return dest


def evaluate_bundle(bundle: dict, X_test, y_test) -> float:
    """Accuracy of a bundle's classifier on an (already label-encoded) test set."""
    return float(accuracy_score(y_test, bundle["classifier"].predict(X_test)))


def train_router(dataset_path: str) -> dict:
    """Train + persist the router from a CSV dataset (CLI / bootstrap entrypoint)."""
    print(f"[train_router] Loading dataset from: {dataset_path}")
    result = fit_router_from_frame(pd.read_csv(dataset_path))
    meta = persist_router_bundle(result, source="train_router")
    print(f"[train_router] test_acc={meta['train_accuracy']} cv_acc={meta['cv_accuracy']} "
          f"baseline_red={meta['baseline_red_rate']} hash={meta['model_version_hash'][:12]}")
    return meta


# ─────────────────────────────────────────────────────────────────────────────
# PART B — Inference
# ─────────────────────────────────────────────────────────────────────────────

def classify_risk(decision: dict) -> dict:
    """
    Classify a single hiring decision into GREEN, YELLOW, or RED.

    Parameters
    ----------
    decision : dict
        Must contain the six safe feature keys listed in SAFE_FEATURES.

    Returns
    -------
    dict with keys:
        risk_level        : str   — "GREEN", "YELLOW", or "RED"
        confidence_score  : float — model's max class probability
        shap_scores       : dict  — feature name -> SHAP value
        model_version_hash: str   — SHA-256 of the serialised model file
        latency_ms        : float — wall-clock time for this call (ms)
    """
    t_start = time.perf_counter()

    # ── Load model bundle ─────────────────────────────────────────────────────
    bundle = _load_model()
    clf: GradientBoostingClassifier = bundle["classifier"]
    le: LabelEncoder = bundle["label_encoder"]

    # ── Build feature vector ──────────────────────────────────────────────────
    try:
        feature_values = [float(decision[f]) for f in SAFE_FEATURES]
    except KeyError as e:
        raise KeyError(f"Missing required feature in decision dict: {e}") from e

    # Named DataFrame keeps sklearn happy (no feature-name warning)
    X_input = pd.DataFrame([feature_values], columns=SAFE_FEATURES)

    # ── Predict ───────────────────────────────────────────────────────────────
    pred_encoded = clf.predict(X_input)[0]
    risk_level = le.inverse_transform([pred_encoded])[0]
    proba = clf.predict_proba(X_input)[0]
    confidence_score = float(np.max(proba))

    # ── SHAP values ───────────────────────────────────────────────────────────
    # PermutationExplainer supports multi-class predict_proba callables.
    # Cache the explainer by model hash so it is only built once per process.
    background: pd.DataFrame = bundle["shap_background"]
    model_hash_key = _load_hash()
    if model_hash_key not in _EXPLAINER_CACHE:
        _EXPLAINER_CACHE[model_hash_key] = shap.PermutationExplainer(
            clf.predict_proba, background
        )
    explainer = _EXPLAINER_CACHE[model_hash_key]
    # max_evals caps the permutation sweeps: 2*n_features+1 is the minimum
    # complete sweep that still assigns credit to every feature.
    max_evals = 2 * len(SAFE_FEATURES) + 1
    explanation = explainer(X_input, max_evals=max_evals)  # shape (1, n_features, n_classes)
    class_idx = int(pred_encoded)

    shap_values_arr = explanation.values       # numpy array
    if shap_values_arr.ndim == 3:
        # Shape: (n_samples=1, n_features, n_classes) — take predicted class
        shap_for_class = shap_values_arr[0, :, class_idx]
    elif shap_values_arr.ndim == 2:
        # Shape: (n_samples=1, n_features) — binary / single-output
        shap_for_class = shap_values_arr[0, :]
    else:
        shap_for_class = shap_values_arr.ravel()

    shap_scores = {
        feat: float(val)
        for feat, val in zip(SAFE_FEATURES, shap_for_class)
    }

    # ── Latency ───────────────────────────────────────────────────────────────
    latency_ms = (time.perf_counter() - t_start) * 1000.0

    return {
        "risk_level": risk_level,
        "confidence_score": confidence_score,
        "shap_scores": shap_scores,
        "model_version_hash": _load_hash(),
        "latency_ms": round(latency_ms, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART C — Drift detection
# ─────────────────────────────────────────────────────────────────────────────

def check_drift(recent_decisions: list) -> dict:
    """
    Analyse the distribution of recent risk-level labels and flag anomalies.

    Parameters
    ----------
    recent_decisions : list of str
        A list of risk_level strings, each being "GREEN", "YELLOW", or "RED".

    Returns
    -------
    dict with keys:
        green_pct  : float — percentage of GREEN decisions
        yellow_pct : float — percentage of YELLOW decisions
        red_pct    : float — percentage of RED decisions
        total      : int   — total decisions analysed
        alert      : bool  — True if RED percentage exceeds 20%
    """
    if not recent_decisions:
        return {
            "green_pct": 0.0,
            "yellow_pct": 0.0,
            "red_pct": 0.0,
            "total": 0,
            "alert": False,
        }

    total = len(recent_decisions)
    normalised = [r.strip().upper() for r in recent_decisions]

    green_pct = round(normalised.count("GREEN") / total * 100, 2)
    yellow_pct = round(normalised.count("YELLOW") / total * 100, 2)
    red_pct = round(normalised.count("RED") / total * 100, 2)

    return {
        "green_pct": green_pct,
        "yellow_pct": yellow_pct,
        "red_pct": red_pct,
        "total": total,
        "alert": red_pct > 20.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART D — Demo entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DATASET = os.path.join(
        os.path.dirname(__file__), "..", "data", "synthetic_hr_dataset.csv"
    )

    # ── Train ─────────────────────────────────────────────────────────────────
    print("=" * 60)
    print("  AgentGuard v3 -- Layer 2: Risk Router Training")
    print("=" * 60)
    train_router(DATASET)

    # ── Sample decisions ──────────────────────────────────────────────────────
    sample_decisions = [
        {   # Expected: GREEN -- strong candidate
            "years_of_experience": 7.0,
            "skill_match_score": 0.92,
            "interview_score": 88.0,
            "assessment_score": 85.0,
            "decision_confidence": 0.91,
            "feature_count": 4,
        },
        {   # Expected: YELLOW -- borderline
            "years_of_experience": 3.0,
            "skill_match_score": 0.60,
            "interview_score": 65.0,
            "assessment_score": 62.0,
            "decision_confidence": 0.55,
            "feature_count": 6,
        },
        {   # Expected: RED -- low confidence, too many features
            "years_of_experience": 1.0,
            "skill_match_score": 0.35,
            "interview_score": 40.0,
            "assessment_score": 38.0,
            "decision_confidence": 0.30,
            "feature_count": 10,
        },
    ]

    print("\n" + "=" * 60)
    print("  Inference on 3 Sample Decisions")
    print("=" * 60)
    risk_levels = []
    for i, dec in enumerate(sample_decisions, 1):
        result = classify_risk(dec)
        risk_levels.append(result["risk_level"])
        print(f"\n-- Decision {i} " + "-" * 44)
        print(f"  Risk Level        : {result['risk_level']}")
        print(f"  Confidence Score  : {result['confidence_score']:.4f}")
        print(f"  Latency           : {result['latency_ms']} ms")
        print(f"  Model Hash        : {result['model_version_hash'][:16]}...")
        print("  SHAP Scores:")
        for feat, val in result["shap_scores"].items():
            direction = "+" if val >= 0 else "-"
            print(f"    [{direction}] {feat:<25} {val:+.4f}")

    # ── Drift check ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Drift Detection on Inference Window")
    print("=" * 60)
    drift = check_drift(risk_levels)
    print(f"  GREEN  : {drift['green_pct']}%")
    print(f"  YELLOW : {drift['yellow_pct']}%")
    print(f"  RED    : {drift['red_pct']}%")
    alert_msg = "ALERT -- RED rate exceeds 20%" if drift["alert"] else "OK"
    print(f"  Alert  : {alert_msg}")
    print()

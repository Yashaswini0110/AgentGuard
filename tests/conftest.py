"""
conftest.py — AgentGuard test session configuration.

Ensures the risk router model is trained once before the test suite runs.
Also warms up the SHAP PermutationExplainer cache so that latency tests
do not pay the cold-start cost (~18s) during measurement.
"""

import os
import sys
import pytest

# Tests must not write to the shared Supabase artifact store (F9). Force the
# artifact store to filesystem-only unless a run explicitly opts in.
os.environ.setdefault("AGENTGUARD_ARTIFACT_DB", "0")

# ── Make sure the repo root is on sys.path so both `core` and `tests` resolve ─
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

MODEL_PATH = os.path.join(REPO_ROOT, "models", "router_model.pkl")
DATASET_PATH = os.path.join(REPO_ROOT, "data", "synthetic_hr_dataset.csv")

# Minimal decision used only to warm up the SHAP explainer cache.
_WARMUP_DECISION = {
    "years_of_experience": 5,
    "skill_match_score": 0.75,
    "interview_score": 70.0,
    "assessment_score": 72.0,
    "decision_confidence": 0.80,
    "feature_count": 4,
}


def _train_if_missing() -> None:
    """Train the router model if it has not been trained yet."""
    if os.path.exists(MODEL_PATH):
        return  # nothing to do

    from core.risk_router import train_router

    if not os.path.exists(DATASET_PATH):
        pytest.skip(
            f"Training dataset not found at '{DATASET_PATH}'. "
            "Generate it first with data/generate_synthetic_dataset.py.",
            allow_module_level=True,
        )

    print(f"\n[conftest] Model not found — training on '{DATASET_PATH}' ...")
    train_router(DATASET_PATH)
    print(f"[conftest] Model saved to '{MODEL_PATH}'.")


def _warmup_shap_cache() -> None:
    """
    Run one throw-away inference call so the PermutationExplainer is built
    and stored in _EXPLAINER_CACHE before any test measures latency.

    PermutationExplainer initialises lazily on the first call (~18s).
    All subsequent calls within the same process are fast (<200ms) because
    the explainer object is reused from the module-level cache in risk_router.
    """
    from core.risk_router import classify_risk
    print("\n[conftest] Warming up SHAP explainer cache (first call is slow) ...")
    classify_risk(_WARMUP_DECISION)
    print("[conftest] SHAP cache warm — latency tests will now be fast.")


# Run once for the entire test session (not once per test or module).
def pytest_sessionstart(session):  # noqa: ARG001
    _train_if_missing()
    _warmup_shap_cache()

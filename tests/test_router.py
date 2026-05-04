"""
tests/test_router.py — pytest suite for AgentGuard v3 Layer 2: risk_router.py

Covered:
  classify_risk()
    1. Returns a dict with all required keys
    2. risk_level is always GREEN, YELLOW, or RED
    3. confidence_score is in [0.0, 1.0]
    4. latency_ms is under 200 ms (generous budget for CI/test environments)
    5. shap_scores is a dict containing exactly the 6 safe feature names

  check_drift()
    6. Mostly-GREEN window returns alert=False
    7. >20% RED window returns alert=True
    8. Percentages are calculated correctly
"""

import pytest
from core.risk_router import classify_risk, check_drift

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAFE_FEATURES = [
    "years_of_experience",
    "skill_match_score",
    "interview_score",
    "assessment_score",
    "decision_confidence",
    "feature_count",
]

SAMPLE_DECISION = {
    "years_of_experience": 5,
    "skill_match_score": 0.87,
    "interview_score": 7.8,
    "assessment_score": 82,
    "decision_confidence": 0.91,
    "feature_count": 4,
}


@pytest.fixture(scope="module")
def result():
    """Run classify_risk once for the entire module; reuse the result."""
    return classify_risk(SAMPLE_DECISION)


# ─────────────────────────────────────────────────────────────────────────────
# classify_risk tests
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyRiskOutputShape:
    """Test 1 — classify_risk returns a dict with all required keys."""

    REQUIRED_KEYS = {
        "risk_level",
        "confidence_score",
        "shap_scores",
        "model_version_hash",
        "latency_ms",
    }

    def test_returns_dict(self, result):
        assert isinstance(result, dict), "classify_risk must return a dict"

    def test_all_required_keys_present(self, result):
        missing = self.REQUIRED_KEYS - result.keys()
        assert not missing, f"Missing keys in result: {missing}"

    def test_no_unexpected_none_values(self, result):
        for key in self.REQUIRED_KEYS:
            assert result[key] is not None, f"Key '{key}' must not be None"


class TestRiskLevel:
    """Test 2 — risk_level is always one of GREEN, YELLOW, RED."""

    VALID_LEVELS = {"GREEN", "YELLOW", "RED"}

    def test_risk_level_is_string(self, result):
        assert isinstance(result["risk_level"], str)

    def test_risk_level_is_valid(self, result):
        assert result["risk_level"] in self.VALID_LEVELS, (
            f"risk_level '{result['risk_level']}' is not one of {self.VALID_LEVELS}"
        )

    @pytest.mark.parametrize("decision,expected_level", [
        (
            {   # Very high confidence, few features -> GREEN
                "years_of_experience": 10,
                "skill_match_score": 0.95,
                "interview_score": 95.0,
                "assessment_score": 93.0,
                "decision_confidence": 0.95,
                "feature_count": 3,
            },
            "GREEN",
        ),
        (
            {   # Low confidence, many features -> RED
                "years_of_experience": 1,
                "skill_match_score": 0.20,
                "interview_score": 30.0,
                "assessment_score": 25.0,
                "decision_confidence": 0.25,
                "feature_count": 12,
            },
            "RED",
        ),
    ])
    def test_extreme_inputs_yield_expected_levels(self, decision, expected_level):
        res = classify_risk(decision)
        assert res["risk_level"] == expected_level, (
            f"Expected {expected_level}, got {res['risk_level']} for input {decision}"
        )


class TestConfidenceScore:
    """Test 3 — confidence_score is between 0.0 and 1.0."""

    def test_confidence_score_is_float(self, result):
        assert isinstance(result["confidence_score"], float)

    def test_confidence_score_lower_bound(self, result):
        assert result["confidence_score"] >= 0.0, (
            f"confidence_score {result['confidence_score']} is below 0.0"
        )

    def test_confidence_score_upper_bound(self, result):
        assert result["confidence_score"] <= 1.0, (
            f"confidence_score {result['confidence_score']} exceeds 1.0"
        )


class TestLatency:
    """Test 4 — latency_ms is under 200 ms."""

    LATENCY_BUDGET_MS = 200.0

    def test_latency_is_numeric(self, result):
        assert isinstance(result["latency_ms"], (int, float))

    def test_latency_is_non_negative(self, result):
        assert result["latency_ms"] >= 0.0

    def test_latency_under_budget(self, result):
        assert result["latency_ms"] < self.LATENCY_BUDGET_MS, (
            f"latency_ms {result['latency_ms']:.2f} exceeds {self.LATENCY_BUDGET_MS} ms"
        )


class TestShapScores:
    """Test 5 — shap_scores is a dict with exactly the 6 safe feature names."""

    def test_shap_scores_is_dict(self, result):
        assert isinstance(result["shap_scores"], dict)

    def test_shap_scores_has_six_keys(self, result):
        assert len(result["shap_scores"]) == 6, (
            f"Expected 6 SHAP keys, got {len(result['shap_scores'])}: "
            f"{list(result['shap_scores'].keys())}"
        )

    def test_shap_scores_keys_match_features(self, result):
        assert set(result["shap_scores"].keys()) == set(SAFE_FEATURES), (
            f"SHAP keys {set(result['shap_scores'].keys())} "
            f"do not match expected features {set(SAFE_FEATURES)}"
        )

    def test_shap_values_are_floats(self, result):
        for feat, val in result["shap_scores"].items():
            assert isinstance(val, float), (
                f"SHAP value for '{feat}' is {type(val).__name__}, expected float"
            )


# ─────────────────────────────────────────────────────────────────────────────
# check_drift tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckDriftNoAlert:
    """Test 6 — mostly-GREEN window returns alert=False."""

    def test_all_green_no_alert(self):
        decisions = ["GREEN"] * 10
        drift = check_drift(decisions)
        assert drift["alert"] is False

    def test_green_heavy_no_alert(self):
        # 80% GREEN, 10% YELLOW, 10% RED — RED <= 20%, no alert
        decisions = ["GREEN"] * 8 + ["YELLOW"] * 1 + ["RED"] * 1
        drift = check_drift(decisions)
        assert drift["alert"] is False

    def test_exactly_20_pct_red_no_alert(self):
        # RED == 20% should NOT trigger alert (threshold is strictly > 20%)
        decisions = ["GREEN"] * 4 + ["RED"] * 1
        drift = check_drift(decisions)
        assert drift["alert"] is False, (
            "alert should be False when RED == 20% (threshold is strictly > 20%)"
        )


class TestCheckDriftAlert:
    """Test 7 — >20% RED returns alert=True."""

    def test_majority_red_triggers_alert(self):
        decisions = ["RED"] * 5 + ["GREEN"] * 5
        drift = check_drift(decisions)
        assert drift["alert"] is True

    def test_all_red_triggers_alert(self):
        drift = check_drift(["RED"] * 10)
        assert drift["alert"] is True

    def test_just_over_20_pct_triggers_alert(self):
        # 21% RED (3 out of ~14, simplest integer fraction > 0.20)
        decisions = ["RED"] * 3 + ["GREEN"] * 11  # 3/14 ≈ 21.4%
        drift = check_drift(decisions)
        assert drift["alert"] is True, (
            f"Expected alert=True for RED={3/14*100:.1f}%, got alert=False"
        )


class TestCheckDriftPercentages:
    """Test 8 — check_drift returns correct percentage values."""

    def test_pure_green_percentages(self):
        drift = check_drift(["GREEN"] * 10)
        assert drift["green_pct"] == 100.0
        assert drift["yellow_pct"] == 0.0
        assert drift["red_pct"] == 0.0
        assert drift["total"] == 10

    def test_equal_split_percentages(self):
        decisions = ["GREEN"] * 4 + ["YELLOW"] * 4 + ["RED"] * 2
        drift = check_drift(decisions)
        assert drift["green_pct"] == 40.0
        assert drift["yellow_pct"] == 40.0
        assert drift["red_pct"] == 20.0
        assert drift["total"] == 10

    def test_total_count_is_accurate(self):
        decisions = ["GREEN"] * 7 + ["RED"] * 3
        drift = check_drift(decisions)
        assert drift["total"] == 10

    def test_percentages_sum_to_100(self):
        decisions = ["GREEN"] * 5 + ["YELLOW"] * 3 + ["RED"] * 2
        drift = check_drift(decisions)
        total_pct = drift["green_pct"] + drift["yellow_pct"] + drift["red_pct"]
        assert abs(total_pct - 100.0) < 1e-6, (
            f"Percentages sum to {total_pct}, expected 100.0"
        )

    def test_case_insensitive_labels(self):
        # check_drift should normalise label casing
        drift = check_drift(["green", "GREEN", "Green", "red", "RED"])
        assert drift["green_pct"] == 60.0
        assert drift["red_pct"] == 40.0

    def test_empty_list_returns_zero_percentages(self):
        drift = check_drift([])
        assert drift["green_pct"] == 0.0
        assert drift["yellow_pct"] == 0.0
        assert drift["red_pct"] == 0.0
        assert drift["total"] == 0
        assert drift["alert"] is False

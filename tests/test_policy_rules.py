"""
F2 data-driven engine tests: the rule validator and the generic evaluator
handling arbitrary uploaded rules. No DB/LLM — pure policy_engine logic.
"""

import pytest

from core import policy_engine as pe


@pytest.fixture(autouse=True)
def _restore_defaults():
    yield
    pe.reset_to_default_policies()


def _rule(condition: dict, name: str = "R") -> dict:
    return {"name": name, "severity": "RED", "regulation": "", "reason": "", "condition": condition}


# --- validate_rule_content ---

def test_validate_feature_present_ok():
    ok, err = pe.validate_rule_content(
        {"severity": "RED", "condition": {"type": "feature_present", "features": ["x"], "match": "any"}}
    )
    assert ok and err == ""


def test_validate_pattern_match_ok():
    ok, _ = pe.validate_rule_content(
        {"severity": "YELLOW", "condition": {"type": "pattern_match", "patterns": ["bad"]}}
    )
    assert ok


def test_validate_bad_severity():
    ok, err = pe.validate_rule_content(
        {"severity": "PURPLE", "condition": {"type": "feature_present", "features": ["x"]}}
    )
    assert not ok and "severity" in err


def test_validate_bad_condition_type():
    ok, _ = pe.validate_rule_content({"severity": "RED", "condition": {"type": "magic"}})
    assert not ok


def test_validate_empty_features():
    ok, _ = pe.validate_rule_content(
        {"severity": "RED", "condition": {"type": "feature_present", "features": [], "match": "any"}}
    )
    assert not ok


# --- generic evaluator over arbitrary uploaded rules ---

def test_custom_feature_present_any():
    pe.set_active_policies([_rule({"type": "feature_present", "features": ["applicant_caste"], "match": "any"})])
    assert pe.check_policy({"features_used": ["applicant_caste"]})["passed"] is False
    assert pe.check_policy({"features_used": ["skill_match_score"]})["passed"] is True


def test_custom_feature_present_all():
    pe.set_active_policies([_rule({"type": "feature_present", "features": ["a", "b"], "match": "all"})])
    assert pe.check_policy({"features_used": ["a"]})["passed"] is True            # only one -> pass
    assert pe.check_policy({"features_used": ["a", "b"]})["passed"] is False      # both -> block


def test_custom_pattern_match_is_case_insensitive():
    pe.set_active_policies([_rule({"type": "pattern_match", "patterns": ["secret code"], "target": "raw_input"})])
    assert pe.check_policy({"features_used": []}, raw_input="the SECRET CODE is here")["passed"] is False
    assert pe.check_policy({"features_used": []}, raw_input="clean text")["passed"] is True


def test_empty_active_set_passes_everything():
    pe.set_active_policies([])
    assert pe.check_policy({"features_used": ["emotion_score"]})["passed"] is True


def test_reset_restores_hardcoded_defaults():
    pe.set_active_policies([])
    assert pe.check_policy({"features_used": ["emotion_score"]})["passed"] is True
    pe.reset_to_default_policies()
    assert pe.check_policy({"features_used": ["emotion_score"]})["passed"] is False

import pytest
import json
from unittest.mock import patch
from core.worker_agent import make_hiring_decision

@pytest.fixture
def sample_candidate():
    return {
        "candidate_id": "CAND-001",
        "name": "Rahul Sharma",
        "years_of_experience": 5,
        "skill_match_score": 0.87,
        "interview_score": 7.8,
        "assessment_score": 82,
        "career_gap_months": 0,
        "gender": "M",
        "institution_tier": 2
    }

@patch('core.worker_agent.chat_json')
def test_make_hiring_decision_format(mock_chat_json, sample_candidate):
    # Mocking the LLM response
    mock_response = {
        "candidate_id": "CAND-001",
        "decision": "APPROVE",
        "confidence": 0.9,
        "reason": "Strong performance across all metrics.",
        "features_used": ["skill_match_score", "assessment_score"],
        "recommended_action": "PROCEED_TO_INTERVIEW"
    }
    mock_chat_json.return_value = mock_response

    result = make_hiring_decision(sample_candidate)

    # 2. Check all required fields are present
    expected_fields = ["candidate_id", "decision", "confidence", "reason", "features_used", "recommended_action"]
    for field in expected_fields:
        assert field in result

    # 3. Decision check
    assert result["decision"] in ["APPROVE", "REJECT"]

    # 4. Confidence check
    assert isinstance(result["confidence"], (float, int))
    assert 0.0 <= result["confidence"] <= 1.0

    # Verify ID match
    assert result["candidate_id"] == sample_candidate["candidate_id"]

@patch('core.worker_agent.chat_json')
def test_make_hiring_decision_rejection(mock_chat_json, sample_candidate):
    mock_response = {
        "candidate_id": "CAND-001",
        "decision": "REJECT",
        "confidence": 0.85,
        "reason": "Interview score below threshold.",
        "features_used": ["interview_score"],
        "recommended_action": "REJECT_APPLICATION"
    }
    mock_chat_json.return_value = mock_response

    result = make_hiring_decision(sample_candidate)
    
    assert result["decision"] == "REJECT"
    assert result["recommended_action"] == "REJECT_APPLICATION"
    assert 0.0 <= result["confidence"] <= 1.0

@patch('core.worker_agent.chat_json')
def test_make_hiring_decision_invalid_json(mock_chat_json, sample_candidate):
    # Test handling of non-JSON response (chat_json raises)
    mock_chat_json.side_effect = ValueError("LLM JSON parse failed")
    with pytest.raises(ValueError, match="LLM JSON parse failed"):
        make_hiring_decision(sample_candidate)

@patch('core.worker_agent.chat_json')
def test_make_hiring_decision_missing_fields(mock_chat_json, sample_candidate):
    # Test handling of missing required fields
    mock_response = {
        "candidate_id": "CAND-001",
        "decision": "APPROVE"
    }
    mock_chat_json.return_value = mock_response
    with pytest.raises(ValueError, match="Invalid response format"):
        make_hiring_decision(sample_candidate)

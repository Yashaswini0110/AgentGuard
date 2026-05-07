import pytest
import json
from unittest.mock import patch, MagicMock
from core.supervisor import semantic_review

@pytest.fixture
def sample_data():
    """Provides sample decision and router result data for testing."""
    decision = {
        "features": {
            "candidate_name": "Test Candidate",
            "education": "PhD",
            "experience": 10,
            "location": "Bangalore",
            "socioeconomic_background": "High"
        },
        "decision": "APPROVE",
        "reason": "Exceptional qualifications and experience."
    }
    router_result = {
        "shap_scores": {
            "education": 0.5,
            "experience": 0.4,
            "location": 0.05,
            "socioeconomic_background": 0.05
        }
    }
    return decision, router_result

@patch("core.supervisor.chat_json")
def test_semantic_review_success_fields(mock_chat_json, sample_data):
    """Test that semantic_review returns all required fields with correct types on success."""
    # Mock successful LLM response
    mock_chat_json.return_value = {
        "supervisor_verdict": "APPROVE",
        "bias_detected": False,
        "bias_reason": None,
        "confidence": 0.98,
        "features_flagged": []
    }

    decision, router_result = sample_data
    result = semantic_review(decision, router_result)

    # 1. Returns dict with all required fields
    required_fields = [
        "supervisor_verdict", 
        "bias_detected", 
        "bias_reason", 
        "confidence", 
        "features_flagged", 
        "review_timestamp"
    ]
    for field in required_fields:
        assert field in result

    # 2. supervisor_verdict is one of the allowed values
    assert result["supervisor_verdict"] in ["APPROVE", "REJECT", "ESCALATE_TO_HUMAN"]
    assert result["supervisor_verdict"] == "APPROVE"

    # 4. bias_detected is a bool
    assert isinstance(result["bias_detected"], bool)
    assert result["bias_detected"] is False

    # 5. features_flagged is a list
    assert isinstance(result["features_flagged"], list)
    
    # Confidence is a float
    assert isinstance(result["confidence"], float)
    
    # Timestamp is a string
    assert isinstance(result["review_timestamp"], str)

@patch("core.supervisor.chat_json")
def test_semantic_review_bias_detection(mock_chat_json, sample_data):
    """Test that semantic_review correctly handles a case where bias is detected."""
    # Mock LLM response flagging bias
    mock_chat_json.return_value = {
        "supervisor_verdict": "REJECT",
        "bias_detected": True,
        "bias_reason": "Potential indirect bias detected in socioeconomic_background proxy.",
        "confidence": 0.88,
        "features_flagged": ["socioeconomic_background"]
    }

    decision, router_result = sample_data
    result = semantic_review(decision, router_result)

    assert result["supervisor_verdict"] == "REJECT"
    assert result["bias_detected"] is True
    assert "socioeconomic_background" in result["features_flagged"]
    assert "Potential indirect bias" in result["bias_reason"]

@patch("core.supervisor.chat_json")
def test_semantic_review_exception_handling(mock_chat_json, sample_data):
    """Test that semantic_review fails gracefully and escalates to human on API error."""
    # Mock LLM raising an exception
    mock_chat_json.side_effect = Exception("Service Unavailable")

    decision, router_result = sample_data
    result = semantic_review(decision, router_result)

    # 3. When Gemini API raises an exception
    assert result["supervisor_verdict"] == "ESCALATE_TO_HUMAN"
    assert result["bias_detected"] is True
    assert "Supervisor review failed" in result["bias_reason"]
    assert isinstance(result["review_timestamp"], str)
    assert result["features_flagged"] == []

@patch("core.supervisor.chat_json")
def test_semantic_review_malformed_json(mock_chat_json, sample_data):
    """Test handling of malformed JSON response from the LLM."""
    # Malformed JSON would have raised inside chat_json; supervisor catches and escalates.
    mock_chat_json.side_effect = ValueError("NOT A JSON OBJECT")

    decision, router_result = sample_data
    result = semantic_review(decision, router_result)

    # Should trigger the catch-all exception handler
    assert result["supervisor_verdict"] == "ESCALATE_TO_HUMAN"
    assert result["bias_detected"] is True
    assert "Supervisor review failed" in result["bias_reason"]

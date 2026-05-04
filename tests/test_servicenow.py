import pytest
import requests
from unittest.mock import patch, MagicMock
from core.servicenow import (
    create_incident,
    create_incident_mock,
    create_incident_with_fallback
)

@pytest.fixture
def sample_inputs():
    """Returns standard synthetic inputs for ServiceNow functions."""
    return {
        "decision": {
            "candidate_id": "CAND-TEST-999",
            "candidate_name": "Test Candidate",
            "timestamp": "2024-05-04T10:00:00Z"
        },
        "policy_result": {
            "rule_fired": "TEST_BIAS_RULE",
            "regulation_reference": "TEST-REG-101",
            "features_used": ["test_feature"]
        },
        "router_result": {
            "classification": "RED",
            "confidence": 0.88,
            "shap_scores": {"test_feature": 0.45}
        }
    }

def test_create_incident_mock_returns_correct_format(sample_inputs):
    """PART B: Verify mock function returns CREATED and a ticket ID."""
    result = create_incident_mock(**sample_inputs)
    assert result["status"] == "CREATED"
    assert "ticket_id" in result
    assert result["ticket_id"] is not None

def test_ticket_id_prefix(sample_inputs):
    """Requirement: Verify ticket_id starts with 'INC'."""
    result = create_incident_mock(**sample_inputs)
    assert result["ticket_id"].startswith("INC")

def test_fallback_uses_mock_in_development(sample_inputs, monkeypatch):
    """PART C: Verify auto-switch uses mock when ENVIRONMENT=development."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    # Using fallback should trigger mock response
    result = create_incident_with_fallback(**sample_inputs)
    assert result["status"] == "CREATED"
    assert result.get("_mock") is True

@patch("requests.post")
def test_create_incident_timeout_handling(mock_post, sample_inputs, monkeypatch):
    """PART A: Verify 5s timeout logic and status=TIMEOUT return."""
    monkeypatch.setenv("SERVICENOW_INSTANCE", "test.service-now.com")
    # Simulate a timeout exception
    mock_post.side_effect = requests.Timeout
    
    result = create_incident(**sample_inputs)
    
    assert result["status"] == "TIMEOUT"
    assert result["ticket_id"] is None
    assert "did not respond within 5 seconds" in result["error"]

@patch("requests.post")
def test_create_incident_connection_error_handling(mock_post, sample_inputs, monkeypatch):
    """PART A: Verify generic error handling (e.g. ConnectionError)."""
    monkeypatch.setenv("SERVICENOW_INSTANCE", "test.service-now.com")
    # Simulate a connection error
    mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")
    
    result = create_incident(**sample_inputs)
    
    assert result["status"] == "ERROR"
    assert result["ticket_id"] is None
    assert "Failed to connect" in result["error"]

@patch("requests.post")
def test_create_incident_success_response(mock_post, sample_inputs, monkeypatch):
    """PART A: Verify successful API response parsing."""
    monkeypatch.setenv("SERVICENOW_INSTANCE", "test.service-now.com")
    
    # Mock successful ServiceNow response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "result": {
            "number": "INC0005678",
            "sys_id": "sys_id_123"
        }
    }
    mock_post.return_value = mock_response
    
    result = create_incident(**sample_inputs)
    
    assert result["status"] == "CREATED"
    assert result["ticket_id"] == "INC0005678"
    assert "sys_id=sys_id_123" in result["url"]

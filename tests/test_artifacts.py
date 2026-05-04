import pytest
import json
import os
import shutil
from pathlib import Path
from core.artifact_engine import generate_artifact, save_artifact, verify_artifact

@pytest.fixture
def sample_data():
    decision = {
        "candidate_id": "CAND-123",
        "candidate_name": "Alice Smith",
        "decision_outcome": "APPROVE",
        "features_used": {"skill_score": 0.9, "experience": 5}
    }
    policy_result = {
        "result": "PASS",
        "violations": []
    }
    router_result = {
        "routing_classification": "GREEN",
        "confidence_score": 0.88,
        "shap_scores": {"skill_score": 0.4, "experience": 0.2},
        "model_version_hash": "v3-abc-123"
    }
    return decision, policy_result, router_result

@pytest.fixture(autouse=True)
def setup_tmp_dir(tmp_path, monkeypatch):
    """Ensure tests run in a temp directory so 'artifacts/' is isolated and cleaned up."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path

def test_generate_artifact_fields(sample_data):
    decision, policy, router = sample_data
    artifact = generate_artifact(decision, policy, router)
    
    required_fields = [
        "decision_id", "timestamp", "candidate_id", "candidate_name",
        "decision_outcome", "policy_result", "policy_violations",
        "policy_rule_cited", "regulation_reference", "routing_classification",
        "confidence_score", "features_used", "shap_scores",
        "model_version_hash", "servicenow_ticket_id", "artifact_hash"
    ]
    for field in required_fields:
        assert field in artifact

def test_artifact_hash_format(sample_data):
    decision, policy, router = sample_data
    artifact = generate_artifact(decision, policy, router)
    assert artifact["artifact_hash"].startswith("sha256:")
    # Verify it has a hex digest (64 chars after "sha256:")
    assert len(artifact["artifact_hash"].split(":")[1]) == 64

def test_verify_unmodified_artifact(sample_data):
    decision, policy, router = sample_data
    artifact = generate_artifact(decision, policy, router)
    path = save_artifact(artifact)
    assert verify_artifact(path) is True

def test_verify_tampered_artifact(sample_data):
    decision, policy, router = sample_data
    artifact = generate_artifact(decision, policy, router)
    path = save_artifact(artifact)
    
    # Tamper with the file
    with open(path, "r") as f:
        data = json.load(f)
    data["decision_outcome"] = "REJECT" if data["decision_outcome"] == "APPROVE" else "APPROVE"
    with open(path, "w") as f:
        json.dump(data, f)
        
    assert verify_artifact(path) is False

def test_red_routing_with_ticket_id(sample_data):
    decision, policy, router = sample_data
    router["routing_classification"] = "RED"
    ticket_id = "INC0001"
    artifact = generate_artifact(decision, policy, router, servicenow_ticket_id=ticket_id)
    assert artifact["routing_classification"] == "RED"
    assert artifact["servicenow_ticket_id"] == ticket_id

def test_green_routing_null_ticket_id(sample_data):
    decision, policy, router = sample_data
    router["routing_classification"] = "GREEN"
    artifact = generate_artifact(decision, policy, router)
    assert artifact["routing_classification"] == "GREEN"
    assert artifact["servicenow_ticket_id"] is None

def test_unique_artifacts_same_candidate(sample_data):
    decision, policy, router = sample_data
    art1 = generate_artifact(decision, policy, router)
    art2 = generate_artifact(decision, policy, router)
    
    assert art1["decision_id"] != art2["decision_id"]
    assert art1["artifact_hash"] != art2["artifact_hash"]
    # Timestamps should also differ slightly but ID is guaranteed unique
    assert art1["timestamp"] != art2["timestamp"] or art1["decision_id"] != art2["decision_id"]

def test_artifact_is_valid_json(sample_data):
    decision, policy, router = sample_data
    artifact = generate_artifact(decision, policy, router)
    path = save_artifact(artifact)
    
    with open(path, "r") as f:
        loaded_data = json.load(f)
    
    assert isinstance(loaded_data, dict)
    assert loaded_data["decision_id"] == artifact["decision_id"]

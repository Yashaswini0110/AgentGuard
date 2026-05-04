"""
tests/test_api.py
-----------------
Pytest tests for the AgentGuard v3 FastAPI application (api/main.py).

All external I/O is mocked at the api.main module boundary so no real LLM
calls, ServiceNow requests, or disk reads happen during the test run.

Endpoints tested
----------------
1.  GET  /health              → 200, {"status": "ok"}
2.  POST /decision (clean)    → 200, routing_classification present
3.  POST /decision (biased)   → routing_classification == "RED" (policy BLOCK)
4.  POST /decision            → artifact_hash present in response
5.  GET  /decisions           → 200, list (may be empty)
6.  GET  /drift               → 200, alert field present
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Suppress the httpx DeprecationWarning regarding the 'app' shortcut.
# This warning occurs because the installed version of TestClient uses a deprecated
# httpx calling pattern that cannot be fixed without a Starlette/FastAPI upgrade.
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated:DeprecationWarning")

# ---------------------------------------------------------------------------
# Import the FastAPI app
# ---------------------------------------------------------------------------
from api.main import app

# ---------------------------------------------------------------------------
# Shared stub data — mirrors the real function return shapes
# ---------------------------------------------------------------------------

_DECISION_STUB = {
    "candidate_id": "CAND-TEST-001",
    "candidate_name": "Test Candidate",
    "decision": "APPROVE",
    "confidence": 0.88,
    "reason": "Strong profile across all dimensions.",
    "features_used": ["years_of_experience", "skill_match_score", "interview_score"],
    "recommended_action": "PROCEED_TO_INTERVIEW",
}

_DECISION_STUB_BIASED = {
    **_DECISION_STUB,
    # policy_engine will fire INSTITUTION_TIER_PROXY_SOCIOECONOMIC
    "features_used": [
        "years_of_experience",
        "skill_match_score",
        "interview_score",
        "emotion_score",  # triggers EMOTION_SCORE_IN_HIRING_PROHIBITED → BLOCK → RED
    ],
}

_POLICY_PASS_STUB = {
    "passed": True,
    "violations": [],
    "recommended_action": "PROCEED",
}

_POLICY_BLOCK_STUB = {
    "passed": False,
    "violations": [
        {
            "rule_name": "EMOTION_SCORE_IN_HIRING_PROHIBITED",
            "severity": "RED",
            "regulation": "EU AI Act Article 5(1)(f) — Prohibited Practice",
            "reason": "Emotion recognition in employment contexts is prohibited.",
        }
    ],
    "recommended_action": "BLOCK",
}

_ROUTER_GREEN_STUB = {
    "risk_level": "GREEN",
    "confidence_score": 0.92,
    "shap_scores": {
        "years_of_experience": 0.15,
        "skill_match_score": 0.40,
        "interview_score": 0.30,
        "assessment_score": 0.10,
        "decision_confidence": 0.03,
        "feature_count": 0.02,
    },
    "model_version_hash": "sha256:testdeadbeef00001",
    "latency_ms": 12.3,
}

_ROUTER_YELLOW_STUB = {**_ROUTER_GREEN_STUB, "risk_level": "YELLOW", "confidence_score": 0.55}

_SUPERVISOR_STUB = {
    "supervisor_verdict": "APPROVE",
    "bias_detected": False,
    "bias_reason": None,
    "confidence": 0.91,
    "features_flagged": [],
    "review_timestamp": "2026-05-04T06:00:00+00:00",
}

_SERVICENOW_STUB = {
    "ticket_id": "INC0001234",
    "status": "CREATED",
    "url": "https://dev00000.service-now.com/nav_to.do?uri=incident.do?sys_id=mock-001",
    "error": None,
    "_mock": True,
}

_ARTIFACT_STUB: dict = {}  # populated dynamically by _make_artifact_stub()


def _make_artifact_stub(routing_classification: str = "GREEN") -> dict:
    """Return a realistic artifact dict like generate_artifact() would produce."""
    decision_id = str(uuid.uuid4())
    body = {
        "decision_id": decision_id,
        "timestamp": "2026-05-04T06:00:00+00:00",
        "candidate_id": "CAND-TEST-001",
        "candidate_name": "Test Candidate",
        "decision_outcome": "APPROVE",
        "policy_result": "PASS",
        "policy_violations": [],
        "policy_rule_cited": "NONE",
        "regulation_reference": "N/A",
        "routing_classification": routing_classification,
        "confidence_score": 0.92,
        "features_used": {"years_of_experience": 0.15},
        "shap_scores": {"years_of_experience": 0.15},
        "model_version_hash": "sha256:testdeadbeef00001",
        "servicenow_ticket_id": None,
    }
    import hashlib

    canonical = json.dumps(body, sort_keys=True)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    body["artifact_hash"] = f"sha256:{digest}"
    return body


# ---------------------------------------------------------------------------
# Candidate payloads for POST /decision
# ---------------------------------------------------------------------------

_CLEAN_CANDIDATE = {
    "candidate_id": "CAND-TEST-001",
    "name": "Test Candidate",
    "years_of_experience": 6,
    "skill_match_score": 0.88,
    "interview_score": 80.0,
    "assessment_score": 83.0,
    "career_gap_months": 0,
    "gender": "M",
    "institution_tier": 2,
}

_BIASED_CANDIDATE = {
    **_CLEAN_CANDIDATE,
    "candidate_id": "CAND-TEST-002",
    "name": "Biased Candidate",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """
    Module-scoped TestClient that patches all external pipeline calls for the
    entire test module. Individual tests can override specific patches if needed.
    """
    artifact_stub_green = _make_artifact_stub("GREEN")

    with (
        patch("api.main.make_hiring_decision", return_value=_DECISION_STUB) as _,
        patch("api.main.check_policy", return_value=_POLICY_PASS_STUB) as _,
        patch("api.main.classify_risk", return_value=_ROUTER_GREEN_STUB) as _,
        patch("api.main.semantic_review", return_value=_SUPERVISOR_STUB) as _,
        patch("api.main.create_incident_with_fallback", return_value=_SERVICENOW_STUB) as _,
        patch("api.main.generate_artifact", return_value=artifact_stub_green) as _,
        patch("api.main.save_artifact", return_value="/tmp/test_artifact.json") as _,
    ):
        with TestClient(app, raise_server_exceptions=True) as tc:
            yield tc


# ---------------------------------------------------------------------------
# Test 1 — GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_status_code_is_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_field_is_ok(self, client: TestClient):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_version_field_present(self, client: TestClient):
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"] == "3.1"


# ---------------------------------------------------------------------------
# Test 2 — POST /decision (clean candidate → GREEN / PASS)
# ---------------------------------------------------------------------------

class TestDecisionClean:
    def test_status_code_is_200(self, client: TestClient):
        response = client.post("/decision", json=_CLEAN_CANDIDATE)
        assert response.status_code == 200

    def test_routing_classification_present(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        assert "classification" in data

    def test_routing_classification_value(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        # With our GREEN stub the classification must be GREEN
        assert data["classification"] == "GREEN"

    def test_policy_blocked_is_false(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        assert data["policy_blocked"] is False

    def test_total_latency_ms_present(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        assert "total_latency_ms" in data
        assert isinstance(data["total_latency_ms"], (int, float))

    def test_decision_field_present(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        assert "decision" in data

    def test_artifact_field_present(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        assert "artifact" in data


# ---------------------------------------------------------------------------
# Test 3 — POST /decision with biased features → policy BLOCK → RED
# ---------------------------------------------------------------------------

class TestDecisionBiased:
    def test_red_when_policy_blocks(self):
        """
        When the policy engine returns BLOCK the pipeline forces RED
        regardless of what the risk router would have returned.
        """
        artifact_red = _make_artifact_stub("RED")

        with (
            patch("api.main.make_hiring_decision", return_value=_DECISION_STUB_BIASED),
            patch("api.main.check_policy", return_value=_POLICY_BLOCK_STUB),
            # classify_risk should NOT be called, but mock it defensively
            patch("api.main.classify_risk", return_value=_ROUTER_GREEN_STUB),
            patch("api.main.semantic_review", return_value=_SUPERVISOR_STUB),
            patch("api.main.create_incident_with_fallback", return_value=_SERVICENOW_STUB),
            patch("api.main.generate_artifact", return_value=artifact_red),
            patch("api.main.save_artifact", return_value="/tmp/test_red.json"),
        ):
            with TestClient(app, raise_server_exceptions=True) as tc:
                response = tc.post("/decision", json=_BIASED_CANDIDATE)

        assert response.status_code == 200
        data = response.json()
        assert data["classification"] == "RED"
        assert data["policy_blocked"] is True

    def test_servicenow_called_when_red(self):
        """ServiceNow must be invoked for RED decisions."""
        artifact_red = _make_artifact_stub("RED")
        sn_mock = MagicMock(return_value=_SERVICENOW_STUB)

        with (
            patch("api.main.make_hiring_decision", return_value=_DECISION_STUB_BIASED),
            patch("api.main.check_policy", return_value=_POLICY_BLOCK_STUB),
            patch("api.main.classify_risk", return_value=_ROUTER_GREEN_STUB),
            patch("api.main.semantic_review", return_value=_SUPERVISOR_STUB),
            patch("api.main.create_incident_with_fallback", sn_mock),
            patch("api.main.generate_artifact", return_value=artifact_red),
            patch("api.main.save_artifact", return_value="/tmp/test_red2.json"),
        ):
            with TestClient(app, raise_server_exceptions=True) as tc:
                tc.post("/decision", json=_BIASED_CANDIDATE)

        sn_mock.assert_called_once()

    def test_servicenow_result_in_response_when_red(self):
        artifact_red = _make_artifact_stub("RED")

        with (
            patch("api.main.make_hiring_decision", return_value=_DECISION_STUB_BIASED),
            patch("api.main.check_policy", return_value=_POLICY_BLOCK_STUB),
            patch("api.main.classify_risk", return_value=_ROUTER_GREEN_STUB),
            patch("api.main.semantic_review", return_value=_SUPERVISOR_STUB),
            patch("api.main.create_incident_with_fallback", return_value=_SERVICENOW_STUB),
            patch("api.main.generate_artifact", return_value=artifact_red),
            patch("api.main.save_artifact", return_value="/tmp/test_red3.json"),
        ):
            with TestClient(app, raise_server_exceptions=True) as tc:
                data = tc.post("/decision", json=_BIASED_CANDIDATE).json()

        assert data["servicenow_result"] is not None
        assert data["servicenow_result"]["ticket_id"] == "INC0001234"


# ---------------------------------------------------------------------------
# Test 4 — POST /decision → artifact_hash in response
# ---------------------------------------------------------------------------

class TestDecisionArtifactHash:
    def test_artifact_hash_present(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        artifact = data.get("artifact", {})
        assert "artifact_hash" in artifact

    def test_artifact_hash_starts_with_sha256(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        artifact_hash = data["artifact"]["artifact_hash"]
        assert artifact_hash.startswith("sha256:")

    def test_artifact_hash_non_empty(self, client: TestClient):
        data = client.post("/decision", json=_CLEAN_CANDIDATE).json()
        artifact_hash = data["artifact"]["artifact_hash"]
        # "sha256:" prefix + 64 hex chars
        assert len(artifact_hash) == len("sha256:") + 64


# ---------------------------------------------------------------------------
# Test 5 — GET /decisions → list (may be empty)
# ---------------------------------------------------------------------------

class TestListDecisions:
    def test_status_code_is_200(self, client: TestClient):
        response = client.get("/decisions")
        assert response.status_code == 200

    def test_artifacts_key_is_list(self, client: TestClient):
        data = client.get("/decisions").json()
        assert "artifacts" in data
        assert isinstance(data["artifacts"], list)

    def test_count_key_matches_list_length(self, client: TestClient):
        data = client.get("/decisions").json()
        assert data["count"] == len(data["artifacts"])

    def test_count_is_non_negative(self, client: TestClient):
        data = client.get("/decisions").json()
        assert data["count"] >= 0


# ---------------------------------------------------------------------------
# Test 6 — GET /drift → alert field present
# ---------------------------------------------------------------------------

class TestDrift:
    def test_status_code_is_200(self, client: TestClient):
        response = client.get("/drift")
        assert response.status_code == 200

    def test_alert_field_present(self, client: TestClient):
        data = client.get("/drift").json()
        assert "alert" in data

    def test_alert_is_bool(self, client: TestClient):
        data = client.get("/drift").json()
        assert isinstance(data["alert"], bool)

    def test_percentage_fields_present(self, client: TestClient):
        data = client.get("/drift").json()
        for field in ("green_pct", "yellow_pct", "red_pct", "total"):
            assert field in data, f"Missing drift field: {field}"

    def test_drift_with_mocked_check_drift(self):
        """
        Verify the drift endpoint correctly delegates to check_drift()
        with whatever classifications are read from disk.
        """
        expected = {
            "green_pct": 60.0,
            "yellow_pct": 20.0,
            "red_pct": 20.0,
            "total": 10,
            "alert": False,
        }
        with patch("api.main.check_drift", return_value=expected):
            with TestClient(app, raise_server_exceptions=True) as tc:
                data = tc.get("/drift").json()

        for key, val in expected.items():
            assert data[key] == val, f"Mismatch on key '{key}'"


# ---------------------------------------------------------------------------
# Test 7 — Bonus: invalid request body → 422
# ---------------------------------------------------------------------------

class TestDecisionValidation:
    def test_missing_required_field_returns_422(self, client: TestClient):
        bad_body = {k: v for k, v in _CLEAN_CANDIDATE.items() if k != "candidate_id"}
        response = client.post("/decision", json=bad_body)
        assert response.status_code == 422

    def test_skill_match_score_out_of_range_returns_422(self, client: TestClient):
        bad_body = {**_CLEAN_CANDIDATE, "skill_match_score": 1.5}
        response = client.post("/decision", json=bad_body)
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient):
        response = client.post("/decision", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 8 — Bonus: YELLOW path invokes supervisor
# ---------------------------------------------------------------------------

class TestDecisionYellow:
    def test_supervisor_called_when_yellow(self):
        artifact_yellow = _make_artifact_stub("YELLOW")
        supervisor_mock = MagicMock(return_value=_SUPERVISOR_STUB)

        with (
            patch("api.main.make_hiring_decision", return_value=_DECISION_STUB),
            patch("api.main.check_policy", return_value=_POLICY_PASS_STUB),
            patch("api.main.classify_risk", return_value=_ROUTER_YELLOW_STUB),
            patch("api.main.semantic_review", supervisor_mock),
            patch("api.main.create_incident_with_fallback", return_value=_SERVICENOW_STUB),
            patch("api.main.generate_artifact", return_value=artifact_yellow),
            patch("api.main.save_artifact", return_value="/tmp/test_yellow.json"),
        ):
            with TestClient(app, raise_server_exceptions=True) as tc:
                data = tc.post("/decision", json=_CLEAN_CANDIDATE).json()

        supervisor_mock.assert_called_once()
        assert data["classification"] == "YELLOW"
        assert data["supervisor_result"] is not None

    def test_supervisor_not_called_when_green(self, client: TestClient):
        """Module-scoped client uses GREEN stub — supervisor must NOT be called."""
        supervisor_mock = MagicMock(return_value=_SUPERVISOR_STUB)
        with patch("api.main.semantic_review", supervisor_mock):
            client.post("/decision", json=_CLEAN_CANDIDATE)

        # classify_risk returns GREEN → supervisor branch is skipped
        supervisor_mock.assert_not_called()

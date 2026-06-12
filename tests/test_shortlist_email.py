"""Tests for shortlist email helpers and API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.email import (
    artifact_is_shortlisted,
    candidate_email_from_artifact,
    candidate_job_role_from_artifact,
    personalize_rejection_message,
    personalize_shortlist_message,
    send_shortlist_email_with_fallback,
)

pytestmark = pytest.mark.filterwarnings(
    "ignore:The 'app' shortcut is now deprecated:DeprecationWarning"
)


def test_artifact_is_shortlisted_green():
    assert artifact_is_shortlisted(
        {"policy_result": "PASS", "routing_classification": "GREEN"}
    )


def test_artifact_is_shortlisted_tech_accept():
    assert artifact_is_shortlisted({"tech_review": {"decision": "ACCEPT"}})


def test_personalize_shortlist_message():
    body = "Dear [Candidate Name], re [Role Title]."
    out = personalize_shortlist_message(
        body, candidate_name="Ada Lovelace", role_title="Data Scientist"
    )
    assert out == "Dear Ada Lovelace, re Data Scientist."


def test_personalize_rejection_message():
    body = "Dear [Candidate Name], role [Role Title]. Reason: [REJECTION_REASON_OR_REVIEWER_COMMENT]"
    out = personalize_rejection_message(
        body,
        candidate_name="Jane",
        role_title="Data Scientist",
        rejection_reason="Skills gap on ML pipeline ownership.",
    )
    assert "Jane" in out
    assert "Data Scientist" in out
    assert "Skills gap on ML pipeline ownership." in out


def test_candidate_email_from_artifact():
    art = {"candidate_email": " Ada@test.com "}
    assert candidate_email_from_artifact(art) == "ada@test.com"


def test_send_mock_in_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    result = send_shortlist_email_with_fallback(
        to_email="test@example.com",
        subject="Hi",
        body="Hello",
    )
    assert result["status"] == "SENT"
    assert result.get("_mock") is True


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def green_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.chdir(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    decision_id = "11111111-1111-1111-1111-111111111111"
    artifact = {
        "decision_id": decision_id,
        "candidate_name": "Jane Doe",
        "candidate_email": "jane.doe@acme.io",
        "job_role": "Software Engineer",
        "policy_result": "PASS",
        "routing_classification": "GREEN",
    }
    (artifacts / f"{decision_id}.json").write_text(json.dumps(artifact), encoding="utf-8")
    return decision_id


def test_post_shortlist_email_mock(client: TestClient, green_artifact: str, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMAIL_FROM", "agentguard.hr@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "fake-app-password")

    res = client.post(
        "/shortlist/email",
        json={
            "decision_ids": [green_artifact],
            "subject": "Subject [Role Title]",
            "body": "Dear [Candidate Name],",
            "sender_id": "HR-COMPLIANCE-01",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sent"] == 1
    assert data["results"][0]["status"] == "SENT"

    art = json.loads(
        (Path("artifacts") / f"{green_artifact}.json").read_text(encoding="utf-8")
    )
    assert art.get("email_dispatch", {}).get("to") == "jane.doe@acme.io"


def test_post_shortlist_email_rejects_non_hr(client: TestClient, green_artifact: str):
    res = client.post(
        "/shortlist/email",
        json={
            "decision_ids": [green_artifact],
            "subject": "Hi",
            "body": "Body",
            "sender_id": "TECH-REVIEWER-01",
        },
    )
    assert res.status_code == 403


def test_post_shortlist_email_skips_missing_email(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    decision_id = "22222222-2222-2222-2222-222222222222"
    artifact = {
        "decision_id": decision_id,
        "candidate_name": "No Email",
        "policy_result": "PASS",
        "routing_classification": "GREEN",
    }
    (artifacts / f"{decision_id}.json").write_text(json.dumps(artifact), encoding="utf-8")

    res = client.post(
        "/shortlist/email",
        json={
            "decision_ids": [decision_id],
            "subject": "Hi",
            "body": "Body",
            "sender_id": "HR-COMPLIANCE-01",
        },
    )
    assert res.status_code == 200
    assert res.json()["skipped"] == 1


def test_human_reject_sends_rejection_email_mock(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMAIL_FROM", "agentguard.hr@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "fake-app-password")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    decision_id = "33333333-3333-3333-3333-333333333333"
    artifact = {
        "decision_id": decision_id,
        "candidate_name": "Rejected User",
        "candidate_email": "reject.me@acme.io",
        "job_role": "Frontend Developer",
        "policy_result": "PASS",
        "routing_classification": "RED",
    }
    (artifacts / f"{decision_id}.json").write_text(json.dumps(artifact), encoding="utf-8")

    res = client.post(
        f"/human-review/{decision_id}",
        json={
            "action": "REJECT",
            "reviewer_id": "HR-COMPLIANCE-01",
            "reason": "Policy concerns remain unresolved after review.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["rejection_email"]["status"] == "SENT"
    art = json.loads((artifacts / f"{decision_id}.json").read_text(encoding="utf-8"))
    assert art["rejection_email_dispatch"]["to"] == "reject.me@acme.io"
    assert "Policy concerns" in art["rejection_email_dispatch"]["reviewer_comment"]


def test_tech_reject_sends_rejection_email_mock(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMAIL_FROM", "agentguard.hr@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "fake-app-password")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    decision_id = "44444444-4444-4444-4444-444444444444"
    artifact = {
        "decision_id": decision_id,
        "candidate_name": "Tech Reject",
        "candidate_email": "tech.no@acme.io",
        "job_role": "Software Engineer",
        "policy_result": "PASS",
        "routing_classification": "YELLOW",
        "escalation": {"reviewer_id": "HR-COMPLIANCE-01", "note": "Needs tech sign-off"},
    }
    (artifacts / f"{decision_id}.json").write_text(json.dumps(artifact), encoding="utf-8")

    res = client.post(
        f"/tech-review/{decision_id}",
        json={
            "action": "REJECT",
            "reviewer_id": "TECH-REVIEWER-01",
            "note": "Insufficient depth in distributed systems experience.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["rejection_email"]["status"] == "SENT"
    art = json.loads((artifacts / f"{decision_id}.json").read_text(encoding="utf-8"))
    assert "distributed systems" in art["rejection_email_dispatch"]["reviewer_comment"]

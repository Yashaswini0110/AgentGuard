"""Bulk rows that fail ingest or governance still persist reviewable artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.batch_ranking import _persist_bulk_failure_governance_sync


@pytest.fixture()
def isolated_artifacts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_ingest_failure_artifact_has_policy_rule(isolated_artifacts_dir: Path) -> None:
    gov = _persist_bulk_failure_governance_sync(
        candidate_id="cand-test-1",
        candidate_name="Example Candidate",
        workflow_context={"bulk_session_id": "bulk-sess-1", "bulk_review_pending": True},
        failure_phase="ingest",
        failure_message="empty extraction",
    )
    assert gov.get("decision_id")
    art = gov.get("artifact") or {}
    assert art.get("policy_rule_cited") == "BULK_RESUME_INGEST_FAILED"
    assert art.get("routing_classification") == "RED"
    wc = art.get("workflow_context") or {}
    assert wc.get("bulk_processing_failure") is True
    assert wc.get("bulk_failure_phase") == "ingest"


def test_pipeline_failure_artifact_rule_name(isolated_artifacts_dir: Path) -> None:
    gov = _persist_bulk_failure_governance_sync(
        candidate_id="cand-test-2",
        candidate_name="Other",
        workflow_context=None,
        failure_phase="pipeline",
        failure_message="timeout",
    )
    art = gov.get("artifact") or {}
    assert art.get("policy_rule_cited") == "BULK_GOVERNANCE_PIPELINE_FAILED"

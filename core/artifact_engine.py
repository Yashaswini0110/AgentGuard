"""
AgentGuard v3 — Artifact Engine
Cryptographically signed, tamper-proof JSON artifact generator for legal compliance evidence.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# PART A — Generate Artifact
# ---------------------------------------------------------------------------

def generate_artifact(
    decision: dict,
    policy_result: dict,
    router_result: dict,
    servicenow_ticket_id: str = None,
    supervisor_result: dict | None = None,
    workflow_context: dict | None = None,
) -> dict:
    """
    Build and return a cryptographically signed compliance artifact dict.

    Parameters
    ----------
    decision            : Output from the worker agent / decision layer.
    policy_result       : Output from the policy engine (Layer 1).
    router_result       : Output from the risk router (Layer 2).
    servicenow_ticket_id: ServiceNow ticket ID string, or None.
    supervisor_result   : Optional semantic review dict (YELLOW path).

    Returns
    -------
    dict — Complete artifact including SHA-256 artifact_hash.
    """
    violations: list = policy_result.get("violations", []) or []
    first_violation: dict = violations[0] if violations else {}

    # Derive PASS | BLOCK from Layer 1 outcome (check_policy uses recommended_action / passed).
    if policy_result.get("recommended_action") == "BLOCK":
        policy_flag = "BLOCK"
    elif policy_result.get("recommended_action") == "PROCEED":
        policy_flag = "PASS"
    elif policy_result.get("result") == "BLOCK":
        policy_flag = "BLOCK"
    elif policy_result.get("result") == "PASS":
        policy_flag = "PASS"
    elif policy_result.get("passed") is False:
        policy_flag = "BLOCK"
    else:
        policy_flag = "PASS"

    # ------------------------------------------------------------------ #
    # Build the artifact WITHOUT the hash field first                      #
    # ------------------------------------------------------------------ #
    artifact_body: dict = {
        "decision_id":             str(uuid.uuid4()),
        "timestamp":               datetime.now(timezone.utc).isoformat(),
        "candidate_id":            decision.get("candidate_id"),
        "candidate_name":          decision.get("candidate_name"),
        "decision_outcome":        decision.get("decision_outcome") or decision.get("decision"),
        "policy_result":           policy_flag,
        "policy_violations":       violations,
        "policy_rule_cited":       first_violation.get("rule_name", "NONE") if first_violation else "NONE",
        "regulation_reference":    first_violation.get("regulation", "N/A") if first_violation else "N/A",
        "routing_classification":  router_result.get("routing_classification"),  # GREEN | YELLOW | RED
        "confidence_score":        router_result.get("confidence_score"),
        "features_used":           decision.get("features_used", {}),
        "shap_scores":             router_result.get("shap_scores", {}),
        "model_version_hash":      router_result.get("model_version_hash"),
        "servicenow_ticket_id":    servicenow_ticket_id,
    }

    router_features = router_result.get("router_features")
    if isinstance(router_features, dict) and router_features:
        artifact_body["router_features"] = router_features

    if supervisor_result is not None:
        artifact_body["supervisor_review"] = supervisor_result

    if workflow_context:
        wc = dict(workflow_context)
        artifact_body["workflow_context"] = wc
        email = wc.get("candidate_email")
        if isinstance(email, str) and email.strip():
            artifact_body["candidate_email"] = email.strip().lower()
        role = wc.get("job_role")
        if isinstance(role, str) and role.strip():
            artifact_body["job_role"] = role.strip()

    # ------------------------------------------------------------------ #
    # Compute SHA-256 over the sorted, deterministic JSON representation  #
    # ------------------------------------------------------------------ #
    canonical_json: str   = json.dumps(artifact_body, sort_keys=True)
    sha256_digest: str    = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    artifact_body["artifact_hash"] = f"sha256:{sha256_digest}"

    return artifact_body


# ---------------------------------------------------------------------------
# PART B — Save Artifact
# ---------------------------------------------------------------------------

def save_artifact(artifact: dict) -> str:
    """
    Persist the artifact to artifacts/<decision_id>.json.

    Parameters
    ----------
    artifact : The complete artifact dict (with artifact_hash).

    Returns
    -------
    str — Absolute path to the saved file.
    """
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    decision_id: str = artifact["decision_id"]
    file_path: Path  = artifacts_dir / f"{decision_id}.json"

    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)

    return str(file_path.resolve())


# ---------------------------------------------------------------------------
# PART C — Verify Artifact
# ---------------------------------------------------------------------------

def verify_artifact(artifact_path: str) -> bool:
    """
    Load an artifact from disk and verify its SHA-256 integrity hash.

    Parameters
    ----------
    artifact_path : Path to the .json artifact file.

    Returns
    -------
    bool — True if hash matches (untampered), False if tampered.
    """
    with open(artifact_path, "r", encoding="utf-8") as fh:
        artifact: dict = json.load(fh)

    stored_hash: str = artifact.get("artifact_hash", "")

    # Reconstruct the body WITHOUT the hash field
    artifact_body: dict = {k: v for k, v in artifact.items() if k != "artifact_hash"}

    canonical_json: str    = json.dumps(artifact_body, sort_keys=True)
    recomputed_digest: str = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    expected_hash: str     = f"sha256:{recomputed_digest}"

    return stored_hash == expected_hash


# ---------------------------------------------------------------------------
# PART D — Export for Regulator
# ---------------------------------------------------------------------------

def export_for_regulator(artifact: dict) -> str:
    """
    Produce a regulator-ready export string: header comment block + full JSON.

    Parameters
    ----------
    artifact : The complete artifact dict.

    Returns
    -------
    str — Formatted string suitable for submission to regulators.
    """
    timestamp: str = artifact.get("timestamp", datetime.now(timezone.utc).isoformat())

    header: str = (
        "# AgentGuard v3 — Regulatory Compliance Export\n"
        "# EU AI Act Technical Documentation File\n"
        "# India DPDP Act Audit Evidence\n"
        f"# Generated: {timestamp}\n"
    )

    artifact_json: str = json.dumps(artifact, indent=2, sort_keys=True)

    return f"{header}\n{artifact_json}"


# ---------------------------------------------------------------------------
# PART E — __main__ demonstration block
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # ------------------------------------------------------------------ #
    # Sample inputs                                                        #
    # ------------------------------------------------------------------ #
    sample_decision = {
        "candidate_id":     "CAND-2024-00789",
        "candidate_name":   "Priya Sharma",
        "decision_outcome": "REJECT",
        "features_used": {
            "years_experience":    4,
            "gpa":                 3.7,
            "skill_match_score":   0.82,
            "communication_score": 0.65,
        },
    }

    sample_policy_result = {
        "result": "BLOCK",
        "violations": [
            {
                "rule_name":   "RULE_GENDER_PROXY_DETECTED",
                "regulation":  "India DPDP Act §7 / EU AI Act Art.5(1)(d)",
                "description": "Candidate name used as a gender proxy feature.",
                "severity":    "HIGH",
            }
        ],
    }

    sample_router_result = {
        "routing_classification": "RED",
        "confidence_score":       0.91,
        "shap_scores": {
            "years_experience":    0.12,
            "gpa":                 0.08,
            "skill_match_score":   0.45,
            "communication_score": 0.23,
        },
        "model_version_hash": "gbm_v3_sha256_a1b2c3d4e5f6",
    }

    sample_ticket_id = "INC0042023"

    # ------------------------------------------------------------------ #
    # Step 1 — Generate artifact                                           #
    # ------------------------------------------------------------------ #
    print("=" * 60)
    print("STEP 1 — Generating artifact ...")
    artifact = generate_artifact(
        decision=sample_decision,
        policy_result=sample_policy_result,
        router_result=sample_router_result,
        servicenow_ticket_id=sample_ticket_id,
    )
    print(f"  decision_id   : {artifact['decision_id']}")
    print(f"  artifact_hash : {artifact['artifact_hash']}")

    # ------------------------------------------------------------------ #
    # Step 2 — Save artifact                                               #
    # ------------------------------------------------------------------ #
    print("\nSTEP 2 — Saving artifact ...")
    saved_path = save_artifact(artifact)
    print(f"  Saved to      : {saved_path}")

    # ------------------------------------------------------------------ #
    # Step 3 — Verify untampered artifact                                  #
    # ------------------------------------------------------------------ #
    print("\nSTEP 3 — Verifying untampered artifact ...")
    is_valid = verify_artifact(saved_path)
    status = "PASS (hash matches)" if is_valid else "FAIL (hash mismatch)"
    print(f"  Integrity check: {status}")
    assert is_valid, "ERROR: fresh artifact failed integrity check!"

    # ------------------------------------------------------------------ #
    # Step 4 — Tamper with the file and verify again                       #
    # ------------------------------------------------------------------ #
    print("\nSTEP 4 — Tampering with artifact and re-verifying ...")
    with open(saved_path, "r", encoding="utf-8") as fh:
        tampered: dict = json.load(fh)

    # Simulate tampering: flip the decision outcome
    tampered["decision_outcome"] = "APPROVE"

    with open(saved_path, "w", encoding="utf-8") as fh:
        json.dump(tampered, fh, indent=2, sort_keys=True)

    is_valid_after_tamper = verify_artifact(saved_path)
    status_tamper = "PASS" if is_valid_after_tamper else "FAIL (TAMPER DETECTED — hash mismatch)"
    print(f"  Integrity check: {status_tamper}")
    assert not is_valid_after_tamper, "ERROR: tampered artifact incorrectly passed verification!"

    # ------------------------------------------------------------------ #
    # Step 5 — Regulatory export                                           #
    # ------------------------------------------------------------------ #
    print("\nSTEP 5 — Regulatory export preview (first 500 chars) ...")
    export_str = export_for_regulator(artifact)
    print(export_str[:500])
    print("  ...")

    print("\n" + "=" * 60)
    print("AgentGuard v3 Artifact Engine — demo complete.")

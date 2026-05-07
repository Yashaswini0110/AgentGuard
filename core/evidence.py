"""
Build provenance/evidence payloads for Layer-1 governance checks.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_evidence(
    canonical_inputs: dict[str, Any],
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Classify observable input fields as SAFE | CONTROLLED | PROHIBITED_CONTEXT
    and attach a hash of canonical JSON for auditing.
    """
    classification: dict[str, str] = {}
    cand = {k: v for k, v in canonical_inputs.items() if not str(k).startswith("_")}

    def _cls(field: str) -> str:
        if field in (
            "candidate_id",
            "name",
            "years_of_experience",
            "skill_match_score",
            "interview_score",
            "assessment_score",
        ):
            return "SAFE"
        if field in ("career_gap_months", "institution_tier"):
            return "CONTROLLED"
        if field in (
            "gender",
            "applicant_surname",
            "home_district",
            "village_code",
            "emotion_score",
        ):
            return "PROHIBITED_CONTEXT"
        return "CONTROLLED"

    for key in cand:
        classification[key] = _cls(str(key))

    canonical_json = json.dumps(cand, sort_keys=True)
    payload_hash = _sha256_text(canonical_json)

    return {
        "canonical_inputs": cand,
        "input_classification": classification,
        "raw_payload_sha256": payload_hash,
        "tenant_id": tenant_id,
    }


def semantic_context_for_supervisor(
    canonical_inputs: Optional[dict[str, Any]],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Structured context bundle for supervised review calls."""
    cand = canonical_inputs or {}
    return {
        "subject_profile": {
            k: v
            for k, v in cand.items()
            if k
            not in ("_scenario_demo_inject_feature",)
            and not str(k).startswith("_")
        },
        "agent_claim_features": decision.get("features_used") or [],
        "agent_decision": decision.get("decision"),
        "agent_confidence": decision.get("confidence"),
        "agent_rationale": decision.get("reason"),
    }

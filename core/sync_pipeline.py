"""
Synchronous AgentGuard governance pipeline (single candidate).

Extracted so batch ranking and POST /decision share one implementation path.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from core.worker_agent import make_hiring_decision
from core.policy_engine import check_policy
from core.risk_router import classify_risk
from core.supervisor import semantic_review
from core.servicenow import create_incident_with_fallback
from core.artifact_engine import generate_artifact, save_artifact

logger = logging.getLogger("agentguard.sync_pipeline")


def sync_governance_pipeline(
    candidate: dict[str, Any],
    *,
    workflow_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run worker → policy → risk router → supervisor (YELLOW) → ServiceNow (RED) → artifact.

    Returns keys aligned with POST /decision response (minus FastAPI wrappers).
    """
    pipeline_start = time.perf_counter()

    try:
        decision = make_hiring_decision(candidate)
    except Exception as exc:
        logger.error("worker_agent failed: %s", exc)
        raise

    decision.setdefault("candidate_name", candidate.get("name"))

    try:
        policy_result = check_policy(decision, raw_input=str(candidate))
    except Exception as exc:
        logger.error("policy_engine failed: %s", exc)
        raise

    policy_blocked = policy_result.get("recommended_action") == "BLOCK"

    router_result: dict[str, Any] = {}
    classification = "RED"

    if not policy_blocked:
        features_used = decision.get("features_used") or []
        # LLM-produced feature lists may be inflated; overly high counts correlate with RED in router training.
        feature_count_raw = len(features_used) if isinstance(features_used, list) else 0
        feature_count_bounded = max(1, min(int(feature_count_raw), 10))
        router_input = {
            "years_of_experience": candidate.get("years_of_experience", 0),
            "skill_match_score": candidate.get("skill_match_score", 0.0),
            "interview_score": candidate.get("interview_score", 0.0),
            "assessment_score": candidate.get("assessment_score", 0.0),
            "decision_confidence": decision.get("confidence", 0.5),
            "feature_count": float(feature_count_bounded),
        }
        try:
            router_result = classify_risk(router_input)
            classification = router_result.get("risk_level", "RED")
        except Exception as exc:
            logger.error("risk_router failed: %s", exc)
            router_result = {
                "risk_level": "RED",
                "confidence_score": 0.0,
                "shap_scores": {},
                "model_version_hash": "unknown",
                "latency_ms": 0.0,
                "error": str(exc),
            }
            classification = "RED"

    normalised_router = {
        "routing_classification": router_result.get("risk_level", classification),
        "confidence_score": router_result.get("confidence_score", 0.0),
        "shap_scores": router_result.get("shap_scores", {}),
        "model_version_hash": router_result.get("model_version_hash", "unknown"),
    }
    if not policy_blocked:
        # Persist the router's raw input features so this decision is retrainable
        # later (F5 retrain on accumulated artifacts).
        normalised_router["router_features"] = router_input
    if policy_blocked:
        normalised_router["routing_classification"] = "RED"

    supervisor_result: Optional[dict[str, Any]] = None
    if classification == "YELLOW":
        try:
            supervisor_result = semantic_review(decision, router_result)
        except Exception as exc:
            logger.error("supervisor failed: %s", exc)
            supervisor_result = {
                "supervisor_verdict": "ESCALATE_TO_HUMAN",
                "bias_detected": True,
                "bias_reason": f"Supervisor unavailable: {exc}",
                "confidence": 0.0,
                "features_flagged": [],
            }

    servicenow_result: Optional[dict[str, Any]] = None
    ticket_id: Optional[str] = None

    is_red = classification == "RED" or policy_blocked
    if is_red:
        try:
            servicenow_result = create_incident_with_fallback(decision, policy_result, normalised_router)
            ticket_id = servicenow_result.get("ticket_id")
        except Exception as exc:
            logger.error("servicenow failed: %s", exc)
            servicenow_result = {
                "ticket_id": None,
                "status": "ERROR",
                "url": None,
                "error": str(exc),
            }

    artifact = generate_artifact(
        decision=decision,
        policy_result=policy_result,
        router_result=normalised_router,
        servicenow_ticket_id=ticket_id,
        supervisor_result=supervisor_result,
        workflow_context=workflow_context,
    )
    artifact_path = save_artifact(artifact)

    total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)

    return {
        "decision_id": artifact["decision_id"],
        "classification": classification,
        "policy_blocked": policy_blocked,
        "decision": decision,
        "policy_result": policy_result,
        "router_result": router_result,
        "supervisor_result": supervisor_result,
        "servicenow_result": servicenow_result,
        "artifact": artifact,
        "artifact_path": artifact_path,
        "total_latency_ms": total_latency_ms,
        "normalised_router": normalised_router,
    }

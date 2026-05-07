"""
Shared governance pipeline orchestration (v1 /decision and v2 /v2/evaluate).

Kept in one module so FastAPI routes stay thin and pytest can patch a single
namespace (``api.pipeline``).
"""

from __future__ import annotations

import datetime
import logging
import time
from typing import Any, Optional

from core.artifact_engine import generate_artifact, save_artifact
from core.evidence import build_evidence
from core.policy_engine import check_policy
from core.risk_router import classify_risk
from core.servicenow import create_incident_with_fallback
from core.supervisor import semantic_review
from core.worker_agent import make_hiring_decision

logger = logging.getLogger("agentguard.pipeline")


def _normalise_router_result(
    router_result: dict,
    policy_blocked: bool,
    fallback_class: str,
) -> dict:
    normalised: dict[str, Any] = {
        "routing_classification": router_result.get("risk_level", fallback_class),
        "confidence_score": float(router_result.get("confidence_score", 0.0) or 0.0),
        "shap_scores": router_result.get("shap_scores", {}) or {},
        "model_version_hash": router_result.get("model_version_hash", "unknown"),
    }
    if policy_blocked:
        normalised["routing_classification"] = "RED"
    return normalised


def run_candidate_pipeline(
    candidate: dict[str, Any],
    *,
    adapter_id: str = "hiring_demo_v1",
    agent_id: str = "hiring_worker_v1",
) -> dict[str, Any]:
    """
    Execute the full governance pipeline for a structured subject profile.

    Returns a dict suitable for JSON responses (includes ``artifact`` and
    latency). Internal-only keys are stripped from the candidate payload before
    invoking the worker agent.
    """
    pipeline_start = time.perf_counter()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    raw_candidate = dict(candidate)
    inject_feature = raw_candidate.pop("_scenario_demo_inject_feature", None)

    governance_events: list[dict[str, Any]] = [
        {"phase": "ingress.received", "at": now, "detail": {"adapter": adapter_id}},
    ]

    try:
        decision: dict[str, Any] = make_hiring_decision(
            raw_candidate,
            inject_prohibited_feature=inject_feature,
        )
    except Exception as exc:  # noqa: BLE001 — propagate as HTTP 502 from route
        logger.error("worker_agent failed: %s", exc)
        raise

    decision.setdefault("candidate_name", raw_candidate.get("name"))

    evidence = build_evidence(raw_candidate)

    governance_events.append(
        {
            "phase": "evidence.bound",
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "detail": {"raw_payload_sha256": evidence.get("raw_payload_sha256")},
        }
    )

    try:
        policy_result: dict[str, Any] = check_policy(
            decision,
            raw_input=str(raw_candidate),
            canonical_inputs=raw_candidate,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("policy_engine failed: %s", exc)
        raise

    governance_events.append(
        {
            "phase": "policy.evaluated",
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "detail": {
                "passed": policy_result.get("passed"),
                "recommended_action": policy_result.get("recommended_action"),
                "violation_count": len(policy_result.get("violations") or []),
            },
        }
    )

    policy_blocked = policy_result.get("recommended_action") == "BLOCK"

    router_result: dict[str, Any] = {}
    classification: str = "RED"
    router_features: Optional[dict[str, Any]] = None
    router_probabilities: Optional[dict[str, Any]] = None
    shap_explained_class: Optional[str] = None
    router_skipped_reason: Optional[str] = None

    if not policy_blocked:
        router_input: dict[str, Any] = {
            "years_of_experience": raw_candidate.get("years_of_experience", 0),
            "skill_match_score": raw_candidate.get("skill_match_score", 0.0),
            "interview_score": raw_candidate.get("interview_score", 0.0),
            "assessment_score": raw_candidate.get("assessment_score", 0.0),
            "decision_confidence": decision.get("confidence", 0.5),
            "feature_count": len(decision.get("features_used") or []),
        }
        router_features = router_input
        try:
            router_result = classify_risk(router_input)
            classification = router_result.get("risk_level", "RED")
            router_probabilities = router_result.get("class_probabilities") or None
            shap_explained_class = router_result.get("shap_explained_class") or classification
        except Exception as exc:  # noqa: BLE001
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
            router_probabilities = None
            shap_explained_class = None

        governance_events.append(
            {
                "phase": "risk_router.evaluated",
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "detail": {"classification": classification},
            }
        )

    normalised_router = _normalise_router_result(
        router_result,
        policy_blocked,
        classification,
    )
    if policy_blocked:
        router_skipped_reason = "POLICY_BLOCK"

    supervisor_result: Optional[dict[str, Any]] = None
    if classification == "YELLOW" and not policy_blocked:
        try:
            supervisor_result = semantic_review(decision, router_result, raw_candidate)
        except Exception as exc:  # noqa: BLE001
            logger.error("supervisor failed: %s", exc)
            supervisor_result = {
                "supervisor_verdict": "ESCALATE_TO_HUMAN",
                "bias_detected": True,
                "bias_reason": f"Supervisor unavailable: {exc}",
                "confidence": 0.0,
                "features_flagged": [],
            }
        governance_events.append(
            {
                "phase": "supervisor.evaluated",
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "detail": {"verdict": supervisor_result.get("supervisor_verdict")},
            }
        )

    servicenow_result: Optional[dict[str, Any]] = None
    ticket_id: Optional[str] = None

    is_red = classification == "RED" or policy_blocked
    if is_red:
        try:
            servicenow_result = create_incident_with_fallback(
                decision,
                policy_result,
                normalised_router,
            )
            ticket_id = servicenow_result.get("ticket_id")
        except Exception as exc:  # noqa: BLE001
            logger.error("servicenow failed: %s", exc)
            servicenow_result = {
                "ticket_id": None,
                "status": "ERROR",
                "url": None,
                "error": str(exc),
            }

        governance_events.append(
            {
                "phase": "itsm.incident",
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "detail": {
                    "ticket_id": ticket_id,
                    "bridge_status": servicenow_result.get("status"),
                },
            }
        )

    agent_identity = {
        "agent_id": agent_id,
        "agent_version": "1.0.0",
        "adapter": adapter_id,
        "tenant_id": "default",
    }

    try:
        artifact = generate_artifact(
            decision=decision,
            policy_result=policy_result,
            router_result=normalised_router,
            servicenow_ticket_id=ticket_id,
            supervisor_result=supervisor_result,
            trace_id=None,
            agent_identity=agent_identity,
            evidence={
                "raw_payload_sha256": evidence.get("raw_payload_sha256"),
                "input_classification": evidence.get("input_classification"),
            },
            router_features=router_features,
            router_probabilities=router_probabilities,
            shap_explained_class=shap_explained_class,
            router_skipped_reason=router_skipped_reason,
            governance_events=governance_events
            + [
                {
                    "phase": "artifact.persist",
                    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "detail": {},
                },
            ],
        )
        artifact_path: str = save_artifact(artifact)
    except Exception as exc:  # noqa: BLE001
        logger.error("artifact_engine failed: %s", exc)
        raise

    total_latency_ms: float = round((time.perf_counter() - pipeline_start) * 1000, 2)

    logger.info(
        "Pipeline complete | decision_id=%s | classification=%s | latency=%.1fms",
        artifact["decision_id"],
        classification,
        total_latency_ms,
    )

    return {
        "decision_id": artifact["decision_id"],
        "trace_id": artifact.get("trace_id") or artifact["decision_id"],
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
        "evidence": evidence,
        "normalised_router": normalised_router,
    }

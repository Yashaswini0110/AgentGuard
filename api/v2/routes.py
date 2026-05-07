"""Versioned ingress + investigation trace endpoints."""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from api.pipeline import run_candidate_pipeline
from api.storage import ARTIFACTS_DIR, load_artifact
from api.v2 import schemas as v2schemas
router = APIRouter()


def _assemble_trace(decision_id: str) -> dict[str, Any]:
    artifact = load_artifact(decision_id)
    tid = artifact.get("trace_id") or artifact.get("decision_id") or decision_id
    ingress = {
        "trace_id": tid,
        "adapter": (artifact.get("agent_identity") or {}).get("adapter", "unknown"),
        "received_subject_id": artifact.get("candidate_id"),
        "received_at": artifact.get("timestamp"),
    }
    timeline = artifact.get("governance_events") or []
    router_block = {
        "risk_classification": artifact.get("routing_classification"),
        "confidence_score": artifact.get("confidence_score"),
        "shap_scores": artifact.get("shap_scores") or {},
        "model_version_hash": artifact.get("model_version_hash"),
        "router_features": artifact.get("router_features") or {},
        "router_probabilities": artifact.get("router_probabilities") or {},
        "shap_explained_class": artifact.get("shap_explained_class"),
        "router_skipped_reason": artifact.get("router_skipped_reason"),
    }
    itsm_block = (
        {}
        if not artifact.get("servicenow_ticket_id")
        else {
            "ticket_id": artifact.get("servicenow_ticket_id"),
            "status": "CREATED_OR_MOCKED",
        }
    )
    return {
        "trace_id": tid,
        "decision_id": artifact.get("decision_id"),
        "ingress_snapshot": ingress,
        "canonical_artifact_view": artifact,
        "normalized_decision": {
            "outcome": artifact.get("decision_outcome"),
            "candidate_id": artifact.get("candidate_id"),
            "candidate_name": artifact.get("candidate_name"),
        },
        "evidence": artifact.get("evidence") or {},
        "policy": {
            "summary": artifact.get("policy_result"),
            "violations": artifact.get("policy_violations") or [],
            "primary_rule": artifact.get("policy_rule_cited"),
            "regulation": artifact.get("regulation_reference"),
        },
        "router": router_block,
        "supervisor": artifact.get("supervisor_review"),
        "itsm": itsm_block,
        "timeline": timeline,
        "artifact_preview": {"artifact_hash": artifact.get("artifact_hash")},
    }


@router.get("/health", summary="v2 liveness")
async def v2_health() -> dict[str, str]:
    return {"status": "ok", "api_version": "2"}


@router.post("/evaluate", summary="Ingress evaluation (canonical trace)")
async def evaluate(body: v2schemas.EvaluateRequest) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    adapter = payload.pop("adapter", "hiring_demo_v1")
    inj = payload.pop("scenario_demo_inject_feature", None)
    if inj:
        payload["_scenario_demo_inject_feature"] = inj
    try:
        return run_candidate_pipeline(payload, adapter_id=adapter)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/traces/{decision_id}", summary="Investigation DTO")
async def get_trace(decision_id: str) -> dict[str, Any]:
    try:
        return _assemble_trace(decision_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/decisions/stream", summary="Paginated governance decisions")
async def decisions_stream(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        ARTIFACTS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    sliced = files[offset : offset + limit]
    artifacts: list[dict[str, Any]] = []
    for fp in sliced:
        try:
            with open(fp, encoding="utf-8") as fh:
                artifacts.append(json.load(fh))
        except Exception:  # noqa: BLE001
            pass

    next_offset: Optional[int]
    next_offset = offset + len(sliced) if len(sliced) == limit else None

    return {
        "count": len(artifacts),
        "offset": offset,
        "next_offset": next_offset,
        "artifacts": artifacts,
    }
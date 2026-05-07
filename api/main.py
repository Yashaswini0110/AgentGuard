"""
AgentGuard v3 — API Gateway
============================
FastAPI application that wires the full governance pipeline:

    worker_agent  →  policy_engine  →  risk_router
        →  supervisor (YELLOW)  →  servicenow (RED)
        →  artifact_engine  →  JSON response

Endpoints
---------
POST   /decision                  Run the full pipeline for one candidate.
GET    /health                    Liveness probe.
GET    /decisions                 List all saved artifact filenames.
GET    /decisions/{decision_id}   Fetch a single artifact by ID.
GET    /drift                     Drift report from the last 100 artifacts.
POST   /human-review/{decision_id} Record a human APPROVE / REJECT action.
GET    /artifacts/recent           Recent saved artifacts (full JSON).
POST   /escalate/{decision_id}     HR escalation to tech review.
POST   /tech-review/{decision_id} Tech reviewer ACCEPT / REJECT.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Core pipeline imports
# ---------------------------------------------------------------------------
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.pipeline import run_candidate_pipeline
from api.storage import ARTIFACTS_DIR, artifact_path, load_artifact, write_artifact_file
from api.v2.routes import router as v2_router
from core.artifact_engine import export_for_regulator, verify_artifact
from core.risk_router import check_drift
from core.resume_parser import extract_text_from_pdf, parse_resume

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("agentguard.api")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AgentGuard v3",
    description=(
        "Runtime governance control plane — pre-execution evaluation, traceable artifacts, oversight hooks."
    ),
    version="3.2",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(v2_router, prefix="/v2", tags=["v2"])

# ---------------------------------------------------------------------------
# CORS — allow all origins (required for Streamlit frontend)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request-timing middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "%-6s %-40s  →  %d  (%s ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    return response

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CandidateInput(BaseModel):
    candidate_id: str = Field(..., json_schema_extra={"example": "CAND-2024-001"})
    name: str = Field(..., json_schema_extra={"example": "Priya Sharma"})
    years_of_experience: float = Field(..., ge=0, json_schema_extra={"example": 5})
    skill_match_score: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.87})
    interview_score: float = Field(..., ge=0.0, json_schema_extra={"example": 78.5})
    assessment_score: float = Field(..., ge=0.0, json_schema_extra={"example": 82.0})
    
    # Bias-related / Prohibited fields (Optional)
    career_gap_months: Optional[int] = Field(None, ge=0)
    gender: Optional[str] = Field(None)
    institution_tier: Optional[int] = Field(None, ge=1, le=5)
    applicant_surname: Optional[str] = Field(None)
    home_district: Optional[str] = Field(None)
    village_code: Optional[str] = Field(None)
    emotion_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    scenario_demo_inject_feature: Optional[str] = Field(
        None,
        description="Scenario Lab only — append a prohibited feature name to the agent claims for policy demos.",
    )


class HumanReviewInput(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$", json_schema_extra={"example": "APPROVE"})
    reviewer_id: str = Field(..., json_schema_extra={"example": "HR-OFFICER-42"})
    reason: str = Field(..., json_schema_extra={"example": "Reviewed all evidence; decision is fair."})


class EscalateInput(BaseModel):
    reviewer_id: str = Field(..., json_schema_extra={"example": "HR-OFFICER-42"})
    note: str = Field("", json_schema_extra={"example": "Needs technical assessment on skills."})


class TechReviewInput(BaseModel):
    action: str = Field(..., pattern="^(ACCEPT|REJECT)$", json_schema_extra={"example": "ACCEPT"})
    reviewer_id: str = Field(..., json_schema_extra={"example": "TECH-LEAD-01"})
    note: str = Field("", json_schema_extra={"example": "Validated against job description."})


# ---------------------------------------------------------------------------
# Endpoint 1: POST /decision — full governance pipeline
# ---------------------------------------------------------------------------

@app.post("/decision", summary="Run the full AgentGuard governance pipeline (v1 shim)")
async def run_decision(candidate_input: CandidateInput):
    """
    Execute :func:`run_candidate_pipeline` for a structured subject profile.

    Maps ``scenario_demo_inject_feature`` to the Scenario Lab shim key internally.
    Prefer ``POST /v2/evaluate`` for new integrations.
    """
    candidate = candidate_input.model_dump()
    inj = candidate.pop("scenario_demo_inject_feature", None)
    if inj:
        candidate["_scenario_demo_inject_feature"] = inj
    try:
        return run_candidate_pipeline(candidate)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Endpoint 2: GET /health
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness probe")
async def health():
    """Returns service status and API version."""
    return {"status": "ok", "version": "3.2"}


# ---------------------------------------------------------------------------
# Endpoint 3: GET /decisions — list all saved artifacts
# ---------------------------------------------------------------------------

@app.get("/decisions", summary="List all saved artifact filenames")
async def list_decisions():
    """
    Returns a list of all artifact filenames (stem = decision_id) stored in
    the artifacts/ directory.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    filenames = sorted(p.name for p in ARTIFACTS_DIR.glob("*.json"))
    return {"count": len(filenames), "artifacts": filenames}


# ---------------------------------------------------------------------------
# Endpoint 4: GET /decisions/{decision_id} — fetch single artifact
# ---------------------------------------------------------------------------

@app.get("/decisions/{decision_id}", summary="Fetch artifact by decision_id")
async def get_decision(decision_id: str):
    """
    Load and return the compliance artifact JSON for the given decision_id.
    Returns 404 if the artifact does not exist.
    """
    artifact = load_artifact(decision_id)
    return artifact


@app.get("/decisions/{decision_id}/export", summary="Regulator-ready export (text)")
async def get_decision_export(decision_id: str):
    """
    Returns a regulator-ready export string (header comment block + JSON).
    """
    artifact = load_artifact(decision_id)
    return PlainTextResponse(export_for_regulator(artifact))


@app.post("/resume/parse", summary="Parse PDF resume against a job description")
async def resume_parse(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """
    Accepts a PDF resume and a job description, returns structured candidate JSON.
    Mirrors the Streamlit dashboard's resume parsing feature.
    """
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")
    try:
        pdf_bytes = await file.read()
        text = extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from this PDF.")
        parsed = parse_resume(text, job_description)
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=502, detail="Resume parser returned invalid JSON.")
        return parsed
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Resume parsing failed: {exc}")


@app.get("/artifacts/recent", summary="Load recent artifacts in one round-trip")
async def artifacts_recent(limit: int = 50):
    """
    Returns full artifact documents for the most recently modified JSON files,
    newest first (bounded by ``limit``, max 200).
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    cap = max(1, min(limit, 200))
    files = sorted(
        ARTIFACTS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:cap]
    artifacts: list[dict] = []
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as fh:
                artifacts.append(json.load(fh))
        except Exception:
            pass
    return {"count": len(artifacts), "artifacts": artifacts}


@app.post("/artifacts/{decision_id}/verify", summary="Verify artifact integrity (SHA-256)")
async def verify_artifact_endpoint(decision_id: str):
    path = artifact_path(decision_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact '{decision_id}' not found.")
    ok = verify_artifact(str(path.resolve()))
    return {"decision_id": decision_id, "integrity_verified": ok}


# ---------------------------------------------------------------------------
# Endpoint 5: GET /drift — distribution / drift report
# ---------------------------------------------------------------------------

@app.get("/drift", summary="Drift report from last 100 artifacts")
async def drift_report():
    """
    Reads the last 100 saved artifacts (sorted by filename, descending),
    extracts their routing_classification values, and calls check_drift()
    to produce a distribution / anomaly report.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Take the 100 most recently written files (sorted descending by name so
    # UUIDs with later timestamps appear first — good-enough approximation).
    artifact_files = sorted(ARTIFACTS_DIR.glob("*.json"), reverse=True)[:100]

    risk_levels: list[str] = []
    for fp in artifact_files:
        try:
            with open(fp, encoding="utf-8") as fh:
                art = json.load(fh)
            level = art.get("routing_classification")
            if level:
                risk_levels.append(level)
        except Exception:
            pass  # skip corrupt files

    drift = check_drift(risk_levels)
    drift["artifacts_analysed"] = len(risk_levels)
    return drift


# ---------------------------------------------------------------------------
# Endpoint 6: POST /human-review/{decision_id}
# ---------------------------------------------------------------------------

@app.post("/human-review/{decision_id}", summary="Record human APPROVE / REJECT on an artifact")
async def human_review(decision_id: str, body: HumanReviewInput):
    """
    Attach a human review record (action, reviewer_id, reason, timestamp) to
    an existing artifact and re-save it to disk.

    The artifact's ``human_review`` field is added / overwritten.
    Returns the updated artifact.
    """
    artifact = load_artifact(decision_id)

    artifact["human_review"] = {
        "action":      body.action,
        "reviewer_id": body.reviewer_id,
        "reason":      body.reason,
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    write_artifact_file(artifact)
    logger.info(
        "Human review recorded | decision_id=%s | action=%s | reviewer=%s",
        decision_id,
        body.action,
        body.reviewer_id,
    )

    return {"message": "Human review recorded.", "artifact": artifact}


@app.post("/escalate/{decision_id}", summary="HR escalation to technical review")
async def escalate_to_tech(decision_id: str, body: EscalateInput):
    """Record an HR escalation note on the artifact (for the Tech Review queue)."""
    artifact = load_artifact(decision_id)
    shap = artifact.get("shap_scores") or {}
    top = sorted(
        ((k, float(v)) for k, v in shap.items()),
        key=lambda kv: abs(kv[1]),
        reverse=True,
    )[:3]
    top_drivers = [k for k, _ in top]
    artifact["escalation"] = {
        "reviewer_id": body.reviewer_id,
        "note": body.note,
        "escalated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "top_shap_drivers": top_drivers,
    }
    write_artifact_file(artifact)
    logger.info("Escalation recorded | decision_id=%s | reviewer=%s", decision_id, body.reviewer_id)
    return {"message": "Escalation recorded.", "artifact": artifact}


@app.post("/tech-review/{decision_id}", summary="Technical reviewer ACCEPT / REJECT")
async def tech_review(decision_id: str, body: TechReviewInput):
    """Persist technical review outcome on the artifact (for shortlist workflow)."""
    artifact = load_artifact(decision_id)
    artifact["tech_review"] = {
        "decision": body.action,
        "reviewer_id": body.reviewer_id,
        "note": body.note,
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    write_artifact_file(artifact)
    logger.info(
        "Tech review recorded | decision_id=%s | action=%s | reviewer=%s",
        decision_id,
        body.action,
        body.reviewer_id,
    )
    return {"message": "Tech review recorded.", "artifact": artifact}


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

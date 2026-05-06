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
POST   /batch_rank                 Bulk ZIP ingest + parallel governance + merit rank.
POST   /batch_rank/stream          Same workflow with SSE progress events.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
import time as _agent_time
from pathlib import Path as _AgentPath

# ---------------------------------------------------------------------------
# Core pipeline imports
# ---------------------------------------------------------------------------
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.risk_router import check_drift
from core.sync_pipeline import sync_governance_pipeline
from core.artifact_engine import export_for_regulator
from core.resume_parser import extract_text_from_pdf, parse_resume
from core.batch_ranking import execute_batch_zip_ranking_async

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
        "AI Governance Platform — full pipeline: "
        "worker_agent → policy_engine → risk_router → supervisor → servicenow → artifact_engine"
    ),
    version="3.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

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
# Artifact directory helper
# ---------------------------------------------------------------------------
ARTIFACTS_DIR = Path("artifacts")
_AGENT_LOG_PATH = str(_AgentPath(__file__).resolve().parents[1] / "debug-924df7.log")

# #region agent log
# Create a single boot log line to prove logging works (no secrets).
try:
    payload = {
        "sessionId": "924df7",
        "runId": "pre-fix",
        "hypothesisId": "H0",
        "location": "api/main.py:module_init",
        "message": "API module imported",
        "data": {"cwd": os.getcwd(), "log_path": _AGENT_LOG_PATH},
        "timestamp": int(_agent_time.time() * 1000),
    }
    with open(_AGENT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
except Exception:
    pass
# #endregion


def _artifact_path(decision_id: str) -> Path:
    return ARTIFACTS_DIR / f"{decision_id}.json"


def _load_artifact(decision_id: str) -> dict:
    path = _artifact_path(decision_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact '{decision_id}' not found.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_artifact_file(artifact: dict) -> None:
    path = _artifact_path(artifact["decision_id"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)


def _clear_bulk_review_pending(artifact: dict) -> None:
    """After HR or tech action, stop surfacing GREEN bulk profiles solely for intake ack."""
    wc = artifact.get("workflow_context")
    if not isinstance(wc, dict) or not wc.get("bulk_review_pending"):
        return
    cleared = dict(wc)
    cleared["bulk_review_pending"] = False
    cleared["bulk_hr_cleared_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    artifact["workflow_context"] = cleared


# ---------------------------------------------------------------------------
# Endpoint 1: POST /decision — full governance pipeline
# ---------------------------------------------------------------------------

@app.post("/decision", summary="Run the full AgentGuard governance pipeline")
async def run_decision(candidate_input: CandidateInput):
    """
    Execute the complete pipeline for one candidate:

    1. **worker_agent** → AI hiring decision
    2. **policy_engine** → hard-rule governance check
    3. **risk_router** → GREEN / YELLOW / RED classification (skipped on BLOCK)
    4. **supervisor** → semantic bias review (YELLOW only)
    5. **servicenow** → incident ticket (RED only)
    6. **artifact_engine** → signed compliance artifact
    """
    candidate: dict = candidate_input.model_dump()
    try:
        payload = sync_governance_pipeline(candidate)
    except Exception as exc:
        logger.error("Governance pipeline failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Governance pipeline error: {exc}")

    logger.info(
        "Pipeline complete | decision_id=%s | classification=%s | latency=%.1fms",
        payload["decision_id"],
        payload["classification"],
        payload["total_latency_ms"],
    )

    return {
        "decision_id": payload["decision_id"],
        "classification": payload["classification"],
        "policy_blocked": payload["policy_blocked"],
        "decision": payload["decision"],
        "policy_result": payload["policy_result"],
        "router_result": payload["router_result"],
        "supervisor_result": payload["supervisor_result"],
        "servicenow_result": payload["servicenow_result"],
        "artifact": payload["artifact"],
        "artifact_path": payload["artifact_path"],
        "total_latency_ms": payload["total_latency_ms"],
    }


@app.post("/batch_rank", summary="Bulk resumes (ZIP), parallel governance, merit-ranked shortlist")
async def batch_rank(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    open_positions: int = Form(..., ge=1, le=5000),
):
    """
    ZIP must contain PDF and/or DOCX resumes. Ranking is deliberately independent of
    intra-archive ordering; ingestion order is randomized from a deterministic PRNG seed.
    """
    ctype = (file.content_type or "").lower()
    if "zip" not in ctype and not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=415, detail="Only application/zip uploads are accepted.")
    try:
        blob = await file.read()
        if len(blob) > 80 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="ZIP larger than 80MB is not accepted.")
        return await execute_batch_zip_ranking_async(blob, job_description=job_description, open_positions=int(open_positions))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("batch_rank failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Batch ranking failed: {exc}")


@app.post("/batch_rank/stream", summary="Same as /batch_rank with SSE progress framing")
async def batch_rank_stream(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    open_positions: int = Form(..., ge=1, le=5000),
):
    ctype = (file.content_type or "").lower()
    if "zip" not in ctype and not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=415, detail="Only application/zip uploads are accepted.")

    blob = await file.read()
    if len(blob) > 80 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="ZIP larger than 80MB is not accepted.")

    sentinel = object()
    queue: asyncio.Queue = asyncio.Queue()

    async def publish(ev: dict) -> None:
        await queue.put(ev)

    async def runner():
        try:
            result = await execute_batch_zip_ranking_async(
                blob,
                job_description=job_description,
                open_positions=int(open_positions),
                progress=publish,
            )
            await queue.put({"type": "result", "payload": result})
        except Exception as exc:
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(sentinel)

    async def event_iter():
        task = asyncio.create_task(runner())
        try:
            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                yield f"data: {json.dumps(item, default=str)}\n\n".encode("utf-8")
        finally:
            await task

    return StreamingResponse(event_iter(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Endpoint 2: GET /health
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness probe")
async def health():
    """Returns service status, version, and capability flags for the *running* process."""
    route_paths = {getattr(r, "path", "") for r in app.routes}
    return {
        "status": "ok",
        "version": "3.1",
        # Absolute path of the loaded module — if this is not your repo, the wrong process bound the port.
        "api_module_file": str(Path(__file__).resolve()),
        "batch_rank_available": "/batch_rank" in route_paths and "/batch_rank/stream" in route_paths,
    }


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
    artifact = _load_artifact(decision_id)
    return artifact


@app.get("/decisions/{decision_id}/export", summary="Regulator-ready export (text)")
async def get_decision_export(decision_id: str):
    """
    Returns a regulator-ready export string (header comment block + JSON).
    """
    artifact = _load_artifact(decision_id)
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
        # #region agent log
        # NOTE: Do not log secrets (API keys) or resume/JD contents.
        try:
            k_raw = os.getenv("GOOGLE_API_KEY")
            k = (k_raw or "").strip()
            payload = {
                "sessionId": "924df7",
                "runId": "pre-fix",
                "hypothesisId": "H2",
                "location": "api/main.py:resume_parse:entry",
                "message": "Resume parse request received",
                "data": {
                    "content_type": file.content_type,
                    "filename_present": bool(file.filename),
                    "job_description_len": len(job_description or ""),
                    "google_api_key_present": bool(k_raw),
                    "google_api_key_len": len(k),
                    "gemini_api_key_present": bool((os.getenv("GEMINI_API_KEY") or "").strip()),
                    "selected_key_source": ("GOOGLE_API_KEY" if k else ("GEMINI_API_KEY" if (os.getenv("GEMINI_API_KEY") or "").strip() else "NONE")),
                },
                "timestamp": int(_agent_time.time() * 1000),
            }
            with open(_AGENT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        # #endregion

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
    newest first (bounded by ``limit``, max 500).
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    cap = max(1, min(limit, 500))
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
    artifact = _load_artifact(decision_id)

    artifact["human_review"] = {
        "action":      body.action,
        "reviewer_id": body.reviewer_id,
        "reason":      body.reason,
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _clear_bulk_review_pending(artifact)

    _write_artifact_file(artifact)
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
    artifact = _load_artifact(decision_id)
    artifact["escalation"] = {
        "reviewer_id": body.reviewer_id,
        "note": body.note,
        "escalated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _clear_bulk_review_pending(artifact)
    _write_artifact_file(artifact)
    logger.info("Escalation recorded | decision_id=%s | reviewer=%s", decision_id, body.reviewer_id)
    return {"message": "Escalation recorded.", "artifact": artifact}


@app.post("/tech-review/{decision_id}", summary="Technical reviewer ACCEPT / REJECT")
async def tech_review(decision_id: str, body: TechReviewInput):
    """Persist technical review outcome on the artifact (for shortlist workflow)."""
    artifact = _load_artifact(decision_id)
    artifact["tech_review"] = {
        "decision": body.action,
        "reviewer_id": body.reviewer_id,
        "note": body.note,
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _clear_bulk_review_pending(artifact)
    _write_artifact_file(artifact)
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

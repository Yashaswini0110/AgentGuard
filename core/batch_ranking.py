"""
Bulk resume ingestion, parallel governance, merit-only ranking.

Application order MUST NOT influence final ordering; ranking keys are merit + governance-safe flags only.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import tempfile
import time
import uuid
import zipfile
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional, cast

from core.resume_parser import (
    coalesce_candidate_full_name,
    extract_resume_text_auto,
    guess_name_from_resume_header,
    humanize_resume_filename_stem,
    parse_resume_structured,
)
from core.job_match_scores import composite_match_scores
from core.artifact_engine import generate_artifact, save_artifact
from core.policy_engine import evaluate_pool_quota_rule
from core.sync_pipeline import sync_governance_pipeline

logger = logging.getLogger("agentguard.batch")


def _persist_bulk_failure_governance_sync(
    *,
    candidate_id: str,
    candidate_name: str,
    workflow_context: dict[str, Any] | None,
    failure_phase: str,
    failure_message: str,
) -> dict[str, Any]:
    """
    Persist a RED/BLOCK artifact when ingest or the governance mesh fails mid-batch.

    Skips ServiceNow — HR reviews the failure reason in the Review Queue without opening incidents per file.
    """
    wc = dict(workflow_context or {})
    wc["bulk_processing_failure"] = True
    wc["bulk_failure_phase"] = failure_phase
    wc["bulk_failure_detail"] = (failure_message or "")[:4000]

    rule_name = (
        "BULK_RESUME_INGEST_FAILED"
        if failure_phase == "ingest"
        else "BULK_GOVERNANCE_PIPELINE_FAILED"
    )
    policy_result: dict[str, Any] = {
        "recommended_action": "BLOCK",
        "violations": [
            {
                "rule_name": rule_name,
                "regulation": "AgentGuard bulk intake",
                "description": (failure_message or "")[:4000],
                "severity": "HIGH",
            }
        ],
    }
    router_result: dict[str, Any] = {
        "routing_classification": "RED",
        "confidence_score": 1.0,
        "shap_scores": {},
        "model_version_hash": "bulk_failure_v1",
    }
    decision: dict[str, Any] = {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "decision": "REJECT",
        "decision_outcome": "REJECT",
        "confidence": 0.0,
        "reason": ("Automated intake guard: " + (failure_message or ""))[:1500],
        "features_used": [],
        "recommended_action": "REJECT_APPLICATION",
    }
    artifact = generate_artifact(
        decision=decision,
        policy_result=policy_result,
        router_result=router_result,
        servicenow_ticket_id=None,
        supervisor_result=None,
        workflow_context=wc,
    )
    artifact_path = save_artifact(artifact)

    return {
        "decision_id": artifact["decision_id"],
        "classification": "RED",
        "policy_blocked": True,
        "decision": decision,
        "policy_result": policy_result,
        "router_result": router_result,
        "supervisor_result": None,
        "servicenow_result": None,
        "artifact": artifact,
        "artifact_path": artifact_path,
        "total_latency_ms": 0.0,
    }

BatchRankSSEMessage = dict[str, Any]

ProgressPublisher = Callable[[dict[str, Any]], Awaitable[None]]

_MAX_PARALLEL_CANDIDATES = 24
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=_MAX_PARALLEL_CANDIDATES)
    return _executor


def _governance_safe_for_ranking(
    policy_blocked: bool,
    classification: str,
    supervisor: dict[str, Any] | None,
) -> bool:
    if policy_blocked:
        return False
    cls = (classification or "").strip().upper()
    if cls == "RED":
        return False
    if cls != "YELLOW":
        return True
    verdict = (supervisor or {}).get("supervisor_verdict") or ""
    verdict = str(verdict).strip().upper()
    return verdict == "APPROVE"


def _merit_classification(
    composite: float,
    governance_safe: bool,
    policy_blocked: bool,
) -> tuple[str, str]:
    if (not governance_safe) or policy_blocked:
        return (
            "NOT_SCORED",
            "Merit score withheld because governance is not clear (policy BLOCK, RED risk, or supervisor non-approval).",
        )
    if composite >= 0.85:
        return ("STRONG_MATCH", "Composite score meets strong threshold with governance-safe signals.")
    if composite >= 0.70:
        return ("GOOD_MATCH", "Solid multi-signal alignment to the job description.")
    if composite >= 0.50:
        return ("BORDERLINE", "Partial alignment — requires human corroboration beyond automated screening.")
    return ("LOW_MATCH", "Below preferred match band — still eligible if governance is clear.")


async def _run_in_thread(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_get_executor(), lambda: fn(*args, **kwargs))


async def process_single_resume_candidate(
    *,
    rel_path: str,
    raw_bytes: bytes,
    job_description: str,
    semaphore: asyncio.Semaphore,
    progress: Optional[ProgressPublisher],
    workflow_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cid = str(uuid.uuid4())

    async def _emit(payload: dict[str, Any]) -> None:
        if progress:
            await progress(payload)

    await _emit({"type": "progress", "phase": "start", "candidate_id": cid, "file": rel_path})

    structured: dict[str, Any]
    extracted_text = ""
    try:
        extracted_text = cast(
            str,
            await _run_in_thread(extract_resume_text_auto, raw_bytes, Path(rel_path).name),
        )
        if not (extracted_text or "").strip():
            raise ValueError("empty extraction")

        async with semaphore:
            structured = cast(
                dict[str, Any],
                await asyncio.wait_for(
                    _run_in_thread(parse_resume_structured, extracted_text, job_description),
                    timeout=180.0,
                ),
            )
    except Exception as exc:
        logger.warning("ingest_failed file=%s err=%s", rel_path, exc)
        stem = Path(rel_path).stem
        display_name = humanize_resume_filename_stem(stem)
        gov = cast(
            dict[str, Any],
            await _run_in_thread(
                _persist_bulk_failure_governance_sync,
                candidate_id=cid,
                candidate_name=display_name,
                workflow_context=workflow_context,
                failure_phase="ingest",
                failure_message=str(exc),
            ),
        )
        await _emit({"type": "progress", "phase": "error", "candidate_id": cid, "file": rel_path, "error": str(exc)})
        return {
            "candidate_id": cid,
            "source_file": rel_path,
            "error": str(exc),
            "governance": gov,
            "_sort_governance_safe": False,
            "_composite": 0.0,
            "_classification": "REJECT",
            "_classification_reason": f"Resume ingestion or structuring failed: {exc}",
        }

    structured.setdefault("candidate_id", cid)
    structured["candidate_id"] = cid
    structured.setdefault("resume_text", extracted_text.strip())
    structured.setdefault("skills", structured.get("primary_skills") or [])
    structured.setdefault("years_of_experience", structured.get("years_of_experience") or 0)
    structured.setdefault("career_gap_months", structured.get("career_gap_months") or 0)

    stem = Path(rel_path).stem
    display_name = coalesce_candidate_full_name(structured)
    if not display_name:
        display_name = guess_name_from_resume_header(extracted_text)
    if not display_name:
        display_name = humanize_resume_filename_stem(stem)
    structured["full_name"] = display_name

    scores = composite_match_scores(structured, job_description)
    composite = float(scores["composite_score"])

    name = structured["full_name"]
    years = structured.get("years_of_experience")
    cand_for_pipeline = {
        "candidate_id": cid,
        "name": name,
        "years_of_experience": float(years or 0),
        "skill_match_score": float(scores["skill_match_score"]),
        "interview_score": float(round(100 * composite * 0.85, 2)),
        "assessment_score": float(round(100 * composite * 0.90, 2)),
        "career_gap_months": int(structured.get("career_gap_months") or 0),
        "gender": structured.get("gender"),
        "institution_tier": structured.get("institution_tier"),
        "applicant_surname": structured.get("applicant_surname"),
        "home_district": structured.get("home_district"),
        "village_code": structured.get("village_code"),
        "emotion_score": structured.get("emotion_score"),
    }

    gov: dict[str, Any]
    try:
        gov = cast(
            dict[str, Any],
            await asyncio.wait_for(
                _run_in_thread(
                    sync_governance_pipeline,
                    cand_for_pipeline,
                    workflow_context=workflow_context,
                ),
                timeout=240.0,
            ),
        )
    except Exception as exc:
        logger.error("pipeline_failed candidate=%s err=%s", cid, exc)
        gov = cast(
            dict[str, Any],
            await _run_in_thread(
                _persist_bulk_failure_governance_sync,
                candidate_id=cid,
                candidate_name=name,
                workflow_context=workflow_context,
                failure_phase="pipeline",
                failure_message=str(exc),
            ),
        )
        await _emit({"type": "progress", "phase": "pipeline_error", "candidate_id": cid, "file": rel_path})
        return {
            "candidate_id": cid,
            "source_file": rel_path,
            "structured": structured,
            "scores": scores,
            "error": str(exc),
            "governance": gov,
            "_sort_governance_safe": False,
            "_composite": composite,
            "_classification": "REJECT",
            "_classification_reason": f"Governance pipeline error — not rankable: {exc}",
        }

    classification = gov.get("classification") or ""
    policy_blocked = bool(gov.get("policy_blocked"))
    supervisor = gov.get("supervisor_result")
    gov_safe = _governance_safe_for_ranking(policy_blocked, str(classification), supervisor)
    merit_class, merit_reason = _merit_classification(composite, gov_safe, policy_blocked)

    # Down-rank composites for governance-unsafe profiles while preserving audit ordering fields.
    await _emit(
        {
            "type": "progress",
            "phase": "done",
            "candidate_id": cid,
            "file": rel_path,
            "classification_router": classification,
            "composite": composite,
        }
    )

    return {
        "candidate_id": cid,
        "source_file": rel_path,
        "structured": structured,
        "scores": scores,
        "governance": gov,
        "_sort_governance_safe": gov_safe,
        "_composite": composite,
        "_classification": merit_class,
        "_classification_reason": merit_reason,
    }


def build_ranked_response(
    *,
    job_role: str,
    job_description: str,
    open_positions: int,
    rows: list[dict[str, Any]],
    processing_time_ms: float,
    pool_total_files: int,
    bulk_session_id: str | None = None,
) -> dict[str, Any]:
    # Merit-only ordering: governance-safe first, then composite score.
    def _rank_key(row: dict[str, Any]) -> tuple[int, float, str]:
        safe = bool(row.get("_sort_governance_safe"))
        composite = float(row.get("_composite") or 0.0)
        cid = str(row.get("candidate_id") or "")
        return (1 if safe else 0, composite, cid)

    ordered = sorted(rows, key=_rank_key, reverse=True)

    merit_eligible_pool = sum(
        1
        for r in ordered
        if r.get("_sort_governance_safe")
        and float(r.get("_composite") or 0.0) >= 0.50
        and not r.get("error")
        and not (r.get("governance") or {}).get("policy_blocked")
    )
    can_fill = open_positions > 0 and merit_eligible_pool >= open_positions

    completed = 0
    for r in rows:
        gov = r.get("governance")
        if gov and isinstance(gov, dict) and gov.get("decision_id"):
            completed += 1

    quota = evaluate_pool_quota_rule(
        open_positions=int(open_positions),
        pool_total=int(pool_total_files),
        governance_completed=int(completed),
        can_fill_all_openings=bool(can_fill),
    )

    ranked: list[dict[str, Any]] = []
    for idx, row in enumerate(ordered, start=1):
        structured = row.get("structured") or {}
        scores = row.get("scores") or {}
        gov = row.get("governance") or {}
        artifact = (gov.get("artifact") or {}) if isinstance(gov, dict) else {}

        gov_safe = bool(row.get("_sort_governance_safe"))
        policy_blocked = bool(gov.get("policy_blocked"))

        gov_status = "CLEAR"
        if row.get("error"):
            gov_status = "BLOCKED"
        elif policy_blocked:
            gov_status = "BLOCKED"
        elif gov.get("classification") == "RED":
            gov_status = "BLOCKED"
        elif not gov_safe:
            gov_status = "CONDITIONAL_HOLD"
        if quota.get("tentative_hold") and gov_safe and idx <= open_positions:
            gov_status = "TENTATIVE_HOLD"

        first_viol = None
        pr = gov.get("policy_result") if isinstance(gov.get("policy_result"), dict) else {}
        viols = pr.get("violations") or []
        if viols:
            first_viol = viols[0]

        reasoning_parts = [
            row.get("_classification_reason") or "",
        ]
        if first_viol:
            reasoning_parts.append(f"Primary policy concern: {first_viol.get('rule_name')}.")

        ranked.append(
            {
                "rank": idx,
                "candidate_name": (
                    (structured.get("full_name") or "").strip()
                    or humanize_resume_filename_stem(Path(str(row.get("source_file") or "")).stem)
                ),
                "candidate_id": row.get("candidate_id"),
                "composite_score": float(row.get("_composite") or 0.0),
                "classification": row.get("_classification"),
                "governance_status": gov_status,
                "policy_rule": (first_viol or {}).get("rule_name"),
                "score_breakdown": {
                    "composite_score": float(scores.get("composite_score", 0.0)),
                    "skill_match_score": float(scores.get("skill_match_score", 0.0)),
                    "experience_score": float(scores.get("experience_score", 0.0)),
                    "semantic_similarity": float(scores.get("semantic_similarity", 0.0)),
                },
                "top_skills": (structured.get("skills") or [])[:10],
                "experience_summary": f"{structured.get('years_of_experience', 0)} yrs · {structured.get('current_role') or 'role unstated'}",
                "reasoning": " ".join(s for s in reasoning_parts if s).strip(),
                "artifact_reference": {
                    "decision_id": artifact.get("decision_id") or gov.get("decision_id"),
                    "artifact_path": gov.get("artifact_path"),
                    "routing_classification": gov.get("classification"),
                    "bulk_session_id": bulk_session_id,
                },
            }
        )

    payload = {
        "job_role": job_role or "Role",
        "job_description_digest": hashlib.sha1((job_description or "").encode("utf-8")).hexdigest()[:12],
        "total_candidates": int(pool_total_files),
        "open_positions": int(open_positions),
        "processing_time_ms": round(float(processing_time_ms), 2),
        "pool_quota_policy": quota,
        "ranked_candidates": ranked,
        "skipped_files": [],
    }
    if bulk_session_id:
        payload["bulk_session_id"] = bulk_session_id
    return payload


async def execute_batch_zip_ranking_async(
    zip_bytes: bytes,
    *,
    job_description: str,
    open_positions: int,
    concurrency: int = 16,
    progress: Optional[ProgressPublisher] = None,
) -> dict[str, Any]:
    jd = job_description or ""
    job_role = jd.strip().splitlines()[0][:180] if jd.strip() else "Open Role"

    bulk_session_id = str(uuid.uuid4())
    open_n = max(1, int(open_positions or 1))
    job_fingerprint = hashlib.sha256(
        zip_bytes + b"|" + str(open_n).encode() + jd.encode("utf-8", errors="replace")
    ).hexdigest()[:32]
    bulk_workflow_context: dict[str, Any] = {
        "ingestion_source": "bulk_zip_rank",
        "bulk_review_pending": True,
        "bulk_session_id": bulk_session_id,
        "bulk_job_fingerprint": job_fingerprint,
        "open_positions_requested": open_n,
    }

    t0 = time.perf_counter()
    skipped: list[dict[str, str]] = []
    extracted: dict[str, bytes] = {}

    digest_seed = zip_bytes[:256] + str(len(zip_bytes)).encode()
    seed = int(hashlib.sha256(digest_seed).hexdigest()[:8], 16)
    rnd = random.Random(seed)

    with tempfile.TemporaryDirectory(prefix="agentguard_batch_") as tmp:
        zp = Path(tmp) / "upload.zip"
        zp.write_bytes(zip_bytes)
        try:
            with zipfile.ZipFile(zp, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    name_lower = Path(info.filename).name.lower()
                    if not name_lower.endswith((".pdf", ".docx")):
                        skipped.append({"file": info.filename, "reason": "unsupported_type"})
                        continue
                    try:
                        extracted[info.filename] = zf.read(info)
                    except Exception as exc:
                        skipped.append({"file": info.filename, "reason": str(exc)})
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Bad ZIP archive: {exc}") from exc

    files = list(extracted.keys())
    rnd.shuffle(files)
    semaphore = asyncio.Semaphore(max(1, min(int(concurrency), _MAX_PARALLEL_CANDIDATES)))

    tasks = [
        asyncio.create_task(
            process_single_resume_candidate(
                rel_path=fname,
                raw_bytes=extracted[fname],
                job_description=jd,
                semaphore=semaphore,
                progress=progress,
                workflow_context=bulk_workflow_context,
            )
        )
        for fname in files
    ]

    rows = []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            logger.error("gather_exception %s", r)
            cid = str(uuid.uuid4())
            rows.append(
                {
                    "candidate_id": cid,
                    "error": str(r),
                    "_sort_governance_safe": False,
                    "_composite": 0.0,
                    "_classification": "REJECT",
                    "_classification_reason": str(r),
                }
            )
        else:
            rows.append(cast(dict[str, Any], r))

    elapsed_ms = (time.perf_counter() - t0) * 1000
    resp = build_ranked_response(
        job_role=job_role,
        job_description=jd,
        open_positions=open_n,
        rows=rows,
        processing_time_ms=elapsed_ms,
        pool_total_files=len(files),
        bulk_session_id=bulk_session_id,
    )
    resp["skipped_files"] = skipped
    resp["successful_ingestion"] = sum(1 for r in rows if not r.get("error"))
    return resp

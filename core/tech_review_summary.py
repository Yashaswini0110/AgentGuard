"""
Advisory LLM summaries for technical / HR reviewers.

Candidate-first: narrative is grounded in résumé text downloaded from Supabase when available.
Router/policy/shap context is secondary (prompt + output field ordering).

Does not invoke policy_engine or mutate routing decisions.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from core.llm_fallback import chat_json
from core.resume_parser import extract_resume_text_auto
from core.supabase_storage import download_resume_bytes

logger = logging.getLogger("agentguard.tech_review_summary")

_BLOCKED_SUBSTRINGS = (
    "surname",
    "emotion",
    "gender",
    "caste",
    "religion",
    "district",
    "village",
    "institution_tier",
    "tier_proxy",
    "home_",
)


def _safe_feature_key(key: str) -> bool:
    kl = (key or "").lower().replace(" ", "_")
    return not any(b in kl for b in _BLOCKED_SUBSTRINGS)


def sanitize_governance_secondary(artifact: dict[str, Any]) -> dict[str, Any]:
    """Minimal router/policy/shap hints for the SECONDARY capsule only."""
    shap = artifact.get("shap_scores") or {}
    if not isinstance(shap, dict):
        shap = {}
    shap_f = {
        k: round(float(v), 5)
        for k, v in shap.items()
        if isinstance(v, (int, float)) and _safe_feature_key(str(k))
    }

    fu = artifact.get("features_used")
    feat: list[str] = []
    if isinstance(fu, list):
        feat = [str(x) for x in fu if _safe_feature_key(str(x))][:24]
    elif isinstance(fu, dict):
        feat = [str(k) for k in fu.keys() if _safe_feature_key(str(k))][:24]

    viols = artifact.get("policy_violations") or []
    vnames: list[str] = []
    if isinstance(viols, list):
        for v in viols:
            if isinstance(v, dict) and v.get("rule_name"):
                vnames.append(str(v.get("rule_name")))
    return {
        "routing_classification": artifact.get("routing_classification"),
        "confidence_score": artifact.get("confidence_score"),
        "policy_result": artifact.get("policy_result"),
        "policy_rule_cited": artifact.get("policy_rule_cited"),
        "top_shap_features": shap_f,
        "model_feature_tags": feat,
        "policy_rule_names": vnames[:8],
    }


def _load_resume_excerpt(decision_id: str) -> tuple[bool, str, str | None]:
    """Return (resume_available, resume_text_excerpt, provenance_hint)."""
    max_chars = int((os.getenv("AG_REVIEW_RESUME_EXCERPT_CHARS") or "16000").strip() or "16000")
    dl = download_resume_bytes(decision_id)
    if not dl:
        return False, "", "no_resume_in_storage"

    blob, mime, name = dl
    try:
        text = extract_resume_text_auto(blob, name or Path("resume.pdf").name)
    except Exception as exc:
        logger.warning("resume_extract_failed decision_id=%s err=%s", decision_id, exc)
        return False, "", f"extract_error:{exc!s:.200}"

    t = (text or "").strip()
    if not t:
        return False, "", "empty_extraction"

    if len(t) > max_chars:
        t = t[:max_chars] + "\n\n[… resume truncated for review assist …]"

    return True, t, f"storage:{mime}"


SUMMARY_SYSTEM_PROMPT = """You are AgentGuard's advisory Technical Review assistant for enterprise hiring.

PRIMARY JOB (must dominate tokens + reader attention)
- Summarise WHO this candidate is as an engineer or technical contributor.
- Ground skills, stack, projects, experience depth, strengths, and weaknesses in RESUME_PAYLOAD.resume_text_excerpt.

SECONDARY JOB (brief)
- governance_notes field ONLY: ~2–4 sentences on routing class, confidence flavour, at most two SHAP/policy signals.

STRICT FACTUALITY
- Do NOT invent employers, internships, cloud accounts, certifications, metrics, or stacks absent from the excerpt.
- If resume_available is false or excerpt empty, say so plainly; keep candidate sections thin — do not fabricate biography.

PROHIBITED (never infer or emphasise)
surname/ethnicity, religion, caste/tribe/community, birthplace/district, gender, emotion-inference traits,
prestige signalling about schools, marital/parental proxies.

JOB DESCRIPTION
Use JOB_PAYLOAD.job_description_excerpt only when JOB_DESCRIPTION_PRESENT is true.

OUTPUT
Return ONLY JSON with these exact keys and types:
{
  "candidate_overview": string,
  "technical_skills_stack": string,
  "projects_and_experience": string,
  "job_alignment": string,
  "skill_gaps_concerns": [string],
  "technical_opinion": string,
  "suggested_action": string,
  "governance_notes": string
}

Field goals:
- candidate_overview: 3–6 lines recruiter/tech-lead vignette of the person (from resume).
- technical_skills_stack: languages, frameworks, data, cloud/CI-CD, observability as evidenced.
- projects_and_experience: project/work signals, complexity/production hints if evidenced.
- job_alignment: JD fit when present else state not assessed.
- skill_gaps_concerns: bullets about missing evidence (not stereotypes).
- technical_opinion: human takeaway.
- suggested_action: advisory workflow label only ("MANUAL REVIEW", "ADDITIONAL TECH SCREEN") — not a hire decision.
- governance_notes: SECONDARY governance capsule (short).

Tone: professional, concise, recruiter + technical lead."""


def generate_tech_review_summary(
    artifact: dict[str, Any],
    decision_id: str,
    job_description: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (summary_json, resume_meta)."""
    resume_ok, excerpt, resume_src = _load_resume_excerpt(decision_id)
    jd = (job_description or "").strip()
    jd_present = len(jd) > 160
    jd_payload = jd[:12000] if jd_present else ""

    gov = sanitize_governance_secondary(artifact)

    payload = {
        "RESUME_PAYLOAD": {
            "resume_available": resume_ok,
            "resume_source": resume_src,
            "resume_text_excerpt": excerpt if resume_ok else "",
        },
        "JOB_PAYLOAD": {
            "JOB_DESCRIPTION_PRESENT": jd_present,
            "job_description_excerpt": jd_payload,
        },
        "CANDIDATE_DISPLAY": {
            "candidate_name_hint": artifact.get("candidate_name"),
            "candidate_id": artifact.get("candidate_id"),
        },
        "GOVERNANCE_PAYLOAD_SECONDARY": gov,
        "META": (
            "Produce candidate sections from RESUME_PAYLOAD first. "
            "If resume_available is false, acknowledge limited visibility."
        ),
    }

    user_msg = "REVIEWER_CONTEXT_JSON:\n" + json.dumps(payload, ensure_ascii=False)

    gemini_model = (
        os.getenv("AG_REVIEW_SUMMARY_GEMINI_MODEL") or os.getenv("AG_GEMINI_MODEL_PARSE") or "gemini-2.5-flash"
    ).strip()
    openrouter_model = (
        os.getenv("AG_REVIEW_SUMMARY_OPENROUTER_MODEL") or os.getenv("AG_OPENROUTER_MODEL") or "openai/gpt-oss-120b"
    ).strip()
    max_tokens = int((os.getenv("AG_REVIEW_SUMMARY_MAX_TOKENS") or "4500").strip() or "4500")

    result = chat_json(
        system=SUMMARY_SYSTEM_PROMPT,
        user=user_msg,
        gemini_model=gemini_model,
        openrouter_model=openrouter_model,
        temperature=0.18,
        max_tokens=max_tokens,
        retries=2,
    )

    required = (
        "candidate_overview",
        "technical_skills_stack",
        "projects_and_experience",
        "job_alignment",
        "skill_gaps_concerns",
        "technical_opinion",
        "suggested_action",
        "governance_notes",
    )
    if not isinstance(result, dict) or any(k not in result for k in required):
        raise ValueError("Reviewer summary model returned incomplete schema.")

    if not isinstance(result.get("skill_gaps_concerns"), list):
        raise ValueError("skill_gaps_concerns must be an array.")

    for k in required:
        if k == "skill_gaps_concerns":
            continue
        if not isinstance(result.get(k), str):
            raise ValueError(f"Field {k} must be a string.")

    meta = {
        "resume_grounded": resume_ok,
        "resume_source": resume_src,
        "resume_chars_used": len(excerpt) if resume_ok else 0,
    }
    return result, meta

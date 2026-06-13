"""
AgentGuard v2 — F2: extract enforceable policy rules from a policy document (M1)

Given the text of a regulation / policy PDF, ask the LLM (Gemini, with the
OpenRouter fallback shared across the app) to propose structured rule candidates
in the engine's content_json shape. Candidates are saved INACTIVE for an admin
to review and activate — the LLM never directly changes what is enforced.
"""

from __future__ import annotations

import os

from core.llm_fallback import chat_json

_SYSTEM = (
    "You are a compliance engineer for an AI hiring governance system. Given the "
    "text of a regulation or policy document, extract concrete, machine-enforceable "
    "HIRING policy rules that BLOCK decisions which use prohibited or proxy "
    "candidate features. Respond with JSON only."
)

_INSTRUCTIONS = """Return JSON of this exact shape:
{"rules": [
  {
    "name": "UPPER_SNAKE_CASE_ID",
    "severity": "RED",
    "regulation": "short citation, e.g. 'DPDP Act 2023 s.4'",
    "reason": "one sentence on why this feature is prohibited",
    "condition": {"type": "feature_present", "features": ["snake_case_feature"], "match": "any"}
  }
]}

Rules:
- Only emit "feature_present" conditions. `features` is a list of candidate
  feature names whose use in a hiring decision would violate the policy.
- Use snake_case feature names (e.g. applicant_caste, applicant_religion,
  applicant_age, disability_status, marital_status).
- Use "match":"all" only when a violation requires several features together.
- Prefer severity "RED" for protected/prohibited attributes.
- Emit at most 8 rules. If the document implies no enforceable hiring-feature
  rule, return {"rules": []}.
"""


def extract_rules_from_text(text: str, max_chars: int = 12000) -> list[dict]:
    """Return a list of rule candidates ({name, severity, regulation, reason, condition})."""
    snippet = (text or "").strip()[:max_chars]
    if not snippet:
        return []
    result = chat_json(
        system=_SYSTEM,
        user=f"{_INSTRUCTIONS}\n\nPOLICY DOCUMENT:\n{snippet}",
        gemini_model=os.getenv("AG_GEMINI_MODEL_POLICY") or "gemini-2.5-flash",
        openrouter_model=os.getenv("AG_OPENROUTER_MODEL") or "openai/gpt-oss-120b",
        temperature=0.0,
    )
    rules = result.get("rules") if isinstance(result, dict) else None
    return rules if isinstance(rules, list) else []

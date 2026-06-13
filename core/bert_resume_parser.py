"""
AgentGuard v3 — BERT-based Fast Resume Parser
==============================================
Uses a HuggingFace NER pipeline as the PRIMARY parser for bulk resume processing.
One API call per resume is avoided entirely — inference runs locally.

Falls back to the existing LLM parser (core/resume_parser.py) only when
``should_use_llm_fallback()`` returns True.

Model: yashpwr/resume-ner-bert-v2
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("agentguard.bert_resume_parser")

# ---------------------------------------------------------------------------
# Model — loaded ONCE at module import time
# ---------------------------------------------------------------------------
_ner_pipeline = None

try:
    from transformers import pipeline as hf_pipeline

    _ner_pipeline = hf_pipeline(
        "token-classification",
        model="yashpwr/resume-ner-bert-v2",
        aggregation_strategy="simple",
    )
    logger.info("BERT NER pipeline loaded: yashpwr/resume-ner-bert-v2")
except Exception as _load_exc:
    logger.warning(
        "BERT NER pipeline failed to load — bert_resume_parser will return empty results. "
        "Error: %s",
        _load_exc,
    )
    _ner_pipeline = None

# ---------------------------------------------------------------------------
# Label → output field mapping
# ---------------------------------------------------------------------------
_LABEL_MAP: dict[str, str] = {
    "NAME":         "candidate_name",
    "SKILLS":       "skills",
    "SKILL":        "skills",
    "COLLEGE":      "institution",
    "UNIVERSITY":   "institution",
    "EDUCATION":    "institution",
    "COMPANY":      "companies",
    "EMPLOYER":     "companies",
    "ORGANIZATION": "companies",
    "DESIGNATION":  "titles",
    "TITLE":        "titles",
    "JOBTITLE":     "titles",
    "EMAIL":        "email",
    "PHONE":        "phone",
    "MOBILE":       "phone",
    "LOCATION":     "location",
    "CITY":         "location",
    "STATE":        "location",
    "EXPERIENCE":   "raw_experience_text",
    "YEARS":        "raw_experience_text",
}

# Fields whose values accumulate into a list
_LIST_FIELDS = {"skills", "companies", "titles"}

# Fields where only the first non-empty value wins
_SCALAR_FIELDS = {"candidate_name", "institution", "email", "phone", "location", "raw_experience_text"}


def _clean_entity_text(word: str) -> str:
    """Strip HuggingFace subword markers and stray whitespace from NER tokens."""
    return word.replace("##", "").strip()


def extract_entities(text: str) -> dict[str, Any]:
    """
    Run the BERT NER pipeline over *text* and aggregate results into a
    structured dict.

    Returns a dict with keys:
        candidate_name, skills, institution, companies, titles,
        email, phone, location, raw_experience_text, _bert_confidence
    """
    result: dict[str, Any] = {
        "candidate_name":    "",
        "skills":            [],
        "institution":       "",
        "companies":         [],
        "titles":            [],
        "email":             "",
        "phone":             "",
        "location":          "",
        "raw_experience_text": "",
        "_bert_confidence":  0.0,
    }

    if _ner_pipeline is None or not text or not text.strip():
        return result

    try:
        entities: list[dict] = _ner_pipeline(text[:4096])  # cap for speed
    except Exception as exc:
        logger.warning("BERT NER inference error: %s", exc)
        return result

    if not entities:
        return result

    scores: list[float] = []
    for ent in entities:
        label = str(ent.get("entity_group") or ent.get("entity") or "").upper().strip()
        word = _clean_entity_text(str(ent.get("word") or ""))
        score = float(ent.get("score") or 0.0)

        if not label or not word:
            continue

        field = _LABEL_MAP.get(label)
        if field is None:
            continue

        scores.append(score)

        if field in _LIST_FIELDS:
            result[field].append(word)
        elif field in _SCALAR_FIELDS:
            if not result[field]:   # first match wins for scalar fields
                result[field] = word

    result["_bert_confidence"] = round(sum(scores) / len(scores), 4) if scores else 0.0
    return result


# ---------------------------------------------------------------------------
# Years-of-experience regex
# ---------------------------------------------------------------------------
_YOE_PATTERNS = [
    r"(\d+(?:\.\d+)?)\s*\+?\s*years?",   # "5 years", "3.5 years", "7+ years"
    r"(\d+(?:\.\d+)?)\s*\+?\s*yrs?",     # "5 yrs", "7+ yr"
]


def _parse_years(raw: str) -> float:
    """Extract the first numeric year value from *raw*, or 0.0."""
    if not raw:
        return 0.0
    for pattern in _YOE_PATTERNS:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    return 0.0


def parse_resume_fast(text: str, job_description: str = "") -> dict[str, Any]:
    """
    Primary fast parser: runs BERT NER and returns a dict compatible with
    AgentGuard's CandidateInput schema.

    Parameters
    ----------
    text:             Raw plain text of the resume.
    job_description:  Optional — reserved for future skill-matching logic.

    Returns
    -------
    dict with keys: candidate_name, email, phone, skills, institution,
                    years_of_experience, location, _bert_confidence, _parse_method
    """
    entities = extract_entities(text)

    years_of_experience = _parse_years(entities["raw_experience_text"])

    # Also scan the full text for a years pattern when raw_experience_text is empty.
    if years_of_experience == 0.0:
        years_of_experience = _parse_years(text)

    # Email: NER is unreliable — always supplement with regex over raw text.
    from core.resume_parser import extract_email_from_text, _normalize_email

    email = _normalize_email(entities["email"]) or ""
    if not email:
        email = extract_email_from_text(text) or ""

    return {
        "candidate_name":     entities["candidate_name"],
        "email":              email,
        "phone":              entities["phone"],
        "skills":             entities["skills"],
        "institution":        entities["institution"],
        "years_of_experience": years_of_experience,
        "location":           entities["location"],
        "_bert_confidence":   entities["_bert_confidence"],
        "_parse_method":      "bert",
    }


def should_use_llm_fallback(bert_result: dict[str, Any]) -> bool:
    """
    Return True when the BERT result is not reliable enough and the LLM
    fallback should be invoked.

    Triggers on ANY of:
    - _bert_confidence < 0.70
    - years_of_experience == 0.0 AND skills is empty
    - candidate_name is empty string
    """
    confidence: float = float(bert_result.get("_bert_confidence") or 0.0)
    if confidence < 0.70:
        return True

    years: float = float(bert_result.get("years_of_experience") or 0.0)
    skills: list = bert_result.get("skills") or []
    if years == 0.0 and len(skills) == 0:
        return True

    if not (bert_result.get("candidate_name") or "").strip():
        return True

    return False


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = "John Smith, 5 years experience in Python and FastAPI. Studied at IIT Delhi."
    result = parse_resume_fast(sample)
    print(result)
    print("Use LLM fallback?", should_use_llm_fallback(result))

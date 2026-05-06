import os
import io
import json
import re
import fitz  # PyMuPDF
import pdfplumber
from openai import OpenAI
from docx import Document
from dotenv import load_dotenv
import time
from pathlib import Path

# Load environment variables
load_dotenv()

# Debug log path (repo root)
_LOG_PATH = str(Path(__file__).resolve().parents[1] / "debug-924df7.log")

# Initialize OpenAI client with Gemini's base URL
_api_key = (os.getenv("GOOGLE_API_KEY") or "").strip() or (os.getenv("GEMINI_API_KEY") or "").strip()
client = OpenAI(
    api_key=_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# #region agent log
# Boot log line to prove logging works (no secrets).
try:
    payload = {
        "sessionId": "924df7",
        "runId": "pre-fix",
        "hypothesisId": "H0",
        "location": "core/resume_parser.py:module_init",
        "message": "Resume parser module imported",
        "data": {
            "log_path": _LOG_PATH,
            "google_api_key_present": bool((os.getenv("GOOGLE_API_KEY") or "").strip()),
            "gemini_api_key_present": bool((os.getenv("GEMINI_API_KEY") or "").strip()),
            "selected_key_source": ("GOOGLE_API_KEY" if (os.getenv("GOOGLE_API_KEY") or "").strip() else ("GEMINI_API_KEY" if (os.getenv("GEMINI_API_KEY") or "").strip() else "NONE")),
            "selected_key_len": len(_api_key),
        },
        "timestamp": int(time.time() * 1000),
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
except Exception:
    pass
# #endregion

STRUCTURED_RESUME_PROMPT = """You extract structured candidate data from resume text.

STRICT RULES:
- Output ONLY valid JSON (no markdown fences).
- Do NOT hallucinate: use null for unknown fields.
- Use the exact schema keys below (including `"full_name"` — do not rename it to `"name"`).
- **full_name** MUST be populated whenever the résumé header or opening lines clearly identify the applicant
  (e.g. capitalized multi-word names at the top). Only use null if no human name is discernible anywhere.
- skills, education, certifications, projects must be arrays (empty if unknown).
- **skills**: list EVERY technical competency visible in the résumé — languages, runtimes,
  frameworks, databases, clouds, infra, data tools, testing, observability — not only a short subset.
  If the résumé states it explicitly or clearly implies it under experience, include it.
- years_of_experience and career_gap_months are numbers (use 0 if unknown).

SCHEMA:
{
  "full_name": string or null,
  "email": string or null,
  "phone": string or null,
  "years_of_experience": number,
  "skills": [string],
  "education": [string or object],
  "certifications": [string or object],
  "projects": [string or object],
  "current_role": string or null,
  "previous_companies": [string],
  "location": string or null,
  "career_gap_months": number,
  "resume_text": string
}

The resume_text field must echo the cleaned free-text resume (may be truncated to 8000 chars if needed).
"""

SYSTEM_PROMPT = """You are an AI Hiring Evaluation Agent.

Your task is to evaluate a candidate based on:
1. Resume content
2. Job Description

STRICT RULES:
- Output ONLY valid JSON
- Do NOT hallucinate missing data
- If unknown → null
- skill_match_score must be 0–1
- Be conservative in scoring

FIELDS TO EXTRACT:
{
  "candidate_id": "CAND-PDF-XXXX",
  "name": string,
  "years_of_experience": number,
  "primary_skills": [list of strings],
  "skill_match_score": number (0.0 to 1.0),
  "match_reasoning": string (one sentence),
  "missing_skills": [list of strings],
  "interview_score": 0.0,
  "assessment_score": 0.0,
  "feature_count": number,
  "applicant_surname": string or null,
  "institution_tier": number (1-4) or null,
  "home_district": string or null
}

LOGIC RULES:
1. skill_match_score:
- Strong alignment → 0.8–1.0
- Moderate → 0.5–0.8
- Weak → <0.5
- Consider skills overlap, experience relevance, and domain match.

2. institution_tier:
- Tier 1: IIT, NIT, top private (BITS, IIIT)
- Tier 2: good state/private colleges
- Tier 3: average colleges
- Tier 4: unknown/unranked
"""

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text from a PDF file using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")
    return text


def extract_text_from_pdf_pdfplumber(pdf_bytes: bytes) -> str:
    """Primary PDF path per enterprise spec (pdfplumber)."""
    try:
        parts: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception as e:
        raise ValueError(f"pdfplumber failed: {e}")


def extract_text_from_docx(docx_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(docx_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception as e:
        raise ValueError(f"DOCX extract failed: {e}")


def extract_resume_text_auto(file_bytes: bytes, filename: str) -> str:
    """Route PDF/DOCX extraction with pdfplumber-first PDF policy."""
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        try:
            t = extract_text_from_pdf_pdfplumber(file_bytes)
            if t.strip():
                return t
        except Exception:
            pass
        return extract_text_from_pdf(file_bytes)
    if lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    raise ValueError(f"Unsupported resume type: {filename}")

def parse_resume(resume_text: str, job_description: str) -> dict:
    """Calls Gemini API to evaluate resume against a specific JD."""
    try:
        # #region agent log
        # NOTE: Do not log secrets (API keys, resume text, JD text).
        try:
            k_raw = os.getenv("GOOGLE_API_KEY")
            k = (k_raw or "").strip()
            payload = {
                "sessionId": "924df7",
                "runId": "pre-fix",
                "hypothesisId": "H1",
                "location": "core/resume_parser.py:parse_resume:env",
                "message": "Resume parser env snapshot",
                "data": {
                    "google_api_key_present": bool(k_raw),
                    "google_api_key_len": len(k),
                    "google_api_key_looks_like_aiZa": bool(k) and k.startswith("AIza"),
                    "gemini_api_key_present": bool((os.getenv("GEMINI_API_KEY") or "").strip()),
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                    "model": "gemini-2.5-flash",
                },
                "timestamp": int(time.time() * 1000),
            }
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        # #endregion

        user_content = (
            f"JOB DESCRIPTION:\n-------------------\n{job_description}\n-------------------\n\n"
            f"RESUME TEXT:\n-------------------\n{resume_text}\n-------------------"
        )
        
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:-3].strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:-3].strip()
            
        return json.loads(raw_output)
    except Exception as e:
        # #region agent log
        try:
            payload = {
                "sessionId": "924df7",
                "runId": "pre-fix",
                "hypothesisId": "H3",
                "location": "core/resume_parser.py:parse_resume:exception",
                "message": "Resume parser exception",
                "data": {
                    "exc_type": type(e).__name__,
                    "exc_str": str(e)[:500],
                },
                "timestamp": int(time.time() * 1000),
            }
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        # #endregion
        raise ValueError(f"Resume parsing failed: {e}")


def coalesce_candidate_full_name(data: dict) -> str:
    """
    LLMs commonly return `"name"` or alternate keys despite the `"full_name"` schema.
    Return the best non-empty string for display.
    """
    priority_keys = (
        "full_name",
        "name",
        "candidate_name",
        "applicant_name",
        "display_name",
        "legal_name",
    )
    for k in priority_keys:
        v = data.get(k)
        if isinstance(v, str):
            s = v.strip()
            if s.lower() not in {"", "null", "none", "n/a"}:
                return s
    for k, v in data.items():
        if not isinstance(v, str) or not v.strip():
            continue
        nk = str(k).lower().replace("-", "_").replace(" ", "_")
        if nk in ("full_name", "name", "candidate_name"):
            s = v.strip()
            if s.lower() not in {"", "null", "none", "n/a"}:
                return s
        if nk in ("fullname", "candidatename"):
            s = v.strip()
            if s.lower() not in {"", "null", "none", "n/a"}:
                return s
    return ""


def guess_name_from_resume_header(text: str, max_lines: int = 14) -> str:
    """
    Fallback: first plausible person-name line at the top of the document (below parsing failures).
    """
    if not (text or "").strip():
        return ""
    skip_re = (
        r"@",
        r"http",
        r"linkedin",
        r"^\s*\d",
        r"\b(phone|mobile|tel|email|address|linkedin|resume|cv|curriculum\s+vitae)\b",
    )
    for line in text.strip().splitlines()[:max_lines]:
        raw = line.strip()
        if not raw or len(raw) > 100:
            continue
        lower = raw.lower()
        if any(re.search(p, lower) for p in skip_re):
            continue
        raw = re.sub(r"^[|•·\-–—\*\s]+", "", raw).strip()
        words = raw.split()
        if len(words) < 2 or len(words) > 8:
            continue
        broken = False
        for w in words:
            w_clean = re.sub(r"^[.\s]+|[.\s]+$", "", w)
            if len(w_clean) > 40:
                broken = True
                break
            # Allow initials (A.) and hyphenated names
            if not re.match(r"^[A-Za-z][A-Za-z.\-'’]*\.?$", w_clean):
                broken = True
                break
        if not broken:
            return raw
    return ""


def humanize_resume_filename_stem(stem: str) -> str:
    """Last-resort display string from archive filename (underscores, noise tokens)."""
    if not stem:
        return ""
    s = stem.replace("_", " ").replace("-", " ").strip()
    s = re.sub(r"\s+", " ", s)
    noise = re.compile(
        r"\s+\b(resume|cv|curriculum vitae|vitae|final|updated|draft|copy|v\d+)\s*$|"
        r"\s+\b(dsu)\s*$|"
        r"\s+\b(amazon|internship|intern)\s*$",
        re.I,
    )
    for _ in range(5):
        s2 = noise.sub("", s).strip(" _-")
        if s2 == s or not s2:
            break
        s = s2
    return s.strip() or stem


def _strip_code_fence(raw: str) -> str:
    t = (raw or "").strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def parse_resume_structured(resume_text: str, job_description: str = "") -> dict:
    """
    Structured candidate JSON extraction (schema aligned with bulk ranking).
    Generates conservative JSON-only output via Gemini.
    """
    resume_text_clean = resume_text.strip()
    if len(resume_text_clean) > 12000:
        resume_text_clean = resume_text_clean[:12000]

    jd_note = ""
    if (job_description or "").strip():
        jd_note = f"\n\nJOB CONTEXT (for skill alignment hints only):\n{job_description[:6000]}"

    user_content = f"RAW RESUME TEXT:\n{resume_text_clean}{jd_note}"

    def _once() -> dict:
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": STRUCTURED_RESUME_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        cleaned = _strip_code_fence(raw)
        return json.loads(cleaned)

    last_exc: Exception | None = None
    for delay in (0.0, 0.6, 1.6):
        if delay:
            time.sleep(delay)
        try:
            data = _once()
            if not isinstance(data, dict):
                raise ValueError("structured parser did not return an object")
            merged = coalesce_candidate_full_name(data)
            if merged:
                data["full_name"] = merged
            return data
        except Exception as e:
            last_exc = e
            continue
    raise ValueError(f"Structured resume parsing failed after retries: {last_exc}")


if __name__ == "__main__":
    # Test
    test_text = "Arjun Mehta, IIT Bombay graduate, 4 years experience in Python and SQL."
    test_jd = "Looking for a Python Backend Developer with 5 years experience."
    try:
        result = parse_resume(test_text, test_jd)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

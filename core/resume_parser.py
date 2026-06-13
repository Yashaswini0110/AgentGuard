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
from core.llm_fallback import chat_json

# Load environment variables
load_dotenv()

# #region agent log
def _dbg_write(payload: dict) -> None:
    try:
        path = str((os.getenv("AGENTGUARD_DEBUG_LOG_PATH") or "debug-ec0bcc.log").strip() or "debug-ec0bcc.log")
        payload = dict(payload)
        payload.setdefault("sessionId", "ec0bcc")
        payload.setdefault("timestamp", int(time.time() * 1000))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion

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
- **email** MUST be populated when a contact email appears in the header, contact block, or anywhere in the résumé.
  Use lowercase. Use null only if no valid email address is present.
- skills, education, certifications, projects must be arrays (empty if unknown).
- **skills**: list EVERY technical competency visible in the résumé — languages, runtimes,
  frameworks, databases, clouds, infra, data tools, testing, observability — not only a short subset.
  If the résumé states it explicitly or clearly implies it under experience, include it.
- years_of_experience and career_gap_months are numbers (use 0 if unknown).
- Do NOT include the full resume text in the JSON. Set `"resume_text": ""` always.
  (The system already stores the raw extracted text separately; including it here causes truncation.)

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

The resume_text field must be an empty string.
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
  "email": string or null,
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
        
        max_out = int((os.getenv("AG_RESUME_PARSE_MAX_TOKENS") or "4096").strip() or "4096")
        data = chat_json(
            system=SYSTEM_PROMPT,
            user=user_content,
            gemini_model=(os.getenv("AG_GEMINI_MODEL_PARSE") or "gemini-2.5-flash").strip(),
            openrouter_model=(os.getenv("AG_OPENROUTER_MODEL") or "openai/gpt-oss-120b").strip(),
            temperature=0.0,
            max_tokens=max_out,
            retries=2,
        )
        if isinstance(data, dict):
            resolved_email = resolve_candidate_email(data, resume_text)
            if resolved_email:
                data["email"] = resolved_email
        return data
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


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PLACEHOLDER_EMAIL_DOMAINS = frozenset({"example.com", "example.org", "test.com", "email.com"})
_GENERIC_LOCAL_PARTS = frozenset({
    "info", "contact", "hr", "careers", "jobs", "recruitment", "noreply", "no-reply",
    "support", "admin", "hello", "office", "enquiry", "inquiry",
})


def _normalize_email_spacing(text: str) -> str:
    """Collapse PDF/OCR spacing artifacts around @ and dots in email-like spans."""
    if not text:
        return ""
    t = text
    t = re.sub(r"(?<=[A-Za-z0-9._%+-])\s+@", "@", t)
    t = re.sub(r"@\s+(?=[A-Za-z0-9])", "@", t)
    t = re.sub(r"(?<=[A-Za-z0-9])\s+\.(?=[A-Za-z0-9])", ".", t)
    return t


def _normalize_email(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("##", "").replace(" ", "")
    cleaned = cleaned.strip(".,;:\"'()[]<>")
    if not _EMAIL_RE.fullmatch(cleaned):
        return None
    domain = cleaned.rsplit("@", 1)[-1]
    if domain in _PLACEHOLDER_EMAIL_DOMAINS:
        return None
    return cleaned


def _pick_best_email(candidates: list[str]) -> str | None:
    """Prefer personal addresses over generic mailbox prefixes (info@, hr@, …)."""
    if not candidates:
        return None
    personal = [
        e for e in candidates
        if e.split("@", 1)[0] not in _GENERIC_LOCAL_PARTS
    ]
    return personal[0] if personal else candidates[0]


def _collect_emails_from_blob(blob: str) -> list[str]:
    found: list[str] = []
    for variant in (blob, _normalize_email_spacing(blob)):
        for match in _EMAIL_RE.finditer(variant):
            normalized = _normalize_email(match.group(0))
            if normalized and normalized not in found:
                found.append(normalized)
    return found


def extract_email_from_text(text: str) -> str | None:
    """Regex extraction with PDF spacing repair; scans header first."""
    if not text:
        return None
    candidates: list[str] = []
    for section in (text[:3000], text):
        for email in _collect_emails_from_blob(section):
            if email not in candidates:
                candidates.append(email)
    return _pick_best_email(candidates)


def resolve_candidate_email(structured: dict | None, resume_text: str = "") -> str | None:
    """Extract email from résumé text (primary) and validate against structured output."""
    structured = structured or {}
    blob = resume_text or structured.get("resume_text") or ""
    from_text = extract_email_from_text(str(blob))
    from_structured = _normalize_email(structured.get("email"))

    if from_text and from_structured:
        if from_structured == from_text:
            return from_structured
        collapsed = _normalize_email_spacing(str(blob)).lower().replace(" ", "")
        if from_structured in collapsed:
            return from_structured
        return from_text

    return from_text or from_structured


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

    # #region agent log
    _dbg_write(
        {
            "runId": "resume-structured",
            "hypothesisId": "H1",
            "location": "core/resume_parser.py:parse_resume_structured:entry",
            "message": "Structured parse call",
            "data": {
                "resume_len": len(resume_text_clean or ""),
                "jd_len": len(job_description or ""),
                "gemini_model": (os.getenv("AG_GEMINI_MODEL_STRUCTURED") or "gemini-2.5-flash").strip(),
                "openrouter_model": (os.getenv("AG_OPENROUTER_MODEL") or "openai/gpt-oss-120b").strip(),
                "openrouter_key_present": bool((os.getenv("OPENROUTER_API_KEY") or "").strip()),
            },
        }
    )
    # #endregion
    data = chat_json(
        system=STRUCTURED_RESUME_PROMPT,
        user=user_content,
        gemini_model=(os.getenv("AG_GEMINI_MODEL_STRUCTURED") or "gemini-2.5-flash").strip(),
        openrouter_model=(os.getenv("AG_OPENROUTER_MODEL") or "openai/gpt-oss-120b").strip(),
        temperature=0.0,
        max_tokens=int((os.getenv("AG_STRUCTURED_MAX_TOKENS") or "2000").strip() or "2000"),
        retries=2,
    )
    if not isinstance(data, dict):
        raise ValueError("structured parser did not return an object")
    merged = coalesce_candidate_full_name(data)
    if merged:
        data["full_name"] = merged
    resolved_email = resolve_candidate_email(data, resume_text_clean)
    if resolved_email:
        data["email"] = resolved_email
    # Ensure we carry the real extracted text even if the model returns empty/truncated text.
    # (Structured prompt forces resume_text to be "", to avoid provider truncation.)
    data["resume_text"] = resume_text_clean[:8000]
    return data


if __name__ == "__main__":
    # Test
    test_text = "Arjun Mehta, IIT Bombay graduate, 4 years experience in Python and SQL."
    test_jd = "Looking for a Python Backend Developer with 5 years experience."
    try:
        result = parse_resume(test_text, test_jd)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

import os
import json
import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client with Gemini's base URL
_api_key = (os.getenv("GOOGLE_API_KEY") or "").strip() or (os.getenv("GEMINI_API_KEY") or "").strip()
client = OpenAI(
    api_key=_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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

def parse_resume(resume_text: str, job_description: str) -> dict:
    """Calls Gemini API to evaluate resume against a specific JD."""
    try:
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
        raise ValueError(f"Resume parsing failed: {e}")

if __name__ == "__main__":
    # Test
    test_text = "Arjun Mehta, IIT Bombay graduate, 4 years experience in Python and SQL."
    test_jd = "Looking for a Python Backend Developer with 5 years experience."
    try:
        result = parse_resume(test_text, test_jd)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

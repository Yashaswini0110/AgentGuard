import os
import json
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client with Gemini's base URL
# This allows us to use the OpenAI SDK to communicate with Gemini
_api_key = (os.getenv("GOOGLE_API_KEY") or "").strip() or (os.getenv("GEMINI_API_KEY") or "").strip()
client = OpenAI(
    api_key=_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def generate_llm_response(prompt: str) -> str:
    """Calls Gemini API using OpenAI-compatible endpoint."""
    try:
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise ValueError(f"LLM request failed: {e}")

def make_hiring_decision(
    candidate: dict,
    inject_prohibited_feature: Optional[str] = None,
) -> dict:
    prompt = (
        "You are an AI hiring screener. Evaluate the given candidate profile and make a hiring decision.\n"
        "Return ONLY valid JSON. No explanation. No extra text.\n"
        "The output MUST be a valid JSON object with EXACTLY these fields:\n"
        '- "candidate_id": string (from input)\n'
        '- "decision": "APPROVE" or "REJECT"\n'
        '- "confidence": float between 0.0 and 1.0\n'
        '- "reason": string (one sentence)\n'
        '- "features_used": list of strings (which candidate fields you weighted most)\n'
        '- "recommended_action": "PROCEED_TO_INTERVIEW" or "REJECT_APPLICATION"\n\n'
        f"Candidate Profile:\n{json.dumps(candidate, indent=2)}"
    )
    
    response_text = generate_llm_response(prompt)
    
    try:
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        decision_data = json.loads(cleaned_text)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON from model")
        
    required_fields = {"candidate_id", "decision", "confidence", "reason", "features_used", "recommended_action"}
    if not isinstance(decision_data, dict) or not required_fields.issubset(decision_data.keys()):
        raise ValueError("Invalid response format")
        
    if inject_prohibited_feature:
        if not isinstance(decision_data.get("features_used"), list):
            decision_data["features_used"] = []
        if inject_prohibited_feature not in decision_data["features_used"]:
            decision_data["features_used"].append(inject_prohibited_feature)

    return decision_data

if __name__ == "__main__":
    sample_candidate = {
        #BorderLine case
                        # "candidate_id": "CAND-003",
                        # "name": "Neha Verma",
                        # "years_of_experience": 2,
                        # "skill_match_score": 0.65,
                        # "interview_score": 6.0,
                        # "assessment_score": 60,
                        # "career_gap_months": 6,
                        # "gender": "F",
                        # "institution_tier": 3

        # Accept
                        # "candidate_id": "CAND-001",
                        # "name": "Rahul Sharma",
                        # "years_of_experience": 5,
                        # "skill_match_score": 0.90,
                        # "interview_score": 8.2,
                        # "assessment_score": 85,
                        # "career_gap_months": 0,
                        # "gender": "M",
                        # "institution_tier": 2


        # Reject
                        "candidate_id": "CAND-002",
                        "name": "Amit Kumar",
                        "years_of_experience": 0,
                        "skill_match_score": 0.30,
                        "interview_score": 3.5,
                        "assessment_score": 40,
                        "career_gap_months": 0,
                        "gender": "M",
                        "institution_tier": 3
            
    }
    
    try:
        result = make_hiring_decision(sample_candidate)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

import os
import json
import datetime
from dotenv import load_dotenv
from core.llm_fallback import chat_json

# Load environment variables
load_dotenv()

def semantic_review(decision: dict, router_result: dict) -> dict:
    """
    Performs a semantic review of a hiring decision using Gemini 2.5 Flash.
    Triggered when the Risk Router classifies a decision as YELLOW.
    """
    try:
        # 1. Build System Prompt
        system_prompt = (
            "You are an AI compliance officer reviewing a hiring decision for potential bias or discrimination. "
            "You must evaluate whether the AI hiring agent's decision shows signs of indirect proxy discrimination "
            "against protected groups in India (caste, gender, religion, geographic origin) or violates EU AI Act Article 5. "
            "You must respond ONLY with a valid JSON object."
        )

        # 2. Extract context for User Prompt
        candidate_features = decision.get("features", {})
        ai_decision = decision.get("decision", "UNKNOWN")
        ai_reason = decision.get("reason", "No reason provided")
        shap_scores = router_result.get("shap_scores", {})

        user_prompt = f"""
Review the following hiring decision for potential indirect bias or proxy discrimination.

Candidate Features:
{json.dumps(candidate_features, indent=2)}

AI Decision: {ai_decision}
AI Reason: {ai_reason}

SHAP Scores (Feature Importance):
{json.dumps(shap_scores, indent=2)}

Does this decision show any signs of indirect bias? Cite specific features.

Your response must be a JSON object with the following fields:
- supervisor_verdict: "APPROVE", "REJECT", or "ESCALATE_TO_HUMAN"
- bias_detected: boolean
- bias_reason: string (detailed explanation or null)
- confidence: float (0.0 to 1.0)
- features_flagged: list of strings (names of suspicious features)
"""

        review_json = chat_json(
            system=system_prompt,
            user=user_prompt,
            gemini_model=(os.getenv("AG_GEMINI_MODEL_SUPERVISOR") or "gemini-2.5-flash").strip(),
            openrouter_model=(os.getenv("AG_OPENROUTER_MODEL") or "openai/gpt-oss-120b").strip(),
            temperature=0.1,
            max_tokens=600,
            retries=2,
        )

        return {
            "supervisor_verdict": review_json.get("supervisor_verdict", "ESCALATE_TO_HUMAN"),
            "bias_detected": review_json.get("bias_detected", False),
            "bias_reason": review_json.get("bias_reason", None),
            "confidence": review_json.get("confidence", 0.0),
            "features_flagged": review_json.get("features_flagged", []),
            "review_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    except Exception:
        # 6. Error handling fallback
        return {
            "supervisor_verdict": "ESCALATE_TO_HUMAN",
            "bias_detected": True,
            "bias_reason": "Supervisor review failed — escalating to human for safety",
            "confidence": 0.0,
            "features_flagged": [],
            "review_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

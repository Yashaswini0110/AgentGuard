"""
core/servicenow.py
------------------
AgentGuard v3 — ServiceNow Integration Layer

When a hiring decision is routed as RED, this module creates a real
ServiceNow incident ticket and holds the decision in PENDING state
until a human HR officer reviews it.

Environment variables required (load via .env):
    SERVICENOW_INSTANCE   — e.g. "dev12345.service-now.com"
    SERVICENOW_USERNAME   — Basic Auth username
    SERVICENOW_PASSWORD   — Basic Auth password
    ENVIRONMENT           — "development" | "production"
"""

import os
import json
import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_description(
    decision: dict,
    policy_result: dict,
    router_result: dict,
) -> str:
    """
    Compose a rich, human-readable incident description from all three
    AgentGuard layers so an HR officer has full context to review.
    """

    candidate_id   = decision.get("candidate_id", "UNKNOWN")
    candidate_name = decision.get("candidate_name", "N/A")
    timestamp      = decision.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z")

    rule_name      = policy_result.get("rule_fired", "UNKNOWN_RULE")
    regulation_ref = policy_result.get("regulation_reference", "N/A")
    features_used  = policy_result.get("features_used", [])

    classification = router_result.get("classification", "RED")
    confidence     = router_result.get("confidence", 0.0)
    shap_scores    = router_result.get("shap_scores", {})

    # Top 3 SHAP features by absolute value
    top_shap = sorted(
        shap_scores.items(),
        key=lambda kv: abs(kv[1]),
        reverse=True,
    )[:3]
    shap_lines = "\n".join(
        f"      {feat}: {score:+.4f}" for feat, score in top_shap
    ) or "      (none provided)"

    features_line = ", ".join(str(f) for f in features_used) if features_used else "N/A"

    description = f"""
=== AgentGuard v3 — RED Flag Incident Report ===

CANDIDATE INFORMATION
  Candidate ID   : {candidate_id}
  Candidate Name : {candidate_name}

POLICY VIOLATION
  Rule Fired           : {rule_name}
  Regulation Reference : {regulation_ref}
  Features Used by AI  : {features_line}

SHAP EXPLAINABILITY (Top 3 Features by |SHAP|)
{shap_lines}

RISK ROUTER RESULT
  Classification  : {classification}
  Confidence      : {confidence:.2%}

INCIDENT METADATA
  Timestamp (UTC) : {timestamp}
  System          : AgentGuard v3 AI Governance Platform

ACTION REQUIRED
  An HR officer must review this decision before it is released.
  The candidate decision remains in PENDING state until resolved.
""".strip()

    return description


def _build_payload(
    decision: dict,
    policy_result: dict,
    router_result: dict,
) -> dict:
    """Build the ServiceNow Table API incident payload."""

    candidate_id = decision.get("candidate_id", "UNKNOWN")
    rule_name    = policy_result.get("rule_fired", "UNKNOWN_RULE")

    return {
        "short_description": (
            f"AgentGuard RED Flag: Candidate {candidate_id} \u2014 {rule_name}"
        ),
        "description"  : _build_description(decision, policy_result, router_result),
        "category"     : "AI Governance",
        "subcategory"  : "Hiring Decision Review",
        "priority"     : "2",   # High
        "urgency"      : "2",
        "impact"       : "2",
    }


# ---------------------------------------------------------------------------
# PART A — Real ServiceNow integration
# ---------------------------------------------------------------------------

def create_incident(
    decision: dict,
    policy_result: dict,
    router_result: dict,
) -> dict:
    """
    Create a ServiceNow incident ticket for a RED-flagged hiring decision.

    Parameters
    ----------
    decision      : Output from the worker agent (candidate profile + AI decision).
    policy_result : Output from core/policy_engine.py.
    router_result : Output from core/risk_router.py.

    Returns
    -------
    dict with keys:
        ticket_id : str | None   — e.g. "INC0001234"
        status    : str          — "CREATED" | "TIMEOUT" | "ERROR"
        url       : str | None   — Full URL to the ticket (on success)
        error     : str | None   — Human-readable error message (on failure)
    """

    instance = os.getenv("SERVICENOW_INSTANCE", "")
    username = os.getenv("SERVICENOW_USERNAME", "")
    password = os.getenv("SERVICENOW_PASSWORD", "")

    if not instance:
        return {
            "ticket_id": None,
            "status": "ERROR",
            "url": None,
            "error": "SERVICENOW_INSTANCE is not set in environment / .env",
        }

    endpoint = f"https://{instance}/api/now/table/incident"
    headers  = {
        "Content-Type": "application/json",
        "Accept"       : "application/json",
    }
    payload = _build_payload(decision, policy_result, router_result)

    try:
        response = requests.post(
            url     = endpoint,
            auth    = (username, password),
            headers = headers,
            json    = payload,
            timeout = 5,          # 5-second hard limit
        )
        response.raise_for_status()

        data      = response.json().get("result", {})
        ticket_id = data.get("number", None)           # e.g. "INC0001234"
        sys_id    = data.get("sys_id", "")
        ticket_url = (
            f"https://{instance}/nav_to.do?uri=incident.do?sys_id={sys_id}"
            if sys_id else None
        )

        return {
            "ticket_id": ticket_id,
            "status"   : "CREATED",
            "url"      : ticket_url,
            "error"    : None,
        }

    except requests.Timeout:
        return {
            "ticket_id": None,
            "status"   : "TIMEOUT",
            "url"      : None,
            "error"    : (
                "ServiceNow did not respond within 5 seconds "
                "\u2014 decision auto-blocked"
            ),
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "ticket_id": None,
            "status"   : "ERROR",
            "url"      : None,
            "error"    : str(exc),
        }


# ---------------------------------------------------------------------------
# PART B — Mock function for development / testing
# ---------------------------------------------------------------------------

def create_incident_mock(
    decision: dict,
    policy_result: dict,
    router_result: dict,
) -> dict:
    """
    Return a realistic fake ServiceNow response without making any HTTP call.
    Use this when ENVIRONMENT=development in .env.

    Returns
    -------
    dict with ticket_id="INC0001234", status="CREATED", and a fake URL.
    """

    instance = os.getenv("SERVICENOW_INSTANCE", "dev00000.service-now.com")

    # Summarise what would have been sent so callers can inspect it
    payload = _build_payload(decision, policy_result, router_result)

    print("[MOCK] ServiceNow incident payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    return {
        "ticket_id": "INC0001234",
        "status"   : "CREATED",
        "url"      : (
            f"https://{instance}/nav_to.do"
            "?uri=incident.do?sys_id=mock-sys-id-000000000001"
        ),
        "error"    : None,
        "_mock"    : True,   # sentinel so callers know this is a fake response
    }


# ---------------------------------------------------------------------------
# PART C — Auto-switch dispatcher
# ---------------------------------------------------------------------------

def create_incident_with_fallback(
    decision: dict,
    policy_result: dict,
    router_result: dict,
) -> dict:
    """
    Public entry point for the rest of the AgentGuard application.

    Routing logic
    -------------
    ENVIRONMENT=development  →  create_incident_mock()
    ENVIRONMENT=production   →  create_incident()
    (default: mock)
    """

    environment = os.getenv("ENVIRONMENT", "development").strip().lower()

    if environment == "production":
        return create_incident(decision, policy_result, router_result)

    # development (default) — safe mock
    return create_incident_mock(decision, policy_result, router_result)


# ---------------------------------------------------------------------------
# PART D — Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Minimal synthetic inputs that mirror real AgentGuard layer outputs
    _sample_decision = {
        "candidate_id"  : "CAND-2025-0042",
        "candidate_name": "Priya Sharma",
        "ai_decision"   : "REJECT",
        "timestamp"     : "2025-05-04T06:00:00Z",
    }

    _sample_policy_result = {
        "rule_fired"           : "PROTECTED_PROXY_DETECTED",
        "regulation_reference" : "DPDP Act 2023 § 4(1)(b); EU AI Act Art. 6",
        "features_used"        : ["pin_code", "school_name", "mother_tongue"],
        "verdict"              : "BLOCK",
    }

    _sample_router_result = {
        "classification": "RED",
        "confidence"    : 0.91,
        "shap_scores"   : {
            "pin_code"     :  0.38,
            "school_name"  :  0.27,
            "mother_tongue":  0.19,
            "gpa"          : -0.05,
            "years_exp"    :  0.03,
        },
    }

    print("=" * 60)
    print("AgentGuard v3 — ServiceNow mock test")
    print("=" * 60)

    result = create_incident_with_fallback(
        _sample_decision,
        _sample_policy_result,
        _sample_router_result,
    )

    print("\n[RESULT]")
    print(json.dumps(result, indent=2, ensure_ascii=False))

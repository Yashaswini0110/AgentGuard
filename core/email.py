"""
AgentGuard v3 — Shortlist email dispatch (Gmail SMTP + development mock).

Environment
-----------
EMAIL_FROM              Sender address (e.g. agentguard.hr@gmail.com)
EMAIL_FROM_NAME         Display name for From header
GMAIL_APP_PASSWORD      Google App Password (spaces optional)
ENVIRONMENT             development → mock; production → real SMTP
EMAIL_ALLOWLIST         Optional comma-separated recipients (dev safety)
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_PLACEHOLDER_EMAIL_RE = re.compile(r"@example\.com$", re.I)


def artifact_is_shortlisted(artifact: dict[str, Any]) -> bool:
    """Mirror ui/app/src/lib/artifactHelpers.ts isShortlisted()."""
    hr = artifact.get("human_review") or {}
    if hr.get("action") == "APPROVE":
        return True
    tech = artifact.get("tech_review") or {}
    if tech.get("decision") == "ACCEPT":
        return True
    sup = artifact.get("supervisor_review") or {}
    if sup.get("supervisor_verdict") == "APPROVE":
        return True
    return (
        artifact.get("policy_result") == "PASS"
        and artifact.get("routing_classification") == "GREEN"
    )


def candidate_email_from_artifact(artifact: dict[str, Any]) -> str | None:
    direct = (artifact.get("candidate_email") or "").strip().lower()
    if direct:
        return direct
    wc = artifact.get("workflow_context") or {}
    nested = (wc.get("candidate_email") or "").strip().lower()
    return nested or None


def candidate_job_role_from_artifact(artifact: dict[str, Any]) -> str:
    raw = (artifact.get("job_role") or "").strip()
    if not raw:
        wc = artifact.get("workflow_context") or {}
        raw = (wc.get("job_role") or "").strip()
    if raw.lower().startswith("role:"):
        raw = raw[5:].strip()
    return raw or "the position"


def personalize_shortlist_message(
    template: str,
    *,
    candidate_name: str,
    role_title: str,
) -> str:
    name = (candidate_name or "").strip() or "Candidate"
    role = (role_title or "").strip() or "the position"
    return (
        template.replace("[Candidate Name]", name).replace("[Role Title]", role)
    )


DEFAULT_REJECTION_SUBJECT = "AgentGuard – Update on Your Application"

DEFAULT_REJECTION_BODY = """Dear [Candidate Name],

Thank you for your interest in the [Role Title] position and for taking the time to participate in our recruitment process.

After careful review of your application and assessment results, we regret to inform you that we will not be moving forward with your application at this time.

Reviewer Feedback / Reason for Decision:

[REJECTION_REASON_OR_REVIEWER_COMMENT]

We understand that receiving this outcome may be disappointing. Please note that this decision reflects the specific requirements and considerations for the current role and should not be viewed as a reflection of your overall capabilities or potential.

We sincerely appreciate the effort you invested throughout the process and encourage you to apply for future opportunities that align with your skills and experience.

We wish you every success in your professional journey and thank you again for considering this opportunity.

Warm regards,

AgentGuard Recruitment Team
agentguard.hr@gmail.com
+91 9000000001"""


def _plain_email_text(text: str) -> str:
    """Strip lightweight markdown for plain-text email bodies."""
    t = (text or "").replace("**", "")
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def personalize_rejection_message(
    template: str,
    *,
    candidate_name: str,
    role_title: str,
    rejection_reason: str,
) -> str:
    body = personalize_shortlist_message(
        template, candidate_name=candidate_name, role_title=role_title
    )
    reason = (rejection_reason or "").strip() or (
        "After review, your application was not selected to proceed to the next stage for this role."
    )
    return body.replace("[REJECTION_REASON_OR_REVIEWER_COMMENT]", reason)


def _allowlist_permits(email: str) -> bool:
    raw = (os.getenv("EMAIL_ALLOWLIST") or "").strip()
    if not raw:
        return True
    allowed = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return email.lower() in allowed


def _email_configured() -> bool:
    return bool((os.getenv("EMAIL_FROM") or "").strip()) and bool(
        (os.getenv("GMAIL_APP_PASSWORD") or "").strip()
    )


def send_shortlist_email_mock(
    *,
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    from_name: str,
    kind: str = "Shortlist email",
) -> dict[str, Any]:
    payload = {
        "to": to_email,
        "from": f"{from_name} <{from_email}>",
        "subject": subject,
        "body_preview": body[:240],
    }
    print(f"[MOCK] {kind} payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return {
        "status": "SENT",
        "provider_message_id": "mock-message-id",
        "error": None,
        "_mock": True,
    }


def send_shortlist_email(
    *,
    to_email: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """
    Send one plain-text email via Gmail SMTP.

    Returns dict: status (SENT | ERROR), provider_message_id, error.
    """
    from_email = (os.getenv("EMAIL_FROM") or "").strip()
    from_name = (os.getenv("EMAIL_FROM_NAME") or "AgentGuard Recruitment Team").strip()
    app_password = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")

    if not from_email or not app_password:
        return {
            "status": "ERROR",
            "provider_message_id": None,
            "error": "EMAIL_FROM or GMAIL_APP_PASSWORD is not set in environment / .env",
        }

    if not _allowlist_permits(to_email):
        return {
            "status": "ERROR",
            "provider_message_id": None,
            "error": f"Recipient {to_email} is not in EMAIL_ALLOWLIST",
        }

    msg = MIMEMultipart()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(from_email, app_password)
            smtp.send_message(msg)
        return {
            "status": "SENT",
            "provider_message_id": None,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "ERROR",
            "provider_message_id": None,
            "error": str(exc),
        }


def send_email_with_fallback(
    *,
    to_email: str,
    subject: str,
    body: str,
    mock_kind: str = "Email",
) -> dict[str, Any]:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    from_email = (os.getenv("EMAIL_FROM") or "agentguard.hr@gmail.com").strip()
    from_name = (os.getenv("EMAIL_FROM_NAME") or "AgentGuard Recruitment Team").strip()

    if environment == "production":
        return send_shortlist_email(to_email=to_email, subject=subject, body=body)

    return send_shortlist_email_mock(
        to_email=to_email,
        subject=subject,
        body=body,
        from_email=from_email,
        from_name=from_name,
        kind=mock_kind,
    )


def send_shortlist_email_with_fallback(
    *,
    to_email: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    return send_email_with_fallback(
        to_email=to_email, subject=subject, body=body, mock_kind="Shortlist email"
    )


def email_transport_status() -> dict[str, Any]:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    return {
        "environment": environment,
        "configured": _email_configured(),
        "transport": "gmail_smtp" if environment == "production" else "mock",
        "from": (os.getenv("EMAIL_FROM") or "").strip() or None,
        "allowlist_active": bool((os.getenv("EMAIL_ALLOWLIST") or "").strip()),
    }


def prepare_shortlist_dispatch(
    artifact: dict[str, Any],
    *,
    subject_template: str,
    body_template: str,
    sender_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Validate artifact, send email, return (result_row, email_dispatch_or_none).

    When send succeeds, email_dispatch is the dict to persist on the artifact.
    """
    decision_id = str(artifact.get("decision_id") or "")
    if not artifact_is_shortlisted(artifact):
        return (
            {"decision_id": decision_id, "status": "SKIPPED", "reason": "not_shortlisted"},
            None,
        )
    if artifact.get("email_dispatch"):
        return (
            {"decision_id": decision_id, "status": "SKIPPED", "reason": "already_sent"},
            None,
        )

    to_email = candidate_email_from_artifact(artifact)
    if not to_email or _PLACEHOLDER_EMAIL_RE.search(to_email):
        return (
            {
                "decision_id": decision_id,
                "status": "SKIPPED",
                "reason": "no_email_on_resume",
            },
            None,
        )

    role = candidate_job_role_from_artifact(artifact)
    name = (artifact.get("candidate_name") or artifact.get("candidate_id") or "Candidate").strip()
    subject = personalize_shortlist_message(
        subject_template, candidate_name=name, role_title=role
    )
    body = personalize_shortlist_message(
        body_template, candidate_name=name, role_title=role
    )

    send_result = send_shortlist_email_with_fallback(
        to_email=to_email, subject=subject, body=body
    )
    if send_result.get("status") != "SENT":
        return (
            {
                "decision_id": decision_id,
                "email": to_email,
                "status": "FAILED",
                "error": send_result.get("error"),
            },
            None,
        )

    dispatch = {
        "sent_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sent_by": sender_id,
        "to": to_email,
        "subject": subject,
        "role_title": role,
        "status": "SENT",
        "provider_message_id": send_result.get("provider_message_id"),
        "mock": bool(send_result.get("_mock")),
    }
    return (
        {"decision_id": decision_id, "email": to_email, "status": "SENT"},
        dispatch,
    )


def prepare_rejection_dispatch(
    artifact: dict[str, Any],
    *,
    sender_id: str,
    reviewer_comment: str,
    rejection_source: str,
    subject_template: str = DEFAULT_REJECTION_SUBJECT,
    body_template: str = DEFAULT_REJECTION_BODY,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Send rejection notice when HR or tech reviewer rejects a candidate.

    rejection_source: ``hr`` | ``tech``
    """
    decision_id = str(artifact.get("decision_id") or "")
    if artifact.get("rejection_email_dispatch"):
        return (
            {"decision_id": decision_id, "status": "SKIPPED", "reason": "already_sent"},
            None,
        )

    to_email = candidate_email_from_artifact(artifact)
    if not to_email or _PLACEHOLDER_EMAIL_RE.search(to_email):
        return (
            {
                "decision_id": decision_id,
                "status": "SKIPPED",
                "reason": "no_email_on_resume",
            },
            None,
        )

    role = candidate_job_role_from_artifact(artifact)
    name = (artifact.get("candidate_name") or artifact.get("candidate_id") or "Candidate").strip()
    comment = (reviewer_comment or "").strip()
    if not comment:
        if rejection_source == "tech":
            comment = (
                "Your application did not meet the technical requirements "
                "for this role at this time."
            )
        else:
            comment = (
                "After review, your application was not selected to proceed "
                "to the next stage for this role."
            )

    subject = _plain_email_text(subject_template)
    body = personalize_rejection_message(
        _plain_email_text(body_template),
        candidate_name=name,
        role_title=role,
        rejection_reason=comment,
    )

    send_result = send_email_with_fallback(
        to_email=to_email,
        subject=subject,
        body=body,
        mock_kind="Rejection email",
    )
    if send_result.get("status") != "SENT":
        return (
            {
                "decision_id": decision_id,
                "email": to_email,
                "status": "FAILED",
                "error": send_result.get("error"),
            },
            None,
        )

    dispatch = {
        "sent_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sent_by": sender_id,
        "to": to_email,
        "subject": subject,
        "role_title": role,
        "rejection_source": rejection_source,
        "reviewer_comment": comment,
        "status": "SENT",
        "provider_message_id": send_result.get("provider_message_id"),
        "mock": bool(send_result.get("_mock")),
    }
    return (
        {"decision_id": decision_id, "email": to_email, "status": "SENT"},
        dispatch,
    )

"""
AgentGuard v2 — F2: Policy database access (M1)

Supabase-backed CRUD for runtime policy rules + an audit trail. Mirrors the
client pattern in core/supabase_storage.py. The policy engine reads ACTIVE
rules from here at startup and on hot-reload; if Supabase is unavailable the
caller falls back to the hardcoded defaults (PRD §5.1).

Tables are created via db/policies_schema.sql (PostgREST cannot do DDL).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from core import policy_engine

load_dotenv()
logger = logging.getLogger("agentguard.policy_store")

_client: Optional[Client] = None

POLICIES_TABLE = "policies"
AUDIT_TABLE = "policy_audit_log"


def _get_client() -> Client:
    """Lazy singleton — avoids constructing the client at import time."""
    global _client
    if _client is None:
        url = (os.getenv("SUPABASE_URL") or "").strip()
        key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        if not url or not key:
            raise RuntimeError(
                "Supabase credentials missing. Set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY in your .env."
            )
        _client = create_client(url, key)
    return _client


def _row_to_rule(row: dict) -> dict:
    """Map a DB policy row to the engine rule shape {name, ...content_json}."""
    content = row.get("content_json") or {}
    return {"name": row.get("name"), **content}


def append_audit(policy_id: Optional[str], action: str, changed_by: str,
                 detail: str = "") -> None:
    """Best-effort audit write; never raises (auditing must not block actions)."""
    try:
        _get_client().table(AUDIT_TABLE).insert({
            "policy_id": policy_id,
            "action": action,
            "changed_by": changed_by or "unknown",
            "detail": detail,
        }).execute()
    except Exception as exc:
        logger.warning("policy audit write failed: %s", exc)


def load_active_policies() -> list[dict]:
    """Active rules in the engine's rule shape. Raises on DB error (caller falls back)."""
    resp = _get_client().table(POLICIES_TABLE).select("*").eq("is_active", True).execute()
    return [_row_to_rule(r) for r in (resp.data or [])]


def list_policies() -> list[dict]:
    """All policies (newest first) for the admin list view."""
    resp = (
        _get_client().table(POLICIES_TABLE).select("*")
        .order("created_at", desc=True).execute()
    )
    return resp.data or []


def get_policy(policy_id: str) -> Optional[dict]:
    resp = _get_client().table(POLICIES_TABLE).select("*").eq("id", policy_id).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def insert_policy(name: str, content_json: dict, uploaded_by: str,
                  source: str = "json", is_active: bool = False) -> dict:
    """Insert a policy (INACTIVE by default) and log the creation."""
    row = {
        "name": name,
        "content_json": content_json,
        "is_active": is_active,
        "source": source,
        "uploaded_by": uploaded_by or "unknown",
    }
    resp = _get_client().table(POLICIES_TABLE).insert(row).execute()
    created = (resp.data or [row])[0]
    append_audit(created.get("id"), "CREATE", uploaded_by,
                 detail=f"name={name} source={source} active={is_active}")
    return created


def retire_other_active_versions(name: str, keep_id: str, changed_by: str) -> list[str]:
    """
    Deactivate any OTHER active policy that shares this name, so at most one
    version of a rule is ever active. Superseded rows are kept (history), just
    flipped inactive. Returns the retired ids.
    """
    if not name:
        return []
    resp = (
        _get_client().table(POLICIES_TABLE).select("id")
        .eq("name", name).eq("is_active", True).neq("id", keep_id).execute()
    )
    retired: list[str] = []
    for row in (resp.data or []):
        rid = row["id"]
        _get_client().table(POLICIES_TABLE).update({"is_active": False}).eq("id", rid).execute()
        append_audit(rid, "DEACTIVATE", changed_by, detail=f"auto-retired: superseded by {keep_id}")
        retired.append(rid)
    return retired


def set_policy_active(policy_id: str, is_active: bool, changed_by: str) -> Optional[dict]:
    """
    Activate/deactivate a policy (no delete) and log it. On activation, any other
    active rule with the same name is auto-retired so only one version enforces.
    """
    resp = (
        _get_client().table(POLICIES_TABLE).update({"is_active": is_active})
        .eq("id", policy_id).execute()
    )
    rows = resp.data or []
    if not rows:
        return None
    updated = rows[0]
    append_audit(policy_id, "ACTIVATE" if is_active else "DEACTIVATE", changed_by)
    updated["retired_version_ids"] = (
        retire_other_active_versions(updated.get("name"), keep_id=policy_id, changed_by=changed_by)
        if is_active else []
    )
    return updated


def refresh_active_policies() -> dict:
    """
    Load active policies from Supabase into the engine's in-memory cache. Used
    at startup and as the hot-reload after an activate/deactivate.

    Falls back to the hardcoded defaults if the database is unavailable, so
    enforcement is never lost (PRD §5.1). Returns a small status dict.
    """
    try:
        seed_defaults_if_empty()  # ensure a fresh DB still carries the baseline
        rules = load_active_policies()
        if not rules:
            policy_engine.reset_to_default_policies()
            return {"source": "default", "count": len(policy_engine.get_active_policies())}
        policy_engine.set_active_policies(rules)
        return {"source": "database", "count": len(rules)}
    except Exception as exc:
        policy_engine.reset_to_default_policies()
        logger.warning("policy DB unavailable; using hardcoded defaults: %s", exc)
        return {
            "source": "fallback",
            "count": len(policy_engine.get_active_policies()),
            "error": str(exc),
        }


def seed_defaults_if_empty() -> int:
    """
    Populate the policies table with the hardcoded defaults (ACTIVE) when it is
    empty, so a fresh DB still enforces the baseline rules. Returns the number
    of rules seeded.
    """
    existing = _get_client().table(POLICIES_TABLE).select("id").limit(1).execute()
    if existing.data:
        return 0
    seeded = 0
    for rule in policy_engine._default_enforced_rules():
        name = rule["name"]
        content = {k: v for k, v in rule.items() if k != "name"}
        insert_policy(name, content, uploaded_by="system",
                      source="default", is_active=True)
        seeded += 1
    logger.info("seeded %d default policies into Supabase", seeded)
    return seeded

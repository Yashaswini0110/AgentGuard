"""
AgentGuard v2 — F9: artifact storage abstraction (M1)

Dual-write artifacts to Supabase AND the local filesystem; read Supabase first
and fall back to the file. The shared DB makes artifacts visible across
containers; the filesystem stays as a live backup. If Supabase is unavailable,
everything degrades to filesystem-only — an artifact is never lost.

Tables are created via db/artifacts_schema.sql.
"""

from __future__ import annotations

import glob
import hashlib
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentguard.artifact_store")

# Cwd-relative, matching the rest of the codebase (uvicorn runs from the repo
# root). Tests rely on this via monkeypatch.chdir().
ARTIFACTS_DIR = "artifacts"
TABLE = "artifacts"
SCHEMA_VERSION = 1

_client = None
_client_tried = False


def _supabase():
    """
    Cached Supabase client, or None. The DB is optional; filesystem is the
    fallback. Set AGENTGUARD_ARTIFACT_DB=0 to disable DB writes (tests / CI).
    """
    global _client, _client_tried
    if os.getenv("AGENTGUARD_ARTIFACT_DB", "1") == "0":
        return None
    if _client_tried:
        return _client
    _client_tried = True
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
    except Exception as exc:
        logger.warning("artifact DB client unavailable: %s", exc)
        _client = None
    return _client


def _fs_path(decision_id: str) -> str:
    return os.path.join(ARTIFACTS_DIR, f"{decision_id}.json")


def _compute_hash(artifact: dict) -> str:
    body = {k: v for k, v in artifact.items() if k != "artifact_hash"}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_hash(artifact: dict) -> bool:
    """True if artifact_hash matches a re-hash of the body (sans hash field)."""
    return artifact.get("artifact_hash", "") == _compute_hash(artifact)


def _to_row(artifact: dict) -> dict:
    return {
        "decision_id": artifact["decision_id"],
        "body": artifact,
        "artifact_hash": artifact.get("artifact_hash", ""),
        "schema_version": SCHEMA_VERSION,
        "created_at": artifact.get("timestamp"),
    }


def save(artifact: dict) -> str:
    """
    Dual-write: filesystem (always) + Supabase (best-effort). Returns the file path.

    The artifact_hash is (re)computed from the current body before persisting, so a
    modified artifact (e.g. a review override) always has a valid integrity hash.
    """
    artifact = dict(artifact)
    artifact["artifact_hash"] = _compute_hash(artifact)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    path = _fs_path(artifact["decision_id"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)

    client = _supabase()
    if client is not None:
        try:
            client.table(TABLE).upsert(_to_row(artifact)).execute()
        except Exception as exc:
            logger.warning("artifact DB upsert failed for %s: %s", artifact.get("decision_id"), exc)
    return os.path.abspath(path)


def load(decision_id: str) -> Optional[dict]:
    """Supabase first, filesystem fallback."""
    client = _supabase()
    if client is not None:
        try:
            resp = client.table(TABLE).select("body").eq("decision_id", decision_id).execute()
            if resp.data:
                return resp.data[0]["body"]
        except Exception as exc:
            logger.warning("artifact DB load failed for %s: %s", decision_id, exc)
    path = _fs_path(decision_id)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None
    return None


def _fs_all() -> list[dict]:
    out: list[dict] = []
    for fp in sorted(glob.glob(os.path.join(ARTIFACTS_DIR, "*.json")),
                     key=os.path.getmtime, reverse=True):
        try:
            with open(fp, encoding="utf-8") as fh:
                out.append(json.load(fh))
        except Exception:
            pass
    return out


def _db_all(limit: Optional[int]) -> list[dict]:
    client = _supabase()
    if client is None:
        return []
    try:
        q = client.table(TABLE).select("body").order("created_at", desc=True)
        if limit:
            q = q.limit(limit)
        resp = q.execute()
        return [r["body"] for r in (resp.data or [])]
    except Exception as exc:
        logger.warning("artifact DB scan failed: %s", exc)
        return []


def load_all(limit: Optional[int] = None) -> list[dict]:
    """Union of DB + filesystem artifacts, deduped by decision_id (DB wins), newest first."""
    merged: dict[str, dict] = {}
    for a in _fs_all():                       # filesystem first
        did = a.get("decision_id")
        if did:
            merged[did] = a
    for a in _db_all(limit * 3 if limit else None):   # DB overrides (authoritative shared copy)
        did = a.get("decision_id")
        if did:
            merged[did] = a
    items = sorted(merged.values(), key=lambda a: a.get("timestamp") or "", reverse=True)
    return items[:limit] if limit else items


def list_recent(limit: int = 50) -> list[dict]:
    """Most-recent artifacts across DB + filesystem (deduped)."""
    return load_all(limit=limit)


def backfill_from_filesystem(dry_run: bool = False) -> dict:
    """
    One-time migration: upsert every filesystem artifact into Supabase, verifying
    each SHA-256 first. Files are kept (never deleted). Hash mismatches are
    reported and NOT migrated. Idempotent (upsert by decision_id).
    """
    client = _supabase()
    if client is None:
        return {"error": "Supabase not available (set creds / AGENTGUARD_ARTIFACT_DB)", "migrated": 0}

    total = migrated = errors = 0
    mismatch_ids: list[str] = []
    for art in _fs_all():
        total += 1
        if not verify_hash(art):
            mismatch_ids.append(art.get("decision_id"))
            continue
        if dry_run:
            migrated += 1
            continue
        try:
            client.table(TABLE).upsert(_to_row(art)).execute()
            migrated += 1
        except Exception as exc:
            errors += 1
            logger.warning("backfill upsert failed for %s: %s", art.get("decision_id"), exc)
    return {
        "total": total,
        "migrated": migrated,
        "hash_mismatch": len(mismatch_ids),
        "errors": errors,
        "mismatch_ids": mismatch_ids[:20],
        "dry_run": dry_run,
    }

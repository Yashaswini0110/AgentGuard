"""
AgentGuard v3 — Supabase Storage helper for candidate resumes.

Responsibilities
----------------
- Upload raw PDF / DOCX bytes to a private Supabase Storage bucket.
- Mirror file metadata (path, mime, hash, size) into the public.candidate_files
  Postgres table so the FastAPI layer can resolve a `decision_id` to a file.
- Mint short-lived signed URLs that allow the React dashboard to render the
  resume inline inside an <iframe> (Content-Disposition: inline) without
  forcing a download or proxying bytes through FastAPI.

Environment
-----------
SUPABASE_URL                Project URL (e.g. https://xxxx.supabase.co)
SUPABASE_SERVICE_ROLE_KEY   Service role JWT — backend only, bypasses RLS
SUPABASE_BUCKET             Bucket name (default: "resumes")

Schema reference
----------------
create table public.candidate_files (
  decision_id      uuid        primary key,
  candidate_id     text        not null,
  original_name    text        not null,
  mime_type        text        not null default 'application/pdf',
  storage_path     text        not null,
  sha256_hash      text        not null,
  file_size_bytes  integer     not null,
  uploaded_at      timestamptz not null default now()
);
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()
logger = logging.getLogger("agentguard.supabase")

_client: Optional[Client] = None
_BUCKET = (os.getenv("SUPABASE_BUCKET") or "resumes").strip()


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


def _ext_for_mime(mime_type: str) -> str:
    if mime_type == "application/pdf":
        return ".pdf"
    if mime_type.endswith("wordprocessingml.document"):
        return ".docx"
    return ".bin"


def upload_resume(
    *,
    decision_id: str,
    raw_bytes: bytes,
    original_name: str,
    candidate_id: str,
    mime_type: str = "application/pdf",
) -> dict:
    """
    Upload a single resume to Supabase Storage and upsert its metadata row.

    Idempotent — re-running for the same `decision_id` overwrites both the
    object and the row, which is what we want when batch ingest re-runs.
    """
    client = _get_client()
    storage_path = f"{decision_id}{_ext_for_mime(mime_type)}"

    # `upsert: "true"` lets us re-upload without 409 on the same key.
    client.storage.from_(_BUCKET).upload(
        path=storage_path,
        file=raw_bytes,
        file_options={"content-type": mime_type, "upsert": "true"},
    )

    row = {
        "decision_id": decision_id,
        "candidate_id": candidate_id,
        "original_name": original_name,
        "mime_type": mime_type,
        "storage_path": storage_path,
        "sha256_hash": hashlib.sha256(raw_bytes).hexdigest(),
        "file_size_bytes": len(raw_bytes),
    }
    client.table("candidate_files").upsert(row).execute()

    logger.info(
        "supabase_resume_uploaded decision_id=%s bytes=%d path=%s",
        decision_id,
        len(raw_bytes),
        storage_path,
    )
    return row


def get_signed_resume_url(decision_id: str, expires_in: int = 300) -> Optional[dict]:
    """
    Return a short-lived signed URL plus original-filename metadata so the
    dashboard can render the PDF inline inside an <iframe>.

    `download=False` ensures Supabase serves the object with
    `Content-Disposition: inline`, which is what makes browsers render
    instead of download.
    """
    client = _get_client()
    res = (
        client.table("candidate_files")
        .select("*")
        .eq("decision_id", decision_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None

    row = res.data[0]
    signed = client.storage.from_(_BUCKET).create_signed_url(
        path=row["storage_path"],
        expires_in=expires_in,
        options={"download": False},
    )
    return {
        "url": signed["signedURL"],
        "original_name": row["original_name"],
        "mime_type": row["mime_type"],
        "file_size_bytes": row["file_size_bytes"],
        "sha256_hash": row["sha256_hash"],
        "expires_in": expires_in,
    }


def delete_resume(decision_id: str) -> bool:
    """
    Remove the file from the bucket and its metadata row.

    Used for retention policies and DPDP "right to erasure" requests.
    Returns False if no row existed.
    """
    client = _get_client()
    res = (
        client.table("candidate_files")
        .select("storage_path")
        .eq("decision_id", decision_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return False

    client.storage.from_(_BUCKET).remove([res.data[0]["storage_path"]])
    client.table("candidate_files").delete().eq("decision_id", decision_id).execute()
    logger.info("supabase_resume_deleted decision_id=%s", decision_id)
    return True

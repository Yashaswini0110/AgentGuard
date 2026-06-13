"""
F9 artifact store tests — filesystem path + hash integrity (DB disabled via
conftest's AGENTGUARD_ARTIFACT_DB=0, so these are deterministic and offline).
"""

import hashlib
import json

import pytest

from core import artifact_store as store


def _artifact(decision_id: str, ts: str = "2026-06-13T10:00:00+00:00", level: str = "GREEN") -> dict:
    body = {"decision_id": decision_id, "timestamp": ts, "routing_classification": level}
    body["artifact_hash"] = "sha256:" + hashlib.sha256(
        json.dumps(body, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return body


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "artifacts").mkdir()
    yield


def test_verify_hash_detects_tampering():
    art = _artifact("x1")
    assert store.verify_hash(art) is True
    art["routing_classification"] = "RED"   # mutate after hashing
    assert store.verify_hash(art) is False


def test_save_load_roundtrip_preserves_hash():
    store.save(_artifact("x2"))
    loaded = store.load("x2")
    assert loaded is not None
    assert loaded["decision_id"] == "x2"
    assert store.verify_hash(loaded) is True


def test_load_missing_returns_none():
    assert store.load("does-not-exist") is None


def test_load_all_dedup_and_newest_first():
    store.save(_artifact("a", ts="2026-06-13T09:00:00+00:00"))
    store.save(_artifact("b", ts="2026-06-13T11:00:00+00:00"))
    store.save(_artifact("a", ts="2026-06-13T09:00:00+00:00"))  # re-save same id
    ids = [a["decision_id"] for a in store.load_all()]
    assert ids == ["b", "a"]                # newest first, deduped


def test_list_recent_honours_limit():
    for i in range(5):
        store.save(_artifact(f"r{i}", ts=f"2026-06-13T1{i}:00:00+00:00"))
    assert len(store.list_recent(3)) == 3

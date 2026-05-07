"""Artifact persistence helpers shared by REST routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

ARTIFACTS_DIR = Path("artifacts")


def artifact_path(decision_id: str) -> Path:
    return ARTIFACTS_DIR / f"{decision_id}.json"


def load_artifact(decision_id: str) -> dict:
    path = artifact_path(decision_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact '{decision_id}' not found.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_artifact_file(artifact: dict) -> None:
    path = artifact_path(str(artifact["decision_id"]))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)

"""
F5 demo seeder — generate a realistic multi-day artifact history with a genuine
recent RED spike so GET /drift/status produces a real drift alert.

This seeds *data*, not the threshold. The drift math is untouched; we simply
create past decisions: normal RED rate (~baseline) for older days, then a spike
for the most recent 3 days so the "baseline x 1.5 for 3 consecutive days" rule
fires honestly.

Usage:
    python scripts/seed_drift_demo.py          # write seed artifacts
    python scripts/seed_drift_demo.py --clean   # remove them

All seeded files are named seed-drift-*.json for easy cleanup. Uses only the
standard library, so it runs on the host (no ML deps needed) and writes into the
bind-mounted artifacts/ directory the API reads.
"""

import argparse
import datetime
import hashlib
import json
import random
import uuid
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
MODEL_HASH_FILE = Path(__file__).resolve().parents[1] / "models" / "model_version_hash.txt"
SEED_PREFIX = "seed-drift-"

UTC = datetime.timezone.utc

FIRST_NAMES = ["Priya", "Arjun", "Ananya", "Rohan", "Kavya", "Vikram", "Sneha",
               "Aditya", "Meera", "Karthik", "Divya", "Rahul", "Pooja", "Sanjay"]
LAST_NAMES = ["Sharma", "Iyer", "Reddy", "Nair", "Gupta", "Patel", "Das",
              "Menon", "Rao", "Singh", "Bose", "Kulkarni"]

# Per-day decision plan: (days_ago, n_red, n_yellow, n_green)
# Older days sit near the 0.25 baseline; the most recent 3 days spike to ~0.56.
DAY_PLAN = [
    (6, 4, 2, 10),  # ~0.25 RED  (normal)
    (5, 4, 2, 10),  # ~0.25
    (4, 5, 2,  9),  # ~0.31  (below threshold 0.3789)
    (3, 4, 3,  9),  # ~0.25  (normal — keeps the spike clearly "recent")
    (2, 9, 2,  5),  # ~0.56  (SPIKE)
    (1, 9, 2,  5),  # ~0.56  (SPIKE)
    (0, 9, 2,  5),  # ~0.56  (SPIKE)
]


def _model_hash() -> str:
    try:
        return MODEL_HASH_FILE.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def _make_artifact(days_ago: int, level: str, rng: random.Random, model_hash: str,
                   now: datetime.datetime) -> dict:
    """Build one tamper-valid artifact for a given routing class."""
    # Anchor at the day's midnight (UTC) and pick a time within that day. For
    # today, never go past `now` (future timestamps are filtered out of the
    # drift window).
    midnight = (now - datetime.timedelta(days=days_ago)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if days_ago == 0:
        span = max((now - midnight).total_seconds() - 60, 60)
    else:
        span = 86400 - 1
    ts = midnight + datetime.timedelta(seconds=rng.uniform(0, span))
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    decision_id = f"{SEED_PREFIX}{uuid.uuid4().hex[:12]}"

    if level == "RED":
        outcome, conf = "REJECT", round(rng.uniform(0.40, 0.62), 2)
    elif level == "YELLOW":
        outcome, conf = "REVIEW", round(rng.uniform(0.55, 0.70), 2)
    else:
        outcome, conf = "APPROVE", round(rng.uniform(0.80, 0.95), 2)

    body = {
        "decision_id": decision_id,
        "timestamp": ts.isoformat(),
        "candidate_id": f"CAND-SEED-{rng.randint(1000, 9999)}",
        "candidate_name": name,
        "decision_outcome": outcome,
        "policy_result": "PASS",          # model-driven RED, not a policy block
        "policy_violations": [],
        "policy_rule_cited": "NONE",
        "regulation_reference": "N/A",
        "routing_classification": level,
        "confidence_score": conf,
        "features_used": ["years_of_experience", "skill_match_score", "interview_score"],
        "shap_scores": {
            "skill_match_score": round(rng.uniform(-0.4, 0.4), 3),
            "interview_score": round(rng.uniform(-0.3, 0.3), 3),
            "years_of_experience": round(rng.uniform(-0.3, 0.3), 3),
        },
        "model_version_hash": model_hash,
        "servicenow_ticket_id": None,
    }
    canonical = json.dumps(body, sort_keys=True)
    body["artifact_hash"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return body


def seed() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    model_hash = _model_hash()
    now = datetime.datetime.now(UTC)
    written = 0
    red = total = 0
    for days_ago, n_red, n_yellow, n_green in DAY_PLAN:
        levels = ["RED"] * n_red + ["YELLOW"] * n_yellow + ["GREEN"] * n_green
        rng.shuffle(levels)
        for level in levels:
            art = _make_artifact(days_ago, level, rng, model_hash, now)
            (ARTIFACTS_DIR / f"{art['decision_id']}.json").write_text(
                json.dumps(art, indent=2, sort_keys=True), encoding="utf-8"
            )
            written += 1
            total += 1
            red += level == "RED"
    print(f"Seeded {written} artifacts across {len(DAY_PLAN)} days "
          f"({red}/{total} RED = {red/total:.2%}). Recent 3 days are a deliberate spike.")


def clean() -> None:
    files = list(ARTIFACTS_DIR.glob(f"{SEED_PREFIX}*.json"))
    for fp in files:
        fp.unlink()
    print(f"Removed {len(files)} seeded artifacts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed/clean F5 drift demo artifacts.")
    parser.add_argument("--clean", action="store_true", help="Remove seeded artifacts.")
    args = parser.parse_args()
    clean() if args.clean else seed()

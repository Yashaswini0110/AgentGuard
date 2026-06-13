"""
F9 one-time migration: backfill existing filesystem artifacts into Supabase.

Verifies each artifact's SHA-256 before upserting; mismatches are reported and
skipped. JSON files are kept as backup. Idempotent.

Usage:
    python scripts/migrate_artifacts_to_supabase.py --dry-run   # verify only
    python scripts/migrate_artifacts_to_supabase.py             # migrate

Run AFTER the team has signed off on db/artifacts_schema.sql and it has been
applied. New artifacts already populate the DB via dual-write; this is only for
pre-existing ones.
"""

import argparse
import json

from core import artifact_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill filesystem artifacts into Supabase.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Verify hashes and count without writing to Supabase.")
    args = parser.parse_args()

    result = artifact_store.backfill_from_filesystem(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if result.get("hash_mismatch"):
        print(f"\nWARNING: {result['hash_mismatch']} artifact(s) failed hash verification "
              "and were NOT migrated. Investigate before re-running.")


if __name__ == "__main__":
    main()

# Contract — Artifact storage (F9 Artifact DB Migration)

**Owner:** M1 · **Reviewers:** whole team (schema sign-off required before backfill) · **Support:** M4 (tests read paths after)

Move decision artifacts from per-container JSON files to a shared Supabase
table, so all instances see the same artifacts. **Dual-write** during transition:
every artifact is written to BOTH Supabase and the local JSON file; reads hit
Supabase first and fall back to the file.

## `public.artifacts`
| column | type | notes |
|---|---|---|
| `decision_id` | text PK | not all ids are UUIDs (seed/test data) |
| `body` | jsonb | the **full** artifact JSON — the exact hashed content |
| `artifact_hash` | text | `sha256:...`, copied out for fast tamper-check queries |
| `schema_version` | int | **metadata column, NOT in the hashed body** — adding it to the body would invalidate every existing SHA-256 |
| `created_at` | timestamptz | set from the artifact `timestamp` |

## Integrity guarantee (PRD §5.2)
`artifact_hash` = `sha256:` + SHA-256 of the artifact body with the `artifact_hash`
field removed, serialized as `json.dumps(body, sort_keys=True)`. The migration
**verifies this for every row** and refuses to claim success on a mismatch. The
hashed body is stored byte-for-byte; `schema_version`/`created_at` live outside it.

## Access (via `core/artifact_store.py`)
- `save(artifact)` → write filesystem (always) + upsert Supabase (best-effort).
- `load(decision_id)` → Supabase first, filesystem fallback.
- `list_recent(limit)` / `load_all(limit)` → union of DB + filesystem, deduped by
  `decision_id` (DB wins), newest first. Degrades to filesystem-only if the DB is
  unavailable — artifacts are never lost.

## Migration (gated)
`scripts/migrate_artifacts_to_supabase.py` reads existing `artifacts/*.json`,
verifies each hash, and upserts. JSON files are **kept as backup**. The
production run waits on team schema sign-off; new artifacts populate the DB
automatically via dual-write in the meantime.

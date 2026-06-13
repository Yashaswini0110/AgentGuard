-- AgentGuard v2 — F9 Artifact storage schema (M1)
-- Run once in the Supabase SQL editor (PostgREST cannot issue DDL).
-- Team must sign off on this schema before the backfill migration runs.

create table if not exists public.artifacts (
  decision_id    text        primary key,   -- text: not all ids are UUIDs (seeds/tests)
  body           jsonb       not null,       -- the full artifact JSON (the hashed content)
  artifact_hash  text        not null,       -- sha256:... copied out for fast tamper queries
  schema_version integer     not null default 1,  -- metadata only; NOT part of the hashed body
  created_at     timestamptz not null default now()
);

create index if not exists artifacts_hash_idx    on public.artifacts (artifact_hash);
create index if not exists artifacts_created_idx on public.artifacts (created_at desc);

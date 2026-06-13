-- AgentGuard v2 — F2 Policy Database schema (M1)
-- Run once in the Supabase SQL editor. The Python client (PostgREST) cannot
-- issue DDL, so these tables must be created here.

create table if not exists public.policies (
  id           uuid        primary key default gen_random_uuid(),
  name         text        not null,
  content_json jsonb       not null,           -- {severity, regulation, reason, condition}
  is_active    boolean     not null default false,  -- uploads land INACTIVE for admin review
  source       text        not null default 'json', -- default | json | pdf
  created_at   timestamptz not null default now(),
  uploaded_by  text
);

create index if not exists policies_active_idx on public.policies (is_active);

create table if not exists public.policy_audit_log (
  id         uuid        primary key default gen_random_uuid(),
  policy_id  uuid,
  action     text        not null,             -- CREATE | ACTIVATE | DEACTIVATE
  changed_by text,
  detail     text,
  changed_at timestamptz not null default now()
);

create index if not exists policy_audit_policy_idx on public.policy_audit_log (policy_id);

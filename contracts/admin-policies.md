# Contract — `POST/GET/PATCH /admin/policies` (F2 Policy Database)

**Owner:** M1 (Backend/ML) · **Consumers:** M3 (F1 Admin Dashboard API wrapper), M2 (policy list UI)

Manage the runtime policy rules that the Layer-1 engine enforces. Rules are
stored in Supabase (`policies` table) and hot-reloaded into the engine. **Every
uploaded or extracted rule lands INACTIVE** and must be explicitly activated by
an admin before it enforces.

> **Auth:** ungated in this milestone — the `admin` role does not exist yet
> (arrives with F1/F8). M3 wraps these behind admin gating when that lands.

## Rule shape (`content_json`)
```json
{
  "severity": "RED",
  "regulation": "EU AI Act Article 5(1)(f)",
  "reason": "Emotion recognition in hiring is prohibited",
  "condition": { "type": "feature_present", "features": ["emotion_score"], "match": "any" }
}
```
Condition types: `feature_present` (`match`: `any`|`all` of `features`) ·
`pattern_match` (`patterns` found in `target`, e.g. `raw_input`).

## `POST /admin/policies`
Create policy rule(s). Accepts **either**:
- **JSON body** — one rule: `{ name, content_json, uploaded_by }`
- **multipart PDF** — `file=<pdf>`, `uploaded_by=<str>`: text is extracted and
  Gemini proposes one or more rule candidates (each saved INACTIVE for review).

**Response `201`:**
```json
{ "created": [ { "id": "uuid", "name": "...", "is_active": false, "severity": "RED", "source": "json|pdf" } ],
  "message": "1 rule created (inactive). Review and activate." }
```
Errors: `400` invalid rule shape · `415` non-PDF upload · `502` extraction failed.

## `GET /admin/policies`
List all policies for the admin view.
```json
{ "count": 8, "policies": [
  { "id": "uuid", "name": "EMOTION_SCORE_IN_HIRING_PROHIBITED", "severity": "RED",
    "is_active": true, "created_at": "2026-06-13T...", "uploaded_by": "admin",
    "source": "default|json|pdf" } ] }
```

## `PATCH /admin/policies/{id}`
Activate / deactivate **without deleting**. Triggers an in-memory hot-reload so
the change takes effect immediately (no restart).
- Body: `{ "is_active": true, "changed_by": "admin" }`
- Response `200`: the updated policy. `404` if id not found.

## Guarantees
- New/extracted rules never enforce until activated (`is_active=false` on create).
- Every create/activate/deactivate appends to `policy_audit_log` (who/what/when).
- If Supabase is unavailable, the engine falls back to the hardcoded defaults and
  these write endpoints return `503` (reads of defaults still work).

## Who calls it
- M3 — F1 Admin Dashboard API proxies these behind admin auth.
- M2 — policy list + activate/deactivate toggle UI.

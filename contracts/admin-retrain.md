# Contract — `POST /admin/retrain` & `GET /admin/retrain/status`

**Owner:** M1 (Backend/ML) · **Feature:** F5.2 Retraining Trigger · **Consumers:** M2 (Admin "Initiate Retraining" button)

Manual-triggered (v2) background retrain of the Layer-2 risk router. Retrains on
accumulated artifacts + the synthetic baseline, cross-validates, and **hot-swaps
the live model only if the new accuracy ≥ the current model's**. The previous
model is archived for rollback.

## `POST /admin/retrain`
- **Auth:** Admin role (demo role gating in v2).
- **Body:** none (optional `{ "min_accuracy_delta": 0.0 }` reserved for later).
- **Response `202 Accepted`:**
```json
{ "job_id": "a3f7c2d1", "status": "STARTED" }
```
- **Response `409 Conflict`:** a retrain job is already running.

## `GET /admin/retrain/status`
- **Response `200 OK`:**
```json
{
  "job_id": "a3f7c2d1",
  "status": "RUNNING",
  "started_at": "2026-06-13T10:00:00Z",
  "finished_at": null,
  "old_accuracy": 0.91,
  "new_accuracy": null,
  "swapped": false,
  "model_version_hash": "sha256:7f4e…",
  "message": "Training on 320 artifacts + synthetic baseline"
}
```

| `status` | Meaning |
|---|---|
| `IDLE` | no job has run |
| `RUNNING` | retrain in progress |
| `DONE` | finished; check `swapped` |
| `FAILED` | error; live model untouched, see `message` |

## Behaviour / guardrails (PRD §5.1)
- **Atomic, last-step swap:** the live `router_model.pkl` is only replaced after the new model passes cross-validation and beats the incumbent. A failure at any point leaves the live model untouched.
- **Rollback:** the current model is copied to `models/archive/<old_hash>.pkl` before any swap.
- **Honest baseline:** on swap, `models/model_meta.json` is recomputed (new `baseline_red_rate`, hash, accuracies).
- **Never blocks the pipeline:** runs as a background job; the governance pipeline keeps serving the old model until the swap moment.

## Error cases
| Status | When |
|---|---|
| 202 | job started |
| 409 | job already running |
| 500 | failed to enqueue (filesystem/permission) |

## Who calls it
- M2 — Admin Dashboard "Initiate Retraining" button → `POST`, then polls `GET …/status`.

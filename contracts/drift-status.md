# Contract — `GET /drift/status`

**Owner:** M1 (Backend/ML) · **Feature:** F5 Data Drift · **Consumers:** M2 (drift banner UI), M3 (drift-alert email)

Drift is defined as: the rolling **7-day RED rate** exceeding the model's
**training baseline RED rate × 1.5** for **3 consecutive days**.

## Request
- **Method / Path:** `GET /drift/status`
- **Auth:** none in v2 (demo). Visible on HR + Admin dashboards.
- **Body:** none

## Response `200 OK`
```json
{
  "is_drifting": false,
  "current_red_rate": 0.18,
  "baseline_red_rate": 0.12,
  "threshold": 0.18,
  "days_exceeded": 1,
  "days_required": 3,
  "window_days": 7,
  "total_decisions": 64,
  "daily": [
    { "date": "2026-06-13", "red_rate": 0.20, "total": 20 },
    { "date": "2026-06-12", "red_rate": 0.10, "total": 18 }
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `is_drifting` | bool | `days_exceeded >= days_required` |
| `current_red_rate` | float 0–1 | RED ÷ total over the last `window_days` |
| `baseline_red_rate` | float 0–1 | RED fraction in the training set (from `models/model_meta.json`) |
| `threshold` | float 0–1 | `baseline_red_rate × 1.5` |
| `days_exceeded` | int | consecutive most-recent days with daily RED rate > `threshold` |
| `days_required` | int | constant `3` |
| `window_days` | int | constant `7` |
| `total_decisions` | int | decisions counted in the window |
| `daily` | array | newest-first per-day RED rate, for sparkline/debug |

## Behaviour / edge cases
- **No baseline yet** (model never trained with meta): `baseline_red_rate` falls back to a documented default and `is_drifting` is `false`. Never 500.
- **Fewer than 3 days of data:** `days_exceeded` reflects what exists; `is_drifting` stays `false` until 3 consecutive days exist.
- **No artifacts:** all rates `0.0`, `is_drifting` false.
- Rates are honest — computed from real artifact `routing_classification` + `timestamp` (UTC day buckets). No threshold tuning.

## Error cases
| Status | When |
|---|---|
| 200 | always under normal operation (degrades gracefully to zeros/defaults) |
| 500 | only on unexpected server fault (corrupt meta is handled, not fatal) |

## Who calls it
- M2 — polls on dashboard load / interval to render the drift banner.
- M3 — may read it (or subscribe to the alert transition) to send the Drift Alert email.

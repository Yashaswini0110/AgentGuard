# Hiring domain scenario (adapter `hiring_demo_v1`)

This repository includes a **scenario adapter** that looks like AI-assisted hiring so governance flows are easy to demo. It is **not** the product: AgentGuard governs **enterprise AI decisions** broadly; resume PDF parsing and candidate fields exist to generate realistic structured ingress with optional proxy fields that trigger policy rules.

- **UI entry:** Scenario Lab (`/scenario-lab`) in the React app.
- **API entry:** `POST /v2/evaluate` with `adapter=hiring_demo_v1` (same shape as the legacy `/decision` body where applicable).
- **Operational surface:** Mission control, Decision stream, Incident queue, and Investigation views are governance-native; they never treat “recruiting” as the core value proposition.

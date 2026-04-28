# AgentGuard v3 — Build Progress

**Project:** Unisys Innovation Program 2026  
**Team:** [Your team name]  
**Start Date:** April 28, 2026  
**Target Demo Date:** [Fill this in]

---

## Completion Status

| Step | Feature | Status | Date Completed | Notes |
|---|---|---|---|---|
| 0 | Project Setup | ✅ DONE | 2026-04-28 | Initial structure and requirements created. |
| 1 | Worker Agent | ⬜ TODO | - | - |
| 2 | Policy Engine (Layer 1) | ⬜ TODO | - | - |
| 3 | Risk Router (Layer 2) | ⬜ TODO | - | - |
| 4 | Artifact Engine | ⬜ TODO | - | - |
| 5 | ServiceNow Integration | ⬜ TODO | - | - |
| 6 | Supervisor LLM | ⬜ TODO | - | - |
| 7 | FastAPI Backend | ⬜ TODO | - | - |
| 8 | Streamlit Dashboard | ⬜ TODO | - | - |
| 9 | Docker Setup | ⬜ TODO | - | - |
| 10 | Demo Cases (A/B/C) | ⬜ TODO | - | - |

**Legend:** ⬜ TODO · 🔄 IN PROGRESS · ✅ DONE · ❌ BLOCKED

---

## Test Results

### Policy Engine (Step 2)
- [ ] EMOTION_SCORE rule fires and blocks
- [ ] SURNAME rule fires and blocks
- [ ] INSTITUTION_TIER rule fires and blocks
- [ ] MATERNITY (career_gap + gender) rule fires and blocks
- [ ] TRIBAL IDENTITY rule fires and blocks
- [ ] PROMPT_INJECTION rule fires and blocks
- [ ] Clean decision passes with no violations
- [ ] All 8 pytest tests pass

### Risk Router (Step 3)
- [ ] Model trains without error on synthetic dataset
- [ ] GREEN decisions return in < 200ms
- [ ] SHAP scores returned for all 6 features
- [ ] Drift detection alerts when RED > 20%
- [ ] All pytest tests pass

### ServiceNow (Step 5)
- [ ] Mock returns valid INC ticket ID
- [ ] Timeout handled gracefully (returns status=TIMEOUT)
- [ ] Connection error handled (returns status=ERROR)
- [ ] All pytest tests pass

### FastAPI (Step 7)
- [ ] GET /health returns 200
- [ ] POST /decision runs full pipeline end-to-end
- [ ] Artifact saved to disk after every decision
- [ ] GET /drift returns alert field
- [ ] All pytest tests pass

### Dashboard (Step 8)
- [ ] Case A shows GREEN banner
- [ ] Case B shows YELLOW banner  
- [ ] Case C shows RED banner + ServiceNow ticket ID
- [ ] SHAP bar chart renders correctly
- [ ] Artifact downloads as valid JSON
- [ ] Drift monitor shows correct percentages

---

## Known Issues & Bugs

<!-- Copy-paste bugs here as you find them. Include: what you expected, what happened, which step you tried to fix it. -->

---

## Daily Standup Log

### 2026-04-28
**Done today:**  
- Initialized requirements.txt with 2026 stable versions.
- Created project folder structure and placeholder files.
- Created .env.example template.
- Updated progress.md for Step 0.
**Working on next:**  
- Step 1: Worker Agent implementation.
**Blocked by:** None. 

---

## Demo Rehearsal Log

| Date | Case A ✅ | Case B ✅ | Case C ✅ | ServiceNow Live | Issues Found |
|---|---|---|---|---|---|
| - | - | - | - | - | - |

---

## Performance Benchmarks (fill in Week 11)

| Metric | Target | Actual |
|---|---|---|
| GREEN decision latency (avg) | < 50ms | TBD |
| RED decision latency (avg) | < 500ms | TBD |
| GREEN routing % on clean data | > 85% | TBD |
| Policy engine latency | < 5ms | TBD |
| All pytest tests passing | 100% | TBD |

---

## Final Demo Readiness

- [ ] All 10 steps complete
- [ ] All pytest tests passing
- [ ] Docker runs with `docker-compose up` — one command
- [ ] Case A runs cleanly (GREEN)
- [ ] Case B runs cleanly (YELLOW)
- [ ] Case C creates real ServiceNow ticket live
- [ ] Artifact hash tamper test demonstrated
- [ ] Team has rehearsed full 8-minute demo 5+ times
- [ ] 30-second backup video recorded (ServiceNow fallback)
- [ ] Everyone can answer: "How is this different from Purview?"

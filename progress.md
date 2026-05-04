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
| 1 | Worker Agent | ✅ DONE | 2026-05-01 | Shifted from OpenAI to Gemini API |
| 2 | Policy Engine (Layer 1) | ✅ DONE | 2026-05-04 | Deterministic 6-rule engine (core/policy_engine.py): covers EU AI Act Art.5(1)(f), India Constitution Art.15, DPDP Act 2023, Maternity Benefit Act 1961, and prompt-injection detection. Full pytest suite (tests/test_policy_engine.py) — 16/16 tests passing. |
| 3 | Risk Router (Layer 2) | ✅ DONE | 2026-05-04 | GradientBoostingClassifier (3-class: GREEN/YELLOW/RED). Composite 6-feature risk scoring with 10% label noise — test accuracy 73.8%, CV 75.4% ± 1.4%. SHAP via PermutationExplainer. Drift detection with RED>20% alert. 29/29 pytest tests passing. |
| 4 | Artifact Engine | ✅ DONE | 2026-05-04 | Cryptographically signed, tamper-proof JSON artifact engine (core/artifact_engine.py). Includes generate, save, verify, and regulator-export functions. 8/8 pytest tests passing (tests/test_artifacts.py). |
| 5 | ServiceNow Integration | ✅ DONE | 2026-05-04 | Real/Mock integration with 5s timeout and automatic .env fallback. |
| 6 | Supervisor LLM | ✅ DONE | 2026-05-04 | Semantic review using Gemini 2.5 Flash for YELLOW decisions. |
| 7 | FastAPI Backend | ✅ DONE | 2026-05-04 | Full pipeline gateway (api/main.py) with 6 endpoints. Integrated all core layers. 30/30 pytest tests passing (tests/test_api.py) with 0 warnings. |
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
- [x] Model trains without error on synthetic dataset
- [x] GREEN decisions return in < 200ms (cache-warmed: ~80–140ms)
- [x] SHAP scores returned for all 6 features
- [x] Drift detection alerts when RED > 20%
- [x] 29/29 pytest tests pass

### Artifact Engine (Step 4)
- [x] generate_artifact returns all 16 required fields
- [x] artifact_hash starts with "sha256:"
- [x] verify_artifact returns True for unmodified, False for tampered
- [x] RED routing includes ServiceNow ticket ID
- [x] Regulatory export includes EU AI Act / India DPDP headers
- [x] 8/8 pytest tests passing

### ServiceNow (Step 5)
- [x] Mock returns valid INC ticket ID
- [x] Timeout handled gracefully (returns status=TIMEOUT)
- [x] Connection error handled (returns status=ERROR)
- [x] 6/6 pytest tests pass (tests/test_servicenow.py)

### Supervisor LLM (Step 6)
- [x] returns all 6 required fields
- [x] supervisor_verdict is one of APPROVE/REJECT/ESCALATE_TO_HUMAN
- [x] handles Gemini API exceptions (escalates to human)
- [x] detects bias in features (e.g. socioeconomic_background)
- [x] 4/4 pytest tests pass (tests/test_supervisor.py)

### FastAPI (Step 7)
- [x] GET /health returns 200
- [x] POST /decision runs full pipeline end-to-end
- [x] Artifact saved to disk after every decision
- [x] GET /drift returns alert field
- [x] All 30/30 pytest tests pass (0 warnings)

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

### 2026-05-04
- Built `core/artifact_engine.py` — cryptographically signed compliance artifact engine (Parts A–D).
- Implemented `tests/test_artifacts.py` — verified hash-based tamper detection and field completeness (8/8 passing).
- Built `core/supervisor.py` — Supervisor LLM semantic review for borderline (YELLOW) decisions using Gemini 2.5 Flash.
- Implemented `tests/test_supervisor.py` — verified bias detection and error handling (4/4 passing).
- Built `api/main.py` — full FastAPI gateway wiring all 6 governance layers together.
- Implemented `tests/test_api.py` — end-to-end pipeline verification (30/30 passing with 0 warnings).

**Working on next:**
- Step 8: Streamlit Dashboard.

**Blocked by:** None.

---

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
| GREEN decision latency (avg) | < 50ms | ~80–140ms (cache-warm; SHAP overhead) |
| RED decision latency (avg) | < 500ms | ~88ms |
| GREEN routing % on clean data | > 85% | 51% recall (noisy labels by design) |
| Policy engine latency | < 5ms | < 1ms |
| Risk Router test accuracy | > 70% | 73.8% hold-out / 75.4% CV |
| All pytest tests passing | 100% | 93/93: 8/8 (artifacts) · 29/29 (router) · 16/16 (policy) · 6/6 (servicenow) · 4/4 (supervisor) · 30/30 (api) |

---

## Final Demo Readiness

- [ ] All 10 steps complete
- [ ] All pytest tests passing
- [ ] Docker runs with `docker-compose up` — one command
- [ ] Case A runs cleanly (GREEN)
- [ ] Case B runs cleanly (YELLOW)
- [ ] Case C creates real ServiceNow ticket live
- [x] Artifact hash tamper test demonstrated
- [ ] Team has rehearsed full 8-minute demo 5+ times
- [ ] 30-second backup video recorded (ServiceNow fallback)
- [ ] Everyone can answer: "How is this different from Purview?"

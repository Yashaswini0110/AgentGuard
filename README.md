# 🛡️ AgentGuard v3
### AI Governance Control Plane for Enterprise HR

**Unisys Innovation Program 2026**

---

> *"We don't audit what your AI did yesterday. We stop what it should not do today."*

---

## The Problem

Indian companies use AI to screen thousands of job applications automatically. These systems are trained on historical hiring data — data that reflects years of human bias. They penalise candidates based on college tier, surname, and emotional expression during video interviews. These are proxies for caste, gender, and socioeconomic background. Nobody stops these decisions before they execute.

The rejection email goes out. The candidate never knows why. The company has no legal record of what happened.

Under India's **DPDP Act 2023** and the **EU AI Act**, this is no longer just unethical — it is a regulatory liability. Penalties reach **₹250 crore**. Full enforcement begins **May 2027**.

**The scale:**
- Indian IT sector screens ~15 million applications annually
- 70%+ of large Indian companies now use AI screening tools
- Conservative estimate: **450,000 wrongful AI rejections per year** involve a prohibited feature

---

## What AgentGuard Is

AgentGuard v3 is **active transactional middleware** that sits between an AI hiring agent and the enterprise systems it controls. Every decision the AI tries to make must pass through AgentGuard before it executes.

| ❌ This is NOT | ✅ This IS |
|---|---|
| A passive monitoring dashboard | Active runtime blocker — stops violations before execution |
| A compliance checklist | Risk-adaptive routing engine |
| An audit tool (logs after the fact) | A prevention tool (blocks before the fact) |
| Vendor-specific | Model-agnostic — governs any AI agent via JSON |

---

## System Architecture

```mermaid
flowchart TD
    ATS(["🏢 Enterprise ATS\nApplicant Tracking System"])
    AGENT["🤖 Hiring AI Worker Agent\nOutputs structured JSON decision\ncandidate_id · score · features_used · confidence"]
    ATS -->|"Candidate application feed"| AGENT

    subgraph AG["🛡️ AgentGuard v3 — Governance Control Plane"]
        direction TB
        INTERCEPT["⛔ Interception Gateway\nEvery decision STOPPED here before any execution"]

        subgraph L1["Layer 1 — Deterministic Policy Engine  •  < 5ms  •  Zero AI"]
            PE["📋 Hard Rule Checker — Python rule dictionary — Binary PASS / BLOCK"]
            R1["🚫 BLOCK: emotion_score used — EU AI Act Article 5"]
            R2["🚫 BLOCK: applicant_surname used — Caste / religion proxy"]
            R3["🚫 BLOCK: institution_tier used — Socioeconomic proxy"]
            R4["🚫 BLOCK: career_gap + gender — Maternity discrimination proxy"]
            R5["🚫 BLOCK: home_district / village_code — Tribal identity proxy"]
            R6["🚫 BLOCK: Prompt injection detected — Security rule"]
            PE --> R1 & R2 & R3 & R4 & R5 & R6
        end

        subgraph L2["Layer 2 — Explainable Risk Router  •  < 50ms  •  sklearn Classifier"]
            ROUTER["⚡ Risk Classifier\nFeatures: experience · skill_match · interview_score · assessment_score · confidence · feature_count"]
            SHAP["📊 SHAP Explainer — Per-feature importance scores — Embedded in every artifact"]
            ROUTER --> SHAP
        end

        GREEN["✅ GREEN — Auto-Execute — No LLM · No cost · < 50ms"]
        YELLOW["🟡 YELLOW — GPT-4o-mini Supervisor — Proxy discrimination scan"]
        RED["🔴 RED — Hard Block — PENDING state — Human required"]

        subgraph L3["Layer 3 — System of Record Commit"]
            SN["🎫 ServiceNow REST API — Real incident ticket — e.g. INC0004821"]
            HOLD["⏸️ Execution Hold — 5-second timeout — Auto-block if no response"]
            SN --> HOLD
        end

        subgraph ART["Signed Decision Artifact Engine  •  Every Decision"]
            ARTGEN["🔏 SHA-256 Artifact\ndecision_id · timestamp · candidate_id · policy_rule_cited\nrouting_classification · shap_scores · model_version_hash\nservicenow_ticket_id · artifact_hash"]
        end

        HUMAN["👤 HR Compliance Officer\nReviews RED queue · Approve / Reject / Override\nAll overrides permanently logged"]

        INTERCEPT --> L1
        L1 -->|"PASS"| L2
        L1 -->|"BLOCK"| RED
        L2 --> GREEN & YELLOW & RED
        RED --> L3
        L3 --> HUMAN
        HUMAN --> ART
        GREEN --> ART
        YELLOW --> ART
    end

    EXEC["✅ Decision Executed — ATS updated — Candidate notified"]
    AUDITDB[("🗄️ Immutable Audit Log — PostgreSQL")]
    REGEXPORT["📄 One-click Regulatory Export\nEU AI Act Technical Doc · DPDP Act Evidence"]
    DASH["📈 Governance Dashboard\nLive feed · Latency benchmarks · Drift detection"]

    GREEN --> EXEC
    YELLOW --> EXEC
    HUMAN -->|"Approved"| EXEC
    ART --> AUDITDB
    AUDITDB --> REGEXPORT
    AUDITDB --> DASH
    AGENT --> INTERCEPT

    classDef entry fill:#1F4E79,stroke:#1F4E79,color:#fff
    classDef block fill:#8B0000,stroke:#8B0000,color:#fff
    classDef green fill:#1E7A3E,stroke:#1E7A3E,color:#fff
    classDef yellow fill:#7B4F00,stroke:#7B4F00,color:#fff
    classDef red fill:#8B0000,stroke:#8B0000,color:#fff
    classDef artifact fill:#2E4057,stroke:#2E4057,color:#fff
    classDef output fill:#0D47A1,stroke:#0D47A1,color:#fff
    classDef human fill:#1B5E20,stroke:#1B5E20,color:#fff

    class ATS,AGENT entry
    class R1,R2,R3,R4,R5,R6 block
    class GREEN green
    class YELLOW yellow
    class RED,HOLD red
    class ARTGEN,ART artifact
    class EXEC,AUDITDB,REGEXPORT,DASH output
    class HUMAN human
```

> Render at [mermaid.live](https://mermaid.live) · Renders natively on GitHub, Notion, GitLab

---

## Core Features

### Layer 1 — Deterministic Policy Engine
**Runtime: < 5ms · Zero AI · Zero cost**

Hard-coded rules written in Python. No machine learning, no probability. If a rule fires, the decision is blocked — no exceptions.

| Rule | Feature Blocked | Legal Basis |
|---|---|---|
| `EMOTION_SCORE_IN_HIRING_PROHIBITED` | `emotion_score` | EU AI Act Article 5 — flat prohibition |
| `SURNAME_PROXY_CASTE_RELIGION` | `applicant_surname` | India Constitution Article 15 |
| `INSTITUTION_TIER_PROXY_SOCIOECONOMIC` | `institution_tier` | DPDP Act — unlawful processing |
| `MATERNITY_DISCRIMINATION_PROXY` | `career_gap` + `gender` | Maternity Benefit Act 1961 |
| `TRIBAL_IDENTITY_PROXY` | `home_district`, `village_code` | India Constitution Article 15 |
| `PROMPT_INJECTION_DETECTED` | Malicious input strings | Security policy |

---

### Layer 2 — Explainable Risk Router
**Runtime: < 50ms · sklearn GradientBoostingClassifier**

Classifies every decision that passes the policy engine as GREEN, YELLOW, or RED.

**Safe features used for classification:**

| Feature | What It Measures |
|---|---|
| `years_of_experience` | Relevant work history |
| `skill_match_score` | NLP match to job description (0–1) |
| `interview_score` | Structured interview score |
| `assessment_score` | Technical test result |
| `decision_confidence` | Agent's confidence in its own output |
| `feature_count` | Number of features used — more unusual = higher risk |

**Routing outcomes:**

| Classification | Action | LLM Cost |
|---|---|---|
| 🟢 GREEN | Auto-execute. Artifact generated. | ₹0 |
| 🟡 YELLOW | GPT-4o-mini semantic review — ~10% of traffic | Minimal |
| 🔴 RED | Hard block. ServiceNow ticket. Human review. | ₹0 |

**SHAP Explainability:** Computed for every decision. Embedded in every artifact. Applies to the router classifier — not the LLM.

**Drift Detection:** If RED exceeds 20% of decisions, system raises an alert.

---

### Layer 3 — ServiceNow System of Record Commit
**Live integration — not a mock**

Every RED decision triggers a live ServiceNow API call. Decision held in `PENDING` state until ticket ID returns. 5-second timeout auto-blocks if no response.

```
RED decision → ServiceNow REST API → INC0004821 created → Decision PENDING → HR Officer reviews → Approve / Reject (logged)
```

---

### Signed Decision Artifact Engine
**Every decision · Every time · Tamper-proof**

```json
{
  "decision_id": "a3f7c2d1-9e4b-4f8a-b6c0-1d2e3f4a5b6c",
  "timestamp": "2026-04-27T09:14:32.441Z",
  "candidate_id": "CAND-2026-004821",
  "policy_rule_cited": "EMOTION_SCORE_IN_HIRING_PROHIBITED",
  "regulation_reference": "EU AI Act Article 5(1)(f)",
  "routing_classification": "RED",
  "confidence_score": 0.91,
  "features_used": ["emotion_score", "institution_tier", "skill_match_score"],
  "shap_scores": {
    "emotion_score": 0.61,
    "institution_tier": 0.28,
    "skill_match_score": -0.11
  },
  "model_version_hash": "sha256:7f4e2a1b9c3d5e8f...",
  "servicenow_ticket_id": "INC0004821",
  "artifact_hash": "sha256:3a9b1c4d7e2f5a8b..."
}
```

`artifact_hash` = SHA-256 of entire artifact. Any modification invalidates it instantly.

---

## Regulatory Alignment

| Regulation | Requirement | How AgentGuard Addresses It |
|---|---|---|
| **EU AI Act — Article 5** | Flat prohibition on emotion recognition in hiring | Hard rule — zero exceptions |
| **EU AI Act — Article 14** | Meaningful human oversight on high-risk decisions | ServiceNow execution hold |
| **EU AI Act — Technical Documentation** | Auditable evidence of every AI decision | Signed Decision Artifacts |
| **India DPDP Act 2023** | Fair, lawful processing of candidate personal data | Policy engine enforces data minimisation |
| **India Constitution — Article 15** | No discrimination on caste, religion, sex, place of birth | Surname, home district, institution tier blocked |
| **Maternity Benefit Act 1961** | No maternity discrimination | Career gap + gender combination blocked |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Worker Agent | Python + OpenAI GPT-4o-mini |
| Policy Engine | Python — custom rule dictionary |
| Risk Router | scikit-learn GradientBoostingClassifier + SHAP |
| Supervisor (YELLOW) | GPT-4o-mini with structured JSON prompt |
| ServiceNow | ServiceNow REST API + Python `requests` |
| Artifact Engine | Python `hashlib` SHA-256 + `uuid` + `json` |
| Backend | FastAPI |
| Frontend | React (Vite) dashboard + legacy Streamlit |
| Database | SQLite → PostgreSQL |
| Infrastructure | Docker + docker-compose |

---

## Competitive Position

| Tool | Blocks Pre-Execution? | SoR Commit? | India-Specific Rules? |
|---|---|---|---|
| Braintrust / Langfuse | ❌ | ❌ | ❌ |
| Arize Phoenix | ❌ | ❌ | ❌ |
| Microsoft Purview | ⚠️ MS agents only | ❌ | ❌ |
| Guardrails AI | ⚠️ Output only | ❌ | ❌ |
| **AgentGuard v3** | ✅ | ✅ | ✅ |

---

## Usage Guide

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the React dashboard)
- API keys in `.env` (see [Environment setup](#environment-setup))
- For bulk resume ingest: a ZIP of **PDF and/or DOCX** résumés

### Environment setup

1. Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

2. Minimum keys for a full demo:

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Resume parsing, worker agent, supervisor |
| `OPENROUTER_API_KEY` | Optional LLM fallback |
| `ENVIRONMENT` | `development` = mock email/ServiceNow; `production` = live SMTP |
| `EMAIL_FROM`, `GMAIL_APP_PASSWORD` | Gmail SMTP for shortlist & rejection mail |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Optional — inline résumé viewer in Review Queue |

3. **Never commit `.env`** — it is gitignored. Use quotes if your App Password contains special characters:

```env
GMAIL_APP_PASSWORD="your sixteen char app password"
```

4. For safe email testing, restrict recipients:

```env
EMAIL_ALLOWLIST=your.personal@gmail.com
```

### Run the application

**Terminal 1 — API (from repo root):**

```bash
pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — React UI:**

```bash
cd ui/app
npm install
npm run dev
```

Open **http://localhost:3000**. The UI proxies API calls to `http://127.0.0.1:8000` via `/agentguard-api`.

Verify the API: **http://127.0.0.1:8000/health** — check `email.transport` (`mock` vs `gmail_smtp`) and `batch_rank_available`.

---

### Demo login

The dashboard uses demo auth (not for production):

| User ID | Role | Password |
|---|---|---|
| `HR-COMPLIANCE-01` | HR | `demo` |
| `TECH-REVIEWER-01` … `03` | Technical reviewer | `demo` |

HR can send shortlist emails and record Review Queue decisions. Tech reviewers handle escalated cases.

---

### End-to-end workflow

#### 1. Bulk Rank (pool intake)

**Tab:** **Bulk rank**

1. Choose a **Target role** preset (Software Engineer, Data Scientist, Frontend Developer) or **Custom** and paste your own JD.
2. Required skills for the preset appear under the job description.
3. Set **Open positions** (e.g. `5`).
4. Upload a **ZIP** of résumés (PDF/DOCX).
5. Click **Start parallel pool review**.

The pipeline parses each résumé, extracts **name**, **email**, and **skills**, runs governance in parallel, and ranks candidates. Each artifact stores `candidate_email`, `job_role`, and bulk session metadata.

#### 2. Review Queue (HR governance)

**Tab:** **Review Queue** · log in as **HR**

Shows candidates that need human attention: policy **BLOCK**, **RED**, **YELLOW**, or bulk ZIP rows pending HR ack.

| Action | Effect |
|---|---|
| **Approve** | HR override — candidate can appear on Shortlist |
| **Reject** | Records rejection; **sends rejection email** to candidate (if résumé email exists) |
| **Escalate** | Sends case to **Tech Review** with your note |

When rejecting, add a comment — it is inserted into the rejection email as reviewer feedback.

#### 3. Tech Review (escalated cases)

**Tab:** **Tech Review** · log in as **TECH-REVIEWER-01** (etc.)

Cases appear after HR escalation. Review the résumé and AI summary, add a technical note, then:

| Action | Effect |
|---|---|
| **Accept** | Candidate becomes eligible for Shortlist |
| **Reject** | Records tech rejection; **sends rejection email** with your note |

#### 4. Shortlist & Email (accepted candidates)

**Tab:** **Shortlist & Email** · log in as **HR**

Lists candidates who passed via GREEN auto-pass, supervisor approve, HR approve, or tech accept.

1. Select candidates (must have a **real résumé email** — not `@example.com`).
2. Edit subject/body if needed. Placeholders are filled per recipient:
   - `[Candidate Name]`
   - `[Role Title]` (from bulk JD / artifact)
3. Click **Send**.

| `ENVIRONMENT` | Behaviour |
|---|---|
| `development` | Mock — payload printed in API terminal (`[MOCK] Shortlist email payload`) |
| `production` | Real Gmail SMTP send |

Successful sends write `email_dispatch` on the artifact for audit.

#### 5. Single candidate (optional)

**Tab:** **Run pipeline**

Run governance on one synthetic or parsed candidate without bulk ZIP. Useful for policy demos (e.g. emotion_score → RED).

---

### Email templates

**Shortlist (manual send from Shortlist tab)**

- Subject: `AgentGuard – Application Shortlisted for Interview Process`
- Includes next-step interview messaging and contact `agentguard.hr@gmail.com` / `+91 9000000001`

**Rejection (automatic on HR or Tech Reject)**

- Subject: `AgentGuard – Update on Your Application`
- Placeholders: `[Candidate Name]`, `[Role Title]`, `[REJECTION_REASON_OR_REVIEWER_COMMENT]`
- Skipped if no résumé email or rejection mail already sent (`rejection_email_dispatch` on artifact)

### Gmail App Password (production email)

1. Enable **2-Step Verification** on the sender Gmail account.
2. Google Account → Security → **App passwords** → generate for Mail.
3. Put the 16-character password in `GMAIL_APP_PASSWORD` (not your normal login password).
4. Set `ENVIRONMENT=production` and restart uvicorn.

---

### API endpoints (reference)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/decision` | Single-candidate governance pipeline |
| `POST` | `/batch_rank` | Bulk ZIP ingest + merit rank |
| `POST` | `/batch_rank/stream` | Same with SSE progress |
| `POST` | `/human-review/{id}` | HR approve / reject |
| `POST` | `/escalate/{id}` | HR → tech escalation |
| `POST` | `/tech-review/{id}` | Tech accept / reject |
| `POST` | `/shortlist/email` | HR shortlist notification batch send |
| `GET` | `/artifacts/recent` | Dashboard artifact feed |
| `GET` | `/health` | Liveness + email/ batch flags |

Interactive docs: **http://127.0.0.1:8000/docs**

---

*AgentGuard v3 · Unisys Innovation Program 2026 · Version 3.1*



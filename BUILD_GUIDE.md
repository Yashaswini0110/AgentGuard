# 🛠️ AgentGuard v3 — Complete Build Guide
### Step-by-Step · Antigravity Prompts · Model Selection · Credit Management

---

## Before You Start — Read This

### Model Selection in Antigravity (Free Tier)

| Task | Model to Use | Why |
|---|---|---|
| Writing code (policy engine, router, artifacts) | **Claude Sonnet 4.6 (Thinking)** | Best reasoning for architecture code |
| Debugging errors | **Claude Sonnet 4.6 (Thinking)** | Fastest at finding root cause |
| Writing boilerplate / simple functions | **Gemini 3 Flash** | Save credits for complex tasks |
| Testing prompts / quick questions | **Gemini 3 Flash** | Cheapest — use freely |
| ServiceNow integration (complex) | **Claude Sonnet 4.6 (Thinking)** | Critical component, needs best model |
| Writing the Streamlit UI | **Gemini 3.1 Pro (Low)** | Good enough, saves credits |

### Credit Management Rules
- **Use Gemini Flash** for anything simple — boilerplate, file creation, simple questions
- **Switch to Claude Sonnet Thinking** only when you hit a real logic/architecture problem
- **Never use Claude Opus** — not worth the credits for this project
- **One feature at a time** — build it, test it, mark it done in progress.md, then move on
- **If a prompt fails twice** — switch to Claude Sonnet Thinking immediately

### Folder Structure to Create First

```
agentguard/
├── data/
│   └── synthetic_hr_dataset.csv      ← your dataset goes here
├── core/
│   ├── worker_agent.py
│   ├── policy_engine.py
│   ├── risk_router.py
│   ├── supervisor.py
│   ├── servicenow.py
│   └── artifact_engine.py
├── api/
│   └── main.py                        ← FastAPI
├── ui/
│   └── dashboard.py                   ← Streamlit
├── models/
│   └── router_model.pkl               ← trained classifier saved here
├── artifacts/
│   └── .gitkeep                       ← signed artifacts stored here
├── tests/
│   ├── test_policy_engine.py
│   ├── test_router.py
│   └── test_artifacts.py
├── progress.md                        ← your tracking file
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## STEP 0 — Project Setup

**Model: Gemini 3 Flash**

### Prompt 0.1 — Create requirements.txt

```
Create a requirements.txt file for a Python project called AgentGuard v3.

The project needs these libraries:
- fastapi
- uvicorn
- streamlit
- scikit-learn
- shap
- pandas
- numpy
- openai
- requests
- python-dotenv
- httpx
- pytest
- joblib
- sqlite3 (built-in, no install needed)

Output only the requirements.txt file contents with pinned versions that are stable as of early 2026. No explanation.
```

### Prompt 0.2 — Create .env template

```
Create a .env.example file for a Python project. It needs these environment variables:

OPENAI_API_KEY=your_openai_key_here
SERVICENOW_INSTANCE=your_instance.service-now.com
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=your_password_here
ENVIRONMENT=development

Output only the file contents. No explanation.
```

### ✅ Test Step 0
Run `pip install -r requirements.txt` — if no errors, Step 0 is done.
Update `progress.md` with: `## Step 0 — Setup ✅ DONE`

---

## STEP 1 — Worker Agent

**Model: Gemini 3.1 Pro (Low)**

This is the simulated AI hiring agent. It takes a candidate profile and outputs a JSON hiring decision.

### Prompt 1.1 — Build the Worker Agent

```
Build a Python file called worker_agent.py for a project called AgentGuard v3.

Context: This file simulates an AI hiring agent. It takes a candidate's profile as input and outputs a structured JSON hiring decision. This is NOT the governance layer — it is the agent being governed.

Requirements:
1. Create a function called `make_hiring_decision(candidate: dict) -> dict`
2. The function should use the OpenAI API (gpt-4o-mini) to generate a hiring decision
3. The system prompt must instruct the model to act as an AI hiring screener
4. The output must ALWAYS be a valid JSON object with EXACTLY these fields:
   - candidate_id: string (from input)
   - decision: "APPROVE" or "REJECT"
   - confidence: float between 0.0 and 1.0
   - reason: string (one sentence)
   - features_used: list of strings (which candidate fields the AI weighted most)
   - recommended_action: "PROCEED_TO_INTERVIEW" or "REJECT_APPLICATION"
5. Sometimes (randomly, 30% of time) inject a biased feature into features_used — one of: ["emotion_score", "institution_tier", "applicant_surname", "home_district"] — to simulate a biased agent
6. Load OPENAI_API_KEY from environment variable using python-dotenv
7. Add error handling — if OpenAI fails, raise a clear ValueError

Also create a simple `if __name__ == "__main__"` test block that runs one sample candidate and prints the result.

Sample candidate input structure:
{
  "candidate_id": "CAND-001",
  "name": "Rahul Sharma",
  "years_of_experience": 5,
  "skill_match_score": 0.87,
  "interview_score": 7.8,
  "assessment_score": 82,
  "career_gap_months": 0,
  "gender": "M",
  "institution_tier": 2
}

Output only the complete Python file. No explanation.
```

### ✅ Test Step 1

**Model: Gemini 3 Flash**

```
I have a Python file called worker_agent.py that calls OpenAI API to generate a hiring decision JSON.

Write me a pytest test file called tests/test_worker_agent.py that:
1. Mocks the OpenAI API call so no real API call is made
2. Tests that the output always has these fields: candidate_id, decision, confidence, reason, features_used, recommended_action
3. Tests that decision is either "APPROVE" or "REJECT"
4. Tests that confidence is between 0.0 and 1.0
5. Uses pytest and unittest.mock

Output only the test file. No explanation.
```

Run: `pytest tests/test_worker_agent.py -v`
All tests pass → Update `progress.md`: `## Step 1 — Worker Agent ✅ DONE`

---

## STEP 2 — Policy Engine (Layer 1)

**Model: Claude Sonnet 4.6 (Thinking)** ← Switch now. This is the most important layer.

### Prompt 2.1 — Build the Policy Engine

```
Build a Python file called policy_engine.py for AgentGuard v3 — an AI governance system for HR hiring decisions in India.

Context: This is Layer 1 of the governance pipeline. It must be DETERMINISTIC — no AI, no probability. Hard rules only. If a rule fires, the decision is BLOCKED with zero exceptions.

Requirements:

1. Create a dictionary called POLICY_RULES with EXACTLY these 6 rules:

Rule 1: EMOTION_SCORE_IN_HIRING_PROHIBITED
- Condition: "emotion_score" is in the decision's features_used list
- Severity: RED
- Regulation: "EU AI Act Article 5(1)(f) — Prohibited Practice"
- Reason: "Emotion recognition in employment contexts is a flat legal prohibition"

Rule 2: SURNAME_PROXY_CASTE_RELIGION  
- Condition: "applicant_surname" is in features_used
- Severity: RED
- Regulation: "India Constitution Article 15 — Anti-discrimination"
- Reason: "Applicant surname is a proxy for caste and religious identity in India"

Rule 3: INSTITUTION_TIER_PROXY_SOCIOECONOMIC
- Condition: "institution_tier" is in features_used
- Severity: RED
- Regulation: "India DPDP Act 2023 — Unlawful data processing"
- Reason: "Institution tier correlates with caste and socioeconomic background"

Rule 4: MATERNITY_DISCRIMINATION_PROXY
- Condition: BOTH "career_gap_months" AND "applicant_gender" are in features_used
- Severity: RED
- Regulation: "Maternity Benefit Act 1961 — India"
- Reason: "Career gap combined with gender is a maternity discrimination proxy"

Rule 5: TRIBAL_IDENTITY_PROXY
- Condition: "home_district" OR "village_code" is in features_used
- Severity: RED
- Regulation: "India Constitution Article 15 — Anti-discrimination"
- Reason: "Geographic micro-codes are proxies for tribal and rural identity"

Rule 6: PROMPT_INJECTION_DETECTED
- Condition: The raw candidate input string contains any of these patterns: "ignore previous", "system prompt", "override", "jailbreak", "forget instructions"
- Severity: RED
- Regulation: "AgentGuard Security Policy v1.0"
- Reason: "Malicious instruction injection detected in candidate input"

2. Create a function called `check_policy(decision: dict, raw_input: str = "") -> dict` that:
   - Loops through all rules
   - Returns a result dict with:
     - passed: bool (True only if NO rules fired)
     - violations: list of dicts, each with: rule_name, severity, regulation, reason
     - recommended_action: "PROCEED" if passed, "BLOCK" if any violation
   - MUST run in under 5ms (pure Python dict operations, no ML)

3. Create a function called `format_violation_report(result: dict) -> str` that returns a clean human-readable string of all violations

4. Add an `if __name__ == "__main__"` block that tests all 6 rules with sample inputs and prints results

Output only the complete Python file. No explanation.
```

### Prompt 2.2 — Test the Policy Engine

**Model: Gemini 3 Flash**

```
Write a pytest test file called tests/test_policy_engine.py for a Python module called policy_engine.py.

The policy_engine has a function check_policy(decision: dict, raw_input: str = "") -> dict

Write 8 tests:
1. Clean decision with no violations → passed=True, violations=[]
2. Decision with emotion_score in features_used → BLOCK, rule EMOTION_SCORE_IN_HIRING_PROHIBITED fires
3. Decision with applicant_surname in features_used → BLOCK, rule SURNAME_PROXY_CASTE_RELIGION fires
4. Decision with institution_tier in features_used → BLOCK
5. Decision with both career_gap_months AND applicant_gender → BLOCK, maternity rule fires
6. Decision with home_district → BLOCK, tribal identity rule fires
7. Decision with village_code → BLOCK, tribal identity rule fires
8. Raw input containing "ignore previous instructions" → BLOCK, prompt injection rule fires

Each test must assert: passed==False, len(violations)>=1, recommended_action=="BLOCK" for violation cases
Clean test must assert: passed==True, violations==[], recommended_action=="PROCEED"

Output only the complete test file. No explanation.
```

### ✅ Test Step 2
Run: `pytest tests/test_policy_engine.py -v`
All 8 tests pass → Update `progress.md`: `## Step 2 — Policy Engine ✅ DONE`

**If any test fails → Switch to Claude Sonnet 4.6 Thinking and paste the error.**

---

## STEP 3 — Risk Router (Layer 2)

**Model: Claude Sonnet 4.6 (Thinking)**

### Prompt 3.1 — Train the Router

```
Build a Python file called risk_router.py for AgentGuard v3.

Context: This is Layer 2 — an ML classifier that routes hiring decisions into GREEN, YELLOW, or RED risk categories. It must be fast (under 50ms), use only safe non-discriminatory features, and produce SHAP explainability scores.

Requirements:

PART A — Training function: `train_router(dataset_path: str) -> None`
1. Load CSV from dataset_path using pandas
2. Features to use (X): years_of_experience, skill_match_score, interview_score, assessment_score, decision_confidence, feature_count
3. Target (y): risk_label column (values: "GREEN", "YELLOW", "RED")
4. If risk_label column doesn't exist, create it with this logic:
   - RED: confidence < 0.4 OR feature_count > 8
   - YELLOW: confidence between 0.4 and 0.65 OR feature_count between 5 and 8
   - GREEN: everything else
5. Train a GradientBoostingClassifier from sklearn
6. Save the trained model to models/router_model.pkl using joblib
7. Save a SHA-256 hash of the model file to models/model_version_hash.txt
8. Print training accuracy and classification report

PART B — Inference function: `classify_risk(decision: dict) -> dict`
1. Load model from models/router_model.pkl
2. Extract the 6 safe features from the decision dict
3. Run prediction — return GREEN, YELLOW, or RED
4. Compute SHAP values for this decision using the shap library (TreeExplainer)
5. Return a dict with:
   - risk_level: "GREEN", "YELLOW", or "RED"
   - confidence_score: float (model's max probability)
   - shap_scores: dict mapping each feature name to its SHAP value
   - model_version_hash: string (read from models/model_version_hash.txt)
   - latency_ms: float (time taken in milliseconds)

PART C — Drift detection: `check_drift(recent_decisions: list) -> dict`
1. Takes a list of recent risk_level strings
2. Calculates percentage of GREEN, YELLOW, RED
3. Returns dict with percentages and alert: True if RED > 20%

PART D — `if __name__ == "__main__"` block
- Trains on data/synthetic_hr_dataset.csv
- Runs classify_risk on 3 sample decisions
- Prints results with latency

Use only: sklearn, shap, pandas, numpy, joblib, hashlib, time
Output only the complete Python file. No explanation.
```

### Prompt 3.2 — Test the Router

**Model: Gemini 3 Flash**

```
Write a pytest test file called tests/test_router.py for a module called risk_router.py.

The module has:
- classify_risk(decision: dict) -> dict  (assumes model already trained and saved)
- check_drift(recent_decisions: list) -> dict

Write these tests:
1. classify_risk returns a dict with keys: risk_level, confidence_score, shap_scores, model_version_hash, latency_ms
2. risk_level is always one of "GREEN", "YELLOW", "RED"
3. confidence_score is between 0.0 and 1.0
4. latency_ms is less than 200 (under 200ms even in test environment)
5. shap_scores is a dict with 6 keys matching the feature names
6. check_drift with mostly GREEN decisions returns alert=False
7. check_drift with >20% RED returns alert=True
8. check_drift returns correct percentages

For tests 1-5, use a mock decision dict:
{
  "years_of_experience": 5,
  "skill_match_score": 0.87,
  "interview_score": 7.8,
  "assessment_score": 82,
  "decision_confidence": 0.91,
  "feature_count": 4
}

Note: The model must already be trained before running these tests. Add a conftest.py that trains the model before the test session if models/router_model.pkl doesn't exist.

Output only the test file and conftest.py. No explanation.
```

### ✅ Test Step 3
First run: `python core/risk_router.py` to train the model.
Then: `pytest tests/test_router.py -v`
All pass → Update `progress.md`: `## Step 3 — Risk Router ✅ DONE`

---

## STEP 4 — Artifact Engine (Layer 3)

**Model: Claude Sonnet 4.6 (Thinking)**

### Prompt 4.1 — Build Artifact Engine

```
Build a Python file called artifact_engine.py for AgentGuard v3.

Context: Every hiring decision that passes through AgentGuard — GREEN, YELLOW, or RED — must generate a cryptographically signed, tamper-proof JSON artifact. This is the legal compliance evidence file.

Requirements:

PART A — Main function: `generate_artifact(decision: dict, policy_result: dict, router_result: dict, servicenow_ticket_id: str = None) -> dict`

Build the artifact dict with EXACTLY these fields:
- decision_id: new UUID4 string
- timestamp: UTC ISO format string
- candidate_id: from decision dict
- candidate_name: from decision dict (for display only)
- decision_outcome: APPROVE or REJECT from decision dict
- policy_result: "PASS" or "BLOCK"
- policy_violations: list from policy_result (empty list if none)
- policy_rule_cited: first violation's rule_name, or "NONE" if no violations
- regulation_reference: first violation's regulation, or "N/A"
- routing_classification: from router_result (GREEN/YELLOW/RED)
- confidence_score: from router_result
- features_used: from decision dict
- shap_scores: from router_result
- model_version_hash: from router_result
- servicenow_ticket_id: the ticket ID string, or null if not applicable
- artifact_hash: SHA-256 hash of the entire artifact (see below)

For artifact_hash:
- Build the complete dict WITHOUT artifact_hash
- Sort the dict keys
- Convert to JSON string with sort_keys=True
- Compute SHA-256 hash of the UTF-8 encoded string
- Add as "artifact_hash": "sha256:{hex_digest}"

PART B — Save function: `save_artifact(artifact: dict) -> str`
- Save to artifacts/ directory as {decision_id}.json
- Return the file path

PART C — Verify function: `verify_artifact(artifact_path: str) -> bool`
- Load artifact from file
- Recompute the hash using the same method
- Return True if hash matches, False if tampered

PART D — Export function: `export_for_regulator(artifact: dict) -> str`
- Returns a clean, formatted JSON string with a header comment block:
  "# AgentGuard v3 — Regulatory Compliance Export"
  "# EU AI Act Technical Documentation File"  
  "# India DPDP Act Audit Evidence"
  "# Generated: {timestamp}"
  Then the full artifact JSON

PART E — `if __name__ == "__main__"` block that:
- Creates a sample artifact
- Saves it
- Verifies it
- Modifies it and verifies again (should return False)
- Prints all results

Output only the complete Python file. No explanation.
```

### Prompt 4.2 — Test Artifacts

**Model: Gemini 3 Flash**

```
Write a pytest test file called tests/test_artifacts.py for artifact_engine.py.

The module has:
- generate_artifact(decision, policy_result, router_result, servicenow_ticket_id=None) -> dict
- save_artifact(artifact) -> str
- verify_artifact(artifact_path) -> bool

Write these tests:

1. generate_artifact returns dict with all required fields: decision_id, timestamp, candidate_id, routing_classification, artifact_hash, shap_scores, model_version_hash
2. artifact_hash starts with "sha256:"
3. verify_artifact returns True for unmodified saved artifact
4. verify_artifact returns False when artifact file is tampered (modify one field and save)
5. generate_artifact with a RED routing and servicenow_ticket_id="INC0001" includes the ticket ID
6. generate_artifact with GREEN routing has servicenow_ticket_id as null
7. Two artifacts for same candidate have different decision_id and different artifact_hash
8. Artifact file is valid JSON when loaded from disk

Use sample dicts for decision, policy_result, router_result. Create tmp artifacts directory for tests and clean up after.

Output only the complete test file. No explanation.
```

### ✅ Test Step 4
Run: `pytest tests/test_artifacts.py -v`
All pass → Update `progress.md`: `## Step 4 — Artifact Engine ✅ DONE`

---

## STEP 5 — ServiceNow Integration (Layer 3)

**Model: Claude Sonnet 4.6 (Thinking)** ← Most critical component. Use best model.

**Before this step:** Sign up at developer.servicenow.com for a free Personal Developer Instance. Takes 20 minutes. Get your instance URL, username, and password.

### Prompt 5.1 — Build ServiceNow Connector

```
Build a Python file called servicenow.py for AgentGuard v3.

Context: When AgentGuard routes a hiring decision as RED, it must create a real ServiceNow incident ticket and hold the decision in PENDING state until a human HR officer reviews it.

Requirements:

PART A — Create ticket function: `create_incident(decision: dict, policy_result: dict, router_result: dict) -> dict`

1. Make a POST request to ServiceNow Table API: https://{instance}/api/now/table/incident
2. Use Basic Auth with username and password from environment variables
3. Set these fields in the incident:
   - short_description: f"AgentGuard RED Flag: Candidate {candidate_id} — {rule_name}"
   - description: Full formatted string including:
     * Candidate ID and name
     * Policy rule that fired
     * Regulation reference  
     * Features the AI used
     * SHAP scores (top 3 by absolute value)
     * Routing classification
     * Confidence score
     * Timestamp
   - category: "AI Governance"
   - subcategory: "Hiring Decision Review"
   - priority: "2" (High)
   - urgency: "2"
   - impact: "2"
4. Set timeout to 5 seconds
5. On SUCCESS: return dict with ticket_id (e.g. "INC0001234"), status="CREATED", url to ticket
6. On TIMEOUT (requests.Timeout): return dict with ticket_id=None, status="TIMEOUT", error="ServiceNow did not respond within 5 seconds — decision auto-blocked"
7. On ANY other error: return dict with ticket_id=None, status="ERROR", error=str(error)

PART B — Mock function for testing: `create_incident_mock(decision: dict, policy_result: dict, router_result: dict) -> dict`
- Returns a realistic fake response: ticket_id="INC0001234", status="CREATED"
- Use this when ENVIRONMENT=development in .env

PART C — Auto-switch function: `create_incident_with_fallback(decision, policy_result, router_result) -> dict`
- If ENVIRONMENT=development → use mock
- If ENVIRONMENT=production → use real ServiceNow
- This is what the rest of the app should call

PART D — `if __name__ == "__main__"` block that tests the mock and prints result

Load all credentials from .env using python-dotenv.
Output only the complete Python file. No explanation.
```

### ✅ Test Step 5

**Model: Gemini 3 Flash**

```
Write a pytest test file tests/test_servicenow.py for servicenow.py.

Test these functions:
1. create_incident_mock returns dict with ticket_id, status="CREATED"
2. ticket_id starts with "INC"
3. create_incident_with_fallback in development mode uses mock (mock returns CREATED)
4. create_incident times out correctly — mock requests with a 6-second delay and verify status="TIMEOUT"
5. create_incident handles connection error — mock requests to raise ConnectionError, verify status="ERROR"

Use unittest.mock to mock all HTTP requests. Never make real HTTP calls in tests.

Output only the complete test file. No explanation.
```

Run: `pytest tests/test_servicenow.py -v`
All pass → Update `progress.md`: `## Step 5 — ServiceNow ✅ DONE`

---

## STEP 6 — Supervisor LLM (YELLOW path)

**Model: Gemini 3.1 Pro (Low)** ← Save credits, this is simpler

### Prompt 6.1 — Build Supervisor

```
Build a Python file called supervisor.py for AgentGuard v3.

Context: When the Risk Router classifies a decision as YELLOW (borderline), it is escalated to a Supervisor LLM for semantic review. The supervisor checks for subtle proxy discrimination that hard rules and the ML classifier may have missed.

Requirements:

Function: `semantic_review(decision: dict, router_result: dict) -> dict`

1. Build a system prompt that says:
   "You are an AI compliance officer reviewing a hiring decision for potential bias or discrimination. You must evaluate whether the AI hiring agent's decision shows signs of indirect proxy discrimination against protected groups in India (caste, gender, religion, geographic origin) or violates EU AI Act Article 5. You must respond ONLY with a valid JSON object."

2. Build a user prompt that includes:
   - The candidate's features used
   - The AI's decision (APPROVE/REJECT) and reason
   - The SHAP scores showing which features mattered most
   - Ask: "Does this decision show any signs of indirect bias? Cite specific features."

3. Call OpenAI gpt-4o-mini with max_tokens=400, temperature=0.1
   Force JSON output using response_format={"type": "json_object"}

4. Parse response and return dict with:
   - supervisor_verdict: "APPROVE", "REJECT", or "ESCALATE_TO_HUMAN"
   - bias_detected: bool
   - bias_reason: string (or null)
   - confidence: float
   - features_flagged: list of strings (suspicious features)
   - review_timestamp: UTC timestamp

5. On any error → return supervisor_verdict="ESCALATE_TO_HUMAN", bias_detected=True, bias_reason="Supervisor review failed — escalating to human for safety"

Output only the complete Python file. No explanation.
```

### ✅ Test Step 6

**Model: Gemini 3 Flash**

```
Write a pytest test file tests/test_supervisor.py for supervisor.py.

Mock all OpenAI API calls. Test:
1. Returns dict with all required fields: supervisor_verdict, bias_detected, bias_reason, confidence, features_flagged
2. supervisor_verdict is one of "APPROVE", "REJECT", "ESCALATE_TO_HUMAN"
3. When OpenAI raises an exception, returns ESCALATE_TO_HUMAN with bias_detected=True
4. bias_detected is a bool
5. features_flagged is a list

Output only the test file. No explanation.
```

Run: `pytest tests/test_supervisor.py -v`
All pass → Update `progress.md`: `## Step 6 — Supervisor LLM ✅ DONE`

---

## STEP 7 — FastAPI Backend (The Pipeline)

**Model: Claude Sonnet 4.6 (Thinking)** ← This wires everything together

### Prompt 7.1 — Build the API

```
Build a Python file called api/main.py for AgentGuard v3 using FastAPI.

This file wires together the full governance pipeline: worker_agent → policy_engine → risk_router → supervisor (if YELLOW) → servicenow (if RED) → artifact_engine.

Import from:
- core.worker_agent: make_hiring_decision
- core.policy_engine: check_policy
- core.risk_router: classify_risk, check_drift
- core.supervisor: semantic_review
- core.servicenow: create_incident_with_fallback
- core.artifact_engine: generate_artifact, save_artifact

Create these endpoints:

1. POST /decision
   Request body: candidate dict (candidate_id, name, years_of_experience, skill_match_score, interview_score, assessment_score, career_gap_months, gender, institution_tier)
   
   Pipeline:
   a. Call make_hiring_decision(candidate) → get AI decision
   b. Call check_policy(decision, raw_input=str(candidate)) → policy check
   c. If policy BLOCK → classification = RED, skip router
   d. If policy PASS → call classify_risk(decision) → get GREEN/YELLOW/RED
   e. If YELLOW → call semantic_review(decision, router_result)
   f. If RED (from policy OR router) → call create_incident_with_fallback(...)
   g. Always → call generate_artifact(...) and save_artifact(...)
   h. Return full pipeline result as JSON

   Also measure total latency and include in response.

2. GET /health
   Returns: {"status": "ok", "version": "3.1"}

3. GET /decisions
   Returns: list of all saved artifact filenames from artifacts/ directory

4. GET /decisions/{decision_id}
   Returns: the artifact JSON for that decision_id

5. GET /drift
   Reads last 100 artifacts, calls check_drift(), returns drift report

6. POST /human-review/{decision_id}
   Body: {"action": "APPROVE" or "REJECT", "reviewer_id": string, "reason": string}
   Updates the artifact to add human_review field and re-saves
   Returns updated artifact

Add CORS middleware to allow all origins (for Streamlit frontend).
Add request timing middleware that logs each request's latency.

Output only the complete Python file. No explanation.
```

### ✅ Test Step 7

**Model: Gemini 3 Flash**

```
Write a pytest test file tests/test_api.py for a FastAPI app in api/main.py using TestClient.

Test these endpoints:
1. GET /health returns 200 and {"status": "ok"}
2. POST /decision with a clean candidate returns 200 with routing_classification field
3. POST /decision with a candidate whose features_used includes "emotion_score" returns routing_classification="RED"
4. POST /decision returns artifact_hash in response
5. GET /decisions returns a list (may be empty)
6. GET /drift returns alert field

Mock all external calls (OpenAI, ServiceNow). Use pytest fixtures for the TestClient.

Output only the complete test file. No explanation.
```

Run: `pytest tests/test_api.py -v`
All pass → Update `progress.md`: `## Step 7 — FastAPI Backend ✅ DONE`

---

## STEP 8 — Streamlit Dashboard (UI)

**Model: Gemini 3.1 Pro (Low)**

### Prompt 8.1 — Build Dashboard

```
Build a Streamlit dashboard file called ui/dashboard.py for AgentGuard v3.

The dashboard connects to a FastAPI backend running at http://localhost:8000.

Build these sections:

SECTION 1 — Header
- Title: "🛡️ AgentGuard v3 — AI Governance Control Plane"
- Subtitle: "Unisys Innovation Program 2026"
- Three metric cards in a row: Total Decisions Today, GREEN %, RED % (fetch from /drift)

SECTION 2 — Submit a Candidate (main demo panel)
- Form with these fields:
  * Candidate Name (text input)
  * Years of Experience (slider 0-20)
  * Skill Match Score (slider 0.0-1.0)
  * Interview Score (slider 0.0-10.0)
  * Assessment Score (slider 0-100)
  * [Checkbox] "Simulate biased AI" — if checked, adds emotion_score to features
- Submit button: "Run AgentGuard Pipeline"
- On submit: POST to /decision, show results

SECTION 3 — Decision Result Display
After submission, show:
- Big colored banner: GREEN / YELLOW / RED with emoji
- Policy check result (PASS or BLOCK with rule cited)
- Router classification with confidence score
- SHAP scores as a horizontal bar chart (use st.bar_chart)
- ServiceNow ticket ID if RED (highlighted in red box)
- Artifact hash (in monospace code block)
- Download button for the full artifact JSON: "📄 Download Regulatory Export"

SECTION 4 — Live Decision Feed
- Table showing last 10 decisions from /decisions endpoint
- Auto-refreshes every 30 seconds (use st.experimental_rerun with time.sleep)
- Columns: Candidate ID, Routing, Policy Result, Timestamp

SECTION 5 — Drift Monitor
- Pie chart of GREEN/YELLOW/RED distribution
- Alert box in red if RED > 20%: "⚠️ DRIFT ALERT: AI agent showing elevated risk pattern"

Use st.session_state to store results between interactions.
Use requests library to call the FastAPI backend.
Make it look professional — use st.columns, st.metric, st.success/error/warning appropriately.

Output only the complete Python file. No explanation.
```

### ✅ Test Step 8
Run: `streamlit run ui/dashboard.py`
Open browser → Submit Case A (clean candidate) → See GREEN
Submit Case C (check "simulate biased AI") → See RED + ServiceNow ticket
Update `progress.md`: `## Step 8 — Streamlit Dashboard ✅ DONE`

---

## STEP 8A — Resume Parsing Agent

**Model: Gemini 3 Flash**

### 1. Goal
Convert PDF resume into structured JSON for AgentGuard pipeline.

### 2. Tech Stack
- PyMuPDF or pdfplumber for text extraction
- Gemini 3 Flash for parsing

### 3. Prompt Template for LLM

"Extract the following structured hiring features from this resume:
- years_of_experience
- primary_skills
- inferred skill_match_score (0–1)
- education level
- possible proxies (institution, location, surname)

Return ONLY JSON."

### 4. Example Output JSON
```json
{
  "candidate_id": "CAND-PDF-9921",
  "name": "Arjun Mehta",
  "years_of_experience": 4.5,
  "skill_match_score": 0.88,
  "interview_score": 0.0,
  "assessment_score": 0.0,
  "applicant_surname": "Mehta",
  "institution_tier": 1,
  "home_district": "Mumbai"
}
```

### 5. Integration
Call this before /decision API to pre-populate the form.

### 6. Error Handling
If parsing fails → fallback to manual mode.

---

## STEP 9 — Docker Setup

**Model: Gemini 3 Flash**

### Prompt 9.1 — Dockerise

```
Create a docker-compose.yml and Dockerfile for AgentGuard v3.

Project structure:
- api/main.py (FastAPI, runs on port 8000)
- ui/dashboard.py (Streamlit, runs on port 8501)
- models/ directory (mounted as volume)
- artifacts/ directory (mounted as volume)
- data/ directory (mounted as volume)
- requirements.txt at root
- .env file at root

Requirements:
- Two services: api and ui
- api: runs uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
- ui: runs streamlit run ui/dashboard.py --server.port 8501 --server.address 0.0.0.0
- ui depends on api
- Both load environment variables from .env file
- Mount models/, artifacts/, data/ as volumes so data persists
- Both use Python 3.11 slim image
- Dockerfile installs requirements.txt

Output docker-compose.yml and Dockerfile. No explanation.
```

### ✅ Test Step 9
Run: `docker-compose up`
Visit http://localhost:8501 → Dashboard loads
Visit http://localhost:8000/health → `{"status": "ok"}`
Update `progress.md`: `## Step 9 — Docker ✅ DONE`

---

## STEP 10 — The Three Demo Cases

**Model: Gemini 3 Flash**

### Prompt 10.1 — Create Demo Script

```
Create a Python file called demo/run_demo.py for AgentGuard v3.

This script runs three pre-defined candidate scenarios against the AgentGuard API at http://localhost:8000 and prints a formatted demo report.

Case A — GREEN (Rahul Sharma):
{
  "candidate_id": "DEMO-CASE-A",
  "name": "Rahul Sharma",
  "years_of_experience": 5,
  "skill_match_score": 0.89,
  "interview_score": 7.8,
  "assessment_score": 82,
  "career_gap_months": 0,
  "gender": "M",
  "institution_tier": 2,
  "simulated_bias": false
}

Case B — YELLOW (Anjali Verma):
{
  "candidate_id": "DEMO-CASE-B", 
  "name": "Anjali Verma",
  "years_of_experience": 3,
  "skill_match_score": 0.71,
  "interview_score": 6.2,
  "assessment_score": 68,
  "career_gap_months": 8,
  "gender": "F",
  "institution_tier": 3,
  "simulated_bias": false
}

Case C — RED (Meena Devi):
{
  "candidate_id": "DEMO-CASE-C",
  "name": "Meena Devi",
  "years_of_experience": 4,
  "skill_match_score": 0.74,
  "interview_score": 7.1,
  "assessment_score": 76,
  "career_gap_months": 6,
  "gender": "F",
  "institution_tier": 4,
  "simulated_bias": true
}

For each case:
1. POST to /decision
2. Print a clear formatted block:
   ================================================
   CASE A — RAHUL SHARMA
   ================================================
   Routing:        GREEN ✅
   Policy:         PASS
   Confidence:     0.91
   Latency:        31ms
   Artifact Hash:  sha256:...
   ServiceNow:     N/A
   ================================================
3. After all three cases, print a summary table

Output only the complete Python file. No explanation.
```

### ✅ Test Step 10
Run API: `uvicorn api.main:app --reload`
Run demo: `python demo/run_demo.py`
All three cases print correctly → Update `progress.md`: `## Step 10 — Demo Cases ✅ DONE`

---

## Progress Tracking — progress.md Template

Create this file at the root of your project. Update it after every step.

```markdown
# AgentGuard v3 — Build Progress

**Project:** Unisys Innovation Program 2026  
**Team:** [Your team name]  
**Start Date:** [Date]  
**Target Demo Date:** [Date]

---

## Completion Status

| Step | Feature | Status | Date Completed | Notes |
|---|---|---|---|---|
| 0 | Project Setup | ⬜ TODO | - | - |
| 1 | Worker Agent | ⬜ TODO | - | - |
| 2 | Policy Engine | ⬜ TODO | - | - |
| 3 | Risk Router | ⬜ TODO | - | - |
| 4 | Artifact Engine | ⬜ TODO | - | - |
| 5 | ServiceNow | ⬜ TODO | - | - |
| 6 | Supervisor LLM | ⬜ TODO | - | - |
| 7 | FastAPI Backend | ⬜ TODO | - | - |
| 8 | Streamlit Dashboard | ⬜ TODO | - | - |
| 9 | Docker | ⬜ TODO | - | - |
| 10 | Demo Cases | ⬜ TODO | - | - |

---

## Test Results Log

### Step 2 — Policy Engine
- [ ] EMOTION_SCORE rule fires correctly
- [ ] SURNAME rule fires correctly
- [ ] INSTITUTION_TIER rule fires correctly
- [ ] MATERNITY rule fires correctly
- [ ] TRIBAL_IDENTITY rule fires correctly
- [ ] PROMPT_INJECTION rule fires correctly
- [ ] Clean decision passes with no violations

### Step 3 — Risk Router
- [ ] Model trains without error
- [ ] GREEN decision returns in < 200ms
- [ ] SHAP scores returned for all 6 features
- [ ] Drift detection alerts at RED > 20%

### Step 5 — ServiceNow
- [ ] Mock returns INC ticket ID
- [ ] Timeout handled gracefully
- [ ] Connection error handled gracefully

### Step 7 — API
- [ ] /health returns 200
- [ ] /decision runs full pipeline
- [ ] Artifact saved to disk
- [ ] /drift returns alert field

### Step 8 — Dashboard
- [ ] Case A shows GREEN banner
- [ ] Case B shows YELLOW banner
- [ ] Case C shows RED banner + ServiceNow ticket
- [ ] Download artifact button works
- [ ] SHAP bar chart renders

---

## Known Issues & Bugs

<!-- Add bugs here as you find them -->

---

## Demo Readiness Checklist

- [ ] All 10 steps complete
- [ ] All pytest tests passing
- [ ] Docker runs with one command
- [ ] Case A demo works live
- [ ] Case B demo works live
- [ ] Case C demo works live (ServiceNow ticket appears)
- [ ] Artifact downloads as valid JSON
- [ ] Artifact hash invalidates on tampering
- [ ] Team has rehearsed demo 5+ times
- [ ] ServiceNow fallback video recorded

---

## Daily Standup Log

### [Date]
**Done:** 
**Doing:** 
**Blocked:** 

```

---

## Debugging Guide — When Things Break

### Policy Engine not blocking
**Model: Claude Sonnet 4.6 Thinking**
```
My policy_engine.py check_policy function is not blocking decisions when it should.

Here is the function: [paste code]
Here is the test that's failing: [paste test]
Here is the error: [paste error]

The rule EMOTION_SCORE_IN_HIRING_PROHIBITED should fire when "emotion_score" is in features_used.
Find the bug and fix only the check_policy function. Do not change anything else.
```

### Router giving wrong classifications
**Model: Claude Sonnet 4.6 Thinking**
```
My risk_router.py classify_risk function is returning wrong risk levels.

Expected: LOW confidence decisions should return RED or YELLOW
Getting: Everything is returning GREEN

Here is the training code: [paste]
Here is the classify_risk function: [paste]
Here is the dataset columns: [paste head of CSV]

Find the root cause. Is it a training data issue, a feature extraction issue, or a prediction threshold issue? Fix only what is broken.
```

### ServiceNow 401 Unauthorized
**Model: Gemini 3 Flash**
```
My ServiceNow API call is returning 401 Unauthorized.

Instance URL: [your url]
I am using Basic Auth with username and password from .env

Here is my request code: [paste]

What are the most common causes of 401 on ServiceNow Table API and how do I fix each one?
```

### SHAP import error
**Model: Gemini 3 Flash**
```
I am getting this error when importing shap: [paste error]
I am using sklearn GradientBoostingClassifier.
Which SHAP explainer should I use and how do I initialise it correctly?
Show me only the corrected import and explainer initialisation code.
```

### Streamlit not connecting to FastAPI
**Model: Gemini 3 Flash**
```
My Streamlit dashboard at port 8501 cannot connect to FastAPI at localhost:8000.
I get a connection refused error on requests.post("http://localhost:8000/decision").

Both are running locally. What are the possible causes and fixes?
I am on [Windows/Mac/Linux].
```

---

## Final Week Checklist (Week 11-12)

### Performance benchmarks to measure and record:
Run `python demo/run_demo.py` 100 times and record:
- Average latency for GREEN decisions (target: < 50ms)
- Average latency for RED decisions (target: < 500ms including ServiceNow)
- % of decisions routed GREEN on clean synthetic data (target: > 85%)

### The one sentence for every judge question:

| Question | Answer |
|---|---|
| "How is this different from Purview?" | "Purview monitors Microsoft agents. We block any AI agent before execution and commit to ServiceNow — Purview does neither." |
| "Why not fix the AI model?" | "Fixing the model takes months and gives no legal evidence. We govern any model without modifying it." |
| "Why not audit after the fact?" | "Because the rejection email has already gone out. You cannot un-reject Meena Devi." |
| "Who audits the auditor?" | "The supervisor's output is logged in every YELLOW artifact. The supervisor cannot approve bias without it being permanently recorded." |
| "What is your false negative rate?" | "[State your actual number from testing on synthetic dataset]" |

---

*AgentGuard v3 · Build Guide v1.0 · Unisys Innovation Program 2026*

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
import json
import uuid
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.resume_parser import extract_text_from_pdf, parse_resume

# Configuration
BASE_URL = os.getenv("AGENTGUARD_API_BASE", "http://127.0.0.1:8000")
st.set_page_config(page_title="AgentGuard v3 — AI Governance", layout="wide", page_icon="🛡️")

# Initialize Session State
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0
if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = {}

# --- Helper Functions ---

def check_backend_health():
    """Checks if the backend is reachable and returns status/version."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            return True, response.json().get("version", "3.x")
    except:
        pass
    return False, None

def remove_none_values(d):
    """Recursively removes None values from a dictionary."""
    if not isinstance(d, dict):
        return d
    return {k: v for k, v in d.items() if v is not None}

# --- SECTION 1: Header & Health Check ---
is_healthy, version = check_backend_health()

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("🛡️ AgentGuard v3 — AI Governance Control Plane")
    st.markdown("### Unisys Innovation Program 2026")

with col_h2:
    if is_healthy:
        st.success(f"🟢 Backend Online\nv{version}")
    else:
        st.error("🔴 Backend Offline\nCheck API Server")

def get_drift_data():
    if not is_healthy:
        return {"total_decisions": 0, "green_pct": 0.0, "red_pct": 0.0, "yellow_pct": 0.0}
    try:
        response = requests.get(f"{BASE_URL}/drift", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"total_decisions": 0, "green_pct": 0.0, "red_pct": 0.0, "yellow_pct": 0.0}

drift = get_drift_data()
col1, col2, col3 = st.columns(3)
col1.metric("Total Decisions Today", drift.get("total_decisions", 0))
col2.metric("GREEN %", f"{drift.get('green_pct', 0):.1f}%", delta=None)
col3.metric("RED %", f"{drift.get('red_pct', 0):.1f}%", delta=None, delta_color="inverse")

st.divider()

# --- SECTION 2: Job-Aware Candidate Ingestion ---
st.header("👤 Job-Aware Candidate Ingestion")

input_mode = st.radio("Select Input Mode", ["Manual Input", "Resume Upload (PDF)"], horizontal=True)

if input_mode == "Resume Upload (PDF)":
    # Predefined Job Descriptions
    PREDEFINED_JDS = {
        "Software Engineer": "Role: Software Engineer. Requirements: Python, APIs, Data Structures, System Design.",
        "Data Scientist": "Role: Data Scientist. Requirements: Python, ML, Pandas, Statistics.",
        "Frontend Developer": "Role: Frontend Developer. Requirements: React, JS, UI/UX."
    }

    # Job Description Input
    jd_option = st.selectbox("Select Target Role", ["Custom"] + list(PREDEFINED_JDS.keys()))
    if jd_option == "Custom":
        jd_text = st.text_area("Job Description", placeholder="Paste the JD here...", height=150)
    else:
        jd_text = PREDEFINED_JDS[jd_option]
        st.info(f"**JD Summary:** {jd_text}")
    
    uploaded_file = st.file_uploader("Upload Candidate Resume", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Evaluate Candidate with Gemini"):
            if not jd_text:
                st.warning("Please provide a Job Description first.")
            else:
                with st.spinner("Analyzing resume against JD..."):
                    try:
                        pdf_bytes = uploaded_file.read()
                        text = extract_text_from_pdf(pdf_bytes)
                        if not text.strip():
                            st.error("No text could be extracted from this PDF.")
                        else:
                            parsed = parse_resume(text, jd_text)
                            st.session_state.parsed_data = parsed
                            st.success("Evaluation complete! Review the derived data below.")
                    except Exception as e:
                        st.error(f"Evaluation failed: {e}")

st.markdown("### 📋 Candidate Data Review")
with st.form("candidate_form"):
    d = st.session_state.parsed_data
    
    # Display Score & Reasoning if available
    if d.get("skill_match_score") is not None:
        c_score, c_reason = st.columns([1, 2])
        c_score.metric("Skill Match Score", f"{d.get('skill_match_score', 0):.2f}")
        c_reason.info(f"**AI Reasoning:** {d.get('match_reasoning', 'N/A')}")
        
        if d.get("missing_skills"):
            st.markdown(f"**Missing Skills Detected:** {', '.join(d.get('missing_skills'))}")

    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Candidate Name", value=d.get("name", "John Doe"))
        candidate_id = st.text_input("Candidate ID", value=d.get("candidate_id", f"CAND-{uuid.uuid4().hex[:6].upper()}"))
        experience = st.slider("Years of Experience", 0.0, 20.0, float(d.get("years_of_experience", 5.0)))
        skill_score = st.slider("Override Skill Match Score", 0.0, 1.0, float(d.get("skill_match_score", 0.75)), step=0.01)
        
    with c2:
        interview_score = st.slider("Interview Score", 0.0, 10.0, float(d.get("interview_score", 7.0)), step=0.1)
        assessment_score = st.slider("Assessment Score", 0.0, 100.0, float(d.get("assessment_score", 75.0)))
        
        with st.expander("Additional Metadata (Optional)"):
            gender = st.selectbox("Gender", [None, "M", "F", "Other"], index=0 if d.get("gender") is None else ["M", "F", "Other"].index(d.get("gender")) + 1 if d.get("gender") in ["M", "F", "Other"] else 0)
            career_gap = st.number_input("Career Gap (Months)", min_value=0, value=int(d.get("career_gap_months", 0)))
            tier = st.selectbox("Institution Tier", [None, 1, 2, 3, 4, 5], index=d.get("institution_tier", 0) if d.get("institution_tier") in [1,2,3,4,5] else 0)

    st.markdown("---")
    simulate_bias = st.toggle("🛡️ Simulate Biased AI", value=False)
    
    biased_payload = {}
    has_proxies = d.get("applicant_surname") or d.get("home_district") or d.get("institution_tier")
    if simulate_bias or has_proxies:
        b1, b2 = st.columns(2)
        with b1:
            surname = st.text_input("Applicant Surname", value=d.get("applicant_surname", ""))
            home_dist = st.text_input("Home District", value=d.get("home_district", ""))
        with b2:
            emotion = st.slider("Emotion Score", 0.0, 1.0, float(d.get("emotion_score", 0.45)))
            village = st.text_input("Village Code", value=d.get("village_code", ""))
        
        biased_payload = {
            "applicant_surname": surname if surname else None,
            "home_district": home_dist if home_dist else None,
            "emotion_score": emotion,
            "village_code": village if village else None
        }

    submit = st.form_submit_button("Submit to Governance Pipeline", disabled=not is_healthy)

if submit:
    if not name:
        st.error("Candidate Name is required.")
    else:
        payload = {
            "candidate_id": candidate_id,
            "name": name,
            "years_of_experience": experience,
            "skill_match_score": skill_score,
            "interview_score": interview_score,
            "assessment_score": assessment_score,
            "career_gap_months": career_gap,
            "gender": gender,
            "institution_tier": tier,
            **biased_payload
        }
        payload = remove_none_values(payload)
        with st.spinner("Processing..."):
            try:
                resp = requests.post(f"{BASE_URL}/decision", json=payload, timeout=15)
                if resp.status_code == 200:
                    st.session_state.last_result = resp.json()
                    st.success("Analysis Complete")
                    st.session_state.parsed_data = {}
                else:
                    st.error(f"Backend Error: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# --- SECTION 3: Decision Result Display ---
if st.session_state.last_result:
    res = st.session_state.last_result
    risk_level = res.get("classification", "UNKNOWN").upper()
    
    st.divider()
    st.header("🎯 Pipeline Analysis Result")
    
    # Banner
    if risk_level == "GREEN":
        st.success(f"### ✅ {risk_level} — SAFE TO PROCEED")
    elif risk_level == "YELLOW":
        st.warning(f"### ⚠️ {risk_level} — MANUAL REVIEW REQUIRED")
    else:
        st.error(f"### 🛑 {risk_level} — AUTOMATIC BLOCK")

    r1, r2 = st.columns([1, 2])
    with r1:
        st.subheader("Compliance & Routing")
        policy = res.get("policy_result", {})
        policy_status = "PASS" if policy.get("passed") else "BLOCK"
        st.write(f"**Policy Result:** `{policy_status}`")
        if not policy.get("passed"):
            violations = policy.get("violations", [])
            for v in violations:
                st.info(f"**Rule Violated:** {v.get('rule_name')}\n\n*Reason: {v.get('reason')}*")
        
        router = res.get("router_result", {})
        st.write(f"**Classification:** {router.get('risk_level', risk_level)}")
        st.write(f"**Confidence:** {router.get('confidence_score', 0):.2%}")
        
        if risk_level == "RED":
            sn_res = res.get("servicenow_result", {})
            ticket = sn_res.get("ticket_id", "PENDING") if sn_res else "PENDING"
            st.markdown(f"""
                <div style="border: 2px solid red; padding: 10px; border-radius: 5px; background-color: #ffe6e6;">
                    <h4 style="color: red; margin-top: 0;">ServiceNow Incident</h4>
                    <code>ID: {ticket}</code>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        artifact = res.get("artifact", {})
        st.write("**Artifact Integrity Hash:**")
        st.code(artifact.get("artifact_hash", "N/A"))
        
        json_data = json.dumps(res, indent=2)
        st.download_button(
            label="📄 Download Regulatory Export",
            data=json_data,
            file_name=f"artifact_{artifact.get('candidate_id', 'unknown')}.json",
            mime="application/json"
        )

    with r2:
        st.subheader("Model Explainability (SHAP)")
        router_res = res.get("router_result", {})
        shap_data = router_res.get("shap_scores", {})
        if shap_data:
            df_shap = pd.DataFrame(list(shap_data.items()), columns=["Feature", "Impact"])
            st.bar_chart(df_shap.set_index("Feature"))
        else:
            st.info("SHAP values not available for this classification level.")

# --- SECTION 4: Live Decision Feed ---
st.divider()
st.header("📡 Live Decision Feed")

def fetch_history():
    if not is_healthy:
        return []
    try:
        response = requests.get(f"{BASE_URL}/decisions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("artifacts", [])
    except:
        pass
    return []

history_files = fetch_history()
if history_files:
    st.write(f"Found {len(history_files)} recent decision artifacts.")
    st.write(history_files[:10])
else:
    st.info("No recent decisions found.")

# --- SECTION 5: Drift Monitor ---
st.divider()
st.header("📊 Drift & Distribution Monitor")

d_col1, d_col2 = st.columns([1, 1])

with d_col1:
    dist_data = {
        "Status": ["GREEN", "YELLOW", "RED"],
        "Count": [drift.get("green_count", 0), drift.get("yellow_count", 0), drift.get("red_count", 0)]
    }
    df_dist = pd.DataFrame(dist_data)
    fig = px.pie(df_dist, values='Count', names='Status', 
                 color='Status',
                 color_discrete_map={'GREEN':'#28a745', 'YELLOW':'#ffc107', 'RED':'#dc3545'})
    st.plotly_chart(fig, width='stretch')

with d_col2:
    red_pct = drift.get("red_pct", 0)
    if red_pct > 20:
        st.error(f"""
            ### ⚠️ DRIFT ALERT
            **AI agent showing elevated risk pattern.**
            Current RED distribution is **{red_pct:.1f}%**, exceeding the 20% safety threshold.
            *Immediate audit recommended.*
        """)
    else:
        st.success("### ✅ System Stable\nRisk distribution within operational bounds.")

# Auto-refresh logic
st.empty()
time.sleep(30)
st.session_state.refresh_counter += 1
st.rerun()

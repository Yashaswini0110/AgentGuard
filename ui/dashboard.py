import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"
st.set_page_config(page_title="AgentGuard v3 — AI Governance", layout="wide", page_icon="🛡️")

# Initialize Session State
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

# --- SECTION 1: Header ---
st.title("🛡️ AgentGuard v3 — AI Governance Control Plane")
st.markdown("### Unisys Innovation Program 2026")

def get_drift_data():
    try:
        response = requests.get(f"{BASE_URL}/drift", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return {"total_decisions": 0, "green_pct": 0.0, "red_pct": 0.0, "yellow_pct": 0.0}
    return {"total_decisions": 0, "green_pct": 0.0, "red_pct": 0.0, "yellow_pct": 0.0}

drift = get_drift_data()
col1, col2, col3 = st.columns(3)
col1.metric("Total Decisions Today", drift.get("total_decisions", 0))
col2.metric("GREEN %", f"{drift.get('green_pct', 0):.1f}%", delta=None)
col3.metric("RED %", f"{drift.get('red_pct', 0):.1f}%", delta=None, delta_color="inverse")

st.divider()

# --- SECTION 2: Submit a Candidate ---
st.header("👤 Submit a Candidate")
with st.form("candidate_form"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Candidate Name", placeholder="John Doe")
        experience = st.slider("Years of Experience", 0, 20, 5)
        skill_score = st.slider("Skill Match Score", 0.0, 1.0, 0.75, step=0.01)
    with c2:
        interview_score = st.slider("Interview Score", 0.0, 10.0, 7.0, step=0.1)
        assessment_score = st.slider("Assessment Score", 0, 100, 75)
        simulate_bias = st.checkbox("Simulate biased AI")
    
    submit = st.form_submit_button("Run AgentGuard Pipeline")

if submit:
    payload = {
        "candidate_name": name,
        "years_experience": experience,
        "skill_match": skill_score,
        "interview_score": interview_score,
        "assessment_score": assessment_score,
        "features": {"emotion_score": 0.1} if simulate_bias else {}
    }
    
    with st.spinner("Processing through governance layers..."):
        try:
            resp = requests.post(f"{BASE_URL}/decision", json=payload)
            if resp.status_code == 200:
                st.session_state.last_result = resp.json()
                st.success("Analysis Complete")
            else:
                st.error(f"Backend Error: {resp.text}")
        except Exception as e:
            st.error(f"Connection Failed: {e}")

# --- SECTION 3: Decision Result Display ---
if st.session_state.last_result:
    res = st.session_state.last_result
    risk_level = res.get("risk_level", "UNKNOWN").upper()
    
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
        policy = res.get("policy_check", {})
        policy_status = "PASS" if policy.get("passed") else "BLOCK"
        st.write(f"**Policy Result:** `{policy_status}`")
        if not policy.get("passed"):
            st.info(f"**Rule Violated:** {policy.get('violation_rule')}")
        
        router = res.get("router", {})
        st.write(f"**Classification:** {router.get('class')}")
        st.write(f"**Confidence:** {router.get('confidence', 0):.2%}")
        
        if risk_level == "RED":
            ticket = res.get("servicenow_ticket", "PENDING")
            st.markdown(f"""
                <div style="border: 2px solid red; padding: 10px; border-radius: 5px; background-color: #ffe6e6;">
                    <h4 style="color: red; margin-top: 0;">ServiceNow Incident</h4>
                    <code>ID: {ticket}</code>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        st.write("**Artifact Integrity Hash:**")
        st.code(res.get("artifact_hash", "N/A"))
        
        json_data = json.dumps(res, indent=2)
        st.download_button(
            label="📄 Download Regulatory Export",
            data=json_data,
            file_name=f"artifact_{res.get('candidate_id', 'unknown')}.json",
            mime="application/json"
        )

    with r2:
        st.subheader("Model Explainability (SHAP)")
        shap_data = res.get("shap_values", {})
        if shap_data:
            df_shap = pd.DataFrame(list(shap_data.items()), columns=["Feature", "Impact"])
            st.bar_chart(df_shap.set_index("Feature"))
        else:
            st.info("SHAP values not available for this classification level.")

# --- SECTION 4: Live Decision Feed ---
st.divider()
st.header("📡 Live Decision Feed")

def fetch_history():
    try:
        response = requests.get(f"{BASE_URL}/decisions", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return []
    return []

history = fetch_history()
if history:
    df_history = pd.DataFrame(history).head(10)
    # Map columns for display
    display_cols = {
        "candidate_id": "Candidate ID",
        "risk_level": "Routing",
        "policy_passed": "Policy Result",
        "timestamp": "Timestamp"
    }
    st.table(df_history[list(display_cols.keys())].rename(columns=display_cols))
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
    st.plotly_chart(fig, use_container_width=True)

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
st.experimental_rerun()

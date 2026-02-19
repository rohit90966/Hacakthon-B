import json
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="SAR Narrative Generator", layout="wide")


def fetch_cases():
    try:
        return requests.get(f"{API_BASE}/cases", timeout=30).json()
    except Exception:
        return []


def fetch_case(case_id: str):
    return requests.get(f"{API_BASE}/cases/{case_id}", timeout=30).json()


def fetch_audit(case_id: str):
    return requests.get(f"{API_BASE}/cases/{case_id}/audit", timeout=30).json()


st.sidebar.header("Case Controls")
uploaded = st.sidebar.file_uploader("Upload alert JSON", type=["json"], help="Upload a single alert file")
run_generation = st.sidebar.button("Run generation")
refresh = st.sidebar.button("Refresh cases")

if refresh or "cases" not in st.session_state:
    st.session_state["cases"] = fetch_cases()

cases = st.session_state.get("cases", [])
selected_case_id = st.sidebar.selectbox("Select case", options=[""].__add__([c["id"] for c in cases]))

if run_generation and uploaded is not None:
    alert_json = json.load(uploaded)
    resp = requests.post(f"{API_BASE}/ingest-alert", json=alert_json, timeout=300)
    if resp.ok:
        st.sidebar.success(f"Case created: {resp.json().get('case_id')} — refresh to view")
        st.session_state.pop("cases", None)
    else:
        st.sidebar.error(resp.text)


tab_upload, tab_sar, tab_evidence, tab_risk, tab_validation, tab_audit = st.tabs([
    "Upload Alert",
    "Generated SAR",
    "Evidence Explorer",
    "Risk Dashboard",
    "Validation Report",
    "Audit Timeline",
])


with tab_upload:
    st.markdown("### Upload Alert")
    st.write("Use the sidebar to upload an alert and run generation. Batch ingest is available via the API at POST /batch-ingest.")


with tab_sar:
    st.markdown("### Generated SAR Narrative")
    if selected_case_id:
        case = fetch_case(selected_case_id)
        st.markdown(f"**Status:** {case.get('status')} | **Risk:** {case.get('risk_level')} ({case.get('risk_score')}) | **Confidence:** {round(case.get('confidence_level', 0),2)}")

        sections = (case.get("draft_narrative") or {}).get("sections", {})
        if sections:
            for title, body in sections.items():
                with st.expander(title, expanded=False):
                    st.write(body)
        else:
            st.info("Narrative not available yet.")

        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("Submit for Review"):
                res = requests.post(f"{API_BASE}/cases/{selected_case_id}/submit", json={"user": "analyst"}, timeout=30)
                st.experimental_rerun() if res.ok else st.error(res.text)
        with colB:
            if st.button("Approve"):
                payload = {"comment": "Approved via UI", "role": "analyst", "narrative": case.get("draft_narrative")}
                res = requests.post(f"{API_BASE}/cases/{selected_case_id}/approve", json=payload, timeout=30)
                st.experimental_rerun() if res.ok else st.error(res.text)
        with colC:
            if st.button("Finalize & Submit"):
                res = requests.post(f"{API_BASE}/cases/{selected_case_id}/finalize", json={"user": "approver"}, timeout=30)
                st.experimental_rerun() if res.ok else st.error(res.text)

        st.download_button("Download PDF", data=requests.get(f"{API_BASE}/cases/{selected_case_id}/export/pdf").content, file_name=f"{selected_case_id}.pdf")
        st.download_button("Download JSON", data=json.dumps(requests.get(f"{API_BASE}/cases/{selected_case_id}/export/json").json()), file_name=f"{selected_case_id}.json")
    else:
        st.info("Select a case from the sidebar to view the SAR narrative.")


with tab_evidence:
    st.markdown("### Evidence Explorer")
    if selected_case_id:
        case = fetch_case(selected_case_id)
        evidence = case.get("evidence_data", {})
        trace = case.get("explainability_trace", [])
        st.subheader("Evidence Blocks")
        st.json(evidence)
        st.subheader("Explainability Trace")
        st.json(trace)
    else:
        st.info("Select a case to explore evidence.")


with tab_risk:
    st.markdown("### Risk Dashboard")
    if selected_case_id:
        case = fetch_case(selected_case_id)
        st.metric(label="Risk Score", value=round(case.get("risk_score", 0), 2), delta=case.get("risk_level"))
        factors = (case.get("draft_narrative") or {}).get("contributing_factors") or {}
        if factors:
            st.bar_chart(factors)
    else:
        st.info("Select a case to view risk metrics.")


with tab_validation:
    st.markdown("### Validation Report")
    if selected_case_id:
        case = fetch_case(selected_case_id)
        validation = case.get("validation_v2_results") or {}
        st.json(validation)
    else:
        st.info("Select a case to view validation results.")


with tab_audit:
    st.markdown("### Audit Timeline")
    if selected_case_id:
        audit = fetch_audit(selected_case_id)
        for ev in audit.get("timeline", []):
            st.markdown(f"**{ev['event_type']}** {ev['timestamp']}")
            with st.expander("View payload"):
                st.json(ev.get("payload"))
    else:
        st.info("Select a case to view audit events.")

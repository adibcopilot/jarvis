"""
dashboard/app.py
JARVIS Dashboard — Streamlit UI

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import cv2
import numpy as np
import json
import tempfile
from datetime import datetime

from database.db import get_all_events, get_pending_events, get_event_stats, update_approval
from detection.pipeline import run_ppe_pipeline, run_fire_pipeline, run_conveyor_fault_pipeline
from simulation.conveyor import get_status as get_conveyor_status, run as run_conveyor, manual_stop as stop_conveyor


# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JARVIS",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal Monochrome CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    *, html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* ── Reset Streamlit chrome ── */
    header[data-testid="stHeader"] { background: #fff; border-bottom: 1px solid #e0e0e0; }
    section[data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #e0e0e0;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 0.82rem;
        font-weight: 500;
        letter-spacing: 0.01em;
        color: #222;
    }
    .block-container { padding-top: 2rem; max-width: 1100px; }

    /* ── Header ── */
    .jarvis-header {
        border-bottom: 1px solid #d0d0d0;
        padding-bottom: 0.6rem;
        margin-bottom: 1.8rem;
    }
    .jarvis-header h1 {
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #000;
        margin: 0;
    }
    .jarvis-header p {
        font-size: 0.72rem;
        color: #888;
        margin: 0.15rem 0 0 0;
        letter-spacing: 0.02em;
    }

    /* ── Stat cards ── */
    .stat-card {
        border: 1px solid #d0d0d0;
        padding: 1rem 0.8rem;
        text-align: center;
    }
    .stat-card .num {
        font-size: 1.6rem;
        font-weight: 700;
        color: #000;
        line-height: 1;
    }
    .stat-card .label {
        font-size: 0.68rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 0.3rem;
    }

    /* ── Severity pills ── */
    .pill {
        display: inline-block;
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.15rem 0.5rem;
        border: 1px solid #999;
        color: #444;
    }
    .pill-filled {
        background: #000;
        color: #fff;
        border-color: #000;
    }
    .pill-outline {
        background: transparent;
        color: #555;
        border-color: #aaa;
    }

    /* ── Status dots ── */
    .dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 5px;
        vertical-align: middle;
    }
    .dot-pending { background: #aaa; }
    .dot-approved { background: #000; }
    .dot-denied { background: #ccc; border: 1px solid #999; }

    /* ── Event row ── */
    .event-row {
        border: 1px solid #e0e0e0;
        padding: 0.9rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.78rem;
        line-height: 1.5;
    }
    .event-row strong { font-weight: 600; color: #000; }
    .event-meta {
        font-size: 0.7rem;
        color: #888;
    }

    /* ── Section headings ── */
    .section-heading {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #666;
        margin-bottom: 0.8rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #e0e0e0;
    }

    /* ── Clean up Streamlit defaults ── */
    .stDataFrame { font-size: 0.78rem; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 0; }
    div[data-testid="stExpander"] summary { font-size: 0.8rem; font-weight: 500; }
    .stAlert { border-radius: 0; border: 1px solid #d0d0d0; }
    button[kind="secondary"] { border-radius: 0 !important; font-size: 0.75rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="jarvis-header">
    <h1>JARVIS</h1>
    <p>Joint Autonomous Reasoning &amp; Vision Inspection System</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar Navigation ──────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Upload & Detect", "Conveyor Control", "Approval Queue", "Event Log"],
    index=0,
)
st.sidebar.markdown("---")


# ── Helpers ──────────────────────────────────────────────────────────────────
def severity_pill(sev: str) -> str:
    if sev in ("critical", "high"):
        return f'<span class="pill pill-filled">{sev}</span>'
    return f'<span class="pill pill-outline">{sev}</span>'

def status_label(status: str) -> str:
    dot_class = {"pending": "dot-pending", "approved": "dot-approved", "denied": "dot-denied"}.get(status, "dot-pending")
    return f'<span class="dot {dot_class}"></span><span style="font-size:0.75rem;color:#444;">{status.upper()}</span>'


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Dashboard
# ════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    stats = get_event_stats()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="num">{stats["total_events"]}</div><div class="label">Total Events</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="num">{stats["pending"]}</div><div class="label">Pending</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="num">{stats["approved"]}</div><div class="label">Approved</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="num">{stats["denied"]}</div><div class="label">Denied</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card"><div class="num">{stats["high_severity"]}</div><div class="label">High / Critical</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Recent Events</div>', unsafe_allow_html=True)

    events = get_all_events()
    if events:
        display_data = []
        for e in events[:25]:
            display_data.append({
                "ID": e["event_id"],
                "Timestamp": e["timestamp"],
                "Type": e["event_type"].upper(),
                "Source": e["source_file"] or "—",
                "Severity": e["severity"].upper(),
                "Status": e["approval_status"].upper(),
                "Proposed Action": (e["proposed_action"][:90] + "...") if len(e["proposed_action"]) > 90 else e["proposed_action"],
            })
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.caption("No events recorded. Upload an image or trigger conveyor simulation to begin.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Upload & Detect
# ════════════════════════════════════════════════════════════════════════════
elif page == "Upload & Detect":
    st.markdown('<div class="section-heading">Upload Image for Detection</div>', unsafe_allow_html=True)

    col_mode, col_upload = st.columns([1, 3])
    with col_mode:
        detection_mode = st.radio("Mode", ["PPE Compliance", "Fire & Smoke"], index=0)
    with col_upload:
        uploaded_file = st.file_uploader("Choose file", type=["jpg", "jpeg", "png"], key="upload_detect", label_visibility="collapsed")

    if uploaded_file is not None:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        with st.spinner("Processing..."):
            if detection_mode == "PPE Compliance":
                result = run_ppe_pipeline(tmp_path)
            else:
                result = run_fire_pipeline(tmp_path)

        col_img, col_info = st.columns([1, 1])

        with col_img:
            st.markdown('<div class="section-heading">Annotated Output</div>', unsafe_allow_html=True)
            annotated_rgb = cv2.cvtColor(result["annotated_image"], cv2.COLOR_BGR2RGB)
            st.image(annotated_rgb, use_container_width=True)

        with col_info:
            cls = result["classification"]
            sev = cls["severity"]

            st.markdown('<div class="section-heading">Agent Classification</div>', unsafe_allow_html=True)

            st.markdown(f"**Severity** &nbsp; {severity_pill(sev)}", unsafe_allow_html=True)
            st.markdown(f"**Category** &nbsp; {cls['category']}")
            st.markdown(f"**Event** &nbsp; #{result['event_id']}")

            st.markdown("---")
            st.markdown("**Proposed Action**")
            st.markdown(f'<div class="event-row">{cls["proposed_action"]}</div>', unsafe_allow_html=True)

            st.markdown("**Reasoning**")
            st.caption(cls["reasoning"])

            st.markdown("---")
            st.markdown("**Summary**")
            if result.get("summary"):
                for label, count in result["summary"].items():
                    st.text(f"  {label}: {count}")

            if result["detections"]:
                with st.expander("All detections"):
                    for i, d in enumerate(result["detections"], 1):
                        st.text(f"#{i:02d}  {d['label']:<12} conf={d['confidence']:.3f}  bbox={d['bbox']}")

        st.caption(f"Event #{result['event_id']} logged. Status: pending.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Conveyor Control (Simulation Layer)
# ════════════════════════════════════════════════════════════════════════════
elif page == "Conveyor Control":
    st.markdown('<div class="section-heading">Conveyor Line 1 — Software Simulation</div>', unsafe_allow_html=True)
    st.caption("Simulated motor/sensor feed standing in for PLC signal per Project Proposal Section 4.")

    c_status = get_conveyor_status()
    curr_status = c_status["status"]
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f'<div class="stat-card"><div class="num">{c_status["line_id"]}</div><div class="label">Line ID</div></div>', unsafe_allow_html=True)
    with col_s2:
        st.markdown(f'<div class="stat-card"><div class="num">{curr_status.upper()}</div><div class="label">Current State</div></div>', unsafe_allow_html=True)
    with col_s3:
        st.markdown(f'<div class="stat-card"><div class="num">{c_status.get("last_change_reason", "—")[:18]}</div><div class="label">Last Change Reason</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Operational Controls</div>', unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶ Run Line (Commanded)", use_container_width=True):
            run_conveyor()
            st.success("Conveyor Line 1 commanded to RUN. (Normal operational state — no incident logged).")
            st.rerun()
    with col_btn2:
        if st.button("⏹ Manual Stop (Commanded)", use_container_width=True):
            stop_conveyor()
            st.info("Conveyor Line 1 commanded to STOP. (User-commanded stop — distinguished from unplanned fault).")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Fault Injection (Unplanned Incident Simulation)</div>', unsafe_allow_html=True)
    
    col_fault_type, col_fault_act = st.columns([2, 1])
    with col_fault_type:
        fault_choice = st.selectbox(
            "Select Fault Type to Inject",
            ["mechanical_jam", "motor_overheat", "sensor_desync", "belt_misalignment"],
            label_visibility="collapsed"
        )
    with col_fault_act:
        if st.button("⚡ Inject Unplanned Fault", use_container_width=True):
            res = run_conveyor_fault_pipeline(fault_choice)
            st.warning(f"Unplanned fault '{fault_choice}' injected! Logged as Event #{res['event_id']}.")
            st.caption("Reasoning agent classified severity as HIGH (mechanical). Action queued in Approval Queue.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Approval Queue
# ════════════════════════════════════════════════════════════════════════════
elif page == "Approval Queue":
    st.markdown('<div class="section-heading">Pending — Approve or Deny</div>', unsafe_allow_html=True)

    pending = get_pending_events()

    if not pending:
        st.caption("Nothing pending. All events have been reviewed.")
    else:
        st.caption(f"{len(pending)} event(s) awaiting review.")

        for event in pending:
            sev = event["severity"]

            st.markdown(f"""
            <div class="event-row">
                <strong>#{event['event_id']}</strong> &nbsp;
                {event['event_type'].upper()} &nbsp;
                {severity_pill(sev)} &nbsp;
                <span class="event-meta">{event['timestamp']} &nbsp; {event['source_file'] or ''}</span>
                <br><span style="font-size:0.75rem;color:#555;margin-top:0.3rem;display:inline-block;">{event['proposed_action']}</span>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_d, col_space = st.columns([1, 1, 6])
            with col_a:
                if st.button("Approve", key=f"approve_{event['event_id']}"):
                    update_approval(event["event_id"], "approved", "Manager")
                    st.rerun()
            with col_d:
                if st.button("Deny", key=f"deny_{event['event_id']}"):
                    update_approval(event["event_id"], "denied", "Manager")
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Event Log
# ════════════════════════════════════════════════════════════════════════════
elif page == "Event Log":
    st.markdown('<div class="section-heading">Event Log</div>', unsafe_allow_html=True)

    events = get_all_events()

    if not events:
        st.caption("No events recorded.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            type_filter = st.selectbox("Type", ["All", "PPE", "Fire", "Conveyor"], label_visibility="visible")
        with col_f2:
            status_filter = st.selectbox("Status", ["All", "Pending", "Approved", "Denied"], label_visibility="visible")

        filtered = events
        if type_filter != "All":
            filtered = [e for e in filtered if e["event_type"] == type_filter.lower()]
        if status_filter != "All":
            filtered = [e for e in filtered if e["approval_status"] == status_filter.lower()]

        st.caption(f"{len(filtered)} of {len(events)} events")

        for event in filtered:
            sev = event["severity"]
            status = event["approval_status"]

            with st.expander(f"#{event['event_id']}  {event['event_type'].upper()}  {sev.upper()}  {status.upper()}  {event['timestamp']}"):
                st.markdown(f"**Source** &nbsp; {event['source_file'] or '—'}")
                st.markdown(f"**Severity** &nbsp; {severity_pill(sev)}", unsafe_allow_html=True)
                st.markdown(f"**Category** &nbsp; {event['category']}")
                st.markdown(f"**Status** &nbsp; {status_label(status)}", unsafe_allow_html=True)
                st.markdown(f"**Proposed Action** &nbsp; {event['proposed_action']}")

                if event.get("approved_by"):
                    st.markdown(f"**Reviewed by** &nbsp; {event['approved_by']} at {event.get('resolved_at', '—')}")

                if event.get("detections_json"):
                    dets = json.loads(event["detections_json"])
                    if dets:
                        st.markdown("**Detections**")
                        for i, d in enumerate(dets, 1):
                            st.text(f"  #{i:02d}  {d.get('label','-'):<15} conf={d.get('confidence',1.0):.3f}  bbox={d.get('bbox','-')}")

                st.caption(f"hash: {(event.get('record_hash') or '—')[:32]}...")
                st.caption(f"prev: {(event.get('prev_hash') or '—')[:32]}...")

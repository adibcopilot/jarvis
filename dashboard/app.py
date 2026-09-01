"""
dashboard/app.py
JARVIS Dashboard — Strict Monochrome Industrial UI

Run with:
    streamlit run dashboard/app.py --server.port 8501
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

import streamlit as st
import cv2
import numpy as np
import pandas as pd

from database.db import (
    get_all_events,
    get_pending_events,
    get_event_stats,
    update_approval,
)
from detection.pipeline import (
    run_ppe_pipeline,
    run_fire_pipeline,
    run_conveyor_fault_pipeline,
    _get_ppe_detector,
    _get_fire_detector,
)
from simulation.conveyor import (
    get_status as get_conveyor_status,
    run as run_conveyor,
    manual_stop as stop_conveyor,
)
from reports.export import export_events_to_csv, get_events_dataframe
from agent.shift_report import generate_shift_report


# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JARVIS — Industrial Monitor",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Strict Monochrome Swiss Design System (No Color / No Gradients / No Shadows)
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Base Reset */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #0a0a0a !important;
        color: #ffffff !important;
    }

    /* Streamlit Chrome Overrides — Unified #0a0a0a Canvas */
    header[data-testid="stHeader"] {
        background-color: #0a0a0a !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: #0a0a0a !important;
    }

    /* Fixed 240px Sidebar with matching dark background */
    section[data-testid="stSidebar"] {
        background-color: #0a0a0a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
        min-width: 240px !important;
        max-width: 240px !important;
    }

    section[data-testid="stSidebar"] > div {
        background-color: #0a0a0a !important;
        padding-top: 1.5rem;
    }

    /* Navigation Radio Items — High Visibility Icon + Text */
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #a0a0a0 !important;
        padding: 8px 12px !important;
        margin-bottom: 4px !important;
        border-radius: 4px !important;
        border-left: 3px solid transparent !important;
        transition: none !important;
        display: flex !important;
        align-items: center !important;
    }

    section[data-testid="stSidebar"] .stRadio label:hover {
        background-color: #141414 !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] .stRadio [data-checked="true"] + div label,
    section[data-testid="stSidebar"] .stRadio div[aria-checked="true"] label {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border-left: 3px solid #ffffff !important;
    }

    /* Main Container Spacing */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1350px !important;
    }

    /* Header Block */
    .top-header {
        margin-top: 0.2rem;
        margin-bottom: 1.6rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .top-header h1 {
        font-size: 22px !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: #ffffff !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .top-header p {
        font-size: 13px !important;
        color: #a0a0a0 !important;
        margin: 0.25rem 0 0 0 !important;
        letter-spacing: 0.02em !important;
    }

    /* Stat Cards Row */
    .stat-card-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 16px;
        margin-bottom: 1.8rem;
    }
    .stat-card {
        background-color: #0a0a0a;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 20px 16px;
        text-align: center;
    }
    .stat-card .num {
        font-size: 32px;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.1;
        margin-bottom: 6px;
    }
    .stat-card .label {
        font-size: 11px;
        font-weight: 600;
        color: #a0a0a0;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Section Headings */
    .section-title {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #ffffff;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Table Styles */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background-color: #0a0a0a;
        border-radius: 8px;
        overflow: hidden;
    }
    .custom-table th {
        background-color: #141414;
        color: #a0a0a0;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 12px 14px;
        text-align: left;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .custom-table td {
        padding: 12px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        color: #ffffff;
        font-size: 13px;
        vertical-align: middle;
    }
    .custom-table tr:hover td {
        background-color: #141414;
    }
    .truncated-text {
        max-width: 380px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #a0a0a0;
    }

    /* Detail Drawer / Inspection Panel */
    .detail-panel {
        background-color: #0f0f0f;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        padding: 20px;
        margin-top: 0.5rem;
    }
    .detail-panel h4 {
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #ffffff;
        margin: 0 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .detail-field {
        margin-bottom: 10px;
        font-size: 13px;
    }
    .detail-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #a0a0a0;
        margin-bottom: 2px;
    }
    .detail-value {
        color: #ffffff;
        font-weight: 500;
    }
    .hash-code {
        font-family: monospace;
        font-size: 11px;
        background-color: #141414;
        padding: 4px 8px;
        border-radius: 4px;
        border: 1px solid rgba(255,255,255,0.08);
        color: #a0a0a0;
        word-break: break-all;
    }

    /* Indicators */
    .dot-white {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #ffffff;
        margin-right: 6px;
    }
    .dot-gray {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #6b6b6b;
        margin-right: 6px;
    }

    /* Buttons Override */
    div.stButton > button, div.stDownloadButton > button {
        background-color: #0a0a0a !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        transition: none !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #1a1a1a !important;
        border-color: #ffffff !important;
        color: #ffffff !important;
    }

    /* Primary Action Buttons */
    div[data-testid="stButton"] button[kind="primary"],
    .primary-btn button {
        background-color: #ffffff !important;
        color: #0a0a0a !important;
        font-weight: 700 !important;
        border: 1px solid #ffffff !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #e0e0e0 !important;
        color: #000000 !important;
    }

    /* Inputs, Selectboxes, and Expanders */
    div[data-baseweb="select"] > div,
    div[data-testid="stFileUploader"] section {
        background-color: #0f0f0f !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 6px !important;
        color: #ffffff !important;
    }
    div[data-testid="stExpander"] {
        background-color: #0a0a0a !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 6px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stExpander"] summary {
        color: #ffffff !important;
        font-size: 13px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ── Persistent Top Header ─────────────────────────────────────────────────────
st.markdown(
    """
<div class="top-header">
    <h1>JARVIS</h1>
    <p>Joint Autonomous Reasoning &amp; Vision Inspection System — Industrial Operations</p>
</div>
""",
    unsafe_allow_html=True,
)


# ── Navigation Sidebar ────────────────────────────────────────────────────────
page = st.sidebar.radio(
    "NAVIGATION",
    [
        "📊  Dashboard",
        "📤  Upload & Detect",
        "⚙️  Conveyor Control",
        "🌐  Digital Twin",
        "📈  Violation Trends",
        "📋  Shift Handover",
        "✅  Approval Queue",
        "📜  Event Log",
    ],
    index=0,
    label_visibility="collapsed",
)


# ── Helper Formatting Functions ───────────────────────────────────────────────
def format_severity(sev: str) -> str:
    s = (sev or "low").lower()
    if s in ("critical", "high"):
        return f'<span class="dot-white"></span><strong>{s.upper()}</strong>'
    return f'<span class="dot-gray"></span><span style="color:#a0a0a0;">{s.upper()}</span>'


def format_status(status: str) -> str:
    st_val = (status or "pending").lower()
    if st_val == "approved":
        return '<strong>[ APPROVED ]</strong>'
    elif st_val == "denied":
        return '<span style="color:#6b6b6b;">[ DENIED ]</span>'
    return '<span style="color:#a0a0a0;">[ PENDING ]</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊  Dashboard":
    stats = get_event_stats()

    # 5 Equal Stat Cards
    st.markdown(
        f"""
    <div class="stat-card-row">
        <div class="stat-card">
            <div class="num">{stats['total_events']}</div>
            <div class="label">Total Events</div>
        </div>
        <div class="stat-card">
            <div class="num">{stats['pending']}</div>
            <div class="label">Pending Review</div>
        </div>
        <div class="stat-card">
            <div class="num">{stats['approved']}</div>
            <div class="label">Approved</div>
        </div>
        <div class="stat-card">
            <div class="num">{stats['denied']}</div>
            <div class="label">Denied</div>
        </div>
        <div class="stat-card">
            <div class="num">{stats['high_severity']}</div>
            <div class="label">High / Critical</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    events = get_all_events()

    if not events:
        st.markdown(
            """
        <div class="stat-card" style="text-align: left; padding: 24px;">
            <p style="color:#a0a0a0; margin:0; font-size:13px;">No events recorded in database yet. Navigate to <strong>Upload &amp; Detect</strong> or <strong>Conveyor Control</strong> to generate telemetry events.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        col_table, col_detail = st.columns([1.5, 1])

        with col_table:
            st.markdown(
                '<div class="section-title"><span>Live Incident Feed</span><span style="font-weight:400;color:#a0a0a0;">Real-time Telemetry</span></div>',
                unsafe_allow_html=True,
            )

            table_rows_html = ""
            for e in events[:15]:
                sev_html = format_severity(e["severity"])
                st_html = format_status(e["approval_status"])
                action_text = e["proposed_action"] or "—"
                truncated = (
                    (action_text[:50] + "...")
                    if len(action_text) > 50
                    else action_text
                )
                source_display = e["source_file"] or "—"
                if len(source_display) > 18:
                    source_display = source_display[:15] + "..."

                table_rows_html += f"""
                <tr>
                    <td style="font-family:monospace;font-size:12px;">#{e['event_id']:03d}</td>
                    <td style="color:#a0a0a0;font-size:12px;">{e['timestamp']}</td>
                    <td><strong>{e['event_type'].upper()}</strong></td>
                    <td style="color:#a0a0a0;font-size:12px;">{source_display}</td>
                    <td>{sev_html}</td>
                    <td>{st_html}</td>
                    <td><div class="truncated-text" title="{action_text}">{truncated}</div></td>
                </tr>
                """

            st.markdown(
                f"""
            <table class="custom-table">
                <thead>
                    <tr>
                        <th style="width:50px;">ID</th>
                        <th style="width:130px;">Timestamp</th>
                        <th style="width:90px;">Type</th>
                        <th style="width:120px;">Source</th>
                        <th style="width:110px;">Severity</th>
                        <th style="width:110px;">Status</th>
                        <th>Proposed Action</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
            """,
                unsafe_allow_html=True,
            )

        with col_detail:
            st.markdown(
                '<div class="section-title"><span>Event Inspection Panel</span><span style="font-weight:400;color:#a0a0a0;">Deep Audit</span></div>',
                unsafe_allow_html=True,
            )

            event_options = {
                f"Event #{e['event_id']} — {e['event_type'].upper()} ({e['timestamp']})": e[
                    "event_id"
                ]
                for e in events
            }
            selected_label = st.selectbox(
                "Select event to inspect",
                list(event_options.keys()),
                label_visibility="collapsed",
            )
            selected_id = event_options[selected_label]
            target_event = next(
                (e for e in events if e["event_id"] == selected_id), None
            )

            if target_event:
                sev_html = format_severity(target_event["severity"])
                status_str = target_event["approval_status"].upper()

                st.markdown(
                    f"""
                <div class="detail-panel">
                    <h4>Event Details — #{target_event['event_id']:03d}</h4>
                    
                    <div class="detail-field">
                        <div class="detail-label">Incident Type &amp; Source</div>
                        <div class="detail-value">{target_event['event_type'].upper()} &nbsp;|&nbsp; {target_event['source_file'] or 'System Stream'}</div>
                    </div>
                    
                    <div class="detail-field">
                        <div class="detail-label">Severity &amp; Category</div>
                        <div class="detail-value">{sev_html} &nbsp;|&nbsp; Category: {target_event['category'].upper()}</div>
                    </div>
                    
                    <div class="detail-field">
                        <div class="detail-label">Approval State</div>
                        <div class="detail-value">{status_str} {('by ' + target_event['approved_by']) if target_event.get('approved_by') else ''}</div>
                    </div>
                    
                    <div class="detail-field">
                        <div class="detail-label">Proposed Action</div>
                        <div class="detail-value" style="font-size:12px; line-height:1.5; color:#e0e0e0;">{target_event['proposed_action']}</div>
                    </div>
                    
                    <div class="detail-field" style="margin-top:12px;">
                        <div class="detail-label">Cryptographic Hash Verification (SHA-256)</div>
                        <div style="margin-top:4px;">
                            <span style="font-size:10px;color:#888;">RECORD_HASH:</span><br>
                            <div class="hash-code">{(target_event.get('record_hash') or 'GENESIS')}</div>
                            <span style="font-size:10px;color:#888;margin-top:4px;display:inline-block;">PREV_HASH:</span><br>
                            <div class="hash-code">{(target_event.get('prev_hash') or 'GENESIS')}</div>
                        </div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if target_event["approval_status"] == "pending":
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_app, col_den = st.columns(2)
                    with col_app:
                        if st.button(
                            "Approve Action",
                            key=f"dash_app_{target_event['event_id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            update_approval(
                                target_event["event_id"], "approved", "Manager"
                            )
                            st.rerun()
                    with col_den:
                        if st.button(
                            "Deny Action",
                            key=f"dash_den_{target_event['event_id']}",
                            use_container_width=True,
                        ):
                            update_approval(
                                target_event["event_id"], "denied", "Manager"
                            )
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2: UPLOAD & DETECT (IMAGE + VIDEO SUPPORT)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📤  Upload & Detect":
    st.markdown(
        '<div class="section-title"><span>Computer Vision Inference Module</span><span style="font-weight:400;color:#a0a0a0;">YOLO Perception Layer</span></div>',
        unsafe_allow_html=True,
    )

    col_ctrl, col_up = st.columns([1, 2.5])
    with col_ctrl:
        st.markdown(
            '<div class="detail-label">Select Inspection Pipeline</div>',
            unsafe_allow_html=True,
        )
        detection_mode = st.radio(
            "Detection Mode",
            ["PPE Compliance Inspection", "Fire & Smoke Hazard Detection"],
            label_visibility="collapsed",
        )
        st.caption(
            "Supports image files (.jpg, .png) and video files (.mp4, .avi) evaluated frame-by-frame on genuine YOLO models."
        )

    with col_up:
        st.markdown(
            '<div class="detail-label">Upload Inspection Asset (Image or Video)</div>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Choose Asset File",
            type=["jpg", "jpeg", "png", "mp4", "avi", "mov"],
            label_visibility="collapsed",
        )

    if uploaded_file is not None:
        suffix = Path(uploaded_file.name).suffix.lower()
        is_video = suffix in [".mp4", ".avi", ".mov"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        if not is_video:
            # ── Single Image Inference ──
            with st.spinner("Executing YOLO inference and Agentic reasoning..."):
                if "PPE" in detection_mode:
                    result = run_ppe_pipeline(tmp_path)
                else:
                    result = run_fire_pipeline(tmp_path)

            col_img, col_out = st.columns([1.2, 1])

            with col_img:
                st.markdown(
                    '<div class="section-title">Annotated Inspection Output</div>',
                    unsafe_allow_html=True,
                )
                annotated_rgb = cv2.cvtColor(
                    result["annotated_image"], cv2.COLOR_BGR2RGB
                )
                st.image(annotated_rgb, use_container_width=True)

            with col_out:
                cls = result["classification"]
                sev = cls["severity"]

                st.markdown(
                    f"""
                <div class="detail-panel">
                    <h4>Agent Decision Output — #{result['event_id']:03d}</h4>
                    
                    <div class="detail-field">
                        <div class="detail-label">Assessed Severity</div>
                        <div class="detail-value">{format_severity(sev)}</div>
                    </div>
                    
                    <div class="detail-field">
                        <div class="detail-label">Classification Category</div>
                        <div class="detail-value">{cls['category'].upper()}</div>
                    </div>
                    
                    <div class="detail-field">
                        <div class="detail-label">Proposed Action</div>
                        <div class="detail-value" style="font-size:12px; line-height:1.5;">{cls['proposed_action']}</div>
                    </div>
                    
                    <div class="detail-field">
                        <div class="detail-label">Reasoning Chain</div>
                        <div class="detail-value" style="font-size:12px; color:#a0a0a0; line-height:1.4;">{cls['reasoning']}</div>
                    </div>
                    
                    <div class="detail-field" style="margin-top:12px;">
                        <div class="detail-label">Detection Counts</div>
                        <div class="detail-value" style="font-size:12px;">
                """,
                    unsafe_allow_html=True,
                )

                if result.get("summary"):
                    for label, count in result["summary"].items():
                        st.markdown(
                            f"<span style='color:#ffffff;'>• {label}:</span> {count}",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<span style='color:#a0a0a0;'>No objects matched confidence threshold.</span>",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    "</div></div></div>",
                    unsafe_allow_html=True,
                )

            st.success(
                f"Event #{result['event_id']:03d} recorded in hash-chained audit log. Status: Awaiting Supervisor Approval."
            )

        else:
            # ── Video Sequence Inference ──
            with st.spinner("Processing video sequence frame-by-frame..."):
                if "PPE" in detection_mode:
                    detector = _get_ppe_detector()
                    v_res = detector.detect_video(tmp_path)
                else:
                    detector = _get_fire_detector()
                    v_res = detector.detect_video(tmp_path)

            st.markdown(
                f"""
            <div class="stat-card-row" style="margin-top:1rem;">
                <div class="stat-card">
                    <div class="num">{v_res['frames_processed']}</div>
                    <div class="label">Frames Processed</div>
                </div>
                <div class="stat-card">
                    <div class="num">{v_res['total_detections']}</div>
                    <div class="label">Total Detections</div>
                </div>
                <div class="stat-card">
                    <div class="num">{v_res.get('total_violations', v_res.get('fire_frames', 0))}</div>
                    <div class="label">Incident Frames</div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="section-title">Aggregated Detections Across Video Sequence</div>',
                unsafe_allow_html=True,
            )
            for k, v in v_res["aggregated_summary"].items():
                st.markdown(f"• **{k}**: {v} detections across frames")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3: CONVEYOR CONTROL (SIMULATION LAYER)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️  Conveyor Control":
    st.markdown(
        '<div class="section-title"><span>Conveyor Telemetry &amp; Fault Simulator</span><span style="font-weight:400;color:#a0a0a0;">Phase 2 Simulation Layer</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Software state machine representing industrial equipment status per Project Proposal Section 4. Distinguishes commanded actions from unplanned faults."
    )

    c_status = get_conveyor_status()
    curr_status = c_status["status"].upper()

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="num">LINE {c_status['line_id']:02d}</div>
            <div class="label">Unit Identifier</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col_c2:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="num">{curr_status}</div>
            <div class="label">Operating State</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col_c3:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="num" style="font-size:20px; padding-top:6px;">{c_status.get('last_change_reason', '—')[:18]}</div>
            <div class="label">Last State Transition</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(
            '<div class="section-title">Commanded Operator Controls</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "User-commanded actions are expected operational state transitions and do not trigger incident alerts."
        )

        c_b1, c_b2 = st.columns(2)
        with c_b1:
            if st.button(
                "Command: Run Line", use_container_width=True, type="primary"
            ):
                run_conveyor()
                st.success("Conveyor Line 1 commanded to RUN.")
                st.rerun()
        with c_b2:
            if st.button("Command: Manual Stop", use_container_width=True):
                stop_conveyor()
                st.info(
                    "Conveyor Line 1 commanded to STOP (Commanded — no fault logged)."
                )
                st.rerun()

    with col_right:
        st.markdown(
            '<div class="section-title">Fault Injection (Unplanned Failure)</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Unplanned halts simulate mechanical, electrical, or sensor faults requiring AI classification and manager sign-off."
        )

        fault_type = st.selectbox(
            "Select Fault Pattern",
            [
                "mechanical_jam",
                "motor_thermal_overload",
                "sensor_misalignment",
                "roller_bearing_failure",
            ],
        )

        if st.button(
            f"Inject Fault: {fault_type.upper()}", use_container_width=True
        ):
            res = run_conveyor_fault_pipeline(fault_type)
            st.warning(
                f"Unplanned fault '{fault_type}' injected! Telemetry logged as Event #{res['event_id']:03d}."
            )
            st.caption(
                "Reasoning agent classified severity as HIGH (Mechanical). Action proposal queued in Approval Queue."
            )
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 4: DIGITAL TWIN STATUS BOARD (FR-16)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌐  Digital Twin":
    st.markdown(
        '<div class="section-title"><span>Digital Twin Status Board</span><span style="font-weight:400;color:#a0a0a0;">Plant Floor Virtual Layout</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "At-a-glance status topology of all manufacturing zones and production units per SRS FR-16."
    )

    c_status = get_conveyor_status()
    l1_status = c_status["status"].upper()

    col_z1, col_z2, col_z3 = st.columns(3)

    with col_z1:
        st.markdown(
            f"""
        <div class="detail-panel" style="text-align:center; padding:28px 16px;">
            <div style="font-size:11px; text-transform:uppercase; color:#a0a0a0; letter-spacing:0.08em;">ZONE 01 — ASSEMBLY</div>
            <div style="font-size:24px; font-weight:700; color:#ffffff; margin:10px 0;">CONVEYOR LINE 1</div>
            <div style="margin-bottom:12px;">{format_status(l1_status)}</div>
            <div style="font-size:11px; color:#a0a0a0;">Telemetry: {c_status.get('last_change_reason','—')}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col_z2:
        st.markdown(
            """
        <div class="detail-panel" style="text-align:center; padding:28px 16px;">
            <div style="font-size:11px; text-transform:uppercase; color:#a0a0a0; letter-spacing:0.08em;">ZONE 02 — QUALITY CHECK</div>
            <div style="font-size:24px; font-weight:700; color:#ffffff; margin:10px 0;">PPE INSPECTION STATION</div>
            <div style="margin-bottom:12px;"><strong>[ ACTIVE ]</strong></div>
            <div style="font-size:11px; color:#a0a0a0;">Camera 01: Optical Flow Normal</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col_z3:
        st.markdown(
            """
        <div class="detail-panel" style="text-align:center; padding:28px 16px;">
            <div style="font-size:11px; text-transform:uppercase; color:#a0a0a0; letter-spacing:0.08em;">ZONE 03 — SAFETY PERIMETER</div>
            <div style="font-size:24px; font-weight:700; color:#ffffff; margin:10px 0;">FIRE &amp; SMOKE HAZARD MONITOR</div>
            <div style="margin-bottom:12px;"><strong>[ STANDBY ]</strong></div>
            <div style="font-size:11px; color:#a0a0a0;">Thermal/Visual Sensors Online</div>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 5: VIOLATION TREND ANALYTICS (FR-17)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈  Violation Trends":
    st.markdown(
        '<div class="section-title"><span>Violation Trend Analytics</span><span style="font-weight:400;color:#a0a0a0;">Pattern Detection &amp; Risk Insights</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Historical aggregation of safety violations, mechanical faults, and approval metrics per SRS FR-17."
    )

    df = get_events_dataframe()

    if df.empty:
        st.markdown(
            """
        <div class="stat-card" style="text-align: left; padding: 24px;">
            <p style="color:#a0a0a0; margin:0; font-size:13px;">No event telemetry recorded yet to compute analytics.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown(
                '<div class="detail-label" style="margin-bottom:8px;">Incidents by Category &amp; Domain</div>',
                unsafe_allow_html=True,
            )
            type_counts = df["event_type"].value_counts()
            st.bar_chart(type_counts, height=220)

        with col_t2:
            st.markdown(
                '<div class="detail-label" style="margin-bottom:8px;">Incidents by Severity Level</div>',
                unsafe_allow_html=True,
            )
            sev_counts = df["severity"].value_counts()
            st.bar_chart(sev_counts, height=220)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 6: SHIFT HANDOVER REPORT (FR-15)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋  Shift Handover":
    st.markdown(
        '<div class="section-title"><span>Automated Shift Handover Report</span><span style="font-weight:400;color:#a0a0a0;">LLM Reasoning &amp; Summarization</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Autonomous generation of plain-English shift handover summaries for oncoming plant supervisors per SRS FR-15 & Section 6.3."
    )

    col_h1, col_h2 = st.columns([1.5, 1])

    with col_h1:
        time_preset = st.selectbox(
            "Shift Time Window Preset",
            ["All Recorded Incidents (Full Log)", "Last 8 Hours (Current Shift)", "Today (24 Hours)"],
        )

    start_iso = None
    end_iso = None
    window_label = time_preset

    if "8 Hours" in time_preset:
        start_iso = (datetime.now() - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        end_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif "Today" in time_preset:
        start_iso = datetime.now().strftime("%Y-%m-%d 00:00:00")
        end_iso = datetime.now().strftime("%Y-%m-%d 23:59:59")

    with col_h2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        generate_btn = st.button("Generate Handover Report", type="primary", use_container_width=True)

    if generate_btn:
        with st.spinner("Analyzing incident telemetry and formulating handover brief..."):
            report_res = generate_shift_report(start_iso, end_iso, window_label)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"""
        <div class="detail-panel" style="padding:24px; line-height:1.7;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
                <span class="detail-label">REASONING ENGINE: {report_res['provider']}</span>
                <span style="font-size:11px; color:#a0a0a0;">EVENTS ANALYZED: {report_res['event_count']} &nbsp;|&nbsp; GENERATED: {report_res['generated_at']}</span>
            </div>
            <div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(report_res["summary"])

        st.markdown("</div></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 7: APPROVAL QUEUE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✅  Approval Queue":
    st.markdown(
        '<div class="section-title"><span>Human-in-the-Loop Approval Queue</span><span style="font-weight:400;color:#a0a0a0;">Supervisor / Manager Gate</span></div>',
        unsafe_allow_html=True,
    )

    pending = get_pending_events()

    if not pending:
        st.markdown(
            """
        <div class="stat-card" style="text-align: left; padding: 24px;">
            <p style="color:#a0a0a0; margin:0; font-size:13px;">✓ All detected incidents have been reviewed. No pending action proposals requiring authorization.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            f"{len(pending)} pending action proposal(s) awaiting explicit human authorization."
        )

        for event in pending:
            sev_html = format_severity(event["severity"])

            with st.container():
                st.markdown(
                    f"""
                <div class="detail-panel" style="margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <strong>EVENT #{event['event_id']:03d} &nbsp;|&nbsp; {event['event_type'].upper()}</strong>
                        <div>{sev_html} &nbsp;|&nbsp; <span style="color:#a0a0a0;font-size:11px;">{event['timestamp']}</span></div>
                    </div>
                    <div style="font-size:11px; color:#a0a0a0; margin-bottom:6px;">SOURCE: {event['source_file'] or 'System Stream'}</div>
                    <div style="font-size:13px; color:#ffffff; padding:8px 0; border-top:1px solid rgba(255,255,255,0.06); border-bottom:1px solid rgba(255,255,255,0.06); margin-bottom:10px;">
                        <strong>Proposed Action:</strong> {event['proposed_action']}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                col_ap, col_dn, col_fill = st.columns([1, 1, 4])
                with col_ap:
                    if st.button(
                        "Approve",
                        key=f"q_app_{event['event_id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        update_approval(
                            event["event_id"], "approved", "Manager"
                        )
                        st.rerun()
                with col_dn:
                    if st.button(
                        "Deny",
                        key=f"q_den_{event['event_id']}",
                        use_container_width=True,
                    ):
                        update_approval(event["event_id"], "denied", "Manager")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 8: EVENT LOG (HASH-CHAINED AUDIT TRAIL + CSV EXPORT)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📜  Event Log":
    st.markdown(
        '<div class="section-title"><span>Tamper-Evident Audit Trail</span><span style="font-weight:400;color:#a0a0a0;">SHA-256 Hash Chain &amp; Export</span></div>',
        unsafe_allow_html=True,
    )

    events = get_all_events()

    if not events:
        st.markdown(
            """
        <div class="stat-card" style="text-align: left; padding: 24px;">
            <p style="color:#a0a0a0; margin:0; font-size:13px;">No events recorded in audit log.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        col_f1, col_f2, col_exp = st.columns([1.5, 1.5, 1.2])
        with col_f1:
            type_filter = st.selectbox(
                "Filter by Event Type", ["All", "PPE", "Fire", "Conveyor"]
            )
        with col_f2:
            status_filter = st.selectbox(
                "Filter by Approval Status",
                ["All", "Pending", "Approved", "Denied"],
            )
        with col_exp:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            csv_data = export_events_to_csv(events)
            st.download_button(
                label="📥 Export CSV",
                data=csv_data,
                file_name=f"jarvis_audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        filtered = events
        if type_filter != "All":
            filtered = [
                e for e in filtered if e["event_type"] == type_filter.lower()
            ]
        if status_filter != "All":
            filtered = [
                e
                for e in filtered
                if e["approval_status"] == status_filter.lower()
            ]

        st.caption(f"Showing {len(filtered)} of {len(events)} logged records.")

        for event in filtered:
            sev_html = format_severity(event["severity"])
            st_html = format_status(event["approval_status"])

            with st.expander(
                f"#{event['event_id']:03d}  |  {event['event_type'].upper():<8}  |  {event['severity'].upper():<8}  |  {event['approval_status'].upper():<8}  |  {event['timestamp']}"
            ):
                st.markdown(
                    f"""
                <div style="font-size:13px; line-height:1.6;">
                    <strong>Source:</strong> {event['source_file'] or '—'}<br>
                    <strong>Category:</strong> {event['category'].upper()}<br>
                    <strong>Severity:</strong> {sev_html}<br>
                    <strong>Approval Status:</strong> {st_html}<br>
                    <strong>Proposed Action:</strong> {event['proposed_action']}<br>
                    {('<strong>Reviewed By:</strong> ' + event['approved_by'] + ' at ' + str(event.get('resolved_at', '—'))) if event.get('approved_by') else ''}
                </div>
                
                <div style="margin-top:12px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.08);">
                    <div class="detail-label">SHA-256 Chain Hashes</div>
                    <span style="font-size:10px;color:#888;">RECORD_HASH:</span>
                    <div class="hash-code">{event.get('record_hash') or 'GENESIS'}</div>
                    <span style="font-size:10px;color:#888;margin-top:4px;display:inline-block;">PREV_HASH:</span>
                    <div class="hash-code">{event.get('prev_hash') or 'GENESIS'}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if event.get("detections_json"):
                    try:
                        dets = json.loads(event["detections_json"])
                        if dets:
                            st.markdown(
                                "<div class='detail-label' style='margin-top:10px;'>Detections Payload</div>",
                                unsafe_allow_html=True,
                            )
                            for i, d in enumerate(dets, 1):
                                st.text(
                                    f"  #{i:02d}  {d.get('label', '-'):<15} conf={d.get('confidence', 1.0):.3f}  bbox={d.get('bbox', '-')}"
                                )
                    except Exception:
                        pass

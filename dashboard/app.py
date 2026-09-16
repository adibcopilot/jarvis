"""
dashboard/app.py
JARVIS Dashboard — Industrial Design System
Dark Graphite / Frosted Slate / Operational Signal Colors

Run with:
    streamlit run dashboard/app.py --server.port 8501
"""

import sys
import os
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
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM — Industrial Graphite / Frosted Slate / Operational Signals
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Design Tokens ────────────────────────────────────────── */
    :root {
        --graphite:     #171817;
        --charcoal:     #20211F;
        --slate:        #292A27;
        --smoke:        #343531;
        --stone:        #454640;
        --mist:         #B9BBB3;
        --paper:        #E8E9E2;
        --soft-white:   #F3F3EE;
        --signal-green: #6F8F73;
        --signal-amber: #B18A52;
        --signal-red:   #B85C58;
        --signal-grey:  #777A73;
    }

    /* ── Global Base ──────────────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: var(--graphite) !important;
        color: var(--paper) !important;
    }

    /* ── Streamlit Chrome ─────────────────────────────────────── */
    header[data-testid="stHeader"] {
        background-color: var(--graphite) !important;
        border-bottom: 1px solid rgba(69, 70, 64, 0.5) !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: var(--graphite) !important;
    }

    /* ── Completely Hide Sidebar & Collapse Control ──────────── */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    div[data-testid="stSidebarCollapsedControl"],
    button[aria-label*="sidebar"],
    button[aria-label*="Sidebar"] {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* ── Main Container ───────────────────────────────────────── */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1440px !important;
    }

    /* ── Top Header Navigation Bar ────────────────────────────── */
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) {
        background-color: var(--charcoal) !important;
        border: 1px solid rgba(69, 70, 64, 0.45) !important;
        border-radius: 8px !important;
        padding: 5px 8px !important;
        margin-top: -6px !important;
        margin-bottom: 24px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }

    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) > label {
        display: none !important;
    }

    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        gap: 3px !important;
    }

    /* Hide Streamlit default radio circle dot */
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }

    /* Top Nav Tab Buttons */
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.12s ease !important;
        display: inline-flex !important;
        align-items: center !important;
    }

    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label p,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label span,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        color: var(--mist) !important;
        letter-spacing: 0.02em !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
    }

    /* Hover State */
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:hover {
        background-color: var(--slate) !important;
        border-color: rgba(69, 70, 64, 0.4) !important;
    }

    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:hover p,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:hover span {
        color: var(--paper) !important;
    }

    /* Active / Checked State */
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:has(input:checked),
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:has([aria-checked="true"]),
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label[data-checked="true"] {
        background-color: var(--slate) !important;
        border: 1px solid rgba(69, 70, 64, 0.6) !important;
        border-bottom: 2px solid var(--signal-green) !important;
    }

    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:has(input:checked) p,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label:has(input:checked) span,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] label[data-checked="true"] p {
        color: var(--soft-white) !important;
        font-weight: 600 !important;
    }

    /* Category Group Dividers: after 3rd (Pending Actions), 6th (Risk Trends), 9th (Shift Handover) */
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] > label:nth-child(3),
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] > label:nth-child(6),
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] > label:nth-child(9) {
        margin-right: 14px !important;
        position: relative !important;
    }

    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] > label:nth-child(3)::after,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] > label:nth-child(6)::after,
    div[data-testid="stRadio"]:has(input[aria-label="Floor View"]) div[role="radiogroup"] > label:nth-child(9)::after {
        content: "" !important;
        position: absolute !important;
        right: -8px !important;
        top: 20% !important;
        height: 60% !important;
        width: 1px !important;
        background-color: rgba(69, 70, 64, 0.6) !important;
    }

    /* ── Top Header Bar ───────────────────────────────────────── */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 0 12px 0;
        margin-bottom: 20px;
        border-bottom: 1px solid rgba(69, 70, 64, 0.5);
    }
    .top-bar .brand {
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--soft-white);
    }
    .top-bar .status {
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.06em;
        color: var(--mist);
        text-transform: uppercase;
    }
    .top-bar .status .dot-live {
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--signal-green);
        margin-right: 5px;
    }

    /* ── Page Title ────────────────────────────────────────────── */
    .page-title {
        margin-bottom: 6px;
    }
    .page-title h2 {
        font-size: 20px !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: var(--soft-white) !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .page-subtitle {
        font-size: 13px;
        color: var(--mist);
        margin: 0 0 20px 0;
    }

    /* ── Glass Surface (Cards & Panels) ───────────────────────── */
    .glass-surface {
        background-color: rgba(41, 42, 39, 0.85);
        border: 1px solid rgba(69, 70, 64, 0.4);
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
        padding: 24px;
        margin-bottom: 16px;
    }

    .glass-surface-raised {
        background-color: rgba(52, 53, 49, 0.9);
        border: 1px solid rgba(69, 70, 64, 0.3);
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
        padding: 20px;
        margin-bottom: 12px;
    }

    /* ── Stat Cards ────────────────────────────────────────────── */
    .stat-card-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 14px;
        margin-bottom: 24px;
    }
    .stat-card {
        background-color: var(--slate);
        border: 1px solid rgba(69, 70, 64, 0.4);
        border-radius: 8px;
        padding: 20px 16px;
        text-align: center;
    }
    .stat-card .num {
        font-size: 30px;
        font-weight: 700;
        color: var(--soft-white);
        line-height: 1.1;
        margin-bottom: 6px;
    }
    .stat-card .label {
        font-size: 10px;
        font-weight: 600;
        color: var(--mist);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Section Title ─────────────────────────────────────────── */
    .section-title {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--mist);
        margin-top: 20px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(69, 70, 64, 0.4);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .section-title span:first-child {
        color: var(--paper);
    }

    /* ── Machine Panel ─────────────────────────────────────────── */
    .machine-panel {
        background-color: var(--slate);
        border: 1px solid rgba(69, 70, 64, 0.5);
        border-radius: 12px;
        padding: 40px 36px;
        text-align: center;
        margin-bottom: 24px;
    }
    .machine-name {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--mist);
        margin-bottom: 24px;
    }
    .machine-state {
        font-size: 28px;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .machine-state-desc {
        font-size: 13px;
        font-weight: 500;
        color: var(--mist);
        letter-spacing: 0.04em;
        margin-bottom: 28px;
    }
    .machine-meta {
        display: flex;
        justify-content: center;
        gap: 40px;
        margin-bottom: 32px;
        font-size: 11px;
        color: var(--mist);
    }
    .machine-meta .meta-item {
        text-align: center;
    }
    .machine-meta .meta-label {
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-size: 10px;
        color: var(--stone);
        margin-bottom: 4px;
    }
    .machine-meta .meta-value {
        color: var(--paper);
        font-weight: 500;
    }

    /* ── Simulation Banner ─────────────────────────────────────── */
    .sim-banner {
        background-color: var(--slate);
        border: 1px solid rgba(69, 70, 64, 0.4);
        border-radius: 8px;
        padding: 12px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .sim-banner .sim-title {
        color: var(--paper);
        font-weight: 600;
    }
    .sim-banner .sim-detail {
        color: var(--mist);
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .sim-banner .sim-dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--signal-grey);
        margin-right: 5px;
    }

    /* ── Control Buttons (Neutral) ─────────────────────────────── */
    .control-grid {
        display: flex;
        gap: 12px;
        justify-content: center;
        flex-wrap: wrap;
    }

    /* ── Event Surface ─────────────────────────────────────────── */
    .event-surface {
        background-color: var(--slate);
        border: 1px solid rgba(69, 70, 64, 0.4);
        border-radius: 8px;
        padding: 16px 20px;
    }
    .event-surface .event-label {
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--stone);
        margin-bottom: 8px;
    }
    .event-surface .event-text {
        font-size: 14px;
        font-weight: 500;
        color: var(--paper);
        margin-bottom: 4px;
    }
    .event-surface .event-meta {
        font-size: 11px;
        color: var(--mist);
    }

    /* ── Table Styles ──────────────────────────────────────────── */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        border: 1px solid rgba(69, 70, 64, 0.4);
        background-color: var(--slate);
        border-radius: 8px;
        overflow: hidden;
    }
    .custom-table th {
        background-color: var(--smoke);
        color: var(--mist);
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 12px 14px;
        text-align: left;
        border-bottom: 1px solid rgba(69, 70, 64, 0.5);
    }
    .custom-table td {
        padding: 12px 14px;
        border-bottom: 1px solid rgba(69, 70, 64, 0.25);
        color: var(--paper);
        font-size: 13px;
        vertical-align: middle;
    }
    .custom-table tr:hover td {
        background-color: var(--smoke);
    }
    .truncated-text {
        max-width: 350px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: var(--mist);
    }

    /* ── Detail Panel ──────────────────────────────────────────── */
    .detail-panel {
        background-color: var(--slate);
        border: 1px solid rgba(69, 70, 64, 0.4);
        border-radius: 10px;
        padding: 24px;
        margin-top: 8px;
    }
    .detail-panel h4 {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--soft-white);
        margin: 0 0 16px 0;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(69, 70, 64, 0.4);
    }
    .detail-field {
        margin-bottom: 12px;
        font-size: 13px;
    }
    .detail-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--stone);
        font-weight: 600;
        margin-bottom: 3px;
    }
    .detail-value {
        color: var(--paper);
        font-weight: 500;
    }
    .hash-code {
        font-family: 'Courier New', monospace;
        font-size: 11px;
        background-color: var(--smoke);
        padding: 4px 8px;
        border-radius: 4px;
        border: 1px solid rgba(69, 70, 64, 0.3);
        color: var(--mist);
        word-break: break-all;
    }

    /* ── Placeholder Page ──────────────────────────────────────── */
    .placeholder-panel {
        background-color: var(--slate);
        border: 1px solid rgba(69, 70, 64, 0.4);
        border-radius: 10px;
        padding: 48px 36px;
        text-align: center;
    }
    .placeholder-panel .ph-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--paper);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
    }
    .placeholder-panel .ph-desc {
        font-size: 13px;
        color: var(--mist);
    }

    /* ── Buttons Override ──────────────────────────────────────── */
    div.stButton > button, div.stDownloadButton > button {
        background-color: var(--smoke) !important;
        color: var(--paper) !important;
        border: 1px solid rgba(69, 70, 64, 0.5) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        transition: none !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: var(--stone) !important;
        border-color: var(--mist) !important;
        color: var(--soft-white) !important;
    }

    /* Primary Action */
    div[data-testid="stButton"] button[kind="primary"],
    .primary-btn button {
        background-color: var(--signal-green) !important;
        color: var(--graphite) !important;
        font-weight: 700 !important;
        border: 1px solid var(--signal-green) !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        opacity: 0.9 !important;
    }

    /* ── Inputs & Selects ─────────────────────────────────────── */
    div[data-baseweb="select"] > div,
    div[data-testid="stFileUploader"] section {
        background-color: var(--smoke) !important;
        border: 1px solid rgba(69, 70, 64, 0.5) !important;
        border-radius: 6px !important;
        color: var(--paper) !important;
    }
    div[data-testid="stExpander"] {
        background-color: var(--slate) !important;
        border: 1px solid rgba(69, 70, 64, 0.4) !important;
        border-radius: 8px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stExpander"] summary {
        color: var(--paper) !important;
        font-size: 13px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ── Top Header Bar & Telemetry ────────────────────────────────────────────────
st.markdown(
    """
<div class="top-bar">
    <div class="brand">
        <span style="font-weight:800; letter-spacing:0.18em; color:#F3F3EE;">JARVIS</span>
        <span style="font-size:10px; font-weight:600; color:#777A73; letter-spacing:0.12em; margin-left:10px;">INDUSTRIAL MONITOR // NODE-01</span>
    </div>
    <div class="status">
        <span><span class="dot-live"></span> SYSTEM READY</span>
        <span style="color:#454640;">|</span>
        <span>ROLE: MANAGER</span>
        <span style="color:#454640;">|</span>
        <span>SHIFT: ALPHA</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ── Top Header Navigation Bar ────────────────────────────────────────────────
NAV_OPTIONS = [
    "Floor View",
    "Upload & Inspect",
    "Pending Actions",
    "Reasoning Trail",
    "Ask JARVIS",
    "Risk Trends",
    "Worker Records",
    "Audit Reports",
    "Shift Handover",
    "Trigger Console",
    "Alert Setup",
    "Audit Verification",
]

page = st.radio(
    "NAV",
    NAV_OPTIONS,
    index=0,
    horizontal=True,
    label_visibility="collapsed",
    key="top_nav_selection",
)


# ── Helper Formatting Functions ───────────────────────────────────────────────
def format_severity(sev: str) -> str:
    s = (sev or "low").lower()
    if s in ("critical", "high"):
        return f'<span style="color:#B85C58;">● {s.upper()}</span>'
    elif s == "medium":
        return f'<span style="color:#B18A52;">● {s.upper()}</span>'
    return f'<span style="color:#777A73;">● {s.upper()}</span>'


def format_status(status: str) -> str:
    st_val = (status or "pending").lower()
    if st_val == "approved":
        return '<span style="color:#6F8F73;font-weight:600;">APPROVED</span>'
    elif st_val == "denied":
        return '<span style="color:#777A73;">DENIED</span>'
    return '<span style="color:#B18A52;">PENDING</span>'


def get_machine_state_html(status: str) -> tuple:
    """Returns (state_text, state_desc, state_color, state_symbol)."""
    s = status.lower()
    if s == "running":
        return ("RUNNING", "NORMAL OPERATION", "#6F8F73", "●")
    elif s == "stopped":
        return ("STOPPED", "MACHINE NOT RUNNING", "#B18A52", "■")
    elif s == "faulted":
        return ("FAULT", "ATTENTION REQUIRED", "#B85C58", "●")
    return ("UNKNOWN", "STATUS UNAVAILABLE", "#777A73", "●")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: FLOOR VIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "Floor View":
    st.markdown(
        '<div class="page-title"><h2>Floor View</h2></div>'
        '<p class="page-subtitle">Facility status overview and live incident feed.</p>',
        unsafe_allow_html=True,
    )

    stats = get_event_stats()

    # Stat Cards
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

    # Zone Status Cards (merged from Digital Twin)
    c_status = get_conveyor_status()
    state_text, state_desc, state_color, _ = get_machine_state_html(c_status["status"])

    st.markdown(
        '<div class="section-title"><span>Facility Zones</span><span style="font-weight:400;">Plant Floor Topology</span></div>',
        unsafe_allow_html=True,
    )

    col_z1, col_z2, col_z3 = st.columns(3)

    with col_z1:
        st.markdown(
            f"""
<div class="glass-surface" style="text-align:center; padding:28px 16px;">
    <div style="font-size:10px; text-transform:uppercase; color:#454640; letter-spacing:0.1em; font-weight:600;">Zone 01 — Assembly</div>
    <div style="font-size:20px; font-weight:700; color:#F3F3EE; margin:12px 0;">CONVEYOR LINE 1</div>
    <div style="margin-bottom:10px;"><span style="color:{state_color};font-weight:600;">● {state_text}</span></div>
    <div style="font-size:11px; color:#B9BBB3;">{c_status.get('last_change_reason','—')}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_z2:
        st.markdown(
            """
<div class="glass-surface" style="text-align:center; padding:28px 16px;">
    <div style="font-size:10px; text-transform:uppercase; color:#454640; letter-spacing:0.1em; font-weight:600;">Zone 02 — Quality Check</div>
    <div style="font-size:20px; font-weight:700; color:#F3F3EE; margin:12px 0;">PPE INSPECTION</div>
    <div style="margin-bottom:10px;"><span style="color:#6F8F73;font-weight:600;">● ACTIVE</span></div>
    <div style="font-size:11px; color:#B9BBB3;">Camera 01: Optical Flow Normal</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_z3:
        st.markdown(
            """
<div class="glass-surface" style="text-align:center; padding:28px 16px;">
    <div style="font-size:10px; text-transform:uppercase; color:#454640; letter-spacing:0.1em; font-weight:600;">Zone 03 — Safety Perimeter</div>
    <div style="font-size:20px; font-weight:700; color:#F3F3EE; margin:12px 0;">FIRE &amp; SMOKE MONITOR</div>
    <div style="margin-bottom:10px;"><span style="color:#6F8F73;font-weight:600;">● STANDBY</span></div>
    <div style="font-size:11px; color:#B9BBB3;">Thermal/Visual Sensors Online</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # Incident Feed
    events = get_all_events()

    if not events:
        st.markdown(
            """
<div class="glass-surface" style="padding:24px;">
    <p style="color:#B9BBB3; margin:0; font-size:13px;">No events recorded yet. Navigate to <strong>Trigger Console</strong> or <strong>Upload &amp; Inspect</strong> to generate events.</p>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="section-title"><span>Live Incident Feed</span><span style="font-weight:400;">Real-time Telemetry</span></div>',
            unsafe_allow_html=True,
        )

        table_rows_html = ""
        for e in events[:15]:
            sev_html = format_severity(e["severity"])
            st_html = format_status(e["approval_status"])
            action_text = e["proposed_action"] or "—"
            truncated = (action_text[:50] + "...") if len(action_text) > 50 else action_text
            source_display = e["source_file"] or "—"
            if len(source_display) > 18:
                source_display = source_display[:15] + "..."

            table_rows_html += f"""<tr>
<td style="font-family:monospace;font-size:12px;color:#B9BBB3;">#{e['event_id']:03d}</td>
<td style="color:#777A73;font-size:12px;">{e['timestamp']}</td>
<td><strong style="color:#E8E9E2;">{e['event_type'].upper()}</strong></td>
<td style="color:#777A73;font-size:12px;">{source_display}</td>
<td>{sev_html}</td>
<td>{st_html}</td>
<td><div class="truncated-text" title="{action_text}">{truncated}</div></td>
</tr>"""

        table_html = f"""<table class="custom-table">
<thead>
<tr>
<th style="width:50px;">ID</th>
<th style="width:130px;">Timestamp</th>
<th style="width:90px;">Type</th>
<th style="width:120px;">Source</th>
<th style="width:100px;">Severity</th>
<th style="width:90px;">Status</th>
<th>Proposed Action</th>
</tr>
</thead>
<tbody>
{table_rows_html}
</tbody>
</table>"""

        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Event Inspection Panel
        st.markdown(
            '<div class="section-title"><span>Event Inspection</span><span style="font-weight:400;">Deep Audit</span></div>',
            unsafe_allow_html=True,
        )

        event_options = {
            f"Event #{e['event_id']} — {e['event_type'].upper()} ({e['timestamp']})": e["event_id"]
            for e in events
        }
        selected_label = st.selectbox(
            "Select event to inspect",
            list(event_options.keys()),
            label_visibility="collapsed",
        )
        selected_id = event_options[selected_label]
        target_event = next((e for e in events if e["event_id"] == selected_id), None)

        if target_event:
            sev_html = format_severity(target_event["severity"])
            status_str = target_event["approval_status"].upper()

            detail_html = f"""<div class="detail-panel">
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
<div class="detail-value">{format_status(target_event['approval_status'])} {('— ' + target_event['approved_by']) if target_event.get('approved_by') else ''}</div>
</div>

<div class="detail-field">
<div class="detail-label">Proposed Action</div>
<div class="detail-value" style="font-size:12px; line-height:1.5; color:#E8E9E2;">{target_event['proposed_action']}</div>
</div>

<div class="detail-field" style="margin-top:14px;">
<div class="detail-label">SHA-256 Chain Verification</div>
<div style="margin-top:6px;">
<span style="font-size:10px;color:#454640;">RECORD_HASH:</span><br>
<div class="hash-code">{(target_event.get('record_hash') or 'GENESIS')}</div>
<span style="font-size:10px;color:#454640;margin-top:4px;display:inline-block;">PREV_HASH:</span><br>
<div class="hash-code">{(target_event.get('prev_hash') or 'GENESIS')}</div>
</div>
</div>
</div>"""

            st.markdown(detail_html, unsafe_allow_html=True)

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
                        update_approval(target_event["event_id"], "approved", "Manager")
                        st.rerun()
                with col_den:
                    if st.button(
                        "Deny Action",
                        key=f"dash_den_{target_event['event_id']}",
                        use_container_width=True,
                    ):
                        update_approval(target_event["event_id"], "denied", "Manager")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: UPLOAD & INSPECT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Upload & Inspect":
    st.markdown(
        '<div class="page-title"><h2>Upload &amp; Inspect</h2></div>'
        '<p class="page-subtitle">Computer vision inference module — YOLO perception layer.</p>',
        unsafe_allow_html=True,
    )

    col_ctrl, col_up = st.columns([1, 2.5])
    with col_ctrl:
        st.markdown('<div class="detail-label">Select Inspection Pipeline</div>', unsafe_allow_html=True)
        detection_mode = st.radio(
            "Detection Mode",
            ["PPE Compliance Inspection", "Fire & Smoke Hazard Detection"],
            label_visibility="collapsed",
        )
        st.caption("Supports image files (.jpg, .png) and video files (.mp4, .avi).")

    with col_up:
        st.markdown('<div class="detail-label">Upload Inspection Asset</div>', unsafe_allow_html=True)
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
            with st.spinner("Executing YOLO inference and agentic reasoning..."):
                if "PPE" in detection_mode:
                    result = run_ppe_pipeline(tmp_path)
                else:
                    result = run_fire_pipeline(tmp_path)

            col_img, col_out = st.columns([1.2, 1])

            with col_img:
                st.markdown('<div class="section-title">Annotated Output</div>', unsafe_allow_html=True)
                annotated_rgb = cv2.cvtColor(result["annotated_image"], cv2.COLOR_BGR2RGB)
                st.image(annotated_rgb, use_container_width=True)

            with col_out:
                cls = result["classification"]
                sev = cls["severity"]

                st.markdown(
                    f"""
<div class="detail-panel">
    <h4>Agent Decision — #{result['event_id']:03d}</h4>
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
        <div class="detail-value" style="font-size:12px; color:#B9BBB3; line-height:1.4;">{cls['reasoning']}</div>
    </div>
    <div class="detail-field" style="margin-top:12px;">
        <div class="detail-label">Detection Counts</div>
        <div class="detail-value" style="font-size:12px;">
""",
                    unsafe_allow_html=True,
                )

                if result.get("summary"):
                    for label, count in result["summary"].items():
                        st.markdown(f"<span style='color:#E8E9E2;'>• {label}:</span> {count}", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#777A73;'>No objects matched confidence threshold.</span>", unsafe_allow_html=True)

                st.markdown("</div></div></div>", unsafe_allow_html=True)

            st.success(f"Event #{result['event_id']:03d} recorded in hash-chained audit log. Status: Awaiting Supervisor Approval.")

        else:
            # Video Inference
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

            st.markdown('<div class="section-title">Aggregated Detections</div>', unsafe_allow_html=True)
            for k, v in v_res["aggregated_summary"].items():
                st.markdown(f"• **{k}**: {v} detections across frames")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: TRIGGER CONSOLE (Hero Page)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Trigger Console":
    st.markdown(
        '<div class="page-title"><h2>Trigger Console</h2></div>'
        '<p class="page-subtitle">Create a controlled simulation event for JARVIS to analyze.</p>',
        unsafe_allow_html=True,
    )

    # Simulation Banner
    st.markdown(
        """
<div class="sim-banner">
    <span class="sim-title">Simulation Mode</span>
    <div class="sim-detail">
        <span><span class="sim-dot"></span> Software Simulation</span>
        <span>Source: Simulated</span>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Main Machine Panel
    c_status = get_conveyor_status()
    state_text, state_desc, state_color, state_sym = get_machine_state_html(c_status["status"])
    last_update_time = c_status.get("last_updated", "—")
    if isinstance(last_update_time, str) and "T" in last_update_time:
        last_update_time = last_update_time.split("T")[-1][:8]

    st.markdown(
        f"""
<div class="machine-panel">
    <div class="machine-name">Processing Machine 01</div>
    <div class="machine-state" style="color:{state_color};">{state_sym} {state_text}</div>
    <div class="machine-state-desc">{state_desc}</div>
    <div class="machine-meta">
        <div class="meta-item">
            <div class="meta-label">Status</div>
            <div class="meta-value">{c_status['status'].upper()}</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Source</div>
            <div class="meta-value">Software Simulation</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Last Update</div>
            <div class="meta-value">{last_update_time}</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Current Event</div>
            <div class="meta-value">{c_status.get('last_change_reason', 'None')[:24]}</div>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Machine Controls
    col_start, col_stop, col_fault = st.columns(3)
    with col_start:
        if st.button("START", use_container_width=True, type="primary"):
            run_conveyor()
            st.rerun()
    with col_stop:
        if st.button("STOP", use_container_width=True):
            stop_conveyor()
            st.rerun()
    with col_fault:
        fault_type = st.selectbox(
            "Fault Type",
            ["mechanical_jam", "motor_thermal_overload", "sensor_misalignment", "roller_bearing_failure"],
            label_visibility="collapsed",
        )
        if st.button("INJECT FAULT", use_container_width=True):
            res = run_conveyor_fault_pipeline(fault_type)
            st.session_state["last_sim_event"] = {
                "text": f"Machine fault injected: {fault_type}",
                "from_state": "RUNNING",
                "to_state": "FAULT",
                "time": datetime.now().strftime("%H:%M:%S"),
                "event_id": res["event_id"],
            }
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Other Simulation Events
    st.markdown(
        '<div class="section-title"><span>Other Simulation Events</span><span style="font-weight:400;">Secondary Triggers</span></div>',
        unsafe_allow_html=True,
    )

    col_ppe, col_fire = st.columns(2)
    with col_ppe:
        st.markdown(
            """
<div class="glass-surface-raised" style="text-align:center; padding:20px;">
    <div style="font-size:12px; font-weight:600; color:#E8E9E2; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">PPE Violation</div>
    <div style="font-size:11px; color:#777A73;">Upload an image via Upload &amp; Inspect to trigger PPE analysis.</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with col_fire:
        st.markdown(
            """
<div class="glass-surface-raised" style="text-align:center; padding:20px;">
    <div style="font-size:12px; font-weight:600; color:#E8E9E2; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">Fire / Smoke</div>
    <div style="font-size:11px; color:#777A73;">Upload an image via Upload &amp; Inspect to trigger fire detection.</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Last Simulation Event
    last_event = st.session_state.get("last_sim_event", None)
    if last_event:
        st.markdown(
            f"""
<div class="event-surface">
    <div class="event-label">Last Simulation Event</div>
    <div class="event-text">{last_event['text']}</div>
    <div class="event-meta">
        <span style="color:#B85C58;">{last_event.get('from_state','—')}</span> → <span style="color:#B85C58;">{last_event.get('to_state','—')}</span>
        &nbsp;&nbsp;&nbsp; Software Simulation &nbsp;&nbsp;&nbsp; {last_event.get('time','—')}
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
<div class="event-surface">
    <div class="event-label">Last Simulation Event</div>
    <div style="font-size:13px; color:#777A73;">No simulation events triggered yet.</div>
</div>
""",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: REASONING TRAIL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Reasoning Trail":
    st.markdown(
        '<div class="page-title"><h2>Reasoning Trail</h2></div>'
        '<p class="page-subtitle">Trace the chain from detection to decision for each event.</p>',
        unsafe_allow_html=True,
    )

    events = get_all_events()

    if not events:
        st.markdown(
            '<div class="glass-surface"><p style="color:#B9BBB3;margin:0;font-size:13px;">No events to display reasoning for. Generate events via Trigger Console or Upload &amp; Inspect.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        event_options = {
            f"Event #{e['event_id']} — {e['event_type'].upper()} ({e['timestamp']})": e["event_id"]
            for e in events
        }
        selected_label = st.selectbox("Select event", list(event_options.keys()), label_visibility="collapsed")
        selected_id = event_options[selected_label]
        ev = next((e for e in events if e["event_id"] == selected_id), None)

        if ev:
            sev_html = format_severity(ev["severity"])
            steps = [
                ("Observation", f"{ev['event_type'].upper()} event detected from {ev['source_file'] or 'system stream'}"),
                ("Classification", f"Category: {ev['category'].upper()}"),
                ("Severity Assessment", sev_html),
                ("Proposed Action", ev["proposed_action"]),
                ("Approval Status", format_status(ev["approval_status"])),
            ]

            for i, (label, value) in enumerate(steps, 1):
                st.markdown(
                    f"""
<div class="glass-surface" style="padding:16px 20px; margin-bottom:8px;">
    <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-size:18px; font-weight:700; color:#454640; min-width:24px;">{i}</div>
        <div>
            <div class="detail-label">{label}</div>
            <div style="color:#E8E9E2; font-size:13px; margin-top:2px;">{value}</div>
        </div>
    </div>
</div>
""",
                    unsafe_allow_html=True,
                )

            # Reasoning text
            if ev.get("proposed_action"):
                st.markdown(
                    f"""
<div class="glass-surface" style="padding:16px 20px; margin-top:8px;">
    <div class="detail-label">Full Reasoning</div>
    <div style="color:#B9BBB3; font-size:12px; line-height:1.6; margin-top:6px;">
        Event type: {ev['event_type']} | Source: {ev['source_file'] or 'system'} | Severity: {ev['severity']} | Category: {ev['category']}<br>
        The reasoning agent evaluated the detection payload and classified this event based on deterministic rules.
        The proposed action has been queued for human approval.
    </div>
</div>
""",
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: PENDING ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Pending Actions":
    st.markdown(
        '<div class="page-title"><h2>Pending Actions</h2></div>'
        '<p class="page-subtitle">Human-in-the-loop approval queue — supervisor gate.</p>',
        unsafe_allow_html=True,
    )

    pending = get_pending_events()

    if not pending:
        st.markdown(
            '<div class="glass-surface" style="padding:24px;">'
            '<p style="color:#B9BBB3; margin:0; font-size:13px;">All incidents reviewed. No pending actions.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(pending)} pending action(s) awaiting authorization.")

        for event in pending:
            sev_html = format_severity(event["severity"])

            with st.container():
                st.markdown(
                    f"""
<div class="detail-panel" style="margin-bottom:12px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <strong style="color:#F3F3EE;">EVENT #{event['event_id']:03d} &nbsp;|&nbsp; {event['event_type'].upper()}</strong>
        <div>{sev_html} &nbsp;|&nbsp; <span style="color:#777A73;font-size:11px;">{event['timestamp']}</span></div>
    </div>
    <div style="font-size:11px; color:#454640; margin-bottom:8px;">SOURCE: {event['source_file'] or 'System Stream'}</div>
    <div style="font-size:13px; color:#E8E9E2; padding:10px 0; border-top:1px solid rgba(69,70,64,0.3); border-bottom:1px solid rgba(69,70,64,0.3); margin-bottom:10px;">
        <strong>Proposed Action:</strong> {event['proposed_action']}
    </div>
</div>
""",
                    unsafe_allow_html=True,
                )

                col_ap, col_dn, col_fill = st.columns([1, 1, 4])
                with col_ap:
                    if st.button("Approve", key=f"q_app_{event['event_id']}", type="primary", use_container_width=True):
                        update_approval(event["event_id"], "approved", "Manager")
                        st.rerun()
                with col_dn:
                    if st.button("Deny", key=f"q_den_{event['event_id']}", use_container_width=True):
                        update_approval(event["event_id"], "denied", "Manager")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: RISK TRENDS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Risk Trends":
    st.markdown(
        '<div class="page-title"><h2>Risk Trends</h2></div>'
        '<p class="page-subtitle">Historical pattern detection and incident analytics.</p>',
        unsafe_allow_html=True,
    )

    df = get_events_dataframe()

    if df.empty:
        st.markdown(
            '<div class="glass-surface" style="padding:24px;">'
            '<p style="color:#B9BBB3; margin:0; font-size:13px;">No event telemetry recorded yet.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown('<div class="detail-label" style="margin-bottom:8px;">Incidents by Category</div>', unsafe_allow_html=True)
            type_counts = df["event_type"].value_counts()
            st.bar_chart(type_counts, height=220)
        with col_t2:
            st.markdown('<div class="detail-label" style="margin-bottom:8px;">Incidents by Severity</div>', unsafe_allow_html=True)
            sev_counts = df["severity"].value_counts()
            st.bar_chart(sev_counts, height=220)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: WORKER RECORDS (Event Log Restyled)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Worker Records":
    st.markdown(
        '<div class="page-title"><h2>Worker Records</h2></div>'
        '<p class="page-subtitle">Complete incident log with filtering and detail view.</p>',
        unsafe_allow_html=True,
    )

    events = get_all_events()

    if not events:
        st.markdown(
            '<div class="glass-surface" style="padding:24px;">'
            '<p style="color:#B9BBB3; margin:0; font-size:13px;">No events recorded in log.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            type_filter = st.selectbox("Filter by Type", ["All", "PPE", "Fire", "Conveyor"])
        with col_f2:
            status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Approved", "Denied"])

        filtered = events
        if type_filter != "All":
            filtered = [e for e in filtered if e["event_type"] == type_filter.lower()]
        if status_filter != "All":
            filtered = [e for e in filtered if e["approval_status"] == status_filter.lower()]

        st.caption(f"Showing {len(filtered)} of {len(events)} records.")

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
""",
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: AUDIT REPORTS (Hash Chain + CSV Export)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Audit Reports":
    st.markdown(
        '<div class="page-title"><h2>Audit Reports</h2></div>'
        '<p class="page-subtitle">Tamper-evident SHA-256 hash chain verification and data export.</p>',
        unsafe_allow_html=True,
    )

    events = get_all_events()

    if not events:
        st.markdown(
            '<div class="glass-surface" style="padding:24px;">'
            '<p style="color:#B9BBB3; margin:0; font-size:13px;">No events recorded in audit log.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        # CSV Export
        col_info, col_exp = st.columns([2, 1])
        with col_info:
            st.markdown(
                f'<div class="detail-label">{len(events)} events in hash-chained audit trail</div>',
                unsafe_allow_html=True,
            )
        with col_exp:
            csv_data = export_events_to_csv(events)
            st.download_button(
                label="Export CSV",
                data=csv_data,
                file_name=f"jarvis_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Hash chain display
        for event in events[:20]:
            st.markdown(
                f"""
<div class="glass-surface" style="padding:14px 20px; margin-bottom:6px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <strong style="color:#E8E9E2; font-size:13px;">#{event['event_id']:03d} — {event['event_type'].upper()}</strong>
        <span style="font-size:11px; color:#777A73;">{event['timestamp']}</span>
    </div>
    <div style="display:flex; gap:20px;">
        <div style="flex:1;">
            <span style="font-size:10px;color:#454640;">RECORD_HASH:</span><br>
            <div class="hash-code">{event.get('record_hash') or 'GENESIS'}</div>
        </div>
        <div style="flex:1;">
            <span style="font-size:10px;color:#454640;">PREV_HASH:</span><br>
            <div class="hash-code">{event.get('prev_hash') or 'GENESIS'}</div>
        </div>
    </div>
</div>
""",
                unsafe_allow_html=True,
            )

            if event.get("detections_json"):
                try:
                    dets = json.loads(event["detections_json"])
                    if dets:
                        for i, d in enumerate(dets, 1):
                            st.text(
                                f"  #{i:02d}  {d.get('label', '-'):<15} conf={d.get('confidence', 1.0):.3f}  bbox={d.get('bbox', '-')}"
                            )
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: SHIFT HANDOVER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Shift Handover":
    st.markdown(
        '<div class="page-title"><h2>Shift Handover</h2></div>'
        '<p class="page-subtitle">Autonomous LLM-powered shift briefing for oncoming supervisors.</p>',
        unsafe_allow_html=True,
    )

    col_h1, col_h2 = st.columns([1.5, 1])

    with col_h1:
        time_preset = st.selectbox(
            "Shift Time Window",
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
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid rgba(69,70,64,0.4); padding-bottom:10px;">
        <span class="detail-label">Reasoning Engine: {report_res['provider']}</span>
        <span style="font-size:11px; color:#777A73;">Events: {report_res['event_count']} &nbsp;|&nbsp; {report_res['generated_at']}</span>
    </div>
    <div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(report_res["summary"])
        st.markdown("</div></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: ASK JARVIS (Placeholder)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Ask JARVIS":
    st.markdown(
        '<div class="page-title"><h2>Ask JARVIS</h2></div>'
        '<p class="page-subtitle">Conversational query interface for JARVIS reasoning.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div class="placeholder-panel">
    <div class="ph-title">Ask JARVIS</div>
    <div class="ph-desc">Conversational AI query interface — available in a future release.</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: ALERT SETUP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Alert Setup":
    st.markdown(
        '<div class="page-title"><h2>Alert Setup</h2></div>'
        '<p class="page-subtitle">Configure notification dispatch, emergency contacts, and gateway channels.</p>',
        unsafe_allow_html=True,
    )

    col_setup, col_telemetry = st.columns([1.5, 1.2])

    with col_setup:
        st.markdown(
            '<div class="section-title"><span>Notification Endpoints</span><span>Dispatch Configuration</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="detail-label">Primary Alert Email (SMTP)</div>', unsafe_allow_html=True)
        email_recipient = st.text_input(
            "Primary Recipient Email",
            value=os.getenv("ALERT_EMAIL", "plant-manager@industrial.local"),
            help="Designated email address for incident reports and approval escalations.",
            label_visibility="collapsed",
        )

        st.markdown('<div class="detail-label" style="margin-top:14px;">Emergency Mobile Phone (SMS)</div>', unsafe_allow_html=True)
        phone_recipient = st.text_input(
            "Emergency Phone",
            value=os.getenv("ALERT_PHONE_NUMBER", "+1-555-0199"),
            help="E.164 phone number for critical emergency alerts.",
            label_visibility="collapsed",
        )

        st.markdown('<div class="detail-label" style="margin-top:16px;">Automated Dispatch Triggers</div>', unsafe_allow_html=True)
        st.checkbox("Emergency stop / Machine faults (Immediate SMS + Email)", value=True)
        st.checkbox("Hazardous fire & smoke incidents (Immediate SMS + Email)", value=True)
        st.checkbox("Critical PPE non-compliance (Digest Email)", value=True)
        st.checkbox("Autonomous agent decision audit trail events", value=False)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save Alert Setup", type="primary"):
            st.success("Alert notification preferences updated successfully.")

    with col_telemetry:
        st.markdown(
            '<div class="section-title"><span>Gateway Status</span><span>Delivery Channels</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
<div class="glass-surface">
    <div style="font-size:10px; text-transform:uppercase; color:#777A73; letter-spacing:0.08em; font-weight:700; margin-bottom:14px;">CHANNEL HEALTH</div>
    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:12px;">
        <span style="color:#B9BBB3;">SMTP Mail Gateway:</span>
        <span style="color:#6F8F73; font-weight:600;">● CONNECTED</span>
    </div>
    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:12px;">
        <span style="color:#B9BBB3;">Twilio SMS Gateway:</span>
        <span style="color:#6F8F73; font-weight:600;">● STANDBY</span>
    </div>
    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:12px;">
        <span style="color:#B9BBB3;">Agent Decision Webhook:</span>
        <span style="color:#6F8F73; font-weight:600;">● ACTIVE</span>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:12px; border-top:1px solid rgba(69,70,64,0.3); padding-top:12px; margin-top:8px;">
        <span style="color:#B9BBB3;">Last Incident Alert:</span>
        <span style="color:#E8E9E2;">Today, 09:41:12</span>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: AUDIT VERIFICATION (Placeholder)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Audit Verification":
    st.markdown(
        '<div class="page-title"><h2>Audit Verification</h2></div>'
        '<p class="page-subtitle">SHA-256 hash chain integrity verification tool.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div class="placeholder-panel">
    <div class="ph-title">Audit Verification</div>
    <div class="ph-desc">Automated hash chain integrity checker — available in a future release.</div>
</div>
""",
        unsafe_allow_html=True,
    )

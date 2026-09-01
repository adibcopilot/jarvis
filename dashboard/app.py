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
from detection.pipeline import run_ppe_pipeline, run_fire_pipeline


# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JARVIS - Manufacturing Monitor",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
    .main-header p { margin: 0.3rem 0 0 0; opacity: 0.8; font-size: 0.95rem; }
    
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        color: white;
    }
    .stat-card h3 { margin: 0; font-size: 2rem; font-weight: 700; }
    .stat-card p { margin: 0.2rem 0 0 0; font-size: 0.85rem; opacity: 0.7; }
    
    .severity-critical { color: #ff4444; font-weight: 700; }
    .severity-high { color: #ff8800; font-weight: 600; }
    .severity-medium { color: #ffcc00; font-weight: 600; }
    .severity-low { color: #44cc44; font-weight: 500; }
    
    .event-card {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏭 JARVIS</h1>
    <p>Joint Autonomous Reasoning & Vision Inspection System — Manufacturing Monitor</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar Navigation ──────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "📤 Upload & Detect", "✅ Approval Queue", "📜 Event Log"],
    index=0,
)


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Dashboard
# ════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    stats = get_event_stats()
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="stat-card"><h3>{stats["total_events"]}</h3><p>Total Events</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><h3>{stats["pending"]}</h3><p>Pending Approval</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><h3>{stats["approved"]}</h3><p>Approved</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><h3>{stats["denied"]}</h3><p>Denied</p></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card"><h3>{stats["high_severity"]}</h3><p>High/Critical</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Recent events table
    st.subheader("Recent Events")
    events = get_all_events()
    if events:
        display_data = []
        for e in events[:20]:
            sev = e["severity"]
            display_data.append({
                "ID": e["event_id"],
                "Time": e["timestamp"],
                "Type": e["event_type"].upper(),
                "Source": e["source_file"] or "-",
                "Severity": sev.upper(),
                "Action": e["proposed_action"][:80] + "..." if len(e["proposed_action"]) > 80 else e["proposed_action"],
                "Status": e["approval_status"].upper(),
            })
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.info("No events yet. Upload an image or video to start detection.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Upload & Detect
# ════════════════════════════════════════════════════════════════════════════
elif page == "📤 Upload & Detect":
    st.subheader("Upload Image for Detection")
    
    col_mode, col_upload = st.columns([1, 3])
    with col_mode:
        detection_mode = st.radio("Detection Type", ["PPE Compliance", "Fire & Smoke"], index=0)
    
    with col_upload:
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=["jpg", "jpeg", "png"],
            key="upload_detect"
        )
    
    if uploaded_file is not None:
        # Save uploaded file to a temp path
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name
        
        with st.spinner("Running detection + reasoning agent..."):
            if detection_mode == "PPE Compliance":
                result = run_ppe_pipeline(tmp_path)
            else:
                result = run_fire_pipeline(tmp_path)
        
        # Show results
        col_img, col_info = st.columns([1, 1])
        
        with col_img:
            st.subheader("Annotated Result")
            annotated_rgb = cv2.cvtColor(result["annotated_image"], cv2.COLOR_BGR2RGB)
            st.image(annotated_rgb, use_container_width=True)
        
        with col_info:
            cls = result["classification"]
            sev = cls["severity"]
            
            st.subheader("Agent Classification")
            
            sev_colors = {"critical": "#ff4444", "high": "#ff8800", "medium": "#ffcc00", "low": "#44cc44"}
            sev_color = sev_colors.get(sev, "#888888")
            st.markdown(f"**Severity:** <span style='color:{sev_color}; font-size:1.2rem; font-weight:700;'>{sev.upper()}</span>", unsafe_allow_html=True)
            st.markdown(f"**Category:** {cls['category']}")
            st.markdown(f"**Event ID:** {result['event_id']}")
            
            st.markdown("---")
            st.markdown("**Proposed Action:**")
            st.info(cls["proposed_action"])
            
            st.markdown("**Agent Reasoning:**")
            st.caption(cls["reasoning"])
            
            st.markdown("---")
            st.markdown("**Detection Summary:**")
            if result.get("summary"):
                for label, count in result["summary"].items():
                    st.text(f"  {label}: {count}")
            
            # Individual detections
            if result["detections"]:
                with st.expander("All Detections", expanded=False):
                    for i, d in enumerate(result["detections"], 1):
                        st.text(f"#{i:02d}: {d['label']:<12} conf={d['confidence']:.3f} bbox={d['bbox']}")
        
        st.success(f"Event #{result['event_id']} logged to database. Status: PENDING APPROVAL.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Approval Queue
# ════════════════════════════════════════════════════════════════════════════
elif page == "✅ Approval Queue":
    st.subheader("Pending Events — Approve or Deny")
    
    pending = get_pending_events()
    
    if not pending:
        st.success("No pending events. All events have been reviewed.")
    else:
        st.warning(f"{len(pending)} event(s) awaiting review.")
        
        for event in pending:
            sev = event["severity"]
            sev_colors = {"critical": "#ff4444", "high": "#ff8800", "medium": "#ffcc00", "low": "#44cc44"}
            sev_color = sev_colors.get(sev, "#888888")
            
            with st.container():
                st.markdown(f"""
                <div class="event-card">
                    <strong>Event #{event['event_id']}</strong> | 
                    <strong>{event['event_type'].upper()}</strong> |
                    <span style="color:{sev_color}; font-weight:700;">{sev.upper()}</span> |
                    {event['timestamp']} |
                    Source: {event['source_file'] or 'N/A'}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"**Proposed Action:** {event['proposed_action']}")
                
                col_a, col_d, col_space = st.columns([1, 1, 4])
                with col_a:
                    if st.button("✅ Approve", key=f"approve_{event['event_id']}"):
                        update_approval(event["event_id"], "approved", "Manager")
                        st.rerun()
                with col_d:
                    if st.button("❌ Deny", key=f"deny_{event['event_id']}"):
                        update_approval(event["event_id"], "denied", "Manager")
                        st.rerun()
                
                st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Event Log
# ════════════════════════════════════════════════════════════════════════════
elif page == "📜 Event Log":
    st.subheader("Complete Event Log (Hash-Chained)")
    
    events = get_all_events()
    
    if not events:
        st.info("No events recorded yet.")
    else:
        # Filter options
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            type_filter = st.selectbox("Filter by Type", ["All", "PPE", "Fire"])
        with col_f2:
            status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Approved", "Denied"])
        
        filtered = events
        if type_filter != "All":
            filtered = [e for e in filtered if e["event_type"] == type_filter.lower()]
        if status_filter != "All":
            filtered = [e for e in filtered if e["approval_status"] == status_filter.lower()]
        
        st.caption(f"Showing {len(filtered)} of {len(events)} events")
        
        for event in filtered:
            sev = event["severity"]
            sev_colors = {"critical": "#ff4444", "high": "#ff8800", "medium": "#ffcc00", "low": "#44cc44"}
            sev_color = sev_colors.get(sev, "#888888")
            
            status = event["approval_status"]
            status_icon = {"pending": "🟡", "approved": "🟢", "denied": "🔴"}.get(status, "⚪")
            
            with st.expander(
                f"Event #{event['event_id']} — {event['event_type'].upper()} — {sev.upper()} — {status_icon} {status.upper()} — {event['timestamp']}"
            ):
                st.markdown(f"**Source File:** {event['source_file'] or 'N/A'}")
                st.markdown(f"**Severity:** <span style='color:{sev_color}'>{sev.upper()}</span>", unsafe_allow_html=True)
                st.markdown(f"**Category:** {event['category']}")
                st.markdown(f"**Proposed Action:** {event['proposed_action']}")
                st.markdown(f"**Approval Status:** {status_icon} {status.upper()}")
                if event.get("approved_by"):
                    st.markdown(f"**Approved By:** {event['approved_by']} at {event.get('resolved_at', 'N/A')}")
                
                # Show detections
                if event.get("detections_json"):
                    dets = json.loads(event["detections_json"])
                    if dets:
                        st.markdown("**Detections:**")
                        for i, d in enumerate(dets, 1):
                            st.text(f"  #{i:02d}: {d['label']:<12} conf={d['confidence']:.3f} bbox={d['bbox']}")
                
                # Hash chain info
                st.caption(f"Record Hash: {event.get('record_hash', 'N/A')[:24]}...")
                st.caption(f"Prev Hash: {event.get('prev_hash', 'N/A')[:24]}...")


# ── Footer ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("JARVIS v0.1 — Final Year Project")
st.sidebar.caption("Adib Sajjad Patel | CO 5th Sem")
st.sidebar.caption(f"Session: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

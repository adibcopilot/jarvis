"""
agent/shift_report.py
Automated Shift Handover Report Generator for JARVIS (SRS FR-15 / Proposal Section 6.3).

Generates plain-English shift handover summaries for oncoming supervisors using
LLM reasoning (NVIDIA NIM / OpenRouter / OpenAI) with graceful local degradation (NFR-7).
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import get_connection

load_dotenv()


def get_events_for_shift(start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Dict]:
    """Fetch events within a specific time window."""
    conn = get_connection()
    if start_time and end_time:
        query = "SELECT * FROM events WHERE timestamp BETWEEN ? AND ? ORDER BY event_id ASC"
        rows = conn.execute(query, (start_time, end_time)).fetchall()
    elif start_time:
        query = "SELECT * FROM events WHERE timestamp >= ? ORDER BY event_id ASC"
        rows = conn.execute(query, (start_time,)).fetchall()
    else:
        query = "SELECT * FROM events ORDER BY event_id ASC"
        rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _build_deterministic_report(events: List[Dict], time_window_label: str) -> str:
    """Fallback rule-based plain-English handover report when no LLM API key is configured."""
    total = len(events)
    if total == 0:
        return f"### 📋 Shift Handover Summary ({time_window_label})\n\n**Status:** ✅ All quiet. No safety violations, equipment faults, or hazard alerts were recorded during this shift period."

    types = {}
    severities = {}
    pending = []
    critical_items = []

    for e in events:
        t = e["event_type"].upper()
        s = e["severity"].upper()
        types[t] = types.get(t, 0) + 1
        severities[s] = severities.get(s, 0) + 1

        if e["approval_status"] == "pending":
            pending.append(e)
        if s in ("CRITICAL", "HIGH"):
            critical_items.append(e)

    summary_lines = [
        f"### 📋 Shift Handover Report — {time_window_label}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **Total Events Logged:** {total}",
        "",
        "#### 1. Executive Shift Overview",
        f"During this shift, the system recorded **{total} operational telemetry event(s)** across manufacturing zones.",
        f"• **Breakdown by Domain:** " + ", ".join([f"{k}: {v}" for k, v in types.items()]),
        f"• **Severity Distribution:** " + ", ".join([f"{k}: {v}" for k, v in severities.items()]),
        "",
        "#### 2. Critical & High-Priority Incidents",
    ]

    if critical_items:
        for c in critical_items:
            summary_lines.append(
                f"- **Event #{c['event_id']:03d} ({c['event_type'].upper()})** at `{c['timestamp']}`: {c['proposed_action']} [Status: {c['approval_status'].upper()}]"
            )
    else:
        summary_lines.append("• No critical or high-severity incidents recorded.")

    summary_lines.extend([
        "",
        "#### 3. Action Items Requiring Oncoming Supervisor Authorization",
    ])

    if pending:
        summary_lines.append(f"⚠️ **{len(pending)} pending action proposal(s)** require supervisor review:")
        for p in pending:
            summary_lines.append(f"- **Event #{p['event_id']:03d}** ({p['event_type'].upper()} - {p['severity'].upper()}): {p['proposed_action']}")
    else:
        summary_lines.append("✅ All incident proposals from this shift have been reviewed and resolved.")

    summary_lines.extend([
        "",
        "#### 4. Safety & Operational Recommendations",
        "• Ensure Line 1 conveyor optical sensors and belt alignments are inspected during the pre-shift routine.",
        "• Remind floor operators in Zone 2 regarding PPE vest compliance prior to entering active machinery areas.",
    ])

    return "\n".join(summary_lines)


def generate_shift_report(start_time: Optional[str] = None, end_time: Optional[str] = None, time_window_label: str = "Current Window") -> Dict[str, Any]:
    """
    Generate an autonomous Shift Handover Report using LLM reasoning (or graceful fallback).
    
    Returns dict:
        {
            "summary": str (Markdown text),
            "event_count": int,
            "provider": str ("NVIDIA NIM", "OpenRouter", "OpenAI", or "Local Rule Engine"),
            "generated_at": str,
            "time_window": str,
        }
    """
    events = get_events_for_shift(start_time, end_time)
    event_count = len(events)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check available LLM credentials
    nim_key = os.getenv("NIM_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    client = None
    model_name = None
    provider_name = None

    if nim_key and not nim_key.startswith("your_"):
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                api_key=nim_key
            )
            model_name = os.getenv("NIM_MODEL", "meta/llama-3.1-8b-instruct")
            provider_name = "NVIDIA NIM (" + model_name + ")"
        except Exception:
            client = None

    elif openrouter_key and not openrouter_key.startswith("your_"):
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                api_key=openrouter_key
            )
            model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
            provider_name = "OpenRouter (" + model_name + ")"
        except Exception:
            client = None

    elif openai_key and not openai_key.startswith("your_"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            provider_name = "OpenAI (" + model_name + ")"
        except Exception:
            client = None

    # If LLM client is available, attempt AI generation
    if client and model_name:
        try:
            prompt_events = []
            for e in events:
                prompt_events.append({
                    "id": e["event_id"],
                    "time": e["timestamp"],
                    "type": e["event_type"],
                    "severity": e["severity"],
                    "category": e["category"],
                    "action": e["proposed_action"],
                    "approval": e["approval_status"],
                    "source": e["source_file"],
                })

            system_prompt = (
                "You are JARVIS, an autonomous industrial reasoning assistant on a manufacturing plant floor. "
                "Generate a professional, structured plain-English Shift Handover Report for the oncoming shift supervisor. "
                "Highlight key safety violations (PPE), hazard detections (fire/smoke), conveyor mechanical faults, "
                "unresolved pending approvals, and prioritized recommendations for the next shift."
            )

            user_prompt = f"Shift Time Window: {time_window_label}\nTotal Events: {event_count}\n\nIncident Telemetry Data:\n{json.dumps(prompt_events, indent=2)}"

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=800,
            )

            ai_text = response.choices[0].message.content
            return {
                "summary": ai_text,
                "event_count": event_count,
                "provider": provider_name,
                "generated_at": gen_time,
                "time_window": time_window_label,
            }
        except Exception as e:
            # Graceful degradation per NFR-7
            report_text = _build_deterministic_report(events, time_window_label)
            return {
                "summary": report_text,
                "event_count": event_count,
                "provider": f"Local Fallback Engine (LLM API unreachable: {str(e)[:50]}...)",
                "generated_at": gen_time,
                "time_window": time_window_label,
            }

    # Default: Graceful deterministic fallback engine
    report_text = _build_deterministic_report(events, time_window_label)
    return {
        "summary": report_text,
        "event_count": event_count,
        "provider": "Autonomous Reasoning Engine (Local Deterministic)",
        "generated_at": gen_time,
        "time_window": time_window_label,
    }

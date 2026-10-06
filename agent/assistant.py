"""
JARVIS Conversational & Project Knowledge Assistant
Evaluates queries via Guardrails, supports cloud LLM (NVIDIA NIM / OpenRouter / OpenAI),
and provides comprehensive local knowledge reasoning for project inquiries.
"""
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from guardrails.rules import evaluate_chat_guardrail
from database.db import (
    get_all_events,
    get_event_stats,
    get_all_workers,
    get_events_for_worker,
    get_events_by_type,
    find_mentioned_worker,
    get_event_by_id,
)
from simulation.conveyor import get_status as get_machine_status

SYSTEM_PROMPT = """You are JARVIS (Joint Autonomous Reasoning & Vision Inspection System), an intelligent industrial AI assistant.
Project Details:
- Group: Group No. 12
- Authors: Adib Sajjad Patel (Lead, Roll No. 26, Enr: 24211320284), Rudra Sujit Sagar (Roll No. 27, Enr: 24211320291), Abhishek Sharadchandra Chavan (Roll No. 24, Enr: 24211320226).
- Institute: Rasiklal M. Dhariwal Institute of Technology.
- Course: Diploma in Computer Engineering, 5th Semester.
- Core Purpose: AI-based manufacturing floor monitoring through perception, reasoning, and human-approved action.
- Scope: Pure Software Simulation. No real industrial hardware, PLCs, or actuators are wired.
- Computer Vision: YOLOv8 model detecting Workers, PPE (Helmet, Vest, Gloves, Boots, Goggles), Fire, Smoke, and Processing Machines.
- Core Safety Rule: Human Approval Gate — JARVIS recommends interventions, but an authorized human supervisor must approve before simulated execution.
- Audit Trail: Immutable SHA-256 cryptographic hash-chaining stored in SQLite.
- Notifications: Multi-tier escalation including Gmail SMTP alerts to safety managers.
- Guardrails: Strict deterministic policies blocking unauthorized physical hardware control, log deletion, or bypassing supervisor approval.

Provide concise, highly professional, technically grounded responses without inventing false benchmarks or real hardware claims.
"""

def _format_event_line(event: Dict[str, Any]) -> str:
    eid = event.get("event_id")
    etype = (event.get("event_type") or "event").upper()
    sev = (event.get("severity") or "n/a").upper()
    status = (event.get("approval_status") or "pending").upper()
    ts = event.get("timestamp") or "unknown time"
    action = event.get("proposed_action") or "No proposed action recorded."
    return f"• Event #{eid} [{etype} / {sev} / {status}] {ts} — {action}"


def _answer_worker_record(worker: Dict[str, Any]) -> str:
    events = get_events_for_worker(worker)
    status = worker.get("status") or "Clear"
    history = worker.get("history_summary") or "No written history on file."
    lines = [
        f"**Worker Record: {worker.get('name')} ({worker.get('worker_code')})**\n",
        f"• **Role:** {worker.get('role')}",
        f"• **Department / Zone:** {worker.get('department')}",
        f"• **Shift:** {worker.get('shift')}",
        f"• **Status:** `{status}`",
        f"• **Incident count:** `{worker.get('incidents_count', 0)}`",
        f"• **Last incident date:** {worker.get('last_incident_date') or '-'}",
        f"\n**What this worker has done:**\n{history}",
    ]
    if events:
        lines.append("\n**Linked floor events:**")
        for event in events[:8]:
            lines.append(_format_event_line(event))
    else:
        lines.append("\nNo linked PPE, fire, or machine events are currently attached to this worker.")
    return "\n".join(lines)


def _answer_event_records(kind: str) -> str:
    events = get_events_by_type(kind)
    label = {"ppe": "PPE / safety", "fire": "fire & smoke", "conveyor": "processing machine / conveyor"}.get(kind, kind)
    if not events:
        return f"No **{label}** records are in the live event log yet."
    lines = [f"**{label.title()} records ({len(events)} total):**\n"]
    for event in events[:12]:
        lines.append(_format_event_line(event))
    return "\n".join(lines)


def _answer_all_records() -> str:
    stats = get_event_stats()
    workers = get_all_workers()
    events = get_all_events()
    flagged = [w for w in workers if (w.get("status") or "").lower() in ("probation", "flagged")]
    lines = [
        "**Live floor records (from SQLite):**\n",
        f"• Total events: `{stats.get('total_events', len(events))}`",
        f"• PPE: `{stats.get('ppe', 0)}` · Fire/smoke: `{stats.get('fire', 0)}` · Conveyor: `{stats.get('conveyor', 0)}`",
        f"• Pending approvals: `{stats.get('pending', 0)}` · Approved: `{stats.get('approved', 0)}` · Denied: `{stats.get('denied', 0)}`",
        f"• Workers on roster: `{len(workers)}` · Flagged/probation: `{len(flagged)}`",
        "\n**Workers needing attention:**",
    ]
    if flagged:
        for w in flagged:
            lines.append(f"• {w.get('name')} ({w.get('worker_code')}) — {w.get('status')}, {w.get('incidents_count')} incident(s). {w.get('history_summary')}")
    else:
        lines.append("• None currently flagged.")
    lines.append("\n**Most recent events:**")
    for event in events[:8]:
        lines.append(_format_event_line(event))
    lines.append("\nAsk about a specific worker (name or ID like W-8472), or say *PPE records*, *fire records*, or *conveyor records*.")
    return "\n".join(lines)


def _records_context_for_llm() -> str:
    workers = get_all_workers()
    events = get_all_events()[:20]
    worker_lines = []
    for w in workers:
        worker_lines.append(
            f"- {w.get('worker_code')} {w.get('name')} | {w.get('role')} | status={w.get('status')} | incidents={w.get('incidents_count')} | last={w.get('last_incident_date')} | {w.get('history_summary')}"
        )
    event_lines = [_format_event_line(e) for e in events]
    return (
        "LIVE WORKER RECORDS:\n" + "\n".join(worker_lines) +
        "\n\nLIVE EVENT LOG:\n" + "\n".join(event_lines)
    )


def _generate_local_response(query: str) -> str:
    """
    Intelligent local domain-expert response generator when cloud LLM is offline or unconfigured.
    Answers first from live worker/event records, then from project knowledge.
    """
    q = query.lower().strip()

    worker = find_mentioned_worker(query)
    if worker and any(k in q for k in [
        "worker", "record", "done", "did", "history", "incident", "what has", "who is",
        "ppe", "fire", "status", "probation", "flagged", "tell me", "about"
    ]):
        return _answer_worker_record(worker)
    if worker and re.search(r"\bw-\d+\b", q):
        return _answer_worker_record(worker)
    if worker and any(part in q for part in (worker.get("name") or "").lower().split() if len(part) > 2):
        if any(k in q for k in ["what", "who", "show", "tell", "record", "done", "did", "history", "about"]):
            return _answer_worker_record(worker)

    if any(k in q for k in ["worker record", "all workers", "list workers", "roster", "who is on probation", "flagged worker"]):
        workers = get_all_workers()
        lines = ["**Worker roster:**\n"]
        for w in workers:
            lines.append(
                f"• **{w.get('name')}** ({w.get('worker_code')}) — {w.get('role')}, {w.get('status')}, "
                f"{w.get('incidents_count')} incident(s). {w.get('history_summary')}"
            )
        lines.append("\nAsk about any name or ID (example: *What has Sarah Miller done?*) to see that person's full record.")
        return "\n".join(lines)

    event_id_match = re.search(r"event\s*#?\s*(\d+)", q)
    if event_id_match:
        event = get_event_by_id(int(event_id_match.group(1)))
        if event:
            return "**Event record:**\n" + _format_event_line(event)
        return f"No event with ID `{event_id_match.group(1)}` exists in the log."

    if any(k in q for k in ["fire record", "smoke record", "fire event", "smoke event", "how many fire", "fire incident"]):
        return _answer_event_records("fire")
    if any(k in q for k in ["ppe record", "ppe event", "ppe violation", "how many ppe", "helmet", "missing vest"]):
        if "what ppe" in q or "ppe equipment" in q or "verified on workers" in q:
            pass
        else:
            return _answer_event_records("ppe")
    if any(k in q for k in ["conveyor record", "machine record", "jam", "mechanical fault", "how many conveyor"]):
        return _answer_event_records("conveyor")
    if any(k in q for k in ["all records", "event log", "show records", "any records", "recent incident", "pending approval"]):
        return _answer_all_records()

    # 1. Project identity & overview
    if any(k in q for k in ["what is jarvis", "about jarvis", "project overview", "full form", "who are you", "what does jarvis provide"]):
        return (
            "**JARVIS** stands for **Joint Autonomous Reasoning & Vision Inspection System**.\n\n"
            "It is an AI-powered industrial floor monitoring platform developed for our Diploma in Computer Engineering "
            "capstone project at **Rasiklal M. Dhariwal Institute of Technology** (Group 12).\n\n"
            "**What JARVIS provides:**\n"
            "1. **Spatial Perception:** Real-time visual tracking of workers, PPE compliance (helmets, vests, gloves, boots, goggles), fire, and smoke.\n"
            "2. **Agentic Reasoning:** Multi-modal information fusion connecting raw detections with machinery state and safety rules.\n"
            "3. **Human Approval Gate:** Mandatory human-in-the-loop validation before any corrective interlock executes.\n"
            "4. **Tamper-Evident Logging:** Cryptographic SHA-256 hash-chaining ensuring permanent, immutable audit trails.\n\n"
            "*Note: JARVIS operates in a software simulation environment with zero physical hardware hazards.*"
        )

    # 2. Team and Contributors
    if any(k in q for k in ["who created", "team", "author", "student", "roll no", "group 12", "developer"]):
        return (
            "**JARVIS Project Team (Group No. 12):**\n\n"
            "• **Adib Sajjad Patel** — Project Lead | Roll No. 26 | Enrollment No. 24211320284\n"
            "• **Rudra Sujit Sagar** — Team Member | Roll No. 27 | Enrollment No. 24211320291\n"
            "• **Abhishek Sharadchandra Chavan** — Team Member | Roll No. 24 | Enrollment No. 24211320226\n\n"
            "**Institution:** Rasiklal M. Dhariwal Institute of Technology\n"
            "**Course:** Diploma in Computer Engineering, 5th Semester"
        )

    # 3. Guardrails & Safety Architecture
    if any(k in q for k in ["guardrail", "safety boundary", "boundary", "restriction", "allowed action", "blocked action"]):
        return (
            "**JARVIS Safety Guardrails Architecture:**\n\n"
            "The system enforces strict deterministic boundaries defined in `guardrails/config.yaml` and `guardrails/rules.py`:\n\n"
            "**Allowed Actions:**\n"
            "✓ Natural language project inquiries and event explanations.\n"
            "✓ Visual hazard detection (PPE, smoke, fire, machine anomalies).\n"
            "✓ Formulating structured intervention recommendations.\n"
            "✓ Email notifications via server-side Gmail SMTP.\n\n"
            "**Prohibited / Blocked Actions:**\n"
            "✕ Direct autonomous actuation without supervisor token (`bypass_human_approval: prohibited`).\n"
            "✕ Physical hardware control (`physical_hardware_control: prohibited`).\n"
            "✕ Deleting or modifying audit logs (`database.allow_delete_events: false`)."
        )

    # 4. Human Approval Gate
    if any(k in q for k in ["human approval", "approval gate", "human in the loop"]):
        return (
            "**The Human Approval Gate:**\n\n"
            "In JARVIS, **AI recommends, but humans approve.**\n\n"
            "When the reasoning engine identifies a critical event (e.g. smoke near an active processing machine), "
            "it formulates a proposed action card with structured context. The simulated machinery cannot halt or change "
            "states until an authorized supervisor clicks **APPROVE** or provides an authentication token. "
            "This invariant guarantees that the software agent can never execute rogue actions."
        )

    # 5. PPE Compliance & Hazard Detection (generic, if not asking for live records)
    if any(k in q for k in ["ppe equipment", "what ppe", "helmet", "vest", "glove", "boot", "goggle", "safety gear"]):
        live = _answer_event_records("ppe")
        return (
            "**PPE Compliance Monitoring:**\n\n"
            "JARVIS verifies 5 key protective equipment categories across simulated floor workers:\n"
            "1. **Hardhat / Helmet**\n"
            "2. **High-Visibility Vest**\n"
            "3. **Protective Gloves**\n"
            "4. **Steel-Toe Boots**\n"
            "5. **Eye Goggles**\n\n"
            + live
        )

    # 6. Processing Machine & Simulation Scope
    if any(k in q for k in ["machine", "conveyor", "simulation", "hardware", "plc"]):
        mach = get_machine_status()
        state = mach.get("status", "UNKNOWN").upper()
        speed = mach.get("speed_rpm", 1200)
        temp = mach.get("temperature_c", 42.5)
        return (
            f"**Processing Machine (Software Simulation):**\n\n"
            f"• **Current Virtual State:** `{state}`\n"
            f"• **Simulated Motor Speed:** `{speed} RPM`\n"
            f"• **Simulated Core Temp:** `{temp}°C`\n\n"
            "**Important Scope Invariant:** JARVIS operates purely on software state machines and uploaded test video streams. "
            "There are **no physical industrial PLCs, robots, or hazardous actuators** connected to the system.\n\n"
            + _answer_event_records("conveyor")
        )

    # 7. Audit Trail & SHA-256 Hash Chain
    if any(k in q for k in ["hash", "audit", "sha-256", "blockchain", "trail", "tamper"]):
        return (
            "**Tamper-Evident Audit Trail:**\n\n"
            "Every incident detection, context evaluation, supervisor approval, and alert dispatch is recorded as a block "
            "in an SQLite database table with **SHA-256 cryptographic hash-chaining**:\n\n"
            "`Block N Hash = SHA-256(Block N Data + Previous Block Hash)`\n\n"
            "If any historical record or timestamp is modified, the cryptographic hash link breaks immediately, providing foolproof proof of tampering."
        )

    # 8. Live Events / Stats Query
    if any(k in q for k in ["incident", "event", "stat", "how many", "count", "recent"]):
        return _answer_all_records()

    if worker:
        return _answer_worker_record(worker)

    return (
        f"**JARVIS Industrial AI Assistant:**\n\n"
        f"You asked: *\"{query}\"*\n\n"
        "I can answer from **live worker records and the event log**, or from project knowledge.\n\n"
        "Try:\n"
        "• *What has Sarah Miller done?*\n"
        "• *Show worker records*\n"
        "• *PPE records* / *fire records* / *conveyor records*\n"
        "• Project overview, guardrails, or the Human Approval Gate"
    )

def answer_query(query: str, user: str = "Supervisor") -> Dict[str, Any]:
    """
    Main entry point for Ask JARVIS.
    Runs Guardrail evaluation, attempts cloud LLM inference, or falls back to local reasoning.
    """
    # 1. Guardrail Validation
    guardrail = evaluate_chat_guardrail(query)
    if not guardrail["allowed"]:
        return {
            "success": False,
            "allowed": False,
            "guardrail_status": "BLOCKED",
            "policy": guardrail["policy"],
            "response": f"⛔ **Action Blocked by System Guardrail:** {guardrail['reason']}",
            "provider": "Guardrail Policy Engine"
        }

    q = query.lower()
    records_intent = bool(find_mentioned_worker(query)) or any(k in q for k in [
        "worker record", "list workers", "roster", "ppe record", "fire record", "smoke record",
        "conveyor record", "event log", "what has", "how many", "pending approval", "all records",
        "event #"
    ])
    if records_intent:
        local_reply = _generate_local_response(query)
        return {
            "success": True,
            "allowed": True,
            "guardrail_status": "PASSED",
            "policy": "records_inquiry",
            "response": local_reply,
            "provider": "JARVIS Records Engine (SQLite)"
        }

    # 2. Check for Cloud LLM
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
            provider_name = f"NVIDIA NIM ({model_name})"
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
            provider_name = f"OpenRouter ({model_name})"
        except Exception:
            client = None

    elif openai_key and not openai_key.startswith("your_"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            provider_name = f"OpenAI ({model_name})"
        except Exception:
            client = None

    # 3. Attempt LLM generation if client available
    if client and model_name:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + _records_context_for_llm()},
                    {"role": "user", "content": query}
                ],
                max_tokens=450,
                temperature=0.3
            )
            response_content = completion.choices[0].message.content.strip()
            return {
                "success": True,
                "allowed": True,
                "guardrail_status": "PASSED",
                "policy": "project_inquiry",
                "response": response_content,
                "provider": provider_name
            }
        except Exception as e:
            # Fall back to local reasoning on network / quota errors
            pass

    # 4. Fallback to Local Knowledge Engine
    local_reply = _generate_local_response(query)
    return {
        "success": True,
        "allowed": True,
        "guardrail_status": "PASSED",
        "policy": "project_inquiry",
        "response": local_reply,
        "provider": "JARVIS Intelligent Local Engine (Grounded)"
    }

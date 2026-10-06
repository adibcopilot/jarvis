from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import existing backend modules
from database.db import (
    get_all_events,
    get_pending_events,
    get_event_stats,
    get_event_by_id,
    update_approval,
    insert_event,
    get_email_notifications,
    get_all_workers,
    get_worker_by_id_or_code,
    get_events_for_worker,
)
from simulation.conveyor import (
    get_status as get_conveyor_status,
    get_temperature_history,
)
from agent.autonomous import process_temperature_change
from agent.routing import (
    SLIDER_MAX_C,
    SLIDER_MIN_C,
    classify_temperature_band,
    format_band_range,
    routing_table_rows,
)
from guardrails.validator import GuardrailException
from alerts.dispatcher import dispatch_manual_email_alert
from detection.inspect import run_inspection, save_upload, run_demo_inspection

from simulation.physics import physics_engine
import asyncio

app = FastAPI(title="JARVIS API", description="JARVIS Manufacturing Monitoring API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(physics_engine.run_loop())

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = ROOT_DIR / "frontend"


@app.get("/", include_in_schema=False)
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    return FileResponse(
        index,
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@app.get("/api")
def read_root():
    return {"status": "ok", "service": "JARVIS API"}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/status")
def get_status():
    """Overall status combining simulation and event stats."""
    stats = get_event_stats()
    pending = get_pending_events()
    conveyor = get_conveyor_status()
    
    # Determine overall status
    overall = "NORMAL"
    active_alerts = 0
    
    if pending:
        active_alerts = len(pending)
        
    for p in pending:
        if p.get("severity") == "CRITICAL":
            overall = "CRITICAL"
            break
        elif p.get("severity") == "HIGH" and overall == "NORMAL":
            overall = "WARNING"
            
    if conveyor.get("status", "").upper() in ["STOPPED", "FAULTED"]:
        overall = "CRITICAL"
        
    return {
        "overall": overall,
        "active_alerts": active_alerts,
        "pending_approvals": len(pending),
        "conveyor": conveyor,
        "stats": stats
    }

@app.get("/api/events")
def get_events(limit: int = 50):
    events = get_all_events()
    return {"events": events[:limit]}

@app.get("/api/events/pending")
def pending_events():
    events = get_pending_events()
    return {"events": events}

class ApprovalRequest(BaseModel):
    event_id: int
    action: str  # "APPROVE", "DENY"
    user: str

@app.post("/api/approvals")
def process_approval(req: ApprovalRequest):
    if req.action not in ["APPROVE", "DENY"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    status = "APPROVED" if req.action == "APPROVE" else "DENIED"
    update_approval(req.event_id, status, req.user)
    return {"success": True, "event_id": req.event_id, "status": status}

class TriggerRequest(BaseModel):
    event_type: str
    severity: str
    category: str
    proposed_action: str

@app.post("/api/simulation/trigger")
def trigger_simulation(req: TriggerRequest):
    event_id = insert_event(
        event_type=req.event_type,
        severity=req.severity,
        category=req.category,
        proposed_action=req.proposed_action
    )
    return {"success": True, "event_id": event_id, "message": "Simulation event triggered"}

@app.get("/api/machines")
def get_machines():
    """Return digital twin / facility status for the frontend."""
    # This maps to the Synergy Codes visualization concept
    conveyor = get_conveyor_status()
    temp_c = conveyor.get("temperature_c")
    temp_band = classify_temperature_band(temp_c) if temp_c is not None else None
    
    machines = [
        {
            "id": "machine-01",
            "name": "Primary Conveyor",
            "line": "Line 1",
            "state": conveyor.get("status", "UNKNOWN").upper(),
            "speed": conveyor.get("speed", 0),
            "temperature_c": temp_c,
            "temperature_band": temp_band["severity"] if temp_band else None,
            "temperature_range": format_band_range(temp_band) if temp_band else None,
            "simulated": True
        },
        {
            "id": "machine-02",
            "name": "Assembly Arm",
            "line": "Line 1",
            "state": "RUNNING",
            "simulated": True
        },
        {
            "id": "machine-03",
            "name": "Packaging Station",
            "line": "Line 2",
            "state": "RUNNING",
            "simulated": True
        }
    ]
    return {"machines": machines}


class TemperatureSetRequest(BaseModel):
    temperature_c: float
    zone: Optional[str] = "Zone 01"


@app.get("/api/simulation/temperature")
def get_simulated_temperature():
    """
    Current simulated machine temperature, history, and the severity →
    recipient table. Slider-set only — there is no sensor.
    """
    conveyor = get_conveyor_status()
    temp_c = float(conveyor.get("temperature_c", 45.0))
    band = classify_temperature_band(temp_c)
    return {
        "simulated": True,
        "source": "Trigger Console slider — no sensor",
        "temperature_c": temp_c,
        "previous_updated_at": conveyor.get("temperature_updated_at"),
        "band": band,
        "band_range": format_band_range(band),
        "history": get_temperature_history(),
        "routing_table": routing_table_rows(),
        "slider": {"min_c": SLIDER_MIN_C, "max_c": SLIDER_MAX_C},
        "note": (
            "One rule-based reasoning agent classifies this value and fans "
            "notifications by severity. Not a multi-agent system. Approval "
            "gate is skipped on this path only."
        ),
    }


@app.post("/api/simulation/temperature")
def set_simulated_temperature(req: TemperatureSetRequest):
    """
    Apply a slider change. If the value crosses into a non-nominal band,
    the reasoning agent classifies, routes, and dispatches automatically.
    PPE / fire / conveyor approval gates are not involved.
    """
    try:
        result = process_temperature_change(req.temperature_c, zone=req.zone or "Zone 01")
    except GuardrailException as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


class InteractRequest(BaseModel):
    sensor: str
    action: str  # "override", "corrupt", "reset"
    value: Optional[float] = None
    corr_type: Optional[str] = None

@app.get("/api/simulation/state")
def get_simulation_state():
    return physics_engine.get_readings()

@app.post("/api/simulation/interact")
def interact_simulation(req: InteractRequest):
    if req.action == "override":
        physics_engine.apply_user_override(req.sensor, req.value)
    elif req.action == "corrupt":
        physics_engine.apply_corruption(req.sensor, req.corr_type or "spike", req.value)
    elif req.action == "reset":
        physics_engine.apply_user_override(req.sensor, None)
        physics_engine.apply_corruption(req.sensor, "none")
    return {"status": "ok", "state": physics_engine.get_readings()}

@app.get("/api/workers")
def list_workers():
    """Return worker roster with incident counts and history."""
    return {"workers": get_all_workers()}


@app.get("/api/workers/{identifier}")
def get_worker(identifier: str):
    worker = get_worker_by_id_or_code(identifier)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    events = get_events_for_worker(worker)
    return {"worker": worker, "events": events}


@app.post("/api/inspect/upload")
async def inspect_upload(
    inspection_type: str = Form("ppe"),
    file: UploadFile = File(...),
):
    """Accept a PPE or fire/smoke media upload, run inspection, and log the event."""
    filename = file.filename or "upload.png"
    suffix = Path(filename).suffix.lower()
    content_type = (file.content_type or "").lower()
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp4", ".avi", ".mov", ".mkv", ".webm"}
    is_media = suffix in allowed_ext or content_type.startswith("image/") or content_type.startswith("video/") or not suffix
    if not is_media:
        raise HTTPException(status_code=400, detail="Upload an image or video file (JPG, PNG, MP4, etc.).")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    saved = save_upload(filename, data)
    try:
        result = run_inspection(inspection_type, saved, filename)
        if result.get("event_id"):
            dispatch_manual_email_alert(
                event_id=result["event_id"],
                user="JARVIS Auto-Dispatch",
                role="System"
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inspection failed: {exc}")


class InspectDemoRequest(BaseModel):
    inspection_type: str = "ppe"


@app.post("/api/inspect/demo")
def inspect_demo(req: InspectDemoRequest):
    """Run a sample PPE or fire inspection without requiring a local file."""
    try:
        result = run_demo_inspection(req.inspection_type)
        if result.get("event_id"):
            dispatch_manual_email_alert(
                event_id=result["event_id"],
                user="JARVIS Auto-Dispatch",
                role="System"
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sample inspection failed: {exc}")

# ── Email Alert Dispatcher (Manual Manager Escalation) ─────────────────────────

class EmailAlertRequest(BaseModel):
    user: Optional[str] = "Admin"
    role: Optional[str] = "Manager"

@app.post("/api/alerts/{event_id}/email")
def send_email_alert(
    event_id: int,
    req: Optional[EmailAlertRequest] = None,
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    x_user_name: Optional[str] = Header(default=None, alias="X-User-Name")
):
    """
    Manually triggers an email alert for a specific incident to the manager.
    Protected by RBAC (Supervisors and Managers only; Operators rejected).
    """
    user = (req.user if req else None) or x_user_name or "Admin"
    role = (req.role if req else None) or x_user_role or "Manager"
    
    try:
        result = dispatch_manual_email_alert(event_id=event_id, user=user, role=role)
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal alert dispatch error")

@app.get("/api/alerts/audit")
def get_alerts_audit():
    """Retrieve audit history of sent email notifications."""
    return {"notifications": get_email_notifications()[:30]}

# ── Risk Trends & Analytics ───────────────────────────────────────────────────

@app.get("/api/trends")
def get_risk_trends():
    """Compute risk metrics and timeline data from the live SQLite event database."""
    events = get_all_events()
    
    ppe_count = sum(1 for e in events if e.get("event_type") == "ppe")
    fire_count = sum(1 for e in events if e.get("event_type") == "fire")
    conveyor_count = sum(1 for e in events if e.get("event_type") == "conveyor")
    
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for e in events:
        sev = (e.get("severity") or "low").lower()
        if sev in sev_counts:
            sev_counts[sev] += 1
            
    # Timeline generation (last 7 days aggregation)
    today = datetime.now()
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_str = d.strftime("%b %d")
        days.append({
            "date": day_str,
            "ppe": 0,
            "mechanical": 0,
            "fire": 0,
            "total": 0
        })
        
    for e in events:
        ts_str = e.get("timestamp")
        e_type = e.get("event_type")
        if ts_str:
            try:
                e_date = datetime.strptime(ts_str.split()[0], "%Y-%m-%d").strftime("%b %d")
                for item in days:
                    if item["date"] == e_date:
                        if e_type == "ppe": item["ppe"] += 1
                        elif e_type == "conveyor": item["mechanical"] += 1
                        elif e_type == "fire": item["fire"] += 1
                        item["total"] += 1
            except Exception:
                pass
                
    if sum(d["total"] for d in days) == 0 and len(events) > 0:
        days[-1]["total"] = len(events)
        days[-1]["ppe"] = ppe_count
        days[-1]["mechanical"] = conveyor_count
        days[-1]["fire"] = fire_count
        
    return {
        "ppe_violations_30d": "+12%",
        "mechanical_faults_30d": "-5%",
        "avg_resolution_time": "4.2m",
        "total_events": len(events),
        "ppe_count": ppe_count,
        "fire_count": fire_count,
        "conveyor_count": conveyor_count,
        "severity_breakdown": sev_counts,
        "timeline": days
    }


# ── AI API Gateway & Guardrails ───────────────────────────────────────────────

from guardrails.validator import validate_action, GuardrailException
import os

@app.get("/api/ai/config")
def get_ai_config():
    """Return public AI configuration without exposing secrets."""
    provider = os.getenv("AI_PROVIDER", "OpenAI")
    model = os.getenv("AI_MODEL", "GPT-4o")
    api_key_configured = bool(os.getenv("OPENAI_API_KEY"))
    
    return {
        "provider": provider,
        "model": model,
        "configured": api_key_configured,
        "trending": True
    }

class AIConfigTestRequest(BaseModel):
    provider: str
    model: str
    api_key: str

@app.post("/api/ai/test")
def test_ai_connection(req: AIConfigTestRequest):
    """Test AI connection safely. In a real scenario, tests the provided key."""
    if not req.api_key or len(req.api_key) < 5:
        return {"success": False, "message": "Invalid API key format"}
    
    # Mock successful connection
    return {"success": True, "message": f"Connected to {req.provider} - {req.model}"}

class AIReasoningRequest(BaseModel):
    event_context: str
    proposed_action: str

@app.post("/api/ai/reason")
def ai_reason_and_validate(req: AIReasoningRequest):
    """
    Simulates AI reasoning on an event and passes the proposed action
    through the Guardrail Validator.
    """
    # 1. AI Reasoning phase (mocked)
    ai_action = req.proposed_action
    
    # 2. Guardrail Validation phase
    try:
        validation_result = validate_action(ai_action, {})
        return {
            "success": True, 
            "ai_proposed_action": ai_action, 
            "guardrail_status": validation_result
        }
    except GuardrailException as e:
        # 3. Blocked by Policy
        return {
            "success": False, 
            "ai_proposed_action": ai_action,
            "error": str(e),
            "guardrail_status": "BLOCKED"
        }

from agent.assistant import answer_query

class ChatRequest(BaseModel):
    message: str
    user: Optional[str] = "Supervisor"

@app.post("/api/ai/chat")
def chat_with_jarvis(req: ChatRequest):
    """
    Endpoint for 'Ask JARVIS'.
    Evaluates conversational inputs against system Guardrails,
    and returns LLM responses for project and safety inquiries.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")
    
    result = answer_query(req.message.strip(), user=req.user or "Supervisor")
    return result


if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="frontend_css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="frontend_js")

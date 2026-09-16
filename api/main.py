from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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
    update_approval,
)
from simulation.conveyor import get_status as get_conveyor_status

app = FastAPI(title="JARVIS API", description="JARVIS Manufacturing Monitoring API", version="1.0.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "JARVIS API"}

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
            
    if conveyor.get("state") == "STOPPED":
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

@app.get("/api/machines")
def get_machines():
    """Return digital twin / facility status for the frontend."""
    # This maps to the Synergy Codes visualization concept
    conveyor = get_conveyor_status()
    
    machines = [
        {
            "id": "machine-01",
            "name": "Primary Conveyor",
            "line": "Line 1",
            "state": conveyor.get("state", "UNKNOWN"),
            "speed": conveyor.get("speed", 0),
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

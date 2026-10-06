"""
agent/reasoner.py
Minimal rule-based reasoning agent for JARVIS.

Takes a detection event, returns severity + category + proposed action.
This is the rule-engine version; LLM-assisted reasoning is planned for Phase 8.
"""

from typing import Dict, Any, List, Optional

from agent.routing import (
    classify_temperature_band,
    format_band_range,
    recipients_for_severity,
    severity_for_temperature,
    severity_rank,
)


def classify_event(event_type: str, detections: Optional[List[Dict]] = None, source_file: str = "", extra_data: Optional[Dict] = None) -> Dict[str, str]:
    """
    Rule-based event classification.
    
    Args:
        event_type: "ppe", "fire", "conveyor", or "temperature"
        detections: list of detection dicts from PPEDetector or FireSmokeDetector
        source_file: filename or identifier that triggered the detection
        extra_data: optional dictionary containing additional context
                    (e.g., fault_type / commanded flag for conveyor;
                     temperature_c / previous_c / zone for temperature)
    
    Returns:
        dict with keys: severity, category, proposed_action, reasoning
        (the "temperature" branch adds routing fields — see _classify_temperature)
    """
    detections = detections or []
    extra_data = extra_data or {}

    if event_type == "fire":
        return _classify_fire(detections)
    elif event_type == "ppe":
        return _classify_ppe(detections)
    elif event_type == "temperature":
        return _classify_temperature(extra_data)
    elif event_type == "conveyor":
        status = extra_data.get("status", "faulted")
        commanded = extra_data.get("commanded", False)
        fault_type = extra_data.get("fault_type", "mechanical_jam")
        res = classify_conveyor_event(status=status, commanded=commanded, fault_type=fault_type)
        if res:
            return res
        return {
            "severity": "low",
            "category": "mechanical",
            "proposed_action": "Commanded status change — no action required.",
            "reasoning": "Conveyor status change was user-commanded."
        }
    else:
        return {
            "severity": "low",
            "category": "technical",
            "proposed_action": "Log event for review.",
            "reasoning": f"Unknown event type '{event_type}'. Logged for manual review."
        }


def classify_conveyor_event(status: str, commanded: bool, fault_type: str = "mechanical_jam") -> Optional[Dict[str, str]]:
    """
    Classify conveyor state changes.
    Returns None if commanded (not an incident requiring approval), or dict with action proposal if unplanned fault.
    """
    if commanded:
        # Not an incident - don't even log it as an event needing approval
        return None

    if status == "faulted":
        return {
            "severity": "high",
            "category": "mechanical",
            "proposed_action": (
                f"Flag conveyor for maintenance inspection (Fault: {fault_type}). "
                "Halt dependent downstream processes and dispatch technician."
            ),
            "reasoning": (
                f"Conveyor stopped without a commanded action (unplanned fault: '{fault_type}') — "
                "classified as unplanned mechanical fault requiring supervisor authorization."
            ),
        }
    return None


def _classify_temperature(extra_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a simulated temperature reading against the bands in agent/routing.py.

    This is the reasoning step of the autonomous temperature path. Unlike the
    PPE / fire / conveyor branches, its output is NOT queued for approval — the
    caller (agent/autonomous.py) dispatches the notifications directly. This
    function only decides; it does not send anything or write to the database.

    extra_data keys:
        temperature_c : float  — current simulated value (required)
        previous_c    : float  — value before this change (optional)
        zone          : str    — label for the machine's zone (optional)

    Returns the usual {severity, category, proposed_action, reasoning} plus:
        recipient_roles   : list of {role, label, env_var} from the routing table
        band              : the matched band dict
        previous_severity : band of previous_c ('nominal' if unknown)
        transition        : "none" | "onset" | "escalation" | "de-escalation" | "recovery"

    severity == "nominal" means "inside normal range, no event should be logged".
    """
    if "temperature_c" not in extra_data:
        raise ValueError("temperature classification requires extra_data['temperature_c']")

    temp_c = float(extra_data["temperature_c"])
    previous_c = extra_data.get("previous_c")
    zone = extra_data.get("zone") or "Zone 01"

    band = classify_temperature_band(temp_c)
    severity = band["severity"]
    previous_severity = (
        severity_for_temperature(previous_c) if previous_c is not None else "nominal"
    )

    # Describe the band change so the audit trail states *why* this fired now.
    if severity == previous_severity:
        transition = "none"
    elif severity == "nominal":
        transition = "recovery"
    elif previous_severity == "nominal":
        transition = "onset"
    elif severity_rank(severity) > severity_rank(previous_severity):
        transition = "escalation"
    else:
        transition = "de-escalation"

    prev_text = f"{float(previous_c):.1f} °C ('{previous_severity}')" if previous_c is not None else "unknown"
    band_range = format_band_range(band)

    if severity == "nominal":
        return {
            "severity": "nominal",
            "category": "mechanical",
            "proposed_action": "No action. Simulated temperature is within the normal operating range.",
            "reasoning": (
                f"Simulated temperature {temp_c:.1f} °C is in the nominal band ({band_range}); "
                f"previous reading {prev_text}. No notification is routed for 'nominal'."
            ),
            "recipient_roles": [],
            "band": band,
            "previous_severity": previous_severity,
            "transition": transition,
        }

    recipient_roles = recipients_for_severity(severity)
    labels = [r["label"] for r in recipient_roles]

    proposed_action = (
        f"Automatically notify {', '.join(labels)} of a {severity.upper()} temperature reading "
        f"on Processing Machine 01 ({zone}): {temp_c:.1f} °C (simulated). "
        "Dispatched by the rule-based reasoning agent under the temperature escalation policy — "
        "no human approval step on this path."
    )
    reasoning = (
        f"Simulated temperature {temp_c:.1f} °C falls in the '{severity}' band ({band_range}); "
        f"previous reading {prev_text}; transition = {transition}. "
        f"Routing table (agent/routing.py) maps '{severity}' -> {labels}. "
        f"Band note: {band['description']}"
    )

    return {
        "severity": severity,
        "category": "mechanical",
        "proposed_action": proposed_action,
        "reasoning": reasoning,
        "recipient_roles": recipient_roles,
        "band": band,
        "previous_severity": previous_severity,
        "transition": transition,
    }


def _classify_fire(detections: List[Dict]) -> Dict[str, str]:
    """Fire/smoke events are always high or critical severity."""
    
    has_fire = any(d["label"] == "fire" for d in detections)
    has_smoke = any(d["label"] == "smoke" for d in detections)
    max_conf = max((d["confidence"] for d in detections if d["label"] in ("fire", "smoke")), default=0)

    if has_fire and has_smoke:
        return {
            "severity": "critical",
            "category": "safety",
            "proposed_action": "EMERGENCY: Activate fire alarm. Evacuate zone immediately. Notify fire safety officer and all supervisors.",
            "reasoning": f"Both fire AND smoke detected (max confidence: {max_conf:.1%}). This is a critical safety emergency requiring immediate evacuation."
        }
    elif has_fire:
        severity = "critical" if max_conf >= 0.6 else "high"
        return {
            "severity": severity,
            "category": "safety",
            "proposed_action": "Alert fire safety officer. Prepare zone for possible evacuation. Dispatch inspection to source location.",
            "reasoning": f"Fire detected (confidence: {max_conf:.1%}). Active fire hazard requires immediate response."
        }
    elif has_smoke:
        return {
            "severity": "high",
            "category": "safety",
            "proposed_action": "Dispatch inspection to verify smoke source. Alert supervisor. Prepare fire response if confirmed.",
            "reasoning": f"Smoke detected without visible fire (confidence: {max_conf:.1%}). Could indicate smoldering hazard or early-stage fire."
        }
    else:
        return {
            "severity": "low",
            "category": "safety",
            "proposed_action": "Log for review. No active fire or smoke hazard detected.",
            "reasoning": "Fire/smoke model ran but detected no fire or smoke hazards."
        }


def _classify_ppe(detections: List[Dict]) -> Dict[str, str]:
    """PPE violations are medium severity by default; multiple violations escalate."""

    VIOLATION_CLASSES = {"no_helmet", "no_goggle", "no_gloves", "no_boots", "none"}
    
    violations = [d for d in detections if d["label"] in VIOLATION_CLASSES]
    violation_labels = [v["label"] for v in violations]
    num_violations = len(violations)
    num_persons = sum(1 for d in detections if d["label"] == "Person")

    if num_violations == 0:
        return {
            "severity": "low",
            "category": "safety",
            "proposed_action": "No action required. All detected workers appear PPE-compliant.",
            "reasoning": f"Detected {num_persons} worker(s), all wearing required PPE. No violations found."
        }

    # Severity escalation based on violation count
    if num_violations >= 3:
        severity = "high"
    elif num_violations >= 1:
        severity = "medium"
    else:
        severity = "low"

    # Build specific action based on what's missing
    missing_items = set()
    for label in violation_labels:
        if label == "no_helmet":
            missing_items.add("helmet")
        elif label == "no_goggle":
            missing_items.add("goggles")
        elif label == "no_gloves":
            missing_items.add("gloves")
        elif label == "no_boots":
            missing_items.add("safety boots")
        elif label == "none":
            missing_items.add("safety vest")

    missing_str = ", ".join(sorted(missing_items))

    action = f"Issue warning to worker(s). Missing PPE: {missing_str}. "
    if severity == "high":
        action += "Multiple violations detected — escalate to supervisor for immediate floor intervention."
    else:
        action += "Log violation and notify floor supervisor."

    reasoning = (
        f"Detected {num_persons} worker(s) with {num_violations} PPE violation(s): "
        f"{', '.join(violation_labels)}. "
        f"Severity set to '{severity}' based on violation count."
    )

    return {
        "severity": severity,
        "category": "safety",
        "proposed_action": action,
        "reasoning": reasoning,
    }

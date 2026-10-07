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
    elif event_type == "simulation":
        return _classify_simulation(extra_data)
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


def _classify_simulation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multivariate fault classifier for the 12 simulated faults.
    Returns the diagnosis based on the reported sensor readings.
    """
    t_motor = state.get("t_motor", 40.0)
    c_flow = state.get("c_flow", 100.0)
    vib = state.get("vib", 1.0)
    vib_pat = state.get("vib_pat", "nominal")
    trq = state.get("trq", 50.0)
    spd_m = state.get("spd_m", 1500.0)
    spd_b = state.get("spd_b", 1500.0)
    cur = state.get("cur", 10.0)
    vol = state.get("vol", 400.0)
    cur_leak = state.get("cur_leak", 2.0)

    # Helper to format return
    def mk_diag(fault: str, cat: str, root_cause: str, sev: str, evidence: str, action: str):
        return {
            "fault": fault, "category": cat, "root_cause": root_cause, 
            "severity": sev, "evidence": evidence, "proposed_action": action
        }

    # -- CHECK 1: LYING SENSORS (Dropout, Freeze, Drift) --
    
    # 12. Signal Dropout / Noise
    if t_motor == 0.0 or vol == 0.0 or cur == 0.0 or spd_m == 0.0:
        # If speed is 0 but torque and current are normal/high, it's a dropout, not a jam (jam has low but nonzero speed)
        return mk_diag(
            "Signal Dropout", "technical", "Technical", "high",
            f"Sensor reports exactly 0.0 while related electrical/load sensors (cur={cur:.1f}, trq={trq:.1f}) suggest machine is live.",
            "Recalibrate/Restart Sensor Module"
        )
        
    # 11. Sensor Drift / Freeze
    # Drift: reading diverged in one step while others stayed flat. We detect this by extreme values with zero secondary effects.
    # For example, T_motor is super high but current and coolant are normal.
    if t_motor >= 100.0 and cur < 15.0 and c_flow >= 80.0 and trq < 60.0:
        return mk_diag(
            "Sensor Drift", "technical", "Technical", "high",
            f"Temperature reports {t_motor:.1f} °C, but Current ({cur:.1f}A) and Coolant ({c_flow:.1f}%) are normal. Real overheating shows secondary effects.",
            "Recalibrate Temperature Sensor"
        )

    # -- CHECK 2: REAL MACHINE FAULTS --

    # 10. Insulation Breakdown
    if cur_leak > 30.0:
        return mk_diag(
            "Insulation Breakdown", "electrical", "Environmental", "critical",
            f"Leakage current is dangerously high ({cur_leak:.1f} mA).",
            "Emergency Stop. Re-insulate windings."
        )

    # 9. Voltage Fluctuation
    if vol < 360.0 or vol > 440.0:
        return mk_diag(
            "Voltage Fluctuation", "electrical", "Environmental", "high",
            f"Supply voltage ({vol:.1f} V) deviated >10% from 400V.",
            "Switch to backup power or condition line voltage."
        )

    # 5. Mechanical Jam
    if trq > 120.0 and cur > 30.0 and spd_m > 0.0 and spd_m < 1200.0:
        return mk_diag(
            "Mechanical Jam", "mechanical", "Mechanical", "critical",
            f"Torque spike ({trq:.1f} Nm) + current spike ({cur:.1f} A) + speed drop ({spd_m:.1f} RPM).",
            "Emergency Stop. Clear physical obstruction."
        )

    # 8. Motor Overload
    if cur > 25.0 and trq > 80.0 and spd_m >= 1200.0:
        return mk_diag(
            "Motor Overload", "mechanical", "Human/Manual", "high",
            f"Current ({cur:.1f} A) and Torque ({trq:.1f} Nm) elevated without a jam.",
            "Reduce throughput/load on the conveyor."
        )

    # 7. Belt Slippage
    if spd_b < (spd_m * 0.9):
        return mk_diag(
            "Belt Slippage", "mechanical", "Mechanical", "medium",
            f"Belt speed ({spd_b:.1f} RPM) lags motor speed ({spd_m:.1f} RPM) by >10%.",
            "Re-tension or replace the drive belt."
        )

    # Disambiguation: 3. Bearing Wear vs 6. Lubrication Failure
    # Rule: Vibration pattern (harmonic) + severity determines bearing wear.
    if vib > 4.0 and vib_pat == "harmonic":
        return mk_diag(
            "Bearing Wear", "mechanical", "Mechanical", "high",
            f"Vibration High ({vib:.1f} mm/s) with harmonic pattern.",
            "Schedule part swap (bearings)."
        )
        
    if vib > 2.5 and t_motor > 45.0 and trq > 55.0:
        return mk_diag(
            "Lubrication Failure", "mechanical", "Human/Manual", "medium",
            f"Vibration elevated ({vib:.1f} mm/s) with friction heat creep ({t_motor:.1f} °C) and slight torque drag.",
            "Re-lubricate moving parts."
        )

    # 4. Shaft Misalignment
    if vib > 4.0 and vib_pat == "random":
        return mk_diag(
            "Shaft Misalignment", "mechanical", "Mechanical", "high",
            f"Vibration High ({vib:.1f} mm/s) with random pattern.",
            "Halt line and realign the drive shaft."
        )

    # 2. Cooling Failure vs 1. Motor Overheating
    # If coolant is explicitly low, it's cooling failure.
    if t_motor > 85.0:
        if c_flow < 50.0:
            return mk_diag(
                "Cooling Failure", "mechanical", "Mechanical", "critical" if t_motor > 100.0 else "high",
                f"Temp high ({t_motor:.1f} °C) due to low coolant flow ({c_flow:.1f}%).",
                "Cooling Override or check fans."
            )
        else:
            return mk_diag(
                "Motor Overheating", "mechanical", "Mechanical", "critical" if t_motor > 100.0 else "high",
                f"Temp high ({t_motor:.1f} °C) despite normal coolant. Ramping from secondary effects.",
                "Halt motor immediately to prevent damage."
            )

    return mk_diag(
        "Nominal", "none", "Unknown", "nominal",
        "All sensors read within nominal bounds.",
        "No action required."
    )

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

"""
agent/autonomous.py
Autonomous temperature-escalation path.

What this is
------------
ONE rule-based reasoning agent acting without a human approval step, on THIS
path only. When the simulated machine temperature crosses into a severity band
it:

    observe   simulation/conveyor.set_temperature()      (slider value, no sensor)
    policy    guardrails/validator.validate_action()     ('incident_creation', 'notifications')
    classify  agent/reasoner.classify_event('temperature')  bands from agent/routing.py
    route     agent/routing.resolve_recipient_addresses()   severity -> roles -> .env addresses
    dispatch  alerts/email.send_email_via_smtp()         one email per recipient
    record    database/db.insert_event()                 approval_status = 'auto_dispatched'
              database/db.log_email_notification()      one audit row per recipient

Every step lands in the same SQLite tables as PPE / fire / conveyor events, so
the reasoning trail is inspectable in the dashboard and the CSV export — this
is not a separate or silent code path.

What this is NOT
----------------
* Not a multi-agent system. There is one agent; it fans notifications out to
  several roles. Do not describe it otherwise.
* Not applied to PPE, fire/smoke, or conveyor-fault events. Those still land in
  the approval queue exactly as before (detection/pipeline.py is unchanged).
* Not a bypass of the guardrails layer. The path only skips approval because
  guardrails/config.yaml marks 'notifications' and 'incident_creation' as
  'allowed'. If either is changed to 'approval_required', this module records
  the event as 'pending' and sends nothing; if 'prohibited', it raises.

Firing rule
-----------
An event fires when the new reading is in a non-nominal band AND that band is
different from the previous reading's band ("crosses into a band"). Moving
within a band does not re-fire. Returning to nominal is recorded in the
simulation state but does not create an event (see recommendations in the
project notes for a 'recovery' event).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from simulation.conveyor import set_temperature
from agent.reasoner import classify_event
from agent.routing import format_band_range, resolve_recipient_addresses
from guardrails.validator import validate_action  # raises GuardrailException if prohibited
from database.db import insert_event, get_event_by_id, log_email_notification
from alerts.email import send_email_via_smtp, AUTO_DISPATCHED_STATUS


# Identity written into events.approved_by and email_notifications.sent_by so
# the audit trail shows a policy — not a person — authorised the dispatch.
AUTONOMOUS_ACTOR = "autonomous: temperature_policy"

# Guardrail action types this path needs permission for (see guardrails/config.yaml).
REQUIRED_POLICY_ACTIONS = ("incident_creation", "notifications")

DEFAULT_ZONE = "Zone 01"
MACHINE_LABEL = "Processing Machine 01"


def process_temperature_change(new_temperature_c: float, zone: str = DEFAULT_ZONE) -> Dict[str, Any]:
    """
    Apply a slider change to the simulated machine and run the autonomous
    response if the reading crossed into a severity band.

    Always returns a result dict; check result["fired"] to see whether an event
    was created. Raises guardrails.validator.GuardrailException if policy marks
    a required action as prohibited.
    """
    change = set_temperature(new_temperature_c)
    previous_c, current_c = change["previous_c"], change["current_c"]

    decision = classify_event(
        "temperature",
        extra_data={"temperature_c": current_c, "previous_c": previous_c, "zone": zone},
    )

    result: Dict[str, Any] = {
        "fired": False,
        "gated": False,
        "event_id": None,
        "temperature_c": current_c,
        "previous_c": previous_c,
        "severity": decision["severity"],
        "transition": decision["transition"],
        "recipients": [],
        "sent": 0,
        "failed": 0,
        "decision": decision,
        "guardrails": {},
    }

    if not change["changed"]:
        return result
    if decision["severity"] == "nominal":
        return result

    return _respond(decision, current_c, previous_c, zone, result)


def _respond(decision: Dict[str, Any], current_c: float, previous_c: float,
             zone: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Policy check -> record event -> dispatch per recipient -> record outcomes."""
    severity = decision["severity"]
    band = decision["band"]

    # 1. Policy check. validate_action() raises GuardrailException when prohibited.
    guardrails: Dict[str, Dict[str, Any]] = {}
    for action_type in REQUIRED_POLICY_ACTIONS:
        verdict = validate_action(action_type, {"event_type": "temperature", "severity": severity})
        guardrails[action_type] = {
            "policy_applied": verdict["policy_applied"],
            "requires_approval": verdict["requires_approval"],
        }
    requires_approval = any(g["requires_approval"] for g in guardrails.values())
    result["guardrails"] = guardrails

    # 2. Resolve recipients (addresses come from .env; None if unset).
    recipients = resolve_recipient_addresses(severity)

    # 3. Build the audit payload. Both dicts carry 'label'/'confidence' so the
    #    existing Audit Reports renderer (which expects detection-like items)
    #    prints them without special-casing. detections_json is covered by the
    #    SHA-256 hash chain, so this decision record is tamper-evident.
    observation = {
        "label": "temperature_sample",
        "confidence": 1.0,
        "temperature_c": current_c,
        "previous_c": previous_c,
        "band": severity,
        "band_range": format_band_range(band),
        "zone": zone,
        "source": "simulated (dashboard slider) - no sensor",
    }
    decision_record = {
        "label": "autonomous_decision",
        "confidence": 1.0,
        "policy": "temperature_escalation",
        "agent": "single rule-based reasoning agent (agent/reasoner.py + agent/routing.py)",
        "transition": decision["transition"],
        "previous_severity": decision["previous_severity"],
        "recipient_roles": [
            {"role": r["role"], "label": r["label"], "env_var": r["env_var"],
             "configured": r["email"] is not None}
            for r in recipients
        ],
        "guardrails": guardrails,
        "approval_gate": (
            "pending - guardrails policy requires approval for this action"
            if requires_approval
            else "none - 'notifications' and 'incident_creation' are 'allowed' in guardrails/config.yaml"
        ),
        "reasoning": decision["reasoning"],
    }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source = f"{MACHINE_LABEL} / {zone} (simulated temperature)"

    # 4. Record the event. Gated path if policy demands approval.
    if requires_approval:
        event_id = insert_event(
            event_type="temperature",
            source_file=source,
            detections=[observation, decision_record],
            severity=severity,
            category=decision["category"],
            proposed_action=decision["proposed_action"],
            approval_status="pending",
        )
        result.update({"fired": True, "gated": True, "event_id": event_id})
        return result

    event_id = insert_event(
        event_type="temperature",
        source_file=source,
        detections=[observation, decision_record],
        severity=severity,
        category=decision["category"],
        proposed_action=decision["proposed_action"],
        approval_status=AUTO_DISPATCHED_STATUS,
        approved_by=AUTONOMOUS_ACTOR,
        resolved_at=now,
    )
    result.update({"fired": True, "event_id": event_id})

    if decision["transition"] == "none":
        return result

    # 5. Dispatch one notification per recipient and record each outcome.
    event = get_event_by_id(event_id) or {}
    dispatch_log: List[Dict[str, Optional[str]]] = []
    for r in recipients:
        if r["email"] is None:
            ok = False
            to_address = f"(unconfigured) {r['env_var']}"
            error = f"No address configured for role '{r['label']}' - set {r['env_var']} in .env"
        else:
            ok, to_address, error = send_email_via_smtp(
                event, recipient=r["email"], recipient_label=r["label"]
            )

        status = "SENT" if ok else "FAILED"
        log_email_notification(
            event_id=event_id,
            recipient=to_address,
            status=status,
            sent_by=f"{AUTONOMOUS_ACTOR} [{r['label']}]",
            error_message=error,
        )
        dispatch_log.append({
            "role": r["role"], "label": r["label"], "email": to_address,
            "status": status, "error": error,
        })

    result["recipients"] = dispatch_log
    result["sent"] = sum(1 for d in dispatch_log if d["status"] == "SENT")
    result["failed"] = len(dispatch_log) - result["sent"]
    return result

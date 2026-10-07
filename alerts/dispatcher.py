"""
alerts/dispatcher.py
Orchestrates alert delivery, enforces RBAC policies, and maintains
tamper-evident audit logging for all notification channels.
"""

from typing import Dict, Any, Optional
from database.db import get_event_by_id, log_email_notification
from .email import send_email_via_smtp, get_smtp_config

# Permitted roles for initiating manager alert dispatches
AUTHORIZED_ALERT_ROLES = {"supervisor", "manager", "admin", "system"}


def check_alert_permission(role: Optional[str]) -> bool:
    """Check if the provided user role is authorized to send manager alerts."""
    if not role:
        return False
    return role.strip().lower() in AUTHORIZED_ALERT_ROLES


def dispatch_manual_email_alert(
    event_id: int,
    user: str = "Admin",
    role: str = "Manager"
) -> Dict[str, Any]:
    """
    Handles a manual 'Send Email Alert' request from the frontend:
    1. Enforces RBAC authorization.
    2. Retrieves the event from SQLite.
    3. Invokes the Gmail SMTP email service.
    4. Records the result to the email_notifications audit table.
    5. Returns a structured response to the API route.
    """
    # 1. RBAC Authorization check
    if not check_alert_permission(role):
        raise PermissionError(
            f"Role '{role}' is not authorized to send email alerts. Only Supervisors and Managers can trigger escalation."
        )

    # 2. Event Lookup & Validation
    event = get_event_by_id(event_id)
    if not event:
        raise LookupError(f"Incident Event #{event_id} does not exist in the database.")

    # 3. Invoke Email Service
    success, recipient, error_message = send_email_via_smtp(event)

    # 4. Audit Logging in SQLite
    status_str = "SENT" if success else "FAILED"
    try:
        log_email_notification(
            event_id=event_id,
            recipient=recipient,
            status=status_str,
            sent_by=f"{user} ({role})",
            error_message=error_message
        )
    except Exception as db_err:
        print(f"[alerts/dispatcher] Warning: Failed to record email audit log: {db_err}")

    # 5. Return structured result
    if success:
        return {
            "success": True,
            "message": "Email alert sent successfully to manager",
            "event_id": event_id,
            "recipient": recipient
        }
    else:
        return {
            "success": False,
            "message": "Unable to send email alert",
            "event_id": event_id,
            "detail": error_message or "Internal SMTP delivery error"
        }


def dispatch_automatic_escalation(event_id: int) -> Dict[str, Any]:
    """
    Invoked when an incident remains unresolved past an escalation threshold.
    Maintains the separation between manual user triggers and automated escalation.
    """
    event = get_event_by_id(event_id)
    if not event:
        return {"success": False, "message": "Event not found"}

    success, recipient, error_message = send_email_via_smtp(event)
    status_str = "SENT" if success else "FAILED"
    
    log_email_notification(
        event_id=event_id,
        recipient=recipient,
        status=status_str,
        sent_by="System (Automated Escalation)",
        error_message=error_message
    )
    
    return {
        "success": success,
        "event_id": event_id,
        "recipient": recipient,
        "escalation_type": "automatic"
    }


"""
alerts/email.py
Gmail SMTP implementation for sending JARVIS incident alerts.
Keeps all SMTP credentials strictly on the server-side.
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

# approval_status value written by agent/autonomous.py for events whose
# notifications were dispatched without a human approval step.
AUTO_DISPATCHED_STATUS = "auto_dispatched"


def _extract_temperature_observation(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Return the 'temperature_sample' payload from the event's detections, if any.
    Accepts either a parsed list (event['detections']) or the raw JSON string
    stored in SQLite (event['detections_json']).
    """
    payload = event.get("detections")
    if payload is None and event.get("detections_json"):
        try:
            payload = json.loads(event["detections_json"])
        except (TypeError, ValueError):
            payload = None
    if not isinstance(payload, list):
        return None
    for item in payload:
        if isinstance(item, dict) and item.get("label") == "temperature_sample":
            return item
    return None


def get_smtp_config() -> Dict[str, Any]:
    """Load and return SMTP configuration from environment variables."""
    host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 587))
    username = os.getenv("SMTP_USERNAME") or os.getenv("ALERT_EMAIL", "")
    password = os.getenv("SMTP_APP_PASSWORD") or os.getenv("SMTP_PASSWORD", "")
    recipient = os.getenv("MANAGER_EMAIL") or os.getenv("ALERT_EMAIL", "")
    
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "recipient": recipient
    }


def generate_email_subject(event: Dict[str, Any]) -> str:
    """Generate a clean, professional subject line based on event attributes."""
    event_type = (event.get("event_type") or "Incident").lower()
    severity = (event.get("severity") or "NORMAL").upper()
    
    if "fire" in event_type:
        return f"JARVIS {severity} ALERT - Fire/Smoke Detected"
    elif "ppe" in event_type:
        return f"JARVIS ALERT - PPE Violation Detected ({severity})"
    elif "temperature" in event_type:
        return f"JARVIS {severity} ALERT - Machine Temperature (simulated) - auto-dispatched"
    elif "conveyor" in event_type or "machine" in event_type:
        return f"JARVIS ALERT - Processing Machine Fault ({severity})"
    else:
        return f"JARVIS ALERT - {event_type.upper()} ({severity})"


def format_email_content(event: Dict[str, Any], recipient_label: Optional[str] = None) -> Tuple[str, str]:
    """
    Constructs plain-text and HTML email bodies from the real event data.
    Does not invent data; uses 'Unknown' or fallback for missing fields.

    recipient_label: optional role name (e.g. "Area supervisor") so a
    multi-recipient dispatch tells each person why they were included.

    The governance footer depends on event['approval_status']:
      * 'auto_dispatched' -> states plainly that no approval step was involved
      * anything else     -> the existing "pending supervisor authorization" text
    """
    event_id = event.get("event_id", "Unknown")
    event_type = event.get("event_type", "Unknown")
    severity = (event.get("severity") or "Unknown").upper()
    timestamp = event.get("timestamp", "Unknown")
    location = event.get("source_file") or "Line 1 (Industrial Floor)"
    action = event.get("proposed_action") or "Immediate manager attention required."
    category = (event.get("category") or "Unknown").capitalize()
    is_auto = (event.get("approval_status") or "").lower() == AUTO_DISPATCHED_STATUS
    temp_obs = _extract_temperature_observation(event)

    # Optional telemetry line (temperature path only). Explicitly simulated.
    telemetry_plain = ""
    telemetry_html = ""
    if temp_obs:
        band_range = temp_obs.get("band_range") or ""
        band = (temp_obs.get("band") or "").upper()
        prev = temp_obs.get("previous_c")
        prev_text = f" (previous: {float(prev):.1f} °C)" if prev is not None else ""
        telemetry_plain = (
            f"Simulated Temperature: {float(temp_obs.get('temperature_c', 0)):.1f} °C{prev_text}\n"
            f"Severity Band: {band} ({band_range})\n"
            f"Source: {temp_obs.get('source', 'simulated')}\n"
        )
        telemetry_html = f"""<tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">Simulated Temperature:</td>
                  <td style="padding: 10px 0; color: #1c1917; font-weight: 600;">{float(temp_obs.get('temperature_c', 0)):.1f} &deg;C{prev_text}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">Severity Band:</td>
                  <td style="padding: 10px 0; color: #1c1917;">{band} ({band_range})</td>
                </tr>"""

    recipient_plain = f"Sent to you as: {recipient_label}\n" if recipient_label else ""
    recipient_html = (
        f"""<tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">Sent to you as:</td>
                  <td style="padding: 10px 0; color: #1c1917;">{recipient_label}</td>
                </tr>"""
        if recipient_label else ""
    )

    if is_auto:
        governance_plain = (
            "Dispatch Mode: AUTOMATIC\n"
            "This notification was sent by the JARVIS rule-based reasoning agent under the "
            "temperature escalation policy (agent/routing.py). There is no human approval step on "
            "this path; the event and this dispatch are recorded in the hash-chained audit log."
        )
        governance_html_title = "Dispatch Mode: Automatic."
        governance_html_body = (
            "This notification was sent by the JARVIS rule-based reasoning agent under the temperature "
            "escalation policy. There is <em>no human approval step</em> on this path. The event and this "
            "dispatch are recorded in the hash-chained audit log."
        )
        intro_html = (
            "A simulated machine-temperature reading crossed a configured severity band. "
            "The reasoning agent classified it and dispatched this notification automatically."
        )
        action_label = "Action Taken"
    else:
        governance_plain = (
            "Human Approval Gate:\n"
            "This operational action is pending supervisor authorization in the JARVIS Live Operations Dashboard."
        )
        governance_html_title = "Governance Note:"
        governance_html_body = (
            "This intervention is held in the <em>Pending Actions</em> queue. Under JARVIS safety policies, "
            "autonomous modifications to plant machinery require human approval before execution."
        )
        intro_html = (
            "An automated safety or equipment event has been captured by the perception pipeline and requires review."
        )
        action_label = "Proposed Action"

    # Root-cause classification is not implemented yet (see agent/reasoner.py);
    # only the legacy paths keep the previous placeholder line.
    root_cause_plain = "" if temp_obs else "Root Cause: Environmental / Operational Telemetry\n"

    # Plain text version
    plain_text = f"""JARVIS ALERT

Severity: {severity}
Event: {event_type.upper()}
Location: {location}
Category: {category}
Time: {timestamp}
{telemetry_plain}{root_cause_plain}{recipient_plain}
{action_label}:
{action}

Event ID:
{event_id}

---
{governance_plain}
"""

    # HTML version with modern Swiss styling
    severity_color = "#d9383a" if severity in ["CRITICAL", "HIGH"] else "#e67e22" if severity == "MEDIUM" else "#1b998b"
    
    html_text = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>JARVIS Alert</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f7f6f2; color: #1c1917;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <table width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
          <!-- Header -->
          <tr>
            <td style="padding: 24px 32px; background-color: #1c1917; color: #ffffff;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <span style="font-size: 20px; font-weight: 700; letter-spacing: 0.08em; color: #ffffff;">JARVIS</span>
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: #a8a29e; margin-left: 8px;">Manufacturing Intelligence</span>
                  </td>
                  <td align="right">
                    <span style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 600; text-transform: uppercase; border-radius: 4px; background-color: {severity_color}; color: #ffffff;">
                      {severity}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 32px;">
              <h2 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #1c1917;">
                Operational Incident Notification
              </h2>
              <p style="margin: 0 0 24px 0; font-size: 14px; color: #78716c; line-height: 1.5;">
                {intro_html}
              </p>

              <!-- Incident Table -->
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; border-top: 1px solid #f5f5f4; border-bottom: 1px solid #f5f5f4; font-size: 13px;">
                <tr>
                  <td style="padding: 10px 0; color: #78716c; width: 140px; font-weight: 500;">Event ID:</td>
                  <td style="padding: 10px 0; font-weight: 600; color: #1c1917;">#{event_id}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">Incident Type:</td>
                  <td style="padding: 10px 0; font-weight: 600; color: #1c1917;">{event_type.upper()}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">Location / Source:</td>
                  <td style="padding: 10px 0; color: #1c1917;">{location}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">Timestamp:</td>
                  <td style="padding: 10px 0; color: #1c1917;">{timestamp}</td>
                </tr>
                {telemetry_html}
                {recipient_html}
                <tr>
                  <td style="padding: 10px 0; color: #78716c; font-weight: 500;">{action_label}:</td>
                  <td style="padding: 10px 0; color: #1c1917; font-weight: 600; background-color: #fafaf9; padding-left: 8px; border-radius: 4px;">{action}</td>
                </tr>
              </table>

              <!-- Notice Box -->
              <div style="background-color: #f5f5f4; border-left: 3px solid #1c1917; padding: 14px 16px; border-radius: 0 4px 4px 0; font-size: 12px; line-height: 1.6; color: #44403c;">
                <strong>{governance_html_title}</strong> {governance_html_body}
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 16px 32px; background-color: #fafaf9; border-top: 1px solid #e7e5e4; font-size: 11px; color: #a8a29e; text-align: center;">
              JARVIS Joint Autonomous Reasoning & Vision Inspection System &bull; Final Year Engineering
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return plain_text, html_text


def send_email_via_smtp(
    event: Dict[str, Any],
    recipient: Optional[str] = None,
    recipient_label: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Sends an incident email via Gmail SMTP using environment variables.

    recipient:       optional explicit "To" address. When omitted, the single
                     MANAGER_EMAIL / ALERT_EMAIL from .env is used (legacy
                     behaviour relied on by alerts/dispatcher.py).
    recipient_label: optional role name shown in the body ("Sent to you as").

    Returns: (success: bool, recipient: str, error_message: Optional[str])
    """
    config = get_smtp_config()
    to_address = (recipient or config["recipient"] or "").strip()

    if not config["username"] or not config["password"] or not to_address:
        err = "SMTP configuration incomplete: missing username, app password, or recipient email."
        print(f"[alerts/email] {err}")
        return False, to_address, err

    subject = generate_email_subject(event)
    plain_text, html_text = format_email_content(event, recipient_label=recipient_label)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"JARVIS Alert System <{config['username']}>"
    msg["To"] = to_address

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_text, "html", "utf-8"))

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=12) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.sendmail(config["username"], [to_address], msg.as_string())
        
        print(f"[alerts/email] Successfully sent email for Event #{event.get('event_id')} to {to_address}")
        return True, to_address, None
    except smtplib.SMTPAuthenticationError as auth_err:
        err_msg = "SMTP Authentication failed. Please verify the Gmail App Password in .env."
        print(f"[alerts/email] Error: {auth_err}")
        return False, to_address, err_msg
    except Exception as exc:
        err_msg = f"Failed to deliver email through SMTP server: {str(exc)}"
        print(f"[alerts/email] Unexpected error: {exc}")
        return False, to_address, err_msg

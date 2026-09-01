"""
simulation/conveyor.py
Simulated conveyor line — no physical hardware. Standing in for a real
motor sensor / PLC signal, per Project Proposal Section 4.

States: "running", "stopped", "faulted"
"stopped" = commanded (user pressed stop) -> not an incident
"faulted" = unplanned -> triggers reasoning agent + approval flow
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "jarvis.db"

# In-memory state for a single simulated line (line_id = 1).
# On real deployment this would come from a PLC/sensor poll instead.
_state = {
    "line_id": 1,
    "status": "running",       # running | stopped | faulted
    "last_updated": datetime.now().isoformat(),
    "last_change_reason": "initial state",
}


def get_status() -> dict:
    """Return current simulated conveyor state."""
    return dict(_state)


def _write_to_db(status: str, reason: str):
    """Persist state change to conveyor_state table."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO conveyor_state (line_id, status, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(line_id) DO UPDATE SET
            status=excluded.status,
            last_updated=excluded.last_updated
        """,
        (_state["line_id"], status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def run():
    """User commands the line to run. No incident."""
    _state["status"] = "running"
    _state["last_updated"] = datetime.now().isoformat()
    _state["last_change_reason"] = "commanded: run"
    _write_to_db("running", "commanded: run")
    return get_status()


def manual_stop():
    """
    User commands the line to stop.
    This is a COMMANDED stop -> not a fault, no agent escalation needed.
    """
    _state["status"] = "stopped"
    _state["last_updated"] = datetime.now().isoformat()
    _state["last_change_reason"] = "commanded: manual stop"
    _write_to_db("stopped", "commanded: manual stop")
    return get_status()


def trigger_fault(fault_type: str = "jam"):
    """
    Simulates an UNPLANNED fault (jam, motor failure, sensor fault, etc.)
    This is what should be logged as an event and passed to the
    reasoning agent, since it was NOT commanded by a user.

    fault_type: short string describing what kind of fault, e.g.
                "jam", "motor_failure", "sensor_error"
    """
    _state["status"] = "faulted"
    _state["last_updated"] = datetime.now().isoformat()
    _state["last_change_reason"] = f"unplanned fault: {fault_type}"
    _write_to_db("faulted", f"unplanned fault: {fault_type}")
    return get_status()


def is_commanded_change() -> bool:
    """
    Used by the reasoning agent (agent/reasoner.py) to check whether the
    current stopped/faulted state was commanded or unplanned.
    Returns True if the last change was user-commanded (run/manual_stop),
    False if it was an unplanned fault.
    """
    return _state["last_change_reason"].startswith("commanded")

"""
simulation/conveyor.py
Simulated conveyor line — no physical hardware. Standing in for a real
motor sensor / PLC signal, per Project Proposal Section 4.

States: "running", "stopped", "faulted"
"stopped" = commanded (user pressed stop) -> not an incident
"faulted" = unplanned -> triggers reasoning agent + approval flow

Temperature: a second, independent dimension of the simulated machine state.
There is NO temperature sensor. The value is whatever the operator sets it to
via the Trigger Console slider (frontend, FastAPI). It exists so
the autonomous temperature-escalation path (agent/autonomous.py) has something
to observe. Do not describe it anywhere as a sensor reading.

Fault taxonomy: six typed faults, each setting distinct state variables so the
reasoning chain (agent/reasoner.py) can produce different classification
outcomes without any real hardware changes.
"""

import sqlite3
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import List, Dict

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "jarvis.db"

# Starting value for the simulated temperature. This is a placeholder chosen
# so the machine starts inside the "nominal" band defined in agent/routing.py;
# it is not derived from any real equipment specification.
NOMINAL_TEMPERATURE_C = 45.0

# Upper bound on how many slider changes we keep for the dashboard chart.
TEMPERATURE_HISTORY_MAX = 500

# ── Fault Catalogue (Phase A expansion) ─────────────────────────────────────
#
# Each fault type sets distinct simulated state variables so that the reasoning
# chain in agent/reasoner.py can produce a different classification outcome per
# fault. THESE ARE SIMULATION LABELS — no hardware is connected.
#
# Keys:
#   vibration_level  float 0–100  (nominal = 5)
#   motor_current_a  float        (nominal = 8 A)
#   severity         hint for the reasoner (does not bypass guardrails)
#   category         mechanical | electrical | sensor
#   description      one-line description for the dashboard

FAULT_CATALOGUE: dict = {
    "mechanical_jam": {
        "vibration_level": 85.0,
        "motor_current_a": 0.5,       # current drops when shaft jams
        "severity": "high",
        "category": "mechanical",
        "description": "Conveyor belt jammed — material obstruction detected (simulated).",
    },
    "motor_failure": {
        "vibration_level": 60.0,
        "motor_current_a": 22.0,      # spike before trip
        "severity": "high",
        "category": "electrical",
        "description": "Motor drive overload — winding fault (simulated).",
    },
    "sensor_drift": {
        "vibration_level": 8.0,       # mild, sensor issue not mechanical
        "motor_current_a": 8.2,
        "severity": "medium",
        "category": "sensor",
        "description": "Encoder/proximity sensor reporting erratic values (simulated).",
    },
    "bearing_wear": {
        "vibration_level": 42.0,      # progressive vibration rise
        "motor_current_a": 9.5,
        "severity": "medium",
        "category": "mechanical",
        "description": "Bearing degradation — vibration trending upward (simulated).",
    },
    "belt_slip": {
        "vibration_level": 55.0,
        "motor_current_a": 6.5,       # fluctuating load
        "severity": "high",
        "category": "mechanical",
        "description": "Belt slip detected — insufficient tension (simulated).",
    },
    "overload_trip": {
        "vibration_level": 70.0,
        "motor_current_a": 24.0,      # >20A → trip
        "severity": "critical",
        "category": "electrical",
        "description": "Thermal overload trip — current >20A sustained (simulated).",
    },
}

# Nominal state values (machine running normally)
NOMINAL_VIBRATION = 5.0
NOMINAL_CURRENT_A = 8.0

# In-memory state for a single simulated line (line_id = 1).
# Module-level on purpose: there is exactly one simulated machine, so every
# dashboard session must see the same state (this is NOT per-user data).
_state = {
    "line_id": 1,
    "status": "running",                   # running | stopped | faulted
    "fault_type": None,                    # active fault key from FAULT_CATALOGUE
    "last_updated": datetime.now().isoformat(),
    "last_change_reason": "initial state",
    # Simulated temperature dimension (slider-driven; no sensor).
    "temperature_c": NOMINAL_TEMPERATURE_C,
    "temperature_updated_at": datetime.now().isoformat(),
    # New simulated sensor proxies (Phase A).
    "vibration_level": NOMINAL_VIBRATION,  # 0-100
    "motor_current_a": NOMINAL_CURRENT_A,  # simulated amperes
    "zone": "Zone 01",
    "alert_count_today": 0,
}

# Ring buffer of (timestamp, temperature) samples. A sample is appended every
# time set_temperature() is called, so the chart shows exactly the values the
# operator set and when. No synthetic noise is added — a flat line means the
# slider was not moved.
_temperature_history: deque = deque(maxlen=TEMPERATURE_HISTORY_MAX)
_temperature_history.append(
    {"timestamp": _state["temperature_updated_at"], "temperature_c": NOMINAL_TEMPERATURE_C}
)


def get_status() -> dict:
    """Return current simulated conveyor state (status + temperature)."""
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
    _state["fault_type"] = None
    _state["last_updated"] = datetime.now().isoformat()
    _state["last_change_reason"] = "commanded: run"
    # Restore nominal sensor values when machine is restarted.
    _state["vibration_level"] = NOMINAL_VIBRATION
    _state["motor_current_a"] = NOMINAL_CURRENT_A
    _write_to_db("running", "commanded: run")
    return get_status()


def manual_stop():
    """
    User commands the line to stop.
    This is a COMMANDED stop -> not a fault, no agent escalation needed.
    """
    _state["status"] = "stopped"
    _state["fault_type"] = None
    _state["last_updated"] = datetime.now().isoformat()
    _state["last_change_reason"] = "commanded: manual stop"
    _state["vibration_level"] = NOMINAL_VIBRATION
    _state["motor_current_a"] = NOMINAL_CURRENT_A
    _write_to_db("stopped", "commanded: manual stop")
    return get_status()


def get_fault_catalogue() -> dict:
    """Return the full fault catalogue for the Trigger Console UI."""
    return {k: dict(v) for k, v in FAULT_CATALOGUE.items()}


def trigger_fault(fault_type: str = "mechanical_jam"):
    """
    Simulates an UNPLANNED fault from the FAULT_CATALOGUE.
    This is what should be logged as an event and passed to the
    reasoning agent, since it was NOT commanded by a user.

    fault_type: key from FAULT_CATALOGUE — one of:
        mechanical_jam | motor_failure | sensor_drift |
        bearing_wear   | belt_slip     | overload_trip
    Falls back to a generic fault if the key is not in the catalogue.
    """
    profile = FAULT_CATALOGUE.get(fault_type, {
        "vibration_level": 50.0,
        "motor_current_a": 10.0,
        "severity": "high",
        "category": "mechanical",
        "description": f"Generic unplanned fault: {fault_type} (simulated).",
    })
    _state["status"] = "faulted"
    _state["fault_type"] = fault_type
    _state["last_updated"] = datetime.now().isoformat()
    _state["last_change_reason"] = f"unplanned fault: {fault_type}"
    _state["vibration_level"] = profile["vibration_level"]
    _state["motor_current_a"] = profile["motor_current_a"]
    _state["alert_count_today"] = _state.get("alert_count_today", 0) + 1
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


# ── Simulated temperature ─────────────────────────────────────────────────────

def get_temperature() -> float:
    """Return the current simulated temperature in °C (slider-set value)."""
    return float(_state["temperature_c"])


def get_temperature_history() -> List[Dict]:
    """
    Return the recorded temperature samples, oldest first.
    Each item: {"timestamp": ISO-8601 str, "temperature_c": float}.
    Only slider changes are recorded; there is no periodic sampling.
    """
    return list(_temperature_history)


def _write_temperature_to_db(temperature_c: float):
    """
    Persist the current simulated temperature to conveyor_state.temperature_c.
    The column is created by database.db.init_db() (same place the table is).
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO conveyor_state (line_id, status, temperature_c, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(line_id) DO UPDATE SET
            temperature_c=excluded.temperature_c,
            last_updated=excluded.last_updated
        """,
        (
            _state["line_id"],
            _state["status"],
            temperature_c,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def set_temperature(temperature_c: float) -> dict:
    """
    Operator sets the simulated temperature (dashboard slider).

    This only updates the simulated machine state and records a history sample.
    It does NOT classify or alert — that is the reasoning layer's job
    (agent/autonomous.py calls this, then decides what to do with the change).

    Returns:
        {"previous_c": float, "current_c": float, "changed": bool, "timestamp": str}
    """
    try:
        new_value = float(temperature_c)
    except (TypeError, ValueError):
        raise ValueError(f"temperature_c must be numeric, got {temperature_c!r}")

    previous = float(_state["temperature_c"])
    now_iso = datetime.now().isoformat()

    changed = new_value != previous
    if changed:
        _state["temperature_c"] = new_value
        _state["temperature_updated_at"] = now_iso
        _temperature_history.append({"timestamp": now_iso, "temperature_c": new_value})
        _write_temperature_to_db(new_value)

    return {
        "previous_c": previous,
        "current_c": new_value,
        "changed": changed,
        "timestamp": now_iso,
    }

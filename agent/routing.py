"""
agent/routing.py
Temperature severity bands and the severity -> recipient routing table used by
the autonomous temperature-escalation path (agent/autonomous.py).

Everything in this file is CONFIGURATION, kept as plain Python data so that:
  * the reasoner (agent/reasoner.py) classifies a temperature reading from it,
  * the autonomous handler (agent/autonomous.py) selects recipients from it, and
  * the Trigger Console (frontend) and /api/simulation/temperature render the
    *same* table a reviewer reads here — there is no second copy of this logic.

STATUS OF THESE NUMBERS AND ROLES — READ BEFORE CITING THEM
-----------------------------------------------------------
The temperature thresholds below are the project owner's chosen DEFAULTS
(nominal < 70, low 70-84, medium 85-99, high 100-119, critical 120+ °C). They
are configuration values, not derived from an equipment datasheet or standard,
and remain open to revision. Likewise the four roles and which severities
notify them follow the evaluator's verbal description. To change either, edit
this file only — the API, reasoner and frontend all read from here.

What this path is (and is not)
------------------------------
One rule-based reasoning agent observes the simulated temperature, classifies
it into a band, looks up the recipients for that band, and dispatches one
notification per recipient without a human approval step. That is a single
agent fanning out notifications by severity. It is not a multi-agent system.
"""

import os
from typing import Dict, List, Optional


# ── Severity bands ────────────────────────────────────────────────────────────

# Lowest to highest. "nominal" is deliberately NOT in this list: it is the
# "inside normal range" state where the agent takes no action at all.
SEVERITY_ORDER: List[str] = ["low", "medium", "high", "critical"]

# Ordered from coolest to hottest. Bands are [min_c, max_c) — the lower bound is
# inclusive, the upper bound exclusive. None means unbounded on that side.
# "70-84 °C" in the spec table is therefore [70, 85) here, and so on.
# CONFIGURATION VALUES — see module docstring.
TEMPERATURE_BANDS: List[Dict] = [
    {
        "severity": "nominal",
        "min_c": None,
        "max_c": 70.0,
        "display_range": "< 70 °C",
        "description": "Normal operating range. No action.",
    },
    {
        "severity": "low",
        "min_c": 70.0,
        "max_c": 85.0,
        "display_range": "70-84 °C",
        "description": "Elevated. Maintenance should be aware.",
    },
    {
        "severity": "medium",
        "min_c": 85.0,
        "max_c": 100.0,
        "display_range": "85-99 °C",
        "description": "Overheating trend. Supervisor attention needed.",
    },
    {
        "severity": "high",
        "min_c": 100.0,
        "max_c": 120.0,
        "display_range": "100-119 °C",
        "description": "Thermal-overload risk to the machine and nearby workers.",
    },
    {
        "severity": "critical",
        "min_c": 120.0,
        "max_c": None,
        "display_range": ">= 120 °C",
        "description": "Fire / injury risk. Fire & Safety must be informed.",
    },
]

# Slider range offered by the UI (also configuration; must cover all bands).
SLIDER_MIN_C = 20.0
SLIDER_MAX_C = 150.0


# ── Recipient roles ───────────────────────────────────────────────────────────

# Each role resolves to ONE email address read from the environment (.env).
# If a variable is unset, dispatch for that role is recorded as FAILED with an
# explicit reason — it is never silently redirected to another address.
# CONFIGURATION — see module docstring.
RECIPIENT_ROLES: Dict[str, Dict[str, str]] = {
    "maintenance": {
        "label": "Maintenance team",
        "env_var": "MAINTENANCE_TEAM_EMAIL",
    },
    "supervisor": {
        "label": "Area supervisor",
        "env_var": "AREA_SUPERVISOR_EMAIL",
    },
    "worker_manager": {
        "label": "Worker-manager (zone)",
        "env_var": "WORKER_MANAGER_EMAIL",
    },
    "fire_safety": {
        "label": "Fire & Safety",
        "env_var": "FIRE_SAFETY_EMAIL",
    },
}


# ── Severity -> recipients ────────────────────────────────────────────────────

# The routing table. Read it as: "when severity is X, notify these roles".
# Each tier includes everything from the tier below it plus one more role.
# CONFIGURATION — see module docstring.
SEVERITY_ROUTING: Dict[str, List[str]] = {
    "low":      ["maintenance"],
    "medium":   ["maintenance", "supervisor"],
    "high":     ["maintenance", "supervisor", "worker_manager"],
    "critical": ["maintenance", "supervisor", "worker_manager", "fire_safety"],
}


# ── Lookup helpers ────────────────────────────────────────────────────────────

def classify_temperature_band(temperature_c: float) -> Dict:
    """Return the band dict (from TEMPERATURE_BANDS) that contains temperature_c."""
    t = float(temperature_c)
    for band in TEMPERATURE_BANDS:
        lower_ok = band["min_c"] is None or t >= band["min_c"]
        upper_ok = band["max_c"] is None or t < band["max_c"]
        if lower_ok and upper_ok:
            return dict(band)
    # Unreachable if TEMPERATURE_BANDS is contiguous; guard anyway.
    raise ValueError(f"No temperature band covers {t} °C — check TEMPERATURE_BANDS")


def severity_for_temperature(temperature_c: float) -> str:
    """Return 'nominal' or one of SEVERITY_ORDER for the given temperature."""
    return classify_temperature_band(temperature_c)["severity"]


def severity_rank(severity: str) -> int:
    """Numeric rank for comparisons. 'nominal' ranks below every severity."""
    if severity == "nominal":
        return -1
    return SEVERITY_ORDER.index(severity)


def recipients_for_severity(severity: str) -> List[Dict[str, str]]:
    """
    Return the recipient roles for a severity, in routing-table order.
    Each item: {"role": key, "label": str, "env_var": str}.
    Returns [] for 'nominal' or unknown severities.
    """
    roles = SEVERITY_ROUTING.get(severity, [])
    return [{"role": r, **RECIPIENT_ROLES[r]} for r in roles]


def resolve_recipient_addresses(severity: str) -> List[Dict[str, Optional[str]]]:
    """
    Same as recipients_for_severity() but with each role's email address read
    from the environment. 'email' is None when the variable is unset/blank.
    """
    resolved = []
    for r in recipients_for_severity(severity):
        address = (os.getenv(r["env_var"]) or "").strip() or None
        resolved.append({**r, "email": address})
    return resolved


def format_band_range(band: Dict) -> str:
    """
    Human-readable range. Prefer band['display_range'] (the inclusive labels
    from the project table: 70-84, 85-99, 100-119, >= 120) so the UI, emails
    and the routing table all match. Fallback is the exclusive-upper interval.
    ASCII operators on purpose: this text goes into plain-text emails.
    """
    if band.get("display_range"):
        return band["display_range"]
    lo, hi = band["min_c"], band["max_c"]
    if lo is None and hi is None:
        return "any"
    if lo is None:
        return f"< {hi:g} °C"
    if hi is None:
        return f">= {lo:g} °C"
    return f"{lo:g}-{hi:g} °C"


def routing_table_rows() -> List[Dict[str, str]]:
    """
    Flattened rows for display (dashboard) — one per band, coolest first:
    {"severity", "range", "recipients", "description"}.
    """
    rows = []
    for band in TEMPERATURE_BANDS:
        sev = band["severity"]
        labels = [r["label"] for r in recipients_for_severity(sev)]
        rows.append({
            "severity": sev,
            "range": format_band_range(band),
            "recipients": ", ".join(labels) if labels else "— (no notification)",
            "description": band["description"],
        })
    return rows

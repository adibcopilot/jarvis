"""
database/db.py
SQLite database layer for JARVIS event logging.
Schema matches TDS Section 3.
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


DB_PATH = Path(__file__).resolve().parent / "jarvis.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       DATETIME DEFAULT (datetime('now','localtime')),
            event_type      TEXT NOT NULL,          -- ppe / fire / conveyor
            source_file     TEXT,                    -- which image/video triggered this
            detections_json TEXT,                    -- full detection payload as JSON
            severity        TEXT DEFAULT 'pending',  -- low / medium / high / critical
            category        TEXT DEFAULT 'pending',  -- safety / mechanical / technical
            proposed_action TEXT DEFAULT '',
            approval_status TEXT DEFAULT 'pending',  -- pending / approved / denied
            approved_by     TEXT,
            resolved_at     DATETIME,
            record_hash     TEXT,
            prev_hash       TEXT
        );

        CREATE TABLE IF NOT EXISTS workers (
            worker_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            face_encoding   BLOB
        );

        CREATE TABLE IF NOT EXISTS conveyor_state (
            line_id         INTEGER PRIMARY KEY,
            status          TEXT DEFAULT 'running',  -- running / stopped / faulted
            last_updated    DATETIME DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()


def _compute_hash(record_data: str, prev_hash: str) -> str:
    """Hash-chain: hash of current record contents + previous record's hash."""
    payload = f"{prev_hash}|{record_data}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_last_hash(conn: sqlite3.Connection) -> str:
    """Get the hash of the most recent event record."""
    row = conn.execute(
        "SELECT record_hash FROM events ORDER BY event_id DESC LIMIT 1"
    ).fetchone()
    return row["record_hash"] if row else "GENESIS"


def insert_event(
    event_type: str,
    source_file: str = "",
    detections: Optional[List[Dict]] = None,
    severity: str = "pending",
    category: str = "pending",
    proposed_action: str = "",
) -> int:
    """Insert a new event and return its event_id."""
    conn = get_connection()
    
    detections_json = json.dumps(detections or [], ensure_ascii=False)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    record_data = f"{timestamp}|{event_type}|{source_file}|{detections_json}|{severity}|{category}"
    prev_hash = _get_last_hash(conn)
    record_hash = _compute_hash(record_data, prev_hash)

    cursor = conn.execute(
        """INSERT INTO events 
           (timestamp, event_type, source_file, detections_json, severity, category, proposed_action, record_hash, prev_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp, event_type, source_file, detections_json, severity, category, proposed_action, record_hash, prev_hash)
    )
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return event_id


def update_approval(event_id: int, status: str, approved_by: str = "Manager"):
    """Set approval_status to 'approved' or 'denied'."""
    conn = get_connection()
    resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status != "pending" else None
    conn.execute(
        """UPDATE events SET approval_status = ?, approved_by = ?, resolved_at = ? WHERE event_id = ?""",
        (status, approved_by, resolved_at, event_id)
    )
    conn.commit()
    conn.close()


def get_all_events() -> List[Dict]:
    """Return all events ordered by most recent first."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM events ORDER BY event_id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_events() -> List[Dict]:
    """Return only events awaiting approval."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE approval_status = 'pending' ORDER BY event_id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_event_stats() -> Dict:
    """Quick stats for the dashboard."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM events WHERE approval_status='pending'").fetchone()["c"]
    approved = conn.execute("SELECT COUNT(*) as c FROM events WHERE approval_status='approved'").fetchone()["c"]
    denied = conn.execute("SELECT COUNT(*) as c FROM events WHERE approval_status='denied'").fetchone()["c"]
    
    high_sev = conn.execute("SELECT COUNT(*) as c FROM events WHERE severity IN ('high','critical')").fetchone()["c"]
    conn.close()
    
    return {
        "total_events": total,
        "pending": pending,
        "approved": approved,
        "denied": denied,
        "high_severity": high_sev,
    }


# Auto-initialize on import
init_db()

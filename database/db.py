"""
database/db.py
SQLite database layer for JARVIS event logging.
Schema matches TDS Section 3.
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


DB_PATH = Path(__file__).resolve().parent / "jarvis.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
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
            event_type      TEXT NOT NULL,          -- ppe / fire / conveyor / temperature
            source_file     TEXT,                    -- which image/video triggered this
            detections_json TEXT,                    -- full detection payload as JSON
            severity        TEXT DEFAULT 'pending',  -- low / medium / high / critical
            category        TEXT DEFAULT 'pending',  -- safety / mechanical / technical
            proposed_action TEXT DEFAULT '',
            approval_status TEXT DEFAULT 'pending',  -- pending / approved / denied / auto_dispatched
                                                     -- (auto_dispatched = temperature path only:
                                                     --  notifications sent with no approval step)
            approved_by     TEXT,
            resolved_at     DATETIME,
            ticket_number   TEXT,                    -- human-readable ticket e.g. TKT-20261006-0042
            record_hash     TEXT,
            prev_hash       TEXT
        );

        CREATE TABLE IF NOT EXISTS workers (
            worker_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_code     TEXT UNIQUE,
            name            TEXT NOT NULL,
            role            TEXT DEFAULT 'Operator',
            department      TEXT DEFAULT 'Assembly Line A',
            shift           TEXT DEFAULT 'Morning (08:00 - 16:00)',
            incidents_count INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'Clear',
            last_incident_date TEXT DEFAULT '-',
            history_summary TEXT DEFAULT '',
            face_encoding   BLOB
        );

        CREATE TABLE IF NOT EXISTS conveyor_state (
            line_id         INTEGER PRIMARY KEY,
            status          TEXT DEFAULT 'running',  -- running / stopped / faulted
            temperature_c   REAL,                    -- simulated, slider-set (no sensor)
            last_updated    DATETIME DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS email_notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        INTEGER NOT NULL,
            recipient       TEXT NOT NULL,
            status          TEXT NOT NULL,          -- SENT / FAILED
            sent_at         DATETIME DEFAULT (datetime('now','localtime')),
            error_message   TEXT,
            sent_by         TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id)
        );
    """)

    # Migrate workers columns if table already existed without them
    cursor = conn.execute("PRAGMA table_info(workers)")
    cols = [r["name"] for r in cursor.fetchall()]
    new_cols = [
        ("worker_code", "TEXT"),
        ("role", "TEXT DEFAULT 'Operator'"),
        ("department", "TEXT DEFAULT 'Assembly Line A'"),
        ("shift", "TEXT DEFAULT 'Morning (08:00 - 16:00)'"),
        ("incidents_count", "INTEGER DEFAULT 0"),
        ("status", "TEXT DEFAULT 'Clear'"),
        ("last_incident_date", "TEXT DEFAULT '-'"),
        ("history_summary", "TEXT DEFAULT ''")
    ]
    for col_name, col_type in new_cols:
        if col_name not in cols:
            try:
                conn.execute(f"ALTER TABLE workers ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    # Migrate conveyor_state for databases created before the simulated
    # temperature dimension was added (simulation/conveyor.py).
    cursor = conn.execute("PRAGMA table_info(conveyor_state)")
    conveyor_cols = [r["name"] for r in cursor.fetchall()]
    if "temperature_c" not in conveyor_cols:
        conn.execute("ALTER TABLE conveyor_state ADD COLUMN temperature_c REAL")

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


def _generate_ticket_number(event_id: int, timestamp: str) -> str:
    """
    Generate a human-readable ticket number: TKT-YYYYMMDD-NNNN.
    Uses the event timestamp date and zero-padded event_id.
    """
    try:
        date_part = datetime.strptime(timestamp[:10], "%Y-%m-%d").strftime("%Y%m%d")
    except Exception:
        date_part = datetime.now().strftime("%Y%m%d")
    return f"TKT-{date_part}-{event_id:04d}"


def insert_event(
    event_type: str,
    source_file: str = "",
    detections: Optional[List[Dict]] = None,
    severity: str = "pending",
    category: str = "pending",
    proposed_action: str = "",
    timestamp: Optional[str] = None,
    approval_status: str = "pending",
    approved_by: Optional[str] = None,
    resolved_at: Optional[str] = None,
) -> int:
    """Insert a new event, generate its ticket number, and return its event_id."""
    conn = get_connection()

    detections_json = json.dumps(detections or [], ensure_ascii=False)
    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    record_data = f"{timestamp}|{event_type}|{source_file}|{detections_json}|{severity}|{category}"
    prev_hash = _get_last_hash(conn)
    record_hash = _compute_hash(record_data, prev_hash)

    cursor = conn.execute(
        """INSERT INTO events
           (timestamp, event_type, source_file, detections_json, severity, category, proposed_action,
            approval_status, approved_by, resolved_at, record_hash, prev_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp, event_type, source_file, detections_json, severity, category, proposed_action,
         approval_status, approved_by, resolved_at, record_hash, prev_hash)
    )
    event_id = cursor.lastrowid

    # Generate and write ticket number now that we have the event_id
    ticket = _generate_ticket_number(event_id, timestamp)
    conn.execute("UPDATE events SET ticket_number = ? WHERE event_id = ?", (ticket, event_id))

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
    auto_dispatched = conn.execute("SELECT COUNT(*) as c FROM events WHERE approval_status='auto_dispatched'").fetchone()["c"]
    
    high_sev = conn.execute("SELECT COUNT(*) as c FROM events WHERE severity IN ('high','critical')").fetchone()["c"]
    critical = conn.execute("SELECT COUNT(*) as c FROM events WHERE LOWER(severity)='critical'").fetchone()["c"]
    high = conn.execute("SELECT COUNT(*) as c FROM events WHERE LOWER(severity)='high'").fetchone()["c"]
    ppe = conn.execute("SELECT COUNT(*) as c FROM events WHERE event_type='ppe'").fetchone()["c"]
    fire = conn.execute("SELECT COUNT(*) as c FROM events WHERE event_type='fire'").fetchone()["c"]
    conveyor = conn.execute("SELECT COUNT(*) as c FROM events WHERE event_type='conveyor'").fetchone()["c"]
    temperature = conn.execute("SELECT COUNT(*) as c FROM events WHERE event_type='temperature'").fetchone()["c"]
    conn.close()
    
    return {
        "total_events": total,
        "pending": pending,
        "approved": approved,
        "denied": denied,
        "auto_dispatched": auto_dispatched,
        "high_severity": high_sev,
        "critical": critical,
        "high": high,
        "ppe": ppe,
        "fire": fire,
        "conveyor": conveyor,
        "temperature": temperature,
        "warning": high,
    }


def get_event_by_id(event_id: int) -> Optional[Dict]:
    """Return a single event by event_id."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def log_email_notification(
    event_id: int,
    recipient: str,
    status: str,
    sent_by: str = "Admin",
    error_message: Optional[str] = None
) -> int:
    """Record an email alert attempt to the audit log."""
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO email_notifications (event_id, recipient, status, sent_by, error_message)
           VALUES (?, ?, ?, ?, ?)""",
        (event_id, recipient, status, sent_by, error_message)
    )
    notif_id = cur.lastrowid
    conn.commit()
    conn.close()
    return notif_id


def get_email_notifications(event_id: Optional[int] = None) -> List[Dict]:
    """Retrieve email audit logs."""
    conn = get_connection()
    if event_id is not None:
        rows = conn.execute(
            "SELECT * FROM email_notifications WHERE event_id = ? ORDER BY notification_id DESC",
            (event_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM email_notifications ORDER BY notification_id DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_workers() -> List[Dict]:
    """Return all registered worker profiles."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM workers ORDER BY worker_id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_worker_by_id_or_code(identifier: str) -> Optional[Dict]:
    """Find a worker by ID, code (e.g. W-101), or partial name."""
    conn = get_connection()
    clean_id = identifier.strip().lower()
    
    # Try exact worker_code match
    row = conn.execute("SELECT * FROM workers WHERE LOWER(worker_code) = ?", (clean_id,)).fetchone()
    if not row:
        # Try numeric worker_id match
        if clean_id.isdigit():
            row = conn.execute("SELECT * FROM workers WHERE worker_id = ?", (int(clean_id),)).fetchone()
        elif clean_id.startswith("w-") and clean_id[2:].isdigit():
            row = conn.execute("SELECT * FROM workers WHERE worker_id = ?", (int(clean_id[2:]),)).fetchone()
    if not row:
        # Try partial name match
        row = conn.execute("SELECT * FROM workers WHERE LOWER(name) LIKE ?", (f"%{clean_id}%",)).fetchone()
        
    conn.close()
    return dict(row) if row else None


def find_mentioned_worker(query: str) -> Optional[Dict]:
    """Return the worker whose name or code appears in a natural-language query."""
    q = (query or "").lower()
    workers = get_all_workers()
    for worker in workers:
        code = (worker.get("worker_code") or "").lower()
        name = (worker.get("name") or "").lower()
        if code and code in q:
            return worker
        if name and name in q:
            return worker
        parts = [p for p in name.replace(",", " ").split() if len(p) > 2]
        if any(p in q for p in parts):
            return worker
    return None


def get_events_for_worker(worker: Dict) -> List[Dict]:
    """Return events linked to a worker via detections, action text, or source file."""
    code = (worker.get("worker_code") or "").lower()
    name = (worker.get("name") or "").lower()
    last = name.split()[-1] if name else ""
    matched = []
    for event in get_all_events():
        blob = " ".join([
            str(event.get("detections_json") or ""),
            str(event.get("proposed_action") or ""),
            str(event.get("source_file") or ""),
        ]).lower()
        if code and code in blob:
            matched.append(event)
        elif name and name in blob:
            matched.append(event)
        elif last and len(last) > 3 and last in blob:
            matched.append(event)
    return matched


def get_events_by_type(event_type: str) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE LOWER(event_type) = ? ORDER BY event_id DESC",
        (event_type.lower(),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _seed_event(conn: sqlite3.Connection, payload: Dict[str, Any]) -> None:
    source_file = payload["source_file"]
    exists = conn.execute("SELECT 1 FROM events WHERE source_file = ?", (source_file,)).fetchone()
    if exists:
        return
    detections_json = json.dumps(payload.get("detections") or [], ensure_ascii=False)
    timestamp = payload["timestamp"]
    event_type = payload["event_type"]
    severity = payload["severity"]
    category = payload["category"]
    record_data = f"{timestamp}|{event_type}|{source_file}|{detections_json}|{severity}|{category}"
    prev_hash = _get_last_hash(conn)
    record_hash = _compute_hash(record_data, prev_hash)
    conn.execute(
        """INSERT INTO events
           (timestamp, event_type, source_file, detections_json, severity, category, proposed_action, approval_status, approved_by, resolved_at, record_hash, prev_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            timestamp,
            event_type,
            source_file,
            detections_json,
            severity,
            category,
            payload.get("proposed_action", ""),
            payload.get("approval_status", "pending"),
            payload.get("approved_by"),
            payload.get("resolved_at"),
            record_hash,
            prev_hash,
        ),
    )


def seed_demo_data():
    """Seed comprehensive demonstration records for workers and incidents."""
    conn = get_connection()
    demo_workers = [
        ("W-101", "Adib Patel", "Project Lead & Senior Tech", "Control Station A", "Morning (08:00 - 16:00)", 0, "Clear", "-", "Group 12 Project Lead. Completed 42 consecutive zero-incident shifts. Validated 18 human approval requests and stayed 100% PPE-compliant. No safety infractions on record."),
        ("W-102", "Rudra Sagar", "Automation & Conveyor Specialist", "Processing Sector B", "Morning (08:00 - 16:00)", 1, "Clear", "2026-09-02", "Group 12 member. On 2026-09-02 he entered Processing Sector B without protective gloves while resetting SIM-01 sensors. He corrected the violation within 2 minutes after a JARVIS audio alert. Completed 38 later shifts with no repeat."),
        ("W-103", "Abhishek Chavan", "Safety Compliance Inspector", "Safety Audit Floor", "Morning (08:00 - 16:00)", 0, "Clear", "-", "Group 12 member. Verified over 140 automated vision detections and SHA-256 hash chains. Zero personal safety infractions. Regularly approves pending actions as inspector."),
        ("W-8472", "Sarah Miller", "Material Handling Specialist", "Logistics & Loading Dock", "Afternoon (16:00 - 00:00)", 3, "Probation", "2026-09-01", "Three recorded infractions: (1) missing steel-toe boots in the loading bay; (2) missing high-vis vest near the forklift lane; (3) delayed evacuation during a simulated smoke alarm on 2026-09-01. Currently on mandatory safety probation with daily gear checks."),
        ("W-1044", "Marcus Lopez", "Processing Line Operator", "Assembly Sector 3", "Night (00:00 - 08:00)", 2, "Flagged", "2026-09-10", "Operated the processing conveyor without eye protection on 2026-09-10. Previously entered the machine perimeter during a mechanical jam on 2026-06-01. Scheduled for refresher training; status Flagged."),
        ("W-9211", "James Davis", "Forklift & Logistics Operator", "Warehouse Aisle 2", "Morning (08:00 - 16:00)", 0, "Clear", "-", "Completed 180+ hours of material transport with a perfect safety record. 100% PPE compliance on all visual checkpoints. No pending or historical incidents."),
        ("W-305", "Elena Rostova", "Electrical Maintenance Tech", "Electrical Bay Line 2", "Day (09:00 - 17:00)", 1, "Clear", "2026-08-28", "Approached a power cabinet without arc-rated gloves on 2026-08-28. Retrained on electrical isolation protocols. Later dispatched to clear a conveyor jam on Line 1 after supervisor approval."),
        ("W-402", "David Kim", "Quality Assurance Inspector", "Testing Station C", "Afternoon (16:00 - 00:00)", 1, "Clear", "2026-07-15", "Missing safety goggles during batch sampling on 2026-07-15. Corrected immediately after the console alert. Otherwise a clean QA inspection record."),
        ("W-510", "Priya Sharma", "Assembly Line Operator", "Assembly Sector 2", "Morning (08:00 - 16:00)", 2, "Flagged", "2026-09-12", "Two PPE hits this month: missing hard hat on 2026-09-05 while staging cartons, and missing gloves on 2026-09-12 during fastener changeover. Flagged for coaching."),
        ("W-612", "Omar Hassan", "Packaging Station Operator", "Zone 03 Packaging", "Afternoon (16:00 - 00:00)", 0, "Clear", "-", "Packaging Station operator with zero incidents. Confirmed compliant helmet, vest, gloves, and boots across all sampled frames."),
        ("W-718", "Chen Wei", "Night Shift Supervisor", "Control Station B", "Night (00:00 - 08:00)", 1, "Clear", "2026-09-08", "Delayed acknowledging a smoke-density alert in Ceiling Bay 2 on 2026-09-08 by four minutes. Completed fire-response drill afterward; record restored to Clear."),
        ("W-220", "Anita Desai", "Quality Sampling Tech", "Testing Station A", "Morning (08:00 - 16:00)", 0, "Clear", "-", "Zero incidents. Assisted hash-chain verification of Q3 audit reports. Fully PPE-compliant."),
        ("W-330", "Tom Bradley", "Mechanical Maintenance Tech", "Processing Sector B", "Day (09:00 - 17:00)", 1, "Clear", "2026-09-11", "Responded to an unplanned belt jam on SIM-01 on 2026-09-11. Cleared the jam after manager approval. One historical near-miss for entering a live perimeter without lockout confirmation."),
        ("W-441", "Nina Kapoor", "Material Handler", "Logistics & Loading Dock", "Night (00:00 - 08:00)", 4, "Probation", "2026-09-14", "Repeat PPE offender: missing helmet, vest, and boots across four night-shift scans. Last incident 2026-09-14 on Dock Door 3. Restricted from forklift operation until probation clears."),
    ]
    existing_rows = conn.execute("SELECT worker_id, worker_code FROM workers").fetchall()
    seen_codes = set()
    duplicate_ids = []
    for row in existing_rows:
        code = row["worker_code"]
        if not code:
            continue
        if code in seen_codes:
            duplicate_ids.append(row["worker_id"])
        else:
            seen_codes.add(code)
    if duplicate_ids:
        conn.executemany("DELETE FROM workers WHERE worker_id = ?", [(i,) for i in duplicate_ids])
        conn.commit()

    for w in demo_workers:
        code = w[0]
        exists = conn.execute("SELECT 1 FROM workers WHERE worker_code = ?", (code,)).fetchone()
        if exists:
            conn.execute(
                """UPDATE workers SET name=?, role=?, department=?, shift=?, incidents_count=?, status=?, last_incident_date=?, history_summary=?
                   WHERE worker_code=?""",
                (w[1], w[2], w[3], w[4], w[5], w[6], w[7], w[8], code),
            )
        else:
            conn.execute(
                """INSERT INTO workers
                   (worker_code, name, role, department, shift, incidents_count, status, last_incident_date, history_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                w,
            )
    conn.commit()

    now = datetime.now()
    def ts(days_ago: int, hour: int, minute: int = 0) -> str:
        return (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    seed_events = [
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_lopez_goggles.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-1044", "worker_name": "Marcus Lopez"}, {"label": "no_goggle", "confidence": 0.91}],
            "severity": "high",
            "category": "safety",
            "proposed_action": "Issue critical warning to Worker W-1044 (Marcus Lopez) for operating the processing unit without eye protection. Propose immediate work pause.",
            "approval_status": "pending",
            "timestamp": ts(0, 2, 10),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_miller_vest_boots.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-8472", "worker_name": "Sarah Miller"}, {"label": "none", "confidence": 0.88}, {"label": "no_boots", "confidence": 0.84}],
            "severity": "high",
            "category": "safety",
            "proposed_action": "Restrict floor access for Worker W-8472 (Sarah Miller) pending safety gear inspection. Notify shift supervisor.",
            "approval_status": "pending",
            "timestamp": ts(1, 17, 22),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_sharma_helmet.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-510", "worker_name": "Priya Sharma"}, {"label": "no_helmet", "confidence": 0.93}],
            "severity": "medium",
            "category": "safety",
            "proposed_action": "Notify Worker W-510 (Priya Sharma) to don a hard hat before continuing carton staging in Assembly Sector 2.",
            "approval_status": "approved",
            "approved_by": "Patel, A.",
            "resolved_at": ts(4, 10, 40),
            "timestamp": ts(4, 9, 18),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_sharma_gloves.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-510", "worker_name": "Priya Sharma"}, {"label": "no_gloves", "confidence": 0.81}],
            "severity": "medium",
            "category": "safety",
            "proposed_action": "Coach Worker W-510 (Priya Sharma) on glove policy during fastener changeover. Log second PPE hit this month.",
            "approval_status": "pending",
            "timestamp": ts(2, 11, 5),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_sagar_gloves.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-102", "worker_name": "Rudra Sagar"}, {"label": "no_gloves", "confidence": 0.79}],
            "severity": "medium",
            "category": "safety",
            "proposed_action": "Warn Worker W-102 (Rudra Sagar) for missing protective gloves while resetting SIM-01 sensors. Confirm correction on next scan.",
            "approval_status": "approved",
            "approved_by": "Chavan, A.",
            "resolved_at": ts(14, 9, 12),
            "timestamp": ts(14, 8, 44),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_kapoor_repeat.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-441", "worker_name": "Nina Kapoor"}, {"label": "no_helmet", "confidence": 0.9}, {"label": "none", "confidence": 0.87}, {"label": "no_boots", "confidence": 0.83}],
            "severity": "high",
            "category": "safety",
            "proposed_action": "Remove Worker W-441 (Nina Kapoor) from Dock Door 3 until helmet, vest, and boots are verified. Escalate probation review.",
            "approval_status": "pending",
            "timestamp": ts(2, 1, 36),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_kim_goggles.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-402", "worker_name": "David Kim"}, {"label": "no_goggle", "confidence": 0.77}],
            "severity": "medium",
            "category": "safety",
            "proposed_action": "Notify Worker W-402 (David Kim) to wear safety goggles during batch sampling at Testing Station C.",
            "approval_status": "approved",
            "approved_by": "Patel, A.",
            "resolved_at": ts(20, 17, 10),
            "timestamp": ts(20, 16, 55),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_davis_compliant.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-9211", "worker_name": "James Davis"}, {"label": "helmet", "confidence": 0.95}, {"label": "vest", "confidence": 0.94}],
            "severity": "low",
            "category": "safety",
            "proposed_action": "No action required. Worker W-9211 (James Davis) is PPE-compliant.",
            "approval_status": "approved",
            "approved_by": "Chavan, A.",
            "resolved_at": ts(3, 10, 2),
            "timestamp": ts(3, 9, 50),
        },
        {
            "event_type": "ppe",
            "source_file": "seed_v2_ppe_rostova_gloves.jpg",
            "detections": [{"label": "Person", "class": "person", "worker_code": "W-305", "worker_name": "Elena Rostova"}, {"label": "no_gloves", "confidence": 0.8}],
            "severity": "medium",
            "category": "safety",
            "proposed_action": "Retrain Worker W-305 (Elena Rostova) on arc-rated glove use before electrical cabinet work.",
            "approval_status": "approved",
            "approved_by": "Patel, A.",
            "resolved_at": ts(19, 11, 20),
            "timestamp": ts(19, 10, 5),
        },
        {
            "event_type": "fire",
            "source_file": "seed_v2_fire_sector4.jpg",
            "detections": [{"label": "fire", "class": "fire", "location": "Sector 04", "confidence": 0.94}],
            "severity": "critical",
            "category": "safety",
            "proposed_action": "Emergency stop on Processing Unit SIM-01. Sound floor siren, notify fire marshal, and dispatch Gmail alert to manager.",
            "approval_status": "approved",
            "approved_by": "Patel, A.",
            "resolved_at": ts(0, 11, 15),
            "timestamp": ts(0, 11, 2),
        },
        {
            "event_type": "fire",
            "source_file": "seed_v2_smoke_bay2.jpg",
            "detections": [{"label": "smoke", "class": "smoke", "location": "Ceiling Bay 2", "confidence": 0.86}],
            "severity": "high",
            "category": "safety",
            "proposed_action": "Activate exhaust isolation dampers. Dispatch pre-combustion alert. Worker W-718 (Chen Wei) must acknowledge the night-shift smoke protocol.",
            "approval_status": "approved",
            "approved_by": "Patel, A.",
            "resolved_at": ts(8, 3, 40),
            "timestamp": ts(8, 3, 12),
        },
        {
            "event_type": "fire",
            "source_file": "seed_v2_fire_packaging.jpg",
            "detections": [{"label": "fire", "class": "fire", "location": "Zone 03 Packaging", "confidence": 0.81}, {"label": "smoke", "class": "smoke", "confidence": 0.74}],
            "severity": "critical",
            "category": "safety",
            "proposed_action": "Evacuate Zone 03 Packaging. Halt packaging station. Notify supervisor and manager immediately.",
            "approval_status": "denied",
            "approved_by": "Sagar, R.",
            "resolved_at": ts(6, 18, 20),
            "timestamp": ts(6, 18, 5),
        },
        {
            "event_type": "fire",
            "source_file": "seed_v2_smoke_loading_dock.jpg",
            "detections": [{"label": "smoke", "class": "smoke", "location": "Loading Dock", "confidence": 0.72}],
            "severity": "high",
            "category": "safety",
            "proposed_action": "Inspect Loading Dock for smoldering pallet heat. Worker W-8472 (Sarah Miller) delayed evacuation during the prior drill — verify muster.",
            "approval_status": "pending",
            "timestamp": ts(1, 19, 8),
        },
        {
            "event_type": "conveyor",
            "source_file": "seed_v2_conveyor_jam_sim01.jpg",
            "detections": [{"label": "machine", "class": "machine", "unit": "SIM-01", "anomaly": "belt_jam", "rpm": 0}],
            "severity": "high",
            "category": "mechanical",
            "proposed_action": "Interlock engaged. Halt upstream feed. Dispatch maintenance technician W-330 (Tom Bradley) after supervisor approval.",
            "approval_status": "approved",
            "approved_by": "Chavan, A.",
            "resolved_at": ts(5, 12, 30),
            "timestamp": ts(5, 12, 4),
        },
        {
            "event_type": "conveyor",
            "source_file": "seed_v2_conveyor_overheat.jpg",
            "detections": [{"label": "machine", "class": "machine", "unit": "SIM-01", "anomaly": "motor_overheat", "temp_c": 78}],
            "severity": "high",
            "category": "mechanical",
            "proposed_action": "Reduce Line 1 speed and dispatch W-305 (Elena Rostova) for motor thermal inspection. Do not restart until approved.",
            "approval_status": "pending",
            "timestamp": ts(0, 14, 18),
        },
        {
            "event_type": "conveyor",
            "source_file": "seed_v2_conveyor_slip.jpg",
            "detections": [{"label": "machine", "class": "machine", "unit": "Packaging Station", "anomaly": "belt_slip"}],
            "severity": "medium",
            "category": "mechanical",
            "proposed_action": "Flag Packaging Station belt slip. Schedule alignment during the next planned stop. Operator W-612 (Omar Hassan) remains on station.",
            "approval_status": "approved",
            "approved_by": "Patel, A.",
            "resolved_at": ts(7, 16, 50),
            "timestamp": ts(7, 16, 22),
        },
    ]
    for payload in seed_events:
        _seed_event(conn, payload)
    conn.commit()
    conn.close()


# Auto-initialize and seed on import
init_db()
seed_demo_data()

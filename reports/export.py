"""
reports/export.py
Audit Report Exporter for JARVIS.

Provides:
- export_events_to_csv: Converts SQLite event records into CSV string or file
- export_events_to_dataframe: Returns a cleaned pandas DataFrame for UI display & analytics
"""

import sys
import csv
import io
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import get_all_events


def get_events_dataframe() -> pd.DataFrame:
    """Return all events as a pandas DataFrame."""
    events = get_all_events()
    if not events:
        return pd.DataFrame(columns=[
            "event_id", "timestamp", "event_type", "source_file",
            "severity", "category", "proposed_action", "approval_status",
            "approved_by", "resolved_at", "record_hash", "prev_hash"
        ])
    return pd.DataFrame(events)


def export_events_to_csv(events: Optional[List[Dict]] = None) -> str:
    """
    Export events to CSV format as a string.
    If events is None, fetches all events from SQLite.
    """
    if events is None:
        events = get_all_events()

    output = io.StringIO()
    if not events:
        return "event_id,timestamp,event_type,source_file,severity,category,proposed_action,approval_status,approved_by,resolved_at,record_hash,prev_hash\n"

    fieldnames = [
        "event_id", "timestamp", "event_type", "source_file",
        "severity", "category", "proposed_action", "approval_status",
        "approved_by", "resolved_at", "record_hash", "prev_hash"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in events:
        writer.writerow(row)

    return output.getvalue()

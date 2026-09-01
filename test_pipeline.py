"""Quick end-to-end pipeline test."""
import sys
sys.path.insert(0, ".")

from detection.pipeline import run_ppe_pipeline, run_fire_pipeline
from database.db import get_all_events, get_event_stats

# Test 1: PPE pipeline
print("=== PPE PIPELINE TEST ===")
r1 = run_ppe_pipeline("detection/test_inputs/ppe/bo.jpg")
print("Event ID:", r1["event_id"])
print("Violations:", len(r1["violations"]))
print("Severity:", r1["classification"]["severity"])
print("Action:", r1["classification"]["proposed_action"])
print("Reasoning:", r1["classification"]["reasoning"])
print()

# Test 2: Fire pipeline
print("=== FIRE PIPELINE TEST ===")
r2 = run_fire_pipeline("detection/test_inputs/fire_smoke/fire.jpg")
print("Event ID:", r2["event_id"])
print("Has Fire:", r2["has_fire"])
print("Severity:", r2["classification"]["severity"])
print("Action:", r2["classification"]["proposed_action"])
print("Reasoning:", r2["classification"]["reasoning"])
print()

# Test 3: Database verification
print("=== DATABASE VERIFICATION ===")
stats = get_event_stats()
print("Total events in DB:", stats["total_events"])
print("Pending:", stats["pending"])
for e in get_all_events():
    print("  Event #%d: %s | %s | %s | %s" % (e["event_id"], e["event_type"], e["severity"], e["approval_status"], e["source_file"]))

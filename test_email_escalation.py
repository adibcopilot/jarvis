import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.abspath('.'))
from agent.autonomous import process_temperature_change

print("Triggering temperature changes: 69.9 -> 100 -> 150")

# Reset to nominal
print("\n--- Sending 69.9 (Nominal) ---")
res1 = process_temperature_change(69.9)
print(f"Fired: {res1.get('fired')}, Severity: {res1.get('severity')}, Transition: {res1.get('transition')}")
time.sleep(1)

# Escalation to 100
print("\n--- Sending 100.0 (High) ---")
res2 = process_temperature_change(100.0)
print(f"Fired: {res2.get('fired')}, Severity: {res2.get('severity')}, Transition: {res2.get('transition')}")
print(f"Sent: {res2.get('sent')}, Failed: {res2.get('failed')}")
time.sleep(1)

# Escalation to 150
print("\n--- Sending 150.0 (Critical) ---")
res3 = process_temperature_change(150.0)
print(f"Fired: {res3.get('fired')}, Severity: {res3.get('severity')}, Transition: {res3.get('transition')}")
print(f"Sent: {res3.get('sent')}, Failed: {res3.get('failed')}")

print("\n--- Database Validation: email_notifications ---")
conn = sqlite3.connect('database/jarvis.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT event_id, recipient, status, sent_at, error_message FROM email_notifications ORDER BY sent_at DESC LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(f"Event: {row['event_id']}, To: {row['recipient']}, Status: {row['status']}, Error: {row['error_message']}")
conn.close()

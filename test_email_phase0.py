import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

print("1. Required email env vars:")
for var in ['MAINTENANCE_TEAM_EMAIL', 'AREA_SUPERVISOR_EMAIL', 'WORKER_MANAGER_EMAIL', 'SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL']:
    val = os.getenv(var)
    status = "SET (non-empty)" if val else "NOT SET or empty"
    print(f"  {var}: {status}")
print(f"  SENDER_PASSWORD: {'SET (hidden)' if os.getenv('SENDER_PASSWORD') else 'NOT SET or empty'}")

print("\n2. Last 10 rows of email_notifications:")
try:
    conn = sqlite3.connect('database/jarvis.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_notifications ORDER BY sent_at DESC LIMIT 10")
    rows = cursor.fetchall()
    if not rows:
        print("  (Table is empty or does not exist)")
    for row in rows:
        print(f"  ID: {row['id']}, Event ID: {row['event_id']}, Recipient: {row['recipient_email']}, Role: {row['recipient_role']}, Status: {row['status']}, Error: {row['error_message']}")
except Exception as e:
    print(f"  Error reading DB: {e}")
finally:
    if 'conn' in locals():
        conn.close()

print("\n3. Testing standalone send:")
import sys
sys.path.insert(0, os.path.abspath('.'))
from alerts.email import send_email_via_smtp

try:
    result = send_email_via_smtp(
        recipient="knowva01@gmail.com",
        event={
            "event_id": 9999,
            "event_type": "Test",
            "severity": "high",
            "proposed_action": "Test action",
            "category": "technical",
            "timestamp": "now"
        }
    )
    print(f"  Send result: {result}")
except Exception as e:
    print(f"  Exception during send: {e}")

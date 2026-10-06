import sqlite3

def check_schema():
    conn = sqlite3.connect('database/jarvis.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(email_notifications)")
    columns = cursor.fetchall()
    print("Columns in email_notifications:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
        
    cursor.execute("SELECT * FROM email_notifications ORDER BY sent_at DESC LIMIT 5")
    rows = cursor.fetchall()
    print("\nLast 5 rows:")
    for row in rows:
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_schema()

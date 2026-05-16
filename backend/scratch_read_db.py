import sqlite3
import os

from core.config import settings

db_url = settings.get_db_url
print(f"DB URL: {db_url}")

if db_url.startswith("sqlite:///"):
    path = db_url.replace("sqlite:///", "")
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT role, content FROM messages WHERE session_id='45ec6ef8-cb23-4580-a8f4-3c3e1ac6dda6' ORDER BY created_at ASC")
            for row in cursor.fetchall():
                print(f"[{row[0]}] {row[1][:1000]}...\n")
        except Exception as e:
            print("Error executing query:", e)
    else:
        print("DB file not found:", path)

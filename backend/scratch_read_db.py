import sqlite3
import json
import os

db_path = "/home/bamuskal/Documents/ai-super/data/ai-orchestrator.db"
session_id = "d82b6829-2c23-4900-9d17-39e2ce481cc3"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"--- History for session {session_id} ---")
cursor.execute("SELECT role, content, thinking_process, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
rows = cursor.fetchall()

for row in rows:
    role, content, thinking, created_at = row
    print(f"[{created_at}] {role.upper()}:")
    print(content)
    if thinking:
        print(f"THINKING: {thinking[:200]}...")
    print("-" * 40)

conn.close()

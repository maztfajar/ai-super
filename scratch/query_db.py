import sqlite3
import json

db_path = "data/ai-orchestrator.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get messages for the session
session_id = "b4626bc2-6cd4-41e8-ad39-4814d5e25ae7"
cursor.execute(
    "SELECT role, content, created_at, model FROM messages WHERE session_id = ? ORDER BY created_at",
    (session_id,)
)
messages = cursor.fetchall()

with open("scratch/inspect_b462.txt", "w", encoding="utf-8") as f:
    f.write(f"=== Session ID: {session_id} ===\n")
    for role, content, created_at, model in messages:
        f.write(f"[{created_at}] {role.upper()}:\n{content}\n")
        f.write("-" * 40 + "\n")

print("Done")
conn.close()

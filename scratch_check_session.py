import sqlite3
import json

conn = sqlite3.connect('data/ai-orchestrator.db')
cursor = conn.cursor()

# Get session info
cursor.execute('SELECT * FROM chat_sessions WHERE id = "b7524fb8-d15c-4f46-93a2-51e746458e99"')
session = cursor.fetchone()

# Get messages
cursor.execute('SELECT role, content FROM messages WHERE session_id = "b7524fb8-d15c-4f46-93a2-51e746458e99" ORDER BY created_at')
messages = cursor.fetchall()

result = {
    "session": session,
    "messages": messages
}

print(json.dumps(result, indent=2))
conn.close()

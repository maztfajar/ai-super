
import sqlite3
import os

db_path = 'backend/data/ai-orchestrator.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Search for the session ID from the screenshot
    cursor.execute("SELECT id FROM chat_sessions WHERE id LIKE 'b1672e42%'")
    rows = cursor.fetchall()
    print(f"Found in SQLite: {rows}")
    
    # Also check the admin user ID in SQLite
    cursor.execute("SELECT id, username FROM users WHERE username = 'admin'")
    user = cursor.fetchone()
    print(f"Admin in SQLite: {user}")
else:
    print("SQLite DB not found.")

import sqlite3
import os
from pathlib import Path

db_path = "/home/bamuskal/Documents/ai-super/data/ai-orchestrator.db"
session_id = "7f0057ed-940a-4622-9502-1f4936702ec5"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check tables first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        # Try to find messages table
        table_name = "messages" # Default guess
        if ("chat_messages",) in tables:
            table_name = "chat_messages"
        
        query = f"SELECT role, content FROM {table_name} WHERE session_id='{session_id}' ORDER BY created_at ASC"
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Found {len(rows)} messages for session {session_id}")
        for row in rows:
            print(f"--- [{row[0]}] ---")
            print(f"{row[1]}")
            print("-" * 20)
    except Exception as e:
        print("Error executing query:", e)
    finally:
        conn.close()
else:
    print("DB file not found:", db_path)

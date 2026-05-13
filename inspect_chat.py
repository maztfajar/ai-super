import sqlite3
import json
import sys
import os

def get_chat_history(session_id):
    db_path = "data/ai-orchestrator.db"
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get session title
        cursor.execute("SELECT title FROM chat_sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        if session:
            print(f"=== Session Title: {session[0]} ===")
        else:
            print(f"Warning: Session {session_id} not found in chat_sessions table.")

        # Get messages
        cursor.execute(
            "SELECT role, content, created_at, model FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        )
        messages = cursor.fetchall()

        if not messages:
            print(f"No messages found for session ID: {session_id}")
            return

        for role, content, created_at, model in messages:
            print(f"[{created_at}] {role.upper()}" + (f" ({model})" if model else "") + ":")
            print(content)
            print("-" * 40)

        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    session_id = "9f684584-5e2f-4ce3-b851-45d3c6c43f02"
    get_chat_history(session_id)

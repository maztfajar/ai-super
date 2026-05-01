
from sqlalchemy import create_engine, text
import json

engine = create_engine('postgresql://ai_orchestrator:admin@localhost/ai_orchestrator_db')

def cleanup():
    with engine.connect() as conn:
        # Fix project_metadata that are literal "null" strings
        res = conn.execute(text("UPDATE chat_sessions SET project_metadata = NULL WHERE project_metadata::text = '\"null\"' OR project_metadata::text = 'null'"))
        print(f"Fixed {res.rowcount} sessions with 'null' metadata.")
        
        # Also check for other tables if necessary
        # agent_performance, api_logs, etc.
        
        conn.commit()

if __name__ == "__main__":
    cleanup()


from sqlalchemy import create_engine, text
import json

engine = create_engine('postgresql://ai_orchestrator:admin@localhost/ai_orchestrator_db')

def dump():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, user_id, title FROM chat_sessions WHERE id LIKE 'b1672e42%'"))
        print(f"{'ID':<40} | {'User ID':<40} | {'Title':<20}")
        print("-" * 110)
        for row in res:
            print(f"{str(row[0]):<40} | {str(row[1]):<40} | {str(row[2]):<20}")

if __name__ == "__main__":
    dump()

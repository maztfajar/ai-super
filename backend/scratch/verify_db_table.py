import asyncio
from sqlmodel import select, text
from db.database import AsyncSessionLocal

async def check_tables():
    async with AsyncSessionLocal() as session:
        try:
            # Query all table names in sqlite
            res = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [r[0] for r in res.fetchall()]
            print("Tables found in SQLite database:")
            for t in tables:
                print(f" - {t}")
            
            if "scheduled_tasks" in tables:
                print("\nSUCCESS: scheduled_tasks table exists!")
            else:
                print("\nFAILURE: scheduled_tasks table does NOT exist.")
        except Exception as e:
            print("Error querying SQLite:", e)

if __name__ == "__main__":
    asyncio.run(check_tables())

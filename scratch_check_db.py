import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.sql import text
import sys

sys.path.append("/home/bamuskal/Documents/ai-super/backend")
from db.models import Message, ChatSession

async def main():
    engine = create_async_engine("sqlite+aiosqlite:////home/bamuskal/Documents/ai-super/data/ai-orchestrator.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(Message).order_by(Message.created_at.desc()).limit(10))
        messages = result.scalars().all()
        for m in messages:
            print(f"[{m.created_at}] Session: {m.session_id} | Role: {m.role} | Content: {m.content[:50]}")
            
if __name__ == "__main__":
    asyncio.run(main())

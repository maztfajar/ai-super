import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.database import engine
from db.models import User, ChatSession
from sqlmodel import select

async def test_db():
    start = time.time()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalars().first()
        print(f"DB Fetch User: {(time.time() - start)*1000:.2f} ms")
        if user:
            start2 = time.time()
            result2 = await session.execute(select(ChatSession).where(ChatSession.user_id == user.id).limit(10))
            sessions = result2.scalars().all()
            print(f"DB Fetch Sessions: {(time.time() - start2)*1000:.2f} ms. Found: {len(sessions)}")

asyncio.run(test_db())

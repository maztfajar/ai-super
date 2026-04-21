#!/usr/bin/env python3
"""
Test script untuk debugging session creation
"""
import asyncio
import sys
import os
sys.path.append('/home/ppidpengasih/Documents/ai-super/backend')

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import AsyncSessionLocal, init_db
from db.models import ChatSession, User

async def test_session_creation():
    print("🔧 Testing database connection and session creation...")
    
    try:
        # Initialize database
        print("📊 Initializing database...")
        await init_db()
        print("✅ Database initialized successfully")
        
        # Test database connection
        print("🔌 Testing database connection...")
        async with AsyncSessionLocal() as db:
            # Check if we can query users
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if user:
                print(f"✅ Found user: {user.username} (ID: {user.id})")
                
                # Test creating a new session
                print("🆕 Testing session creation...")
                new_session = ChatSession(
                    user_id=user.id,
                    title="Test Session",
                )
                db.add(new_session)
                await db.commit()
                await db.refresh(new_session)
                
                print(f"✅ Session created successfully! ID: {new_session.id}")
                
                # Clean up test session
                await db.delete(new_session)
                await db.commit()
                print("🧹 Test session cleaned up")
                
            else:
                print("❌ No users found in database")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_session_creation())

#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append('/home/ppidpengasih/Documents/ai-super/backend')

from db.database import AsyncSessionLocal, init_db
from db.models import User
from sqlmodel import select
from core.auth import hash_password

async def reset_admin():
    print("Resetting admin user...")
    
    # Initialize database
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            # Update password
            admin_user.hashed_password = hash_password("admin")
            admin_user.is_active = True
            admin_user.is_admin = True
            await db.commit()
            print("Admin user password updated successfully!")
        else:
            # Create new admin
            admin_user = User(
                username="admin",
                email="admin@ai-orchestrator.local",
                hashed_password=hash_password("admin"),
                is_active=True,
                is_admin=True,
                role="admin"
            )
            db.add(admin_user)
            await db.commit()
            print("Admin user created successfully!")
        
        print(f"Username: admin")
        print(f"Password: admin")

if __name__ == "__main__":
    asyncio.run(reset_admin())

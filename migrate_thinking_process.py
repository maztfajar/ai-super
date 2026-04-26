#!/usr/bin/env python3
"""
Migration script wrapper
Calls the built-in SQLAlchemy safe_migrate function that supports both SQLite and PostgreSQL.
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path so we can import modules
backend_dir = Path(__file__).parent / "backend"
sys.path.append(str(backend_dir))

from db.database import engine, _safe_migrate

async def migrate_database():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_safe_migrate)
            print("✅ Migration completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Starting database migration (PostgreSQL/SQLite safe)...")
    success = asyncio.run(migrate_database())
    if success:
        print("🎉 Database migration completed!")
        sys.exit(0)
    else:
        print("💥 Database migration failed!")
        sys.exit(1)
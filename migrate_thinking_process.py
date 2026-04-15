#!/usr/bin/env python3
"""
Migration script to add thinking_process column to messages table
Run this after git pull to update database schema
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database():
    db_path = Path(__file__).parent / "backend" / "data" / "ai-super-assistant.db"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if thinking_process column exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in cursor.fetchall()]

        if "thinking_process" not in columns:
            print("📝 Adding thinking_process column to messages table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN thinking_process TEXT")
            conn.commit()
            print("✅ Migration completed successfully")
        else:
            print("ℹ️  thinking_process column already exists")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Starting database migration...")
    success = migrate_database()
    if success:
        print("🎉 Database migration completed!")
        sys.exit(0)
    else:
        print("💥 Database migration failed!")
        sys.exit(1)
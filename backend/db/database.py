from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Create all tables + run safe column migrations"""
    from db import models  # noqa - import to register models
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        # Safe migration: tambah kolom baru jika belum ada
        await conn.run_sync(_safe_migrate)


def _safe_migrate(conn):
    """Tambah kolom yang belum ada tanpa drop data"""
    import sqlalchemy as sa
    inspector = sa.inspect(conn)

    # Migrasi tabel users
    if inspector.has_table("users"):
        existing = [c["name"] for c in inspector.get_columns("users")]
        if "role" not in existing:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'admin'"))
            conn.execute(sa.text("UPDATE users SET role = 'admin' WHERE is_admin = 1"))
            conn.execute(sa.text("UPDATE users SET role = 'subadmin' WHERE is_admin = 0"))
            print("  ✓ Migrasi: kolom 'role' ditambahkan ke tabel users")
        if "totp_secret" not in existing:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN totp_secret TEXT"))
            print("  ✓ Migrasi: kolom totp_secret ditambahkan")
        if "totp_enabled" not in existing:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0"))
            print("  ✓ Migrasi: kolom totp_enabled ditambahkan")
        if "telegram_chat_id" not in existing:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT"))
            print("  ✓ Migrasi: kolom telegram_chat_id ditambahkan")
        if "failed_attempts" not in existing:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0"))
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN locked_until TEXT DEFAULT NULL"))
            print("  ✓ Migrasi: kolom keamanan ditambahkan ke tabel users")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

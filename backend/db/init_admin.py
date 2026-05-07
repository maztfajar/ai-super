"""
Script untuk memastikan user admin selalu ada setelah install.
Aman dijalankan berkali-kali (idempotent).
"""
import asyncio
import os
import sys
from pathlib import Path

# Tambahkan backend ke path agar import bisa jalan
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def ensure_admin_exists():
    from sqlmodel import SQLModel, select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from db.models import User  # noqa — registrasi semua model ke metadata
    import db.models             # noqa — pastikan semua table ter-register
    from core.config import settings
    from core.auth import hash_password  # gunakan bcrypt langsung (tanpa passlib)
    import uuid

    # Ambil kredensial dari .env
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    raw_admin_password = os.getenv("ADMIN_PASSWORD", "")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    
    is_default_password = False
    if not raw_admin_password or raw_admin_password == "GANTI-INI-DENGAN-PASSWORD-KUAT":
        admin_password = "admin123"
        is_default_password = True
    else:
        admin_password = raw_admin_password

    db_url = settings.get_db_url
    is_sqlite = db_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}

    print(f"🔧 Koneksi ke database: {db_url[:40]}...")

    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )

    # Buat semua tabel jika belum ada
    print("🔧 Memastikan semua tabel ada...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ Tabel siap")

    AsyncSession_ = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSession_() as db:
        # Cek apakah admin sudah ada
        result = await db.execute(
            select(User).where(User.username == admin_username)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Pastikan role tetap admin
            if not existing.is_admin:
                existing.is_admin = True
                existing.role = "admin"
                db.add(existing)
                await db.commit()
            print(f"✅ User '{admin_username}' sudah ada di database.")
        else:
            # Buat admin baru
            new_admin = User(
                id=str(uuid.uuid4()),
                username=admin_username,
                email=admin_email,
                hashed_password=hash_password(admin_password),
                is_active=True,
                is_admin=True,
                role="admin",
            )
            db.add(new_admin)
            await db.commit()
            print(f"✅ User admin '{admin_username}' berhasil dibuat")

    await engine.dispose()

    print(f"\n{'='*52}")
    print(f"  LOGIN CREDENTIALS")
    print(f"{'='*52}")
    print(f"  URL      : http://localhost:7860")
    print(f"  Username : {admin_username}")
    if is_default_password:
        print(f"  Password : {admin_password}  <-- (DEFAULT, HARAP DIGANTI!)")
    else:
        print(f"  Password : (Sesuai dengan file .env)")
    print(f"{'='*52}")
    if is_default_password:
        print(f"  ⚠️  PERINGATAN: Anda menggunakan password default!")
        print(f"  Ganti password segera di dashboard atau ubah file .env\n")

if __name__ == "__main__":
    asyncio.run(ensure_admin_exists())

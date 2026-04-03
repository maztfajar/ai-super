#!/bin/bash
# ============================================================
#  AI SUPER ASSISTANT — Reset Password Admin via Terminal
#  Gunakan ini jika lupa password dan tidak bisa login
#  Usage: bash scripts/reset-password.sh
# ============================================================
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${CYAN}${BOLD}AI SUPER ASSISTANT — Reset Password${NC}\n"

# Aktifkan venv
if [ -f "$DIR/backend/venv/bin/activate" ]; then
    source "$DIR/backend/venv/bin/activate"
else
    echo -e "${RED}[✗]${NC} virtualenv tidak ditemukan di backend/venv"
    echo "Jalankan install.sh terlebih dahulu"
    exit 1
fi

cd "$DIR/backend"

python3 - << 'PYEOF'
import asyncio, sys, getpass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent if '__file__' in dir() else Path('.')))

async def reset():
    try:
        from db.database import init_db, AsyncSessionLocal
        from db.models import User
        from core.auth import hash_password
        from sqlmodel import select
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/ai-super-assistant.db")

        await init_db()

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()

        if not users:
            print("\n[✗] Tidak ada user ditemukan di database")
            return

        print("\nDaftar pengguna:")
        for i, u in enumerate(users):
            role = getattr(u, 'role', 'admin' if u.is_admin else 'subadmin')
            print(f"  {i+1}. {u.username} ({role}) — {'Aktif' if u.is_active else 'Nonaktif'}")

        print()
        try:
            choice = int(input("Pilih nomor pengguna: ")) - 1
            if choice < 0 or choice >= len(users):
                print("[✗] Nomor tidak valid"); return
        except ValueError:
            print("[✗] Input tidak valid"); return

        target = users[choice]
        print(f"\nReset password untuk: {target.username}")

        while True:
            pw1 = getpass.getpass("Password baru (min 6 karakter): ")
            if len(pw1) < 6:
                print("[!] Password terlalu pendek"); continue
            pw2 = getpass.getpass("Konfirmasi password: ")
            if pw1 != pw2:
                print("[!] Password tidak cocok"); continue
            break

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == target.id))
            user = result.scalar_one()
            user.hashed_password = hash_password(pw1)
            user.is_active = True
            db.add(user)
            await db.commit()

        print(f"\n[✓] Password {target.username} berhasil direset!")
        print(f"[✓] Akun diaktifkan kembali jika sebelumnya nonaktif")
        print(f"\n    Login: http://localhost:7860")
        print(f"    Username: {target.username}")

    except Exception as e:
        print(f"\n[✗] Error: {e}")
        import traceback; traceback.print_exc()

asyncio.run(reset())
PYEOF

deactivate 2>/dev/null || true

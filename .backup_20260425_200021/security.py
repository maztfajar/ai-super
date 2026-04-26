"""
AI ORCHESTRATOR — Security API
Recovery token, audit log, login history, session management
"""
import secrets
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import User, LoginLog
from core.auth import get_current_user, get_admin_user, hash_password

def _clean_username(username: str) -> str:
    """Strip @ dan whitespace dari username input."""
    return username.strip().lstrip("@")


router = APIRouter()

# ── In-memory store untuk recovery tokens ────────────────────
# { hashed_token: { user_id, expires_at, used } }
_recovery_tokens: dict = {}
TOKEN_TTL = 15 * 60   # 15 menit


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── Recovery Token ────────────────────────────────────────────
@router.post("/recovery/generate")
async def generate_recovery_token(
    target_user_id: Optional[str] = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate recovery token. Admin bisa generate untuk user lain.
    User biasa generate untuk diri sendiri (jika masih login).
    Token berlaku 15 menit, sekali pakai.
    """
    # Target: diri sendiri jika tidak ada target_user_id
    if target_user_id and target_user_id != admin.id:
        res = await db.execute(select(User).where(User.id == target_user_id))
        target = res.scalar_one_or_none()
        if not target:
            raise HTTPException(404, "User tidak ditemukan")
    else:
        target = admin

    # Buat token acak 32 karakter
    token = secrets.token_urlsafe(24)
    hashed = _hash_token(token)

    _recovery_tokens[hashed] = {
        "user_id":    target.id,
        "username":   target.username,
        "expires_at": time.time() + TOKEN_TTL,
        "used":       False,
        "created_by": admin.username,
    }

    return {
        "token":      token,
        "username":   target.username,
        "expires_in": TOKEN_TTL,
        "expires_at": (datetime.utcnow() + timedelta(seconds=TOKEN_TTL)).isoformat(),
        "warning":    "Token ini hanya ditampilkan SEKALI. Simpan dengan aman!",
    }


@router.post("/recovery/use")
async def use_recovery_token(
    token: str,
    new_password: str,
    username: Optional[str] = None,  # opsional: validasi username sesuai token
    db: AsyncSession = Depends(get_db),
):
    """Gunakan recovery token untuk reset password. Tidak butuh auth."""
    if len(new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    hashed = _hash_token(token.strip())
    rec = _recovery_tokens.get(hashed)

    if not rec:
        raise HTTPException(400, "Token tidak valid atau sudah expired")
    if rec["used"]:
        raise HTTPException(400, "Token sudah pernah digunakan")
    if time.time() > rec["expires_at"]:
        del _recovery_tokens[hashed]
        raise HTTPException(400, "Token sudah kadaluarsa (15 menit)")

    # Validasi username jika diberikan
    if username and _clean_username(username):
        if rec["username"].lower() != _clean_username(username).lower():
            raise HTTPException(403,
                f"Token ini bukan untuk akun '{_clean_username(username)}'. "
                f"Token ini untuk akun '{rec['username']}'. "
                "Minta Admin generate token untuk akun Anda."
            )

    # Tandai sebagai sudah digunakan
    rec["used"] = True

    # Reset password
    res = await db.execute(select(User).where(User.id == rec["user_id"]))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="password_reset_via_token"))
    await db.commit()

    return {"status": "ok", "message": f"Password akun '{user.username}' berhasil direset"}


@router.get("/recovery/tokens")
async def list_active_tokens(admin: User = Depends(get_admin_user)):
    """Lihat token recovery yang masih aktif (tanpa nilai tokennya)."""
    now = time.time()
    active = []
    to_del = []
    for h, rec in _recovery_tokens.items():
        if rec["expires_at"] < now:
            to_del.append(h)
            continue
        secs_left = int(rec["expires_at"] - now)
        active.append({
            "username":    rec["username"],
            "expires_in":  secs_left,
            "used":        rec["used"],
            "created_by":  rec["created_by"],
        })
    for h in to_del:
        del _recovery_tokens[h]
    return {"tokens": active}


# ── Emergency CLI Reset (via .env) ───────────────────────────
@router.post("/recovery/emergency")
async def emergency_reset(
    emergency_key: str,
    new_password:  str,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password admin utama via emergency key dari .env.
    Tidak butuh login. Emergency key = sha256(SECRET_KEY + 'emergency').
    """
    from core.config import settings
    expected = hashlib.sha256(
        (settings.SECRET_KEY + "emergency").encode()
    ).hexdigest()[:16]   # 16 char pertama

    if emergency_key.strip() != expected:
        raise HTTPException(403, "Emergency key salah")
    if len(new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    res = await db.execute(
        select(User).where(User.is_admin == True)
    )
    admins = res.scalars().all()
    if not admins:
        raise HTTPException(404, "Tidak ada akun admin")

    # Reset akun admin pertama
    admin = admins[0]
    admin.hashed_password = hash_password(new_password)
    db.add(admin)
    db.add(LoginLog(
        username=admin.username, success=True,
        reason="emergency_password_reset"
    ))
    await db.commit()

    return {
        "status": "ok",
        "message": f"Password admin '{admin.username}' berhasil direset",
        "hint": "Segera login dan ganti emergency key (SECRET_KEY) di .env",
    }


# ── Login History ─────────────────────────────────────────────
@router.get("/login-history")
async def get_login_history(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Riwayat 50 login terakhir."""
    from sqlalchemy import desc
    result = await db.execute(
        select(LoginLog)
        .order_by(desc(LoginLog.created_at))
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id":         l.id,
            "username":   l.username,
            "success":    l.success,
            "reason":     l.reason,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }
        for l in logs
    ]


@router.delete("/login-history")
async def clear_login_history(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    await db.execute(text("DELETE FROM login_logs"))
    await db.commit()
    return {"status": "ok", "message": "Riwayat login dihapus"}


# ── Change password (user sendiri) ───────────────────────────
@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from core.auth import verify_password as vp
    if not vp(current_password, user.hashed_password):
        raise HTTPException(403, "Password lama salah")
    if len(new_password) < 6:
        raise HTTPException(400, "Password baru minimal 6 karakter")
    if current_password == new_password:
        raise HTTPException(400, "Password baru harus berbeda dari password lama")
    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="password_changed"))
    await db.commit()
    return {"status": "ok", "message": "Password berhasil diubah"}

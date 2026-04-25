"""
AI SUPER ASSISTANT — Security API
Recovery token (DB-persisted), audit log, login history, session management.

PATCH 5: Recovery token sekarang disimpan di database (bukan dict memory)
         sehingga tidak hilang saat aplikasi restart.
"""
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, delete

from db.database import get_db
from db.models import User, LoginLog, RecoveryToken
from core.auth import get_current_user, get_admin_user, hash_password, verify_password

router = APIRouter()

TOKEN_TTL_MINUTES = 60  # 1 jam (dinaikkan dari 15 menit)


def _clean_username(username: str) -> str:
    return username.strip().lstrip("@")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utcnow() -> datetime:
    """Timezone-aware UTC now (menggantikan datetime.utcnow() yang deprecated)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC untuk SQLite


# ══════════════════════════════════════════════════════════════
# PATCH 5: Recovery Token — simpan di DB bukan dict memory
# ══════════════════════════════════════════════════════════════

class GenerateTokenRequest(BaseModel):
    target_user_id: Optional[str] = None


@router.post("/recovery/generate")
async def generate_recovery_token(
    req: GenerateTokenRequest = GenerateTokenRequest(),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate recovery token yang disimpan di database.
    Admin bisa generate untuk user lain via target_user_id.
    Token berlaku 1 jam, sekali pakai.
    """
    if req.target_user_id and req.target_user_id != admin.id:
        res = await db.execute(select(User).where(User.id == req.target_user_id))
        target = res.scalar_one_or_none()
        if not target:
            raise HTTPException(404, "User tidak ditemukan")
    else:
        target = admin

    # Hapus token lama milik user ini yang belum expired (bersihkan)
    await db.execute(
        delete(RecoveryToken).where(
            RecoveryToken.user_id == target.id,
            RecoveryToken.used == False,
        )
    )

    # Buat token baru
    raw_token  = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = _utcnow() + timedelta(minutes=TOKEN_TTL_MINUTES)

    rec = RecoveryToken(
        user_id=target.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(rec)
    await db.commit()

    return {
        "token":      raw_token,
        "username":   target.username,
        "expires_in": TOKEN_TTL_MINUTES * 60,
        "expires_at": expires_at.isoformat(),
        "warning":    "Token ini hanya ditampilkan SEKALI. Simpan dengan aman!",
    }


class UseTokenRequest(BaseModel):
    token: str
    new_password: str
    username: Optional[str] = None


@router.post("/recovery/use")
async def use_recovery_token(
    req: UseTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Gunakan recovery token untuk reset password. Tidak butuh auth."""
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    token_hash = _hash_token(req.token.strip())

    result = await db.execute(
        select(RecoveryToken)
        .where(RecoveryToken.token_hash == token_hash)
        .where(RecoveryToken.used == False)
    )
    rec = result.scalar_one_or_none()

    if not rec:
        raise HTTPException(400, "Token tidak valid atau sudah digunakan")

    if rec.expires_at < _utcnow():
        # Hapus token expired
        await db.delete(rec)
        await db.commit()
        raise HTTPException(400, "Token sudah kadaluarsa")

    # Validasi username jika diberikan
    res_user = await db.execute(select(User).where(User.id == rec.user_id))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    if req.username:
        if _clean_username(req.username).lower() != user.username.lower():
            raise HTTPException(403, f"Token ini bukan untuk akun '{req.username}'")

    # Tandai token sudah dipakai (jangan hapus, untuk audit trail)
    rec.used = True
    db.add(rec)

    # Reset password
    user.hashed_password = hash_password(req.new_password)
    user.is_active = True
    db.add(user)

    db.add(LoginLog(username=user.username, success=True, reason="password_reset_via_token"))
    await db.commit()

    return {
        "status":  "ok",
        "message": f"Password akun '{user.username}' berhasil direset.",
    }


@router.get("/recovery/tokens")
async def list_active_tokens(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Lihat token recovery aktif (admin only)."""
    now = _utcnow()

    # Hapus token expired dari DB
    await db.execute(
        delete(RecoveryToken).where(RecoveryToken.expires_at < now)
    )
    await db.commit()

    result = await db.execute(
        select(RecoveryToken, User)
        .join(User, RecoveryToken.user_id == User.id)
        .where(RecoveryToken.used == False)
        .where(RecoveryToken.expires_at >= now)
    )
    rows = result.all()

    return {
        "tokens": [
            {
                "username":    user.username,
                "expires_at":  rec.expires_at.isoformat(),
                "used":        rec.used,
                "created_at":  rec.created_at.isoformat(),
            }
            for rec, user in rows
        ]
    }


# ── Emergency Reset via SECRET_KEY ───────────────────────────
class EmergencyResetRequest(BaseModel):
    secret_key:   str
    new_password: str
    username:     str = "admin"


@router.post("/recovery/emergency")
async def emergency_reset(
    req: EmergencyResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password tanpa login menggunakan SECRET_KEY dari .env.
    Gunakan hanya saat tidak bisa login sama sekali.
    """
    from core.config import settings

    if not hmac.compare_digest(settings.SECRET_KEY.encode(), req.secret_key.encode()):
        raise HTTPException(403, "Verifikasi gagal")

    if len(req.new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    result = await db.execute(
        select(User).where(User.username == _clean_username(req.username))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    user.hashed_password = hash_password(req.new_password)
    user.is_active = True
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="emergency_reset"))
    await db.commit()

    import structlog
    structlog.get_logger().warning(
        "Emergency password reset used",
        username=req.username,
    )

    return {
        "status":  "ok",
        "message": f"Password '{user.username}' berhasil direset. Segera ganti SECRET_KEY!",
    }


# ── Login History ─────────────────────────────────────────────
@router.get("/login-history")
async def get_login_history(
    limit: int = 50,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginLog).order_by(desc(LoginLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id":         l.id,
            "username":   l.username,
            "success":    l.success,
            "reason":     l.reason,
            "ip_address": getattr(l, "ip_address", ""),
            "user_agent": getattr(l, "user_agent", ""),
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }
        for l in logs
    ]


@router.delete("/login-history")
async def clear_login_history(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    await db.execute(text("DELETE FROM login_logs"))
    await db.commit()
    return {"status": "ok", "message": "Riwayat login dihapus"}


# ── Change password (user sendiri) ───────────────────────────
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(403, "Password lama salah")
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password baru minimal 6 karakter")
    if req.current_password == req.new_password:
        raise HTTPException(400, "Password baru harus berbeda dari yang lama")

    user.hashed_password = hash_password(req.new_password)
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="password_changed"))
    await db.commit()
    return {"status": "ok", "message": "Password berhasil diubah"}

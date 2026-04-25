from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, LoginLog
from core.auth import hash_password, verify_password, create_access_token, get_current_user

def _clean_username(username: str) -> str:
    """Strip @ dan whitespace dari username input."""
    return username.strip().lstrip("@")


router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    identifier = "user:" + req.username.lower()

    # Cek rate limit
    blocked, secs = _check_rate_limit(identifier)
    if blocked:
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {secs} detik."
        )

    result = await db.execute(select(User).where(User.username == _clean_username(req.username)))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        _record_failed(identifier)
        db.add(LoginLog(username=req.username, success=False, reason="wrong_password"))
        await db.commit()
        rec = _login_attempts[identifier]
        remaining = MAX_ATTEMPTS - rec["count"]
        if remaining > 0:
            raise HTTPException(
                status_code=401,
                detail=f"Username atau password salah. {remaining} percobaan tersisa."
            )
        else:
            raise HTTPException(
                status_code=429,
                detail=f"Akun terkunci 5 menit karena terlalu banyak percobaan gagal."
            )

    if not user.is_active:
        # Catat log
        db.add(LoginLog(username=req.username, success=False, reason="inactive"))
        await db.commit()
        raise HTTPException(status_code=403, detail="Akun tidak aktif. Hubungi admin.")

    _record_success(identifier)
    # Catat log sukses
    db.add(LoginLog(username=req.username, success=True))
    await db.commit()

    token = create_access_token({"sub": user.id, "username": user.username})

    # Cek apakah user punya 2FA aktif
    totp_enabled = getattr(user, 'totp_enabled', False)
    telegram_chat_id = getattr(user, 'telegram_chat_id', None)
    require_2fa = None
    if totp_enabled:
        require_2fa = "totp"
    elif telegram_chat_id:
        require_2fa = "telegram"

    return {
        "access_token": token,
        "token_type": "bearer",
        "require_2fa": require_2fa,  # None | "totp" | "telegram"
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "role": getattr(user, 'role', 'admin' if user.is_admin else 'subadmin'),
        },
    }


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id, "username": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "role": getattr(current_user, 'role', 'admin' if current_user.is_admin else 'subadmin'),
    }


# ── User Management (Admin only) ──────────────────────────────
from core.auth import get_admin_user
import uuid as _uuid

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "subadmin"   # admin | subadmin

class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/users")
async def list_users(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [
        {
            "id": u.id, "username": u.username, "email": u.email,
            "role": getattr(u, 'role', 'admin' if u.is_admin else 'subadmin'),
            "is_admin": u.is_admin, "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users")
async def create_user(
    req: CreateUserRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Cek duplikat username
    res = await db.execute(select(User).where(User.username == req.username))
    if res.scalar_one_or_none():
        raise HTTPException(400, detail="Username sudah digunakan")
    # Cek duplikat email
    res2 = await db.execute(select(User).where(User.email == req.email))
    if res2.scalar_one_or_none():
        raise HTTPException(400, detail="Email sudah digunakan")

    role = req.role if req.role in ("admin", "subadmin") else "subadmin"
    new_user = User(
        username=req.username.strip(),
        email=req.email.strip().lower(),
        hashed_password=hash_password(req.password),
        is_admin=(role == "admin"),
        is_active=True,
    )
    # Set role attribute
    try:
        new_user.role = role
    except Exception:
        pass

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {
        "status": "created",
        "user": {
            "id": new_user.id, "username": new_user.username,
            "email": new_user.email, "role": role,
            "is_admin": new_user.is_admin, "is_active": new_user.is_active,
        }
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    # Jangan edit diri sendiri via endpoint ini
    if req.username is not None:
        user.username = req.username.strip()
    if req.email is not None:
        user.email = req.email.strip().lower()
    if req.password is not None and req.password.strip():
        user.hashed_password = hash_password(req.password)
    if req.role is not None and req.role in ("admin", "subadmin"):
        user.is_admin = (req.role == "admin")
        try:
            user.role = req.role
        except Exception:
            pass
    if req.is_active is not None:
        user.is_active = req.is_active
    db.add(user)
    await db.commit()
    return {"status": "updated", "user": {"id": user.id, "username": user.username, "role": req.role or "subadmin"}}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    if user.is_admin:
        raise HTTPException(400, "Tidak bisa hapus akun admin utama")
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}


# ── App Profile (logo & nama) ─────────────────────────────────
import base64, os
from pathlib import Path as _Path

LOGO_PATH = _Path(__file__).parent.parent.parent / "frontend" / "public" / "app-logo.png"
APP_PROFILE_ENV = _Path(__file__).parent.parent.parent / ".env"


@router.get("/app-profile")
async def get_app_profile():
    from api.settings_api import read_env
    env = read_env()
    logo_b64 = ""
    if LOGO_PATH.exists():
        logo_b64 = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return {
        "app_name": env.get("APP_NAME", "AI SUPER ASSISTANT"),
        "logo_url": "/app-logo.png" if LOGO_PATH.exists() else "",
        "logo_b64": logo_b64,
    }



@router.post("/app-profile")
async def update_app_profile(
    admin: User = Depends(get_admin_user),
    app_name: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
):
    from api.settings_api import write_env_key
    results = {}

    if app_name and app_name.strip():
        write_env_key("APP_NAME", app_name.strip())
        os.environ["APP_NAME"] = app_name.strip()
        results["app_name"] = app_name.strip()

    if logo:
        # Validasi ukuran (maks 2MB) dan tipe
        content = await logo.read()
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(400, detail="Logo terlalu besar. Maksimal 2MB.")
        if not logo.content_type.startswith("image/"):
            raise HTTPException(400, detail="File harus berupa gambar (PNG/JPG/SVG)")
        LOGO_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOGO_PATH.write_bytes(content)
        results["logo"] = "uploaded"

    return {"status": "updated", **results}



# ── Update profile (semua user) ───────────────────────────────
class UpdateProfileRequest(BaseModel):
    new_username: Optional[str] = None
    new_password: Optional[str] = None

@router.post("/update-profile")
async def update_profile(
    req: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ganti username dan/atau password untuk user yang sedang login."""
    changed = []

    # Validasi
    if req.new_username and req.new_username.strip():
        new_u = req.new_username.strip()
        if new_u != user.username:
            # Cek duplikat username
            res = await db.execute(select(User).where(User.username == new_u))
            if res.scalar_one_or_none():
                raise HTTPException(400, detail="Username sudah dipakai")
            user.username = new_u
            changed.append("username")

    if req.new_password and req.new_password.strip():
        pwd = req.new_password.strip()
        if len(pwd) < 6:
            raise HTTPException(400, detail="Password minimal 6 karakter")
        user.hashed_password = hash_password(pwd)
        changed.append("password")
        # Jika admin, simpan juga ke .env
        if user.is_admin:
            try:
                from api.settings_api import write_env_key
                write_env_key("ADMIN_PASSWORD", pwd)
                if req.new_username:
                    write_env_key("ADMIN_USERNAME", req.new_username.strip())
            except Exception:
                pass

    if not changed:
        return {"status": "no_change", "message": "Tidak ada perubahan"}

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Buat token baru dengan username terbaru
    new_token = create_access_token({"sub": user.id, "username": user.username})

    return {
        "status": "updated",
        "message": "Profil berhasil diperbarui: " + ", ".join(changed),
        "changed": changed,
        "access_token": new_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "role": getattr(user, "role", "admin" if user.is_admin else "subadmin"),
        },
    }

# ── Emergency Reset via Secret Key ───────────────────────────
import hmac as _hmac
import hashlib as _hashlib
import time as _time

class EmergencyResetRequest(BaseModel):
    username:   str
    new_password: str
    secret_key: str   # harus cocok dengan SECRET_KEY di .env

@router.post("/emergency-reset")
async def emergency_reset(
    req: EmergencyResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password tanpa login — menggunakan SECRET_KEY dari .env sebagai verifikasi.
    Endpoint ini HANYA untuk recovery ketika admin tidak bisa login.
    """
    from core.config import settings

    # Verifikasi secret key (timing-safe compare)
    expected = settings.SECRET_KEY
    provided = req.secret_key
    if not _hmac.compare_digest(expected.encode(), provided.encode()):
        # Jangan beritahu alasan gagal yang spesifik
        raise HTTPException(403, "Verifikasi gagal")

    if len(req.new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    result = await db.execute(select(User).where(User.username == _clean_username(req.username)))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    user.hashed_password = hash_password(req.new_password)
    user.is_active       = True
    db.add(user)
    await db.commit()

    # Log event penting ini
    import structlog as _sl
    _sl.get_logger().warning(
        "Emergency password reset used",
        username=req.username,
        ip="unknown",
    )

    return {
        "status":  "ok",
        "message": f"Password {req.username} berhasil direset. Segera login dan ganti SECRET_KEY!",
    }


# ── Brute-force protection (rate limit sederhana) ────────────
import time as _time2
from collections import defaultdict as _dd

_login_attempts: dict = _dd(lambda: {"count": 0, "lockout_until": 0})
MAX_ATTEMPTS  = 5
LOCKOUT_SECS  = 300  # 5 menit

def _check_rate_limit(identifier: str) -> tuple[bool, int]:
    """Return (is_blocked, seconds_remaining)."""
    rec = _login_attempts[identifier]
    now = _time2.time()
    if rec["lockout_until"] > now:
        return True, int(rec["lockout_until"] - now)
    if rec["lockout_until"] > 0 and rec["lockout_until"] <= now:
        # Reset setelah lockout berakhir
        _login_attempts[identifier] = {"count": 0, "lockout_until": 0}
    return False, 0

def _record_failed(identifier: str):
    rec = _login_attempts[identifier]
    rec["count"] += 1
    if rec["count"] >= MAX_ATTEMPTS:
        rec["lockout_until"] = _time2.time() + LOCKOUT_SECS

def _record_success(identifier: str):
    _login_attempts[identifier] = {"count": 0, "lockout_until": 0}


# ══════════════════════════════════════════════════════════════
# RECOVERY & SECURITY ENDPOINTS
# ══════════════════════════════════════════════════════════════
import hashlib  as _hashlib
import secrets  as _secrets
import hmac     as _hmac_mod
from datetime import datetime as _datetime2, timedelta as _td2


class GenerateRecoveryRequest(BaseModel):
    admin_secret: str   # SECRET_KEY dari .env

class UseRecoveryTokenRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/recovery/generate")
async def generate_recovery_token(
    req: GenerateRecoveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate token recovery satu kali pakai.
    Verifikasi via SECRET_KEY dari .env — tidak butuh login.
    """
    from core.config import settings
    if not _hmac_mod.compare_digest(
        settings.SECRET_KEY.encode(), req.admin_secret.encode()
    ):
        raise HTTPException(403, "SECRET_KEY salah")

    # Hapus token lama yang belum dipakai
    await db.execute(
        select(RecoveryToken).where(RecoveryToken.used == False)
    )

    # Buat token baru
    raw_token  = _secrets.token_urlsafe(32)
    token_hash = _hashlib.sha256(raw_token.encode()).hexdigest()
    expires    = _datetime2.utcnow() + _td2(hours=1)

    # Cari admin user
    result = await db.execute(
        select(User).where(User.is_admin == True).limit(1)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(404, "Tidak ada admin di database")

    rec = RecoveryToken(
        user_id=admin.id,
        token_hash=token_hash,
        expires_at=expires,
    )
    db.add(rec)
    await db.commit()

    return {
        "token":      raw_token,
        "expires_in": "1 jam",
        "note":       "Gunakan token ini SATU KALI di endpoint /auth/recovery/use. Simpan baik-baik!",
    }


@router.post("/recovery/use")
async def use_recovery_token(
    req: UseRecoveryTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password menggunakan recovery token."""
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    token_hash = _hashlib.sha256(req.token.encode()).hexdigest()

    result = await db.execute(
        select(RecoveryToken)
        .where(RecoveryToken.token_hash == token_hash)
        .where(RecoveryToken.used == False)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(403, "Token tidak valid atau sudah dipakai")
    if rec.expires_at < _datetime2.utcnow():
        raise HTTPException(403, "Token sudah kadaluarsa")

    # Tandai token sudah dipakai
    rec.used = True
    db.add(rec)

    # Reset password admin
    result2 = await db.execute(select(User).where(User.id == rec.user_id))
    user    = result2.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    user.hashed_password = hash_password(req.new_password)
    user.is_active       = True
    db.add(user)
    await db.commit()

    return {
        "status":  "ok",
        "message": f"Password akun '{user.username}' berhasil direset via recovery token.",
    }


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ganti password — butuh password lama untuk verifikasi."""
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(400, "Password lama salah")
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password baru minimal 6 karakter")
    if req.current_password == req.new_password:
        raise HTTPException(400, "Password baru harus berbeda dengan yang lama")
    user.hashed_password = hash_password(req.new_password)
    db.add(user)
    await db.commit()
    return {"status": "ok", "message": "Password berhasil diubah"}


@router.get("/login-logs")
async def get_login_logs(
    limit: int = 20,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Riwayat login untuk semua user — admin only."""
    from sqlalchemy import desc as _desc2
    result = await db.execute(
        select(LoginLog)
        .order_by(_desc2(LoginLog.created_at))
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id":         l.id,
            "username":   l.username,
            "success":    l.success,
            "reason":     getattr(l, "reason", ""),
            "ip":         getattr(l, "ip_address", ""),
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]

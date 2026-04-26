from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
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


# ══════════════════════════════════════════════════════════════
# PATCH 2: Rate limiting berbasis Redis (bukan in-memory dict)
# Efektif di multi-worker deployment
# ══════════════════════════════════════════════════════════════
import time as _time
from collections import defaultdict as _dd

MAX_ATTEMPTS = 5
LOCKOUT_SECS = 300  # 5 menit

# Fallback in-memory jika Redis tidak tersedia
_memory_attempts: dict = _dd(lambda: {"count": 0, "lockout_until": 0})


async def _get_redis():
    """Ambil Redis client dari memory_manager jika tersedia."""
    try:
        from memory.manager import memory_manager
        if memory_manager._redis_available and memory_manager.redis:
            return memory_manager.redis
    except Exception:
        pass
    return None


async def _check_rate_limit_redis(identifier: str, redis) -> tuple[bool, int]:
    """Rate limit check via Redis — shared across all workers."""
    now = _time.time()
    key_count   = f"login:count:{identifier}"
    key_lockout = f"login:lockout:{identifier}"

    lockout_until = await redis.get(key_lockout)
    if lockout_until:
        remaining = float(lockout_until) - now
        if remaining > 0:
            return True, int(remaining)
        # Lockout expired, hapus
        await redis.delete(key_lockout, key_count)

    return False, 0


async def _record_failed_redis(identifier: str, redis):
    key_count   = f"login:count:{identifier}"
    key_lockout = f"login:lockout:{identifier}"

    count = await redis.incr(key_count)
    await redis.expire(key_count, LOCKOUT_SECS * 2)

    if count >= MAX_ATTEMPTS:
        lockout_until = _time.time() + LOCKOUT_SECS
        await redis.setex(key_lockout, LOCKOUT_SECS, str(lockout_until))


async def _record_success_redis(identifier: str, redis):
    await redis.delete(
        f"login:count:{identifier}",
        f"login:lockout:{identifier}",
    )


def _check_rate_limit_memory(identifier: str) -> tuple[bool, int]:
    rec = _memory_attempts[identifier]
    now = _time.time()
    if rec["lockout_until"] > now:
        return True, int(rec["lockout_until"] - now)
    if rec["lockout_until"] > 0 and rec["lockout_until"] <= now:
        _memory_attempts[identifier] = {"count": 0, "lockout_until": 0}
    return False, 0


def _record_failed_memory(identifier: str):
    rec = _memory_attempts[identifier]
    rec["count"] += 1
    if rec["count"] >= MAX_ATTEMPTS:
        rec["lockout_until"] = _time.time() + LOCKOUT_SECS


def _record_success_memory(identifier: str):
    _memory_attempts[identifier] = {"count": 0, "lockout_until": 0}


# ══════════════════════════════════════════════════════════════
# PATCH 3: Login — tambahkan IP address ke LoginLog
# PATCH 2: Rate limiting via Redis (dengan fallback memory)
# ══════════════════════════════════════════════════════════════
@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    identifier = "user:" + req.username.lower()

    # Ambil IP address untuk audit log
    client_ip = request.client.host if request.client else ""
    # Support X-Forwarded-For untuk reverse proxy / Cloudflare
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "")[:200]

    # Cek rate limit (Redis-first, fallback memory)
    redis = await _get_redis()
    if redis:
        blocked, secs = await _check_rate_limit_redis(identifier, redis)
    else:
        blocked, secs = _check_rate_limit_memory(identifier)

    if blocked:
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {secs} detik.",
        )

    result = await db.execute(select(User).where(User.username == _clean_username(req.username)))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        # Record failure
        if redis:
            await _record_failed_redis(identifier, redis)
        else:
            _record_failed_memory(identifier)

        # ✅ PATCH: Isi ip_address & user_agent di LoginLog
        db.add(LoginLog(
            username=req.username,
            success=False,
            reason="wrong_password",
            ip_address=client_ip,
            user_agent=user_agent,
        ))
        await db.commit()

        # Hitung sisa percobaan
        if redis:
            count_key = f"login:count:{identifier}"
            count = int(await redis.get(count_key) or 0)
        else:
            count = _memory_attempts[identifier]["count"]

        remaining = MAX_ATTEMPTS - count
        if remaining > 0:
            raise HTTPException(
                status_code=401,
                detail=f"Username atau password salah. {remaining} percobaan tersisa.",
            )
        else:
            raise HTTPException(
                status_code=429,
                detail="Akun terkunci 5 menit karena terlalu banyak percobaan gagal.",
            )

    if not user.is_active:
        db.add(LoginLog(
            username=req.username,
            success=False,
            reason="inactive",
            ip_address=client_ip,
            user_agent=user_agent,
        ))
        await db.commit()
        raise HTTPException(status_code=403, detail="Akun tidak aktif. Hubungi admin.")

    # Login berhasil — reset rate limit
    if redis:
        await _record_success_redis(identifier, redis)
    else:
        _record_success_memory(identifier)

    # ✅ PATCH: Catat login sukses dengan IP
    db.add(LoginLog(
        username=req.username,
        success=True,
        ip_address=client_ip,
        user_agent=user_agent,
    ))
    await db.commit()

    token = create_access_token({"sub": user.id, "username": user.username})

    totp_enabled     = getattr(user, "totp_enabled", False)
    telegram_chat_id = getattr(user, "telegram_chat_id", None)
    require_2fa = None
    if totp_enabled:
        require_2fa = "totp"
    elif telegram_chat_id:
        require_2fa = "telegram"

    return {
        "access_token": token,
        "token_type": "bearer",
        "require_2fa": require_2fa,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "role": getattr(user, "role", "admin" if user.is_admin else "subadmin"),
        },
    }


# ══════════════════════════════════════════════════════════════
# PATCH 4: Register — hanya admin atau jika ALLOW_PUBLIC_REGISTER=true
# ══════════════════════════════════════════════════════════════
@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    from core.config import settings

    # ✅ PATCH: Blokir registrasi publik kecuali admin mengizinkan
    if not settings.ALLOW_PUBLIC_REGISTER:
        # Cek apakah sudah ada user (jika belum ada, izinkan untuk inisialisasi pertama)
        result = await db.execute(select(User))
        existing_users = result.scalars().all()
        if existing_users:
            raise HTTPException(
                status_code=403,
                detail="Registrasi publik dinonaktifkan. Hubungi admin untuk membuat akun.",
            )

    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password minimal 6 karakter")

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
        "role": getattr(current_user, "role", "admin" if current_user.is_admin else "subadmin"),
    }


# ── User Management (Admin only) ──────────────────────────────
from core.auth import get_admin_user
import uuid as _uuid

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "subadmin"

class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/users")
async def list_users(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [
        {
            "id": u.id, "username": u.username, "email": u.email,
            "role": getattr(u, "role", "admin" if u.is_admin else "subadmin"),
            "is_admin": u.is_admin, "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users")
async def create_user(req: CreateUserRequest, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username == req.username))
    if res.scalar_one_or_none():
        raise HTTPException(400, detail="Username sudah digunakan")
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
async def update_user(user_id: str, req: UpdateUserRequest, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
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
    return {"status": "updated", "user": {"id": user.id, "username": user.username}}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    if user.is_admin:
        raise HTTPException(400, "Tidak bisa hapus akun admin utama")
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}


# ── App Profile ───────────────────────────────────────────────
import base64, os
from pathlib import Path as _Path

LOGO_PATH = _Path(__file__).parent.parent.parent / "frontend" / "public" / "app-logo.png"

@router.get("/app-profile")
async def get_app_profile():
    from api.settings_api import read_env
    env = read_env()
    logo_b64 = ""
    if LOGO_PATH.exists():
        logo_b64 = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return {
        "app_name": env.get("APP_NAME", "AI ORCHESTRATOR"),
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
        content = await logo.read()
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(400, detail="Logo terlalu besar. Maksimal 2MB.")
        if not logo.content_type.startswith("image/"):
            raise HTTPException(400, detail="File harus berupa gambar")
        LOGO_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOGO_PATH.write_bytes(content)
        results["logo"] = "uploaded"
    return {"status": "updated", **results}


# ── Update profile ────────────────────────────────────────────
class UpdateProfileRequest(BaseModel):
    new_username: Optional[str] = None
    new_password: Optional[str] = None

@router.post("/update-profile")
async def update_profile(req: UpdateProfileRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    changed = []
    if req.new_username and req.new_username.strip():
        new_u = req.new_username.strip()
        if new_u != user.username:
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
    new_token = create_access_token({"sub": user.id, "username": user.username})
    return {
        "status": "updated",
        "message": "Profil berhasil diperbarui: " + ", ".join(changed),
        "changed": changed,
        "access_token": new_token,
        "user": {
            "id": user.id, "username": user.username,
            "email": user.email, "is_admin": user.is_admin,
            "role": getattr(user, "role", "admin" if user.is_admin else "subadmin"),
        },
    }

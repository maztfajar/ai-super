"""
AI ORCHESTRATOR — Auth 2FA API
Email reset, Telegram OTP, TOTP setup & verify
"""
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import User, LoginLog
from core.auth import get_current_user, hash_password, create_access_token, verify_password
from core.totp_service import (
    new_secret, get_qr_uri, generate_totp, verify_totp,
    generate_otp, verify_otp, has_pending_otp,
)
from core.email_service import send_password_reset, send_otp_email, test_smtp


# ── FIX BUG 1: _clean_username yang benar ────────────────────
def _clean_username(username: str) -> str:
    """Strip @ dan whitespace dari username input."""
    if not username:
        return ""
    return username.strip().lstrip("@")


router = APIRouter()

# ── In-memory email reset tokens ─────────────────────────────
_email_tokens: dict = {}
EMAIL_TOKEN_TTL = 15 * 60  # 15 menit


def _hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


# ══════════════════════════════════════════════════════════════
# RESET PASSWORD VIA EMAIL
# ══════════════════════════════════════════════════════════════

@router.post("/email/send-reset")
async def send_email_reset(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    from core.config import settings

    res = await db.execute(select(User).where(User.email == email.lower().strip()))
    user = res.scalar_one_or_none()

    generic_resp = {
        "status": "sent",
        "message": "Jika email terdaftar, link reset akan dikirim dalam beberapa menit."
    }

    if not user or not user.is_active:
        return generic_resp

    token  = secrets.token_urlsafe(32)
    hashed = _hash(token)
    _email_tokens[hashed] = {
        "user_id":    user.id,
        "expires_at": time.time() + EMAIL_TOKEN_TTL,
    }

    reset_link = f"{settings.APP_URL}/reset-password?token={token}"
    ok, err = send_password_reset(user.email, user.username, reset_link)

    if not ok:
        import structlog
        structlog.get_logger().error("Email send failed", error=err, user=user.username)
        return {
            "status":  "smtp_error",
            "message": "Email gagal dikirim. Hubungi admin.",
            "error":   err,
            "token":   token,
        }

    return generic_resp


@router.post("/email/reset-password")
async def reset_password_via_email(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    if len(new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    hashed = _hash(token)
    rec    = _email_tokens.get(hashed)

    if not rec:
        raise HTTPException(400, "Link tidak valid atau sudah expired")
    if time.time() > rec["expires_at"]:
        del _email_tokens[hashed]
        raise HTTPException(400, "Link sudah kadaluarsa (15 menit). Minta link baru.")

    del _email_tokens[hashed]

    res  = await db.execute(select(User).where(User.id == rec["user_id"]))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="password_reset_via_email"))
    await db.commit()
    return {"status": "ok", "message": f"Password {user.username} berhasil direset"}


@router.post("/email/test-smtp")
async def test_smtp_connection(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403)
    ok, msg = test_smtp()
    return {"ok": ok, "message": msg}


@router.get("/email/smtp-status")
async def smtp_status(user: User = Depends(get_current_user)):
    from core.config import settings
    configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS)
    return {
        "configured": configured,
        "host":       settings.SMTP_HOST or "",
        "port":       settings.SMTP_PORT,
        "user":       settings.SMTP_USER or "",
        "tls":        settings.SMTP_TLS,
        "app_url":    settings.APP_URL,
    }


# ══════════════════════════════════════════════════════════════
# OTP VIA TELEGRAM
# ══════════════════════════════════════════════════════════════

@router.post("/telegram-otp/setup")
async def setup_telegram_otp(
    telegram_chat_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.telegram_chat_id = telegram_chat_id.strip()
    db.add(user)
    await db.commit()

    otp = generate_otp("setup_test_" + user.id)
    ok  = await _send_telegram_otp(telegram_chat_id, user.username, otp)
    if not ok:
        raise HTTPException(400,
            "Gagal kirim ke Telegram. Pastikan Anda sudah kirim /start ke bot dulu.")

    return {"status": "ok", "message": "Chat ID tersimpan. Cek Telegram untuk kode test."}


@router.post("/telegram-otp/verify-setup")
async def verify_telegram_otp_setup(
    otp_code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    valid, msg = verify_otp("setup_test_" + user.id, otp_code)
    if not valid:
        raise HTTPException(400, msg)
    return {"status": "ok", "message": "OTP Telegram aktif!"}


@router.post("/telegram-otp/disable")
async def disable_telegram_otp(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.telegram_chat_id = None
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="telegram_otp_disabled"))
    await db.commit()
    return {"status": "ok", "message": "Telegram OTP berhasil dinonaktifkan"}


@router.post("/telegram-otp/send")
async def send_telegram_otp_login(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    clean = _clean_username(username)
    res   = await db.execute(select(User).where(User.username == clean))
    user  = res.scalar_one_or_none()
    if not user or not getattr(user, "telegram_chat_id", None):
        raise HTTPException(400, "User tidak terdaftar atau Telegram OTP belum disetup")

    otp_key = "login_otp_" + user.id
    if has_pending_otp(otp_key):
        raise HTTPException(429, "OTP sudah dikirim. Tunggu 5 menit atau minta kode baru.")

    otp = generate_otp(otp_key)
    ok  = await _send_telegram_otp(getattr(user, "telegram_chat_id", ""), user.username, otp)
    if not ok:
        raise HTTPException(500, "Gagal kirim OTP ke Telegram")

    return {"status": "sent", "message": "Kode OTP dikirim ke Telegram Anda"}


@router.post("/telegram-otp/verify-login")
async def verify_telegram_otp_login(
    username: str,
    otp_code: str,
    db: AsyncSession = Depends(get_db),
):
    clean = _clean_username(username)
    res   = await db.execute(select(User).where(User.username == clean))
    user  = res.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "User tidak ditemukan")

    valid, msg = verify_otp("login_otp_" + user.id, otp_code)
    if not valid:
        db.add(LoginLog(username=username, success=False, reason="wrong_otp_telegram"))
        await db.commit()
        raise HTTPException(401, msg)

    db.add(LoginLog(username=username, success=True, reason="otp_telegram_login"))
    await db.commit()
    token = create_access_token({"sub": user.id, "username": user.username})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id": user.id, "username": user.username, "email": user.email,
            "is_admin": user.is_admin,
            "role": getattr(user, "role", "admin" if user.is_admin else "subadmin"),
        },
    }


async def _send_telegram_otp(chat_id: str, username: str, otp: str) -> bool:
    import os, httpx
    import structlog
    log = structlog.get_logger()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        from core.config import settings
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        log.error("Telegram OTP: TELEGRAM_BOT_TOKEN tidak ditemukan")
        return False
    if not chat_id or not chat_id.strip():
        log.error("Telegram OTP: chat_id kosong", username=username)
        return False

    msg = (
        f"🔐 Kode OTP AI ORCHESTRATOR\n\n"
        f"Halo {username}!\n\n"
        f"Kode verifikasi Anda:\n\n"
        f"  {otp}\n\n"
        f"Berlaku 5 menit. Jangan bagikan ke siapapun."
    )
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id.strip(), "text": msg},
            )
        if r.status_code == 200:
            log.info("Telegram OTP sent", username=username)
            return True
        else:
            body = r.json() if "application/json" in r.headers.get("content-type", "") else {}
            log.error("Telegram OTP failed", status=r.status_code,
                      desc=body.get("description", ""))
            return False
    except Exception as e:
        log.error("Telegram OTP exception", error=str(e))
        return False


# ══════════════════════════════════════════════════════════════
# TOTP (Google Authenticator)
# ══════════════════════════════════════════════════════════════

_otp_store_2fa: dict = {}


@router.post("/totp/setup/start")
async def totp_setup_start(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from core.config import settings
    secret = new_secret()
    qr_uri = get_qr_uri(secret, user.username, issuer=settings.APP_NAME)

    _otp_store_2fa["setup_" + user.id] = {
        "secret":     secret,
        "expires_at": time.time() + 600,
    }

    return {
        "secret": secret,
        "qr_uri": qr_uri,
        "instructions": [
            "1. Buka Google Authenticator / Authy / FreeOTP di HP Anda",
            "2. Ketuk '+' → Scan QR code di bawah",
            "3. Masukkan kode 6 digit yang muncul di kolom verifikasi",
            "4. Klik 'Aktifkan 2FA'",
        ],
    }


@router.post("/totp/setup/verify")
async def totp_setup_verify(
    code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = _otp_store_2fa.get("setup_" + user.id)
    if not rec or time.time() > rec["expires_at"]:
        raise HTTPException(400, "Setup session kadaluarsa. Mulai ulang setup 2FA.")

    if not verify_totp(rec["secret"], code):
        raise HTTPException(400, "Kode salah. Pastikan waktu HP Anda sinkron.")

    user.totp_secret  = rec["secret"]
    user.totp_enabled = True
    db.add(user)
    await db.commit()

    del _otp_store_2fa["setup_" + user.id]
    db.add(LoginLog(username=user.username, success=True, reason="2fa_totp_enabled"))
    await db.commit()

    return {"status": "ok", "message": "2FA berhasil diaktifkan!"}


@router.post("/totp/disable")
async def totp_disable(
    password: str,
    code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(password, user.hashed_password):
        raise HTTPException(403, "Password salah")
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(400, "2FA tidak aktif")
    if not verify_totp(user.totp_secret, code):
        raise HTTPException(400, "Kode 2FA salah")

    user.totp_secret  = None
    user.totp_enabled = False
    db.add(user)
    db.add(LoginLog(username=user.username, success=True, reason="2fa_totp_disabled"))
    await db.commit()
    return {"status": "ok", "message": "2FA dinonaktifkan"}


@router.post("/totp/verify-login")
async def totp_verify_login(
    username: str,
    code: str,
    db: AsyncSession = Depends(get_db),
):
    clean = _clean_username(username)
    res   = await db.execute(select(User).where(User.username == clean))
    user  = res.scalar_one_or_none()
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(400, "TOTP tidak aktif untuk user ini")

    if not verify_totp(user.totp_secret, code):
        db.add(LoginLog(username=username, success=False, reason="wrong_totp_code"))
        await db.commit()
        raise HTTPException(401, "Kode 2FA salah atau sudah expired. Coba kode berikutnya.")

    db.add(LoginLog(username=username, success=True, reason="totp_2fa_login"))
    await db.commit()
    token = create_access_token({"sub": user.id, "username": user.username})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id": user.id, "username": user.username, "email": user.email,
            "is_admin": user.is_admin,
            "role": getattr(user, "role", "admin" if user.is_admin else "subadmin"),
        },
    }


@router.get("/totp/status")
async def totp_status(user: User = Depends(get_current_user)):
    return {
        "totp_enabled":       user.totp_enabled,
        "telegram_otp_ready": bool(getattr(user, "telegram_chat_id", None)),
    }


# ══════════════════════════════════════════════════════════════
# RESET PASSWORD VIA TELEGRAM OTP
# ══════════════════════════════════════════════════════════════

@router.post("/telegram-otp/send-reset")
async def send_telegram_otp_reset(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    # ── FIX BUG 2: gunakan _clean_username yang sudah diperbaiki ──
    clean = _clean_username(username)
    res   = await db.execute(select(User).where(User.username == clean))
    user  = res.scalar_one_or_none()

    if not user:
        raise HTTPException(400, "Username tidak ditemukan")

    chat_id = getattr(user, "telegram_chat_id", None) or ""
    if not chat_id:
        raise HTTPException(400, (
            "Telegram OTP belum disetup untuk akun ini. "
            "Setup dulu di menu 2FA & Login setelah login dengan cara lain."
        ))

    otp_key = "reset_otp_" + user.id
    if has_pending_otp(otp_key):
        raise HTTPException(429, "OTP sudah dikirim. Tunggu 5 menit atau minta kode baru.")

    otp = generate_otp(otp_key)
    ok  = await _send_telegram_otp(chat_id, user.username, otp)

    if not ok:
        raise HTTPException(500, (
            "Gagal kirim OTP ke Telegram. Kemungkinan penyebab: "
            "1) Bot Telegram belum aktif, "
            "2) TELEGRAM_BOT_TOKEN tidak diset, "
            "3) Chat ID salah."
        ))

    return {"status": "sent", "message": "Kode OTP dikirim ke Telegram Anda"}


class TelegramPasswordResetRequest(BaseModel):
    username:     str
    otp_code:     str
    new_password: str


@router.post("/telegram-otp/reset-password")
async def telegram_otp_reset_password(
    req: TelegramPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    # ── FIX BUG 2: gunakan req.username dengan benar ──
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")

    clean = _clean_username(req.username)  # ← FIXED: req.username bukan req._clean_username(username)
    res   = await db.execute(select(User).where(User.username == clean))
    user  = res.scalar_one_or_none()

    if not user or not getattr(user, "telegram_chat_id", None):
        raise HTTPException(400, "User tidak ditemukan atau Telegram OTP belum disetup")

    valid, msg = verify_otp("reset_otp_" + user.id, req.otp_code.strip())
    if not valid:
        db.add(LoginLog(username=req.username, success=False, reason="wrong_otp_reset"))
        await db.commit()
        raise HTTPException(401, msg)

    user.hashed_password = hash_password(req.new_password)
    db.add(user)
    db.add(LoginLog(
        username=req.username,
        success=True,
        reason="password_reset_via_telegram_otp"
    ))
    await db.commit()

    return {"status": "ok", "message": f"Password {user.username} berhasil direset"}


@router.get("/telegram-otp/check/{username}")
async def check_telegram_setup(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    clean = _clean_username(username)
    res   = await db.execute(select(User).where(User.username == clean))
    user  = res.scalar_one_or_none()

    if not user:
        return {"found": False, "has_telegram": False, "message": "User tidak ditemukan"}

    chat_id = getattr(user, "telegram_chat_id", None)
    return {
        "found":        True,
        "has_telegram": bool(chat_id),
        "message": "Telegram OTP sudah disetup" if chat_id else "Telegram OTP belum disetup",
    }

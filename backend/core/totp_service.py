"""
AI ORCHESTRATOR — TOTP Service
Two-Factor Authentication via Google Authenticator / Authy / FreeOTP
Tidak butuh library pihak ketiga — implementasi TOTP RFC 6238 murni Python
"""
import hmac
import hashlib
import base64
import time
import struct
import secrets
import os


def _hotp(key_bytes: bytes, counter: int) -> int:
    msg = struct.pack(">Q", counter)
    h = hmac.new(key_bytes, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
    return code % 1_000_000


def generate_totp(secret_b32: str, window: int = 0) -> str:
    """Generate kode TOTP 6 digit untuk window waktu tertentu."""
    key = base64.b32decode(secret_b32.upper().replace(" ", ""))
    counter = int(time.time()) // 30 + window
    code = _hotp(key, counter)
    return str(code).zfill(6)


def verify_totp(secret_b32: str, code: str, tolerance: int = 1) -> bool:
    """
    Verifikasi kode TOTP. tolerance=1 artinya kode ±30 detik masih diterima
    (mengatasi masalah clock skew antara server dan HP user).
    """
    if not code or len(code) != 6 or not code.isdigit():
        return False
    for w in range(-tolerance, tolerance + 1):
        if generate_totp(secret_b32, window=w) == code:
            return True
    return False


def new_secret() -> str:
    """Generate Base32 secret baru untuk user."""
    raw = secrets.token_bytes(20)   # 160 bits = standar TOTP
    return base64.b32encode(raw).decode().rstrip("=")


def get_qr_uri(secret: str, username: str, issuer: str = "AI ORCHESTRATOR") -> str:
    """
    Buat otpauth:// URI yang bisa di-scan oleh Google Authenticator.
    QR code di-render di frontend menggunakan library qrcode.js
    """
    import urllib.parse
    secret_padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    label = urllib.parse.quote(f"{issuer}:{username}")
    params = urllib.parse.urlencode({
        "secret": secret_padded,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    })
    return f"otpauth://totp/{label}?{params}"


# ── OTP untuk Telegram / Email (6 digit, 5 menit) ────────────
_otp_store: dict = {}   # { key: { code, expires_at, attempts } }
OTP_TTL      = 5 * 60   # 5 menit
OTP_MAX_TRY  = 5


def generate_otp(key: str) -> str:
    """Buat OTP 6 digit dan simpan di memory."""
    code = str(secrets.randbelow(900000) + 100000)   # 100000-999999
    _otp_store[key] = {
        "code":       code,
        "expires_at": time.time() + OTP_TTL,
        "attempts":   0,
    }
    return code


def verify_otp(key: str, code: str) -> tuple[bool, str]:
    """
    Verifikasi OTP. Return (valid, message).
    OTP dihapus setelah terpakai atau maks percobaan terlampaui.
    """
    rec = _otp_store.get(key)
    if not rec:
        return False, "Kode OTP tidak ditemukan atau sudah kadaluarsa"
    if time.time() > rec["expires_at"]:
        del _otp_store[key]
        return False, "Kode OTP sudah kadaluarsa (5 menit)"
    rec["attempts"] += 1
    if rec["attempts"] > OTP_MAX_TRY:
        del _otp_store[key]
        return False, "Terlalu banyak percobaan. Minta kode OTP baru."
    if rec["code"] != code.strip():
        remaining = OTP_MAX_TRY - rec["attempts"]
        return False, f"Kode salah. {remaining} percobaan tersisa."
    del _otp_store[key]
    return True, "OK"


def has_pending_otp(key: str) -> bool:
    rec = _otp_store.get(key)
    if not rec:
        return False
    if time.time() > rec["expires_at"]:
        del _otp_store[key]
        return False
    return True

"""
AI ORCHESTRATOR — Email Service
Kirim email via SMTP untuk reset password
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import structlog

log = structlog.get_logger()


def _html_template(title: str, body_html: str, app_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="id">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#16181f;border:1px solid #2a2d3e;border-radius:16px;overflow:hidden;">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#5b63f7,#7c3aed);padding:28px 32px;text-align:center;">
      <div style="font-size:32px;margin-bottom:8px;">🧠</div>
      <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700;">AI ORCHESTRATOR</h1>
      <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:12px;">AI Orchestrator</p>
    </div>
    <!-- Body -->
    <div style="padding:32px;">
      {body_html}
    </div>
    <!-- Footer -->
    <div style="padding:16px 32px;border-top:1px solid #2a2d3e;text-align:center;">
      <p style="margin:0;color:#4a5568;font-size:11px;">
        Email ini dikirim otomatis oleh AI ORCHESTRATOR.<br>
        Jika Anda tidak merasa meminta ini, abaikan saja.
      </p>
      <a href="{app_url}" style="color:#5b63f7;font-size:11px;text-decoration:none;">{app_url}</a>
    </div>
  </div>
</body>
</html>"""


def send_email(to: str, subject: str, html: str) -> tuple[bool, str]:
    """Kirim email. Return (success, error_message)."""
    from core.config import settings

    if not settings.SMTP_HOST or not settings.SMTP_USER:
        return False, "SMTP belum dikonfigurasi di .env (SMTP_HOST, SMTP_USER, SMTP_PASS)"

    from_addr = settings.SMTP_FROM or settings.SMTP_USER
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"AI ORCHESTRATOR <{from_addr}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if settings.SMTP_TLS:
            # STARTTLS (port 587)
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
                s.sendmail(from_addr, [to], msg.as_string())
        else:
            # SSL langsung (port 465)
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx, timeout=15) as s:
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
                s.sendmail(from_addr, [to], msg.as_string())

        log.info("Email sent", to=to, subject=subject)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Autentikasi SMTP gagal — cek SMTP_USER dan SMTP_PASS di .env"
    except smtplib.SMTPConnectError:
        return False, f"Tidak bisa terhubung ke {settings.SMTP_HOST}:{settings.SMTP_PORT}"
    except Exception as e:
        log.error("Email error", error=str(e))
        return False, str(e)


def send_password_reset(to: str, username: str, reset_link: str) -> tuple[bool, str]:
    from core.config import settings
    body = f"""
      <h2 style="color:#d4d8f0;margin:0 0 16px;">Reset Password</h2>
      <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 24px;">
        Halo <strong style="color:#fff;">{username}</strong>,<br>
        Permintaan reset password untuk akun AI ORCHESTRATOR Anda diterima.
      </p>
      <div style="text-align:center;margin:28px 0;">
        <a href="{reset_link}"
          style="display:inline-block;background:linear-gradient(135deg,#5b63f7,#7c3aed);
                 color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;
                 font-weight:700;font-size:14px;">
          🔑 Reset Password Sekarang
        </a>
      </div>
      <div style="background:#1e2130;border:1px solid #2a2d3e;border-radius:10px;padding:16px;margin:0 0 20px;">
        <p style="margin:0;color:#6b7280;font-size:12px;">Atau copy link ini:</p>
        <p style="margin:6px 0 0;color:#5b63f7;font-size:11px;word-break:break-all;">{reset_link}</p>
      </div>
      <div style="background:#291f00;border:1px solid #7c5200;border-radius:10px;padding:14px;">
        <p style="margin:0;color:#d97706;font-size:12px;line-height:1.6;">
          ⚠️ <strong>Link berlaku 15 menit</strong> dan hanya bisa digunakan sekali.<br>
          Jika Anda tidak meminta reset password, abaikan email ini.
        </p>
      </div>
    """
    return send_email(
        to, "Reset Password AI ORCHESTRATOR",
        _html_template("Reset Password", body, settings.APP_URL)
    )


def send_otp_email(to: str, username: str, otp: str) -> tuple[bool, str]:
    from core.config import settings
    body = f"""
      <h2 style="color:#d4d8f0;margin:0 0 16px;">Kode Verifikasi Login</h2>
      <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 24px;">
        Halo <strong style="color:#fff;">{username}</strong>,<br>
        Gunakan kode berikut untuk menyelesaikan login:
      </p>
      <div style="background:#1a2030;border:2px solid #5b63f7;border-radius:16px;padding:28px;text-align:center;margin:0 0 24px;">
        <p style="margin:0 0 8px;color:#9ca3af;font-size:12px;letter-spacing:2px;text-transform:uppercase;">Kode OTP</p>
        <p style="margin:0;color:#fff;font-size:42px;font-weight:700;letter-spacing:12px;font-family:monospace;">{otp}</p>
      </div>
      <div style="background:#291f00;border:1px solid #7c5200;border-radius:10px;padding:14px;">
        <p style="margin:0;color:#d97706;font-size:12px;line-height:1.6;">
          ⚠️ Kode berlaku <strong>5 menit</strong>. Jangan bagikan ke siapapun.
        </p>
      </div>
    """
    return send_email(
        to, "Kode OTP Login AI ORCHESTRATOR",
        _html_template("Kode OTP", body, settings.APP_URL)
    )


def test_smtp() -> tuple[bool, str]:
    from core.config import settings
    if not settings.SMTP_HOST:
        return False, "SMTP_HOST kosong"
    try:
        if settings.SMTP_TLS:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
        else:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx, timeout=10) as s:
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
        return True, f"Koneksi SMTP ke {settings.SMTP_HOST}:{settings.SMTP_PORT} berhasil"
    except Exception as e:
        return False, str(e)

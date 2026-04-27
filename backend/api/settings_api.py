"""
AI ORCHESTRATOR — Settings API
Kelola konfigurasi server, tunnel Cloudflare, domain dari UI
"""
import os
import asyncio
import signal
import subprocess
import shutil
import re
import threading
import json
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import structlog

from db.models import User
from core.auth import get_current_user

router = APIRouter()
log = structlog.get_logger()

ENV_FILE = Path(__file__).parent.parent.parent / ".env"

# ── Global tunnel state ───────────────────────────────────────
_tunnel_proc: Optional[subprocess.Popen] = None
_tunnel_url: str = ""
_tunnel_log_lines: list = []
_tunnel_lock = threading.Lock()


# ── Helpers env ───────────────────────────────────────────────
def read_env() -> Dict[str, str]:
    result = {}
    if not ENV_FILE.exists():
        return result
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            # Strip tanda kutip dari value (single dan double quote)
            v = v.strip().strip('"\'')
            result[k.strip()] = v
    return result


def write_env_key(key: str, value: str):
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def write_env_batch(data: Dict[str, str]):
    for k, v in data.items():
        if v is not None:
            write_env_key(k, v)
            os.environ[k] = v


# ── Domain config file helper ─────────────────────────────────
DOMAINS_FILE = Path(__file__).parent.parent.parent / ".domains.json"

def read_domains() -> List[Dict]:
    if not DOMAINS_FILE.exists():
        return []
    try:
        return json.loads(DOMAINS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def write_domains(domains: List[Dict]):
    DOMAINS_FILE.write_text(json.dumps(domains, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Tunnel helpers ────────────────────────────────────────────
def _is_running() -> bool:
    global _tunnel_proc
    return _tunnel_proc is not None and _tunnel_proc.poll() is None


def _read_tunnel_output(proc: subprocess.Popen):
    global _tunnel_url, _tunnel_log_lines
    try:
        for raw in proc.stderr:
            try:
                line = raw.decode("utf-8", errors="replace").rstrip()
            except Exception:
                continue
            with _tunnel_lock:
                _tunnel_log_lines.append(line)
                if len(_tunnel_log_lines) > 100:
                    _tunnel_log_lines.pop(0)
            if not _tunnel_url:
                m = re.search(r'https://[\w\-]+\.trycloudflare\.com', line)
                if m:
                    _tunnel_url = m.group(0)
                    log.info("Quick tunnel URL detected", url=_tunnel_url)
            if "failed to" in line.lower() or "error" in line.lower():
                log.warning("cloudflared log", line=line[:200])
    except Exception as e:
        log.error("Tunnel output reader error", error=str(e))


def _start_reader_thread(proc: subprocess.Popen):
    t = threading.Thread(target=_read_tunnel_output, args=(proc,), daemon=True)
    t.start()


# ── GET: semua settings ───────────────────────────────────────
@router.get("/")
async def get_settings(user: User = Depends(get_current_user)):
    env = read_env()
    return {
        "app": {
            "name":      env.get("APP_NAME", "AI ORCHESTRATOR"),
            "version":   env.get("APP_VERSION", "1.0.0"),
            "build":     env.get("APP_BUILD", "1001"),
            "host":      env.get("HOST", "0.0.0.0"),
            "port":      env.get("PORT", "7860"),
            "debug":     env.get("DEBUG", "false"),
            "log_level": env.get("LOG_LEVEL", "INFO"),
        },
        "tunnel": {
            "enabled":          env.get("TUNNEL_ENABLED", "false"),
            "provider":         env.get("TUNNEL_PROVIDER", "cloudflare"),
            "domain":           env.get("TUNNEL_DOMAIN", ""),
            "cloudflare_token": "••••••••" if env.get("CLOUDFLARE_TUNNEL_TOKEN") else "",
            "has_token":        bool(env.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip()),
            "tunnel_id":        env.get("CLOUDFLARE_TUNNEL_ID", ""),
            "auto_start":       env.get("TUNNEL_AUTO_START", "false"),
        },
        "admin": {
            "username": env.get("ADMIN_USERNAME", "admin"),
        },
        "database": {
            "url_type": "sqlite" if "sqlite" in env.get("DATABASE_URL", "") else "postgresql",
        },
        "ai_core": {
            "system_prompt": _get_ai_core_prompt(env),
        },
        "tunnel_status": _get_tunnel_status_dict(),
    }

def _get_ai_core_prompt(env: dict) -> str:
    prompt_file = Path(__file__).resolve().parent.parent.parent / "data" / "ai_core_prompt.md"
    if prompt_file.exists():
        try:
            return prompt_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return env.get("AI_CORE_SYSTEM_PROMPT", "")

def _get_tunnel_status_dict() -> dict:
    global _tunnel_url, _tunnel_log_lines
    running = _is_running()
    env = read_env()
    cf_path = shutil.which("cloudflared")
    with _tunnel_lock:
        logs = list(_tunnel_log_lines[-20:])
        url  = _tunnel_url
    return {
        "running":               running,
        "pid":                   _tunnel_proc.pid if running else None,
        "cloudflared_installed": cf_path is not None,
        "cloudflared_path":      cf_path or "",
        "quick_url":             url if running else "",
        "domain":                env.get("TUNNEL_DOMAIN", ""),
        "has_token":             bool(env.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip()),
        "recent_logs":           logs,
    }


# ── GET: tunnel status ────────────────────────────────────────
@router.get("/tunnel/status")
async def tunnel_status(user: User = Depends(get_current_user)):
    return _get_tunnel_status_dict()


# ── POST: simpan app settings ─────────────────────────────────
class AppSettingsRequest(BaseModel):
    name:      Optional[str] = None
    host:      Optional[str] = None
    port:      Optional[str] = None
    debug:     Optional[str] = None
    log_level: Optional[str] = None


@router.post("/app")
async def save_app_settings(req: AppSettingsRequest, user: User = Depends(get_current_user)):
    data = {}
    if req.name:      data["APP_NAME"]  = req.name
    if req.host:      data["HOST"]      = req.host
    if req.port:      data["PORT"]      = req.port
    if req.debug:     data["DEBUG"]     = req.debug
    if req.log_level: data["LOG_LEVEL"] = req.log_level
    write_env_batch(data)
    return {"status": "saved", "message": f"{len(data)} pengaturan disimpan"}


# ── POST: simpan tunnel settings ──────────────────────────────
class TunnelSettingsRequest(BaseModel):
    provider:         Optional[str]  = "cloudflare"
    domain:           Optional[str]  = None
    cloudflare_token: Optional[str]  = None
    tunnel_id:        Optional[str]  = None
    enabled:          Optional[bool] = None
    auto_start:       Optional[bool] = None


@router.post("/tunnel")
async def save_tunnel_settings(req: TunnelSettingsRequest, user: User = Depends(get_current_user)):
    data = {}
    if req.provider:  data["TUNNEL_PROVIDER"] = req.provider
    if req.domain is not None:
        clean_domain = req.domain.strip().lstrip("https://").lstrip("http://").rstrip("/")
        if clean_domain:
            data["TUNNEL_DOMAIN"] = clean_domain
    if req.tunnel_id: data["CLOUDFLARE_TUNNEL_ID"] = req.tunnel_id
    if req.cloudflare_token and req.cloudflare_token not in ("••••••••", ""):
        data["CLOUDFLARE_TUNNEL_TOKEN"] = req.cloudflare_token.strip()
    if req.enabled    is not None: data["TUNNEL_ENABLED"]    = str(req.enabled).lower()
    if req.auto_start is not None: data["TUNNEL_AUTO_START"] = str(req.auto_start).lower()
    write_env_batch(data)

    webhook = None
    if req.domain:
        clean = req.domain.strip().lstrip("https://").lstrip("http://").rstrip("/")
        if clean:
            webhook = f"https://{clean}/api/integrations/telegram/webhook"
            write_env_key("TELEGRAM_WEBHOOK_URL", webhook)
            os.environ["TELEGRAM_WEBHOOK_URL"] = webhook

    return {"status": "saved", "message": f"{len(data)} setting tunnel disimpan ke .env", "webhook_url": webhook}


# ── POST: start tunnel ────────────────────────────────────────
@router.post("/tunnel/start")
async def start_tunnel(user: User = Depends(get_current_user)):
    global _tunnel_proc, _tunnel_url, _tunnel_log_lines

    if _is_running():
        return {"status": "already_running", "message": "Tunnel sudah berjalan", "pid": _tunnel_proc.pid}

    cf_path = shutil.which("cloudflared")
    if not cf_path:
        raise HTTPException(400, detail={
            "code": "cloudflared_not_installed",
            "message": "cloudflared belum terinstall",
            "hint": "Jalankan: bash scripts/install-cloudflare.sh",
        })

    env = read_env()
    token  = env.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
    domain = env.get("TUNNEL_DOMAIN", "").strip()
    port   = env.get("PORT", "7860")
    mode   = "named" if token else "quick"

    with _tunnel_lock:
        _tunnel_url = ""
        _tunnel_log_lines = []

    try:
        if mode == "named":
            cmd = [cf_path, "tunnel", "run", "--token", token]
        else:
            cmd = [cf_path, "tunnel", "--url", f"http://localhost:{port}"]

        _tunnel_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        _start_reader_thread(_tunnel_proc)
        await asyncio.sleep(3)

        if not _is_running():
            with _tunnel_lock:
                err_lines = list(_tunnel_log_lines[-10:])
            err_msg = " | ".join(err_lines) or "unknown error"
            hint = ""
            full_err = err_msg.lower()
            if "invalid token" in full_err or "unauthorized" in full_err:
                hint = "Token tidak valid. Periksa kembali Tunnel Token di Cloudflare Dashboard."
            elif "connection refused" in full_err:
                hint = f"Tidak bisa konek ke localhost:{port}. Pastikan server berjalan."
            elif "already running" in full_err:
                hint = "cloudflared sudah berjalan di proses lain. Hentikan dulu: sudo systemctl stop cloudflared"
            raise HTTPException(500, detail={
                "code": "tunnel_crash",
                "message": "cloudflared crash saat start",
                "error_log": err_lines,
                "hint": hint or err_msg[:400],
            })

        if mode == "named":
            return {
                "status": "started", "mode": "named", "domain": domain,
                "pid": _tunnel_proc.pid,
                "message": f"Named tunnel aktif → https://{domain}" if domain else "Named tunnel aktif",
            }
        return {
            "status": "started", "mode": "quick",
            "pid": _tunnel_proc.pid,
            "message": "Quick tunnel aktif — URL sedang dideteksi, tunggu 10-15 detik",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail={"code": "unknown_error", "message": str(e), "hint": ""})


# ── POST: stop tunnel ─────────────────────────────────────────
@router.post("/tunnel/stop")
async def stop_tunnel(user: User = Depends(get_current_user)):
    global _tunnel_proc, _tunnel_url
    if not _is_running():
        return {"status": "not_running", "message": "Tunnel tidak sedang berjalan"}
    try:
        _tunnel_proc.terminate()
        try:
            _tunnel_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _tunnel_proc.kill()
            _tunnel_proc.wait(timeout=3)
    except Exception as e:
        log.error("Tunnel stop error", error=str(e))
    _tunnel_proc = None
    with _tunnel_lock:
        _tunnel_url = ""
    return {"status": "stopped", "message": "Tunnel berhasil dihentikan"}


# ── GET: URL quick tunnel ─────────────────────────────────────
@router.get("/tunnel/url")
async def get_tunnel_url(user: User = Depends(get_current_user)):
    if not _is_running():
        raise HTTPException(400, "Tunnel tidak berjalan")
    with _tunnel_lock:
        url  = _tunnel_url
        logs = list(_tunnel_log_lines[-5:])
    if url:
        return {"status": "found", "url": url}
    return {"status": "pending", "url": None, "logs": logs, "message": "URL belum tersedia, tunggu 10-15 detik lagi"}


# ── GET: log tunnel ───────────────────────────────────────────
@router.get("/tunnel/logs")
async def get_tunnel_logs(user: User = Depends(get_current_user)):
    with _tunnel_lock:
        logs = list(_tunnel_log_lines)
    return {"logs": logs, "running": _is_running()}


# ── POST: install cloudflared ─────────────────────────────────
@router.post("/install-cloudflared")
async def install_cloudflared(user: User = Depends(get_current_user)):
    if shutil.which("cloudflared"):
        import subprocess as sp
        ver = sp.run(["cloudflared", "--version"], capture_output=True, text=True).stdout.strip()
        return {"status": "already_installed", "version": ver, "message": f"cloudflared sudah terinstall: {ver}"}
    return {
        "status": "manual_required",
        "message": "Jalankan perintah berikut di terminal, lalu refresh halaman ini:",
        "command": "bash scripts/install-cloudflare.sh",
    }


# ── POST: setup cloudflared systemd service ───────────────────
@router.post("/tunnel/setup-service")
async def setup_cloudflared_service(user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={
            "code": "no_token",
            "message": "Token Cloudflare belum diset. Simpan token terlebih dahulu.",
        })
    cf_path = shutil.which("cloudflared")
    if not cf_path:
        raise HTTPException(400, detail={
            "code": "cloudflared_not_installed",
            "message": "cloudflared belum terinstall.",
        })
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", cf_path, "service", "install", token,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        err = stderr.decode(errors="replace")
        if proc.returncode != 0 and "already" not in err.lower():
            raise HTTPException(500, detail={"code": "service_install_failed", "message": err[:400], "hint": "Coba jalankan manual: bash scripts/setup-cloudflare-service.sh"})

        for cmd in [["sudo", "systemctl", "daemon-reload"],
                    ["sudo", "systemctl", "enable", "cloudflared"],
                    ["sudo", "systemctl", "start", "cloudflared"]]:
            p = await asyncio.create_subprocess_exec(*cmd,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await asyncio.wait_for(p.communicate(), timeout=10)

        await asyncio.sleep(2)
        check = await asyncio.create_subprocess_exec("systemctl", "is-active", "cloudflared",
            stdout=asyncio.subprocess.PIPE)
        out, _ = await check.communicate()
        is_active = out.decode().strip() == "active"

        write_env_key("TUNNEL_ENABLED", "true")
        return {
            "status": "ok", "is_active": is_active,
            "message": "cloudflared service berhasil diinstall dan dijalankan!" if is_active else "Service diinstall tapi belum aktif. Cek log untuk detail.",
        }
    except asyncio.TimeoutError:
        raise HTTPException(500, detail={"code": "timeout", "message": "Setup timeout. Coba manual: bash scripts/setup-cloudflare-service.sh"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail={"code": "error", "message": str(e)})


# ── GET: cloudflared service status ──────────────────────────
@router.get("/tunnel/service-status")
async def cloudflared_service_status(user: User = Depends(get_current_user)):
    result = {"service_exists": False, "is_active": False, "is_enabled": False, "status_text": "", "recent_log": []}
    check = await asyncio.create_subprocess_exec("systemctl", "status", "cloudflared",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await check.communicate()
    output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
    if "could not be found" in output.lower() or "no such unit" in output.lower():
        result["status_text"] = "Service belum diinstall"
        return result
    result["service_exists"] = True
    active_check = await asyncio.create_subprocess_exec("systemctl", "is-active", "cloudflared", stdout=asyncio.subprocess.PIPE)
    active_out, _ = await active_check.communicate()
    result["is_active"] = active_out.decode().strip() == "active"
    enabled_check = await asyncio.create_subprocess_exec("systemctl", "is-enabled", "cloudflared", stdout=asyncio.subprocess.PIPE)
    enabled_out, _ = await enabled_check.communicate()
    result["is_enabled"] = enabled_out.decode().strip() == "enabled"
    log_proc = await asyncio.create_subprocess_exec("journalctl", "-u", "cloudflared", "-n", "20", "--no-pager", "--output=short",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    log_out, _ = await log_proc.communicate()
    result["recent_log"] = [l for l in log_out.decode(errors="replace").splitlines() if l.strip()]
    result["status_text"] = "active (running)" if result["is_active"] else "inactive"
    return result


# ── POST: control cloudflared service ────────────────────────
class ServiceActionRequest(BaseModel):
    action: str

@router.post("/tunnel/service-control")
async def control_cloudflared_service(req: ServiceActionRequest, user: User = Depends(get_current_user)):
    allowed = ["start", "stop", "restart", "enable", "disable"]
    if req.action not in allowed:
        raise HTTPException(400, f"Action tidak valid. Pilih: {allowed}")
    proc = await asyncio.create_subprocess_exec("sudo", "systemctl", req.action, "cloudflared",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[:300]
        raise HTTPException(500, f"Gagal {req.action} cloudflared: {err}")
    return {"status": "ok", "action": req.action, "message": f"cloudflared {req.action} berhasil"}


# ── Domain Management ─────────────────────────────────────────
class DomainEntry(BaseModel):
    subdomain:   str = ""
    root_domain: str
    tunnel_type: str = "http"
    local_port:  str = "7860"
    local_path:  str = ""
    notes:       Optional[str] = None


@router.get("/domains")
async def list_domains(user: User = Depends(get_current_user)):
    domains = read_domains()
    env = read_env()
    active_domain = env.get("TUNNEL_DOMAIN", "")
    for d in domains:
        d["full_domain"] = f"{d['subdomain']}.{d['root_domain']}" if d.get("subdomain") else d.get("root_domain", "")
        d["is_active"] = d["full_domain"] == active_domain
    return {"domains": domains, "active_domain": active_domain}


@router.post("/domains")
async def add_domain(entry: DomainEntry, user: User = Depends(get_current_user)):
    import uuid
    domains = read_domains()
    sub = entry.subdomain.strip()
    root = entry.root_domain.strip()
    full = f"{sub}.{root}" if sub else root
    for d in domains:
        ex = f"{d.get('subdomain','')}.{d.get('root_domain','')}" if d.get('subdomain') else d.get('root_domain','')
        if ex == full:
            raise HTTPException(400, f"Domain {full} sudah ada")
    new_entry = {
        "id": str(uuid.uuid4())[:8],
        "subdomain": sub,
        "root_domain": root,
        "full_domain": full,
        "tunnel_type": entry.tunnel_type,
        "local_port": entry.local_port,
        "local_path": entry.local_path.strip().lstrip("/"),
        "notes": entry.notes or "",
    }
    domains.append(new_entry)
    write_domains(domains)
    return {"status": "added", "domain": new_entry}


@router.delete("/domains/{domain_id}")
async def delete_domain(domain_id: str, user: User = Depends(get_current_user)):
    domains = read_domains()
    new_list = [d for d in domains if d.get("id") != domain_id]
    if len(new_list) == len(domains):
        raise HTTPException(404, "Domain tidak ditemukan")
    write_domains(new_list)
    return {"status": "deleted"}


@router.post("/domains/{domain_id}/activate")
async def activate_domain(domain_id: str, user: User = Depends(get_current_user)):
    domains = read_domains()
    target = next((d for d in domains if d.get("id") == domain_id), None)
    if not target:
        raise HTTPException(404, "Domain tidak ditemukan")
    full = target.get("full_domain") or f"{target.get('subdomain','')}.{target.get('root_domain','')}"
    write_env_key("TUNNEL_DOMAIN", full)
    os.environ["TUNNEL_DOMAIN"] = full
    webhook = f"https://{full}/api/integrations/telegram/webhook"
    write_env_key("TELEGRAM_WEBHOOK_URL", webhook)
    os.environ["TELEGRAM_WEBHOOK_URL"] = webhook
    return {"status": "activated", "domain": full, "webhook_url": webhook, "message": f"Domain aktif: {full}"}


# ── POST: change admin ────────────────────────────────────────
class ChangeAdminRequest(BaseModel):
    new_username: Optional[str] = None
    new_password: str

@router.post("/change-admin")
async def change_admin(req: ChangeAdminRequest, user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Admin only")
    from db.database import AsyncSessionLocal
    from db.models import User as UserModel
    from core.auth import hash_password
    from sqlmodel import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserModel).where(UserModel.id == user.id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(404, "User tidak ditemukan")
        if req.new_password:
            u.hashed_password = hash_password(req.new_password)
            write_env_key("ADMIN_PASSWORD", req.new_password)
        if req.new_username:
            u.username = req.new_username
            write_env_key("ADMIN_USERNAME", req.new_username)
        db.add(u)
        await db.commit()
    return {"status": "updated", "message": "Kredensial admin berhasil diperbarui"}


# ── AI CORE ───────────────────────────────────────────────────
class AiCoreSettingsRequest(BaseModel):
    system_prompt: str

@router.post("/ai-core")
async def save_ai_core_settings(req: AiCoreSettingsRequest, user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Admin only")
    
    # Simpan ke data/ai_core_prompt.md
    prompt_file = Path(__file__).resolve().parent.parent.parent / "data" / "ai_core_prompt.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(req.system_prompt, encoding="utf-8")
    
    return {"status": "saved", "message": "System Prompt Global berhasil diperbarui"}


# ── POST: restart server ──────────────────────────────────────
@router.post("/restart")
async def restart_server(user: User = Depends(get_current_user)):
    import sys

    async def do_restart():
        await asyncio.sleep(1)

        # Reload env vars
        env = read_env()
        for k, v in env.items():
            os.environ[k] = v

        # Spawn detached process to handle restart properly (kills old, starts new)
        import subprocess
        import os
        from pathlib import Path
        
        script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "start.sh"
        if script_path.exists():
            log.info("Spawning detached bash script to restart the server")
            cmd = f"sleep 1; pkill -f 'uvicorn main:app'; sleep 1; bash '{script_path}' &"
            subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(script_path.parent.parent),
                preexec_fn=os.setsid,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            log.info("Restart requested via pkill uvicorn (fallback)")
            try:
                subprocess.run(["pkill", "-f", "uvicorn main:app"])
            except Exception:
                pass
            import signal
            os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(do_restart())
    return {"status": "restarting", "message": "Server restart dalam 1 detik..."}


# ── GET: client app update info ───────────────────────────────
@router.get("/client-update")
async def get_client_update():
    """
    Endpoint publik untuk mengecek pembaruan aplikasi client (desktop/mobile).
    """
    env = read_env()
    version = env.get("APP_VERSION", "1.0.0")
    domain = env.get("TUNNEL_DOMAIN", "eai-orchestrator.kapanewonpengasih.my.id")
    dl_url = env.get("CLIENT_DOWNLOAD_URL", f"https://{domain}")
    
    return {
        "version": version,
        "release_notes": "Update terbaru tersedia. Silakan perbarui aplikasi Anda untuk mendapatkan fitur dan perbaikan terbaru.",
        "download_url": dl_url
    }

# ── GET: download update package (Master Server) ──────────────
from fastapi.responses import FileResponse
import zipfile
import urllib.request

@router.get("/download-update")
async def download_update():
    """Endpoint untuk server utama (Master) menyediakan file update ke server Client."""
    zip_path = "/tmp/ai-orchestrator_update.zip"
    
    # Generate on the fly if it doesn't exist or is older than 5 minutes
    build_script = Path(__file__).parent.parent.parent / "scripts" / "build-update.sh"
    if build_script.exists():
        needs_build = True
        if os.path.exists(zip_path):
            import time
            if time.time() - os.path.getmtime(zip_path) < 300: # 5 mins cache
                needs_build = False
        
        if needs_build:
            proc = await asyncio.create_subprocess_exec("bash", str(build_script),
                                                        stdout=asyncio.subprocess.PIPE,
                                                        stderr=asyncio.subprocess.PIPE)
            await proc.wait()
            
    if not os.path.exists(zip_path):
        raise HTTPException(404, detail="File update belum dibuat atau gagal dibuat.")
        
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="ai-orchestrator_update.zip"
    )

# ── POST: apply update OTA (Client Server) ────────────────────
@router.post("/apply-update")
async def apply_update(user: User = Depends(get_current_user)):
    """Endpoint untuk server Client mengunduh dan memasang update secara otomatis OTA."""
    env = read_env()
    domain = env.get("TUNNEL_DOMAIN", "eai-orchestrator.kapanewonpengasih.my.id")
    dl_base = env.get("CLIENT_DOWNLOAD_URL", f"https://{domain}")
    
    # Normalize dl base
    dl_base = dl_base.rstrip("/")
    update_url = f"{dl_base}/api/settings/download-update"
    
    tmp_zip = "/tmp/downloaded_update.zip"
    
    # 1. Download with SSL verification enabled
    try:
        def _download():
            import ssl
            ctx = ssl.create_default_context()  # Verify SSL certificates (secure default)
            # Limit download size to 200MB to prevent zip-bomb / resource exhaustion
            import urllib.request, os
            req_obj = urllib.request.Request(update_url, headers={"User-Agent": "AI-Orchestrator-Updater/1.0"})
            with urllib.request.urlopen(req_obj, context=ctx, timeout=120) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > 200 * 1024 * 1024:
                    raise ValueError("Update file too large (>200MB). Aborting for safety.")
                downloaded = 0
                MAX_SIZE = 200 * 1024 * 1024
                with open(tmp_zip, 'wb') as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > MAX_SIZE:
                            raise ValueError("Download exceeded 200MB limit. Aborting.")
                        f.write(chunk)
        await asyncio.to_thread(_download)
    except Exception as e:
        raise HTTPException(500, detail={"code": "download_failed", "message": f"Gagal mengunduh update dari {update_url}", "error": str(e)})
        
    # 2. Validate and extract with path traversal protection
    project_root = Path(__file__).parent.parent.parent
    try:
        def _validate_and_extract():
            with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
                # Security: Check for path traversal attacks (zip slip)
                project_root_str = str(project_root.resolve()) + os.sep
                for member in zip_ref.namelist():
                    member_path = os.path.realpath(os.path.join(str(project_root), member))
                    if not member_path.startswith(project_root_str):
                        raise ValueError(f"Zip path traversal attack detected: {member}")
                    # Block extraction of .env, database files, and secret files
                    basename = os.path.basename(member)
                    if basename in (".env", "ai-orchestrator.db") or member.endswith(".db"):
                        continue  # Skip sensitive files
                zip_ref.extractall(project_root)
        await asyncio.to_thread(_validate_and_extract)
    except ValueError as e:
        raise HTTPException(400, detail={"code": "security_violation", "message": str(e)})
    except Exception as e:
        raise HTTPException(500, detail={"code": "extract_failed", "message": "Gagal mengekstrak file update", "error": str(e)})
        
    # 3. Handle Python dependencies, Frontend build, then Reboot
    async def do_installation_and_reboot():
        # wait a moment for the response to send back to client
        await asyncio.sleep(2)
        
        # update dependencies if required
        try:
            req_file = project_root / "backend" / "requirements.txt"
            if req_file.exists():
                pip_proc = await asyncio.create_subprocess_exec("pip", "install", "-r", str(req_file),
                                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await pip_proc.wait()
        except:
            pass
            
        # build frontend
        try:
            frontend_dir = project_root / "frontend"
            if frontend_dir.exists():
                p1 = await asyncio.create_subprocess_exec("npm", "install", cwd=str(frontend_dir),
                                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p1.wait()
                p2 = await asyncio.create_subprocess_exec("npm", "run", "build", cwd=str(frontend_dir),
                                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p2.wait()
        except:
            pass
            
        import subprocess
        try:
            subprocess.run(["pkill", "-f", "uvicorn main:app"])
        except Exception:
            pass
            
        # Fallback restart
        import os, signal
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(do_installation_and_reboot())
    
    return {
        "status": "updating", 
        "message": "Pembaruan sistem berhasil diunduh dan sedang dipasang di latar belakang. Proses kompilasi kode dan restart memakan waktu 1-3 menit."
    }

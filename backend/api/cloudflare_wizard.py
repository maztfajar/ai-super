"""
AI ORCHESTRATOR — Cloudflare Tunnel Wizard API
Setup lengkap tunnel, DNS record, dan service via Cloudflare API.
"""
import os
import asyncio
import json
import shutil
import subprocess
import re
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
import structlog

from db.models import User
from core.auth import get_current_user

router = APIRouter()
log = structlog.get_logger()

ENV_FILE = Path(__file__).parent.parent.parent / ".env"
CF_API   = "https://api.cloudflare.com/client/v4"


# ── Helpers ───────────────────────────────────────────────────
def read_env() -> Dict[str, str]:
    result = {}
    if not ENV_FILE.exists():
        return result
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def write_env_key(key: str, value: str):
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    found, new_lines = False, []
    for line in lines:
        s = line.strip()
        if s.startswith(f"{key}=") or s.startswith(f"# {key}="):
            new_lines.append(f"{key}={value}"); found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def cf_err(msg: str, hint: str = "", code: str = "cf_error"):
    """Buat HTTPException dengan format detail yang konsisten."""
    raise HTTPException(400, detail={"code": code, "message": msg, "hint": hint})


async def cf_request(method: str, path: str, token: str, payload: dict = None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as c:
        fn = getattr(c, method.lower())
        kwargs = {"headers": headers}
        if payload is not None:
            kwargs["json"] = payload
        r = await fn(f"{CF_API}{path}", **kwargs)

    try:
        data = r.json()
    except Exception:
        raise HTTPException(500, detail={"code": "parse_error", "message": f"Respon Cloudflare tidak valid (HTTP {r.status_code})", "hint": r.text[:200]})

    if not data.get("success"):
        errors = data.get("errors", [])
        msg  = errors[0].get("message", "Cloudflare API error") if errors else "Cloudflare API error"
        code = str(errors[0].get("code", "")) if errors else ""
        hint = ""
        if "10000" in code:
            hint = "Token tidak memiliki izin yang cukup. Pastikan token punya akses: Cloudflare Tunnel (Edit) dan Zone DNS (Edit)."
        elif "6111" in code:
            hint = "Tunnel dengan nama ini sudah ada. Gunakan nama berbeda atau pilih 'Pakai Tunnel Ada'."
        raise HTTPException(400, detail={"code": f"cf_{code}", "message": msg, "hint": hint})

    return data.get("result")


# ── Cek apakah sudo tersedia tanpa password ───────────────────
async def _check_sudo() -> bool:
    """Cek apakah user bisa sudo tanpa password."""
    try:
        p = await asyncio.create_subprocess_exec(
            "sudo", "-n", "true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(p.communicate(), timeout=3)
        return p.returncode == 0
    except Exception:
        return False


async def _run_cmd(cmd: List[str], timeout: int = 30) -> tuple[int, str, str]:
    """Jalankan command, return (returncode, stdout, stderr)."""
    try:
        p = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(p.communicate(), timeout=timeout)
        return p.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


# ── GET: wizard status ────────────────────────────────────────
@router.get("/wizard/status")
async def wizard_status(user: User = Depends(get_current_user)):
    env = read_env()
    cf_path = shutil.which("cloudflared")

    # Cek service aktif
    is_service_active = False
    _, out, _ = await _run_cmd(["systemctl", "is-active", "cloudflared"], timeout=5)
    is_service_active = out.strip() == "active"

    # Cek sudo
    has_sudo = await _check_sudo()

    has_api_token    = bool(env.get("CLOUDFLARE_API_TOKEN", "").strip())
    has_tunnel_token = bool(env.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip())
    has_tunnel_id    = bool(env.get("CLOUDFLARE_TUNNEL_ID", "").strip())
    has_domain       = bool(env.get("TUNNEL_DOMAIN", "").strip())

    steps_completed = []
    if has_api_token:     steps_completed.append("api_token")
    if has_tunnel_token:  steps_completed.append("tunnel_created")
    if has_domain:        steps_completed.append("domain_configured")
    if cf_path:           steps_completed.append("cloudflared_installed")
    if is_service_active: steps_completed.append("service_running")

    return {
        "has_api_token":    has_api_token,
        "has_tunnel_token": has_tunnel_token,
        "has_tunnel_id":    has_tunnel_id,
        "has_domain":       has_domain,
        "tunnel_domain":    env.get("TUNNEL_DOMAIN", ""),
        "tunnel_id":        env.get("CLOUDFLARE_TUNNEL_ID", ""),
        "account_id":       env.get("CLOUDFLARE_ACCOUNT_ID", ""),
        "cloudflared_installed": cf_path is not None,
        "cloudflared_path": cf_path or "",
        "service_active":   is_service_active,
        "has_sudo":         has_sudo,
        "steps_completed":  steps_completed,
        "setup_complete":   len(steps_completed) >= 4,
    }


# ── Step 1: Validasi API Token ────────────────────────────────
class ValidateTokenReq(BaseModel):
    api_token: str

@router.post("/wizard/validate-token")
async def validate_token(req: ValidateTokenReq, user: User = Depends(get_current_user)):
    t = req.api_token.strip()
    if not t:
        raise HTTPException(400, detail={"code": "empty", "message": "Token kosong", "hint": "Paste API Token dari Cloudflare Dashboard."})

    # Verifikasi token
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{CF_API}/user/tokens/verify",
                            headers={"Authorization": f"Bearer {t}", "Content-Type": "application/json"})
        data = r.json()
    except httpx.ConnectError:
        raise HTTPException(503, detail={"code": "network_error", "message": "Tidak bisa terhubung ke Cloudflare API", "hint": "Periksa koneksi internet server."})
    except Exception as e:
        raise HTTPException(500, detail={"code": "request_error", "message": str(e), "hint": ""})

    if not data.get("success"):
        raise HTTPException(400, detail={
            "code": "invalid_token",
            "message": "Token tidak valid atau sudah kadaluarsa",
            "hint": "Buat token baru di: dash.cloudflare.com → Profile → API Tokens → Create Token"
        })

    # Cek izin — token harus punya akses account
    token_info = data.get("result", {})
    policies   = token_info.get("policies", [])

    # Ambil daftar akun
    try:
        account_result = await cf_request("GET", "/accounts?per_page=20", t)
        accounts = [{"id": a["id"], "name": a["name"]} for a in (account_result or [])]
    except Exception:
        accounts = []

    if not accounts:
        raise HTTPException(400, detail={
            "code": "no_accounts",
            "message": "Token valid tapi tidak ada akun yang bisa diakses",
            "hint": "Pastikan token punya izin 'Account: Cloudflare Tunnel (Edit)'. Cek resource scope saat membuat token."
        })

    write_env_key("CLOUDFLARE_API_TOKEN", t)
    os.environ["CLOUDFLARE_API_TOKEN"] = t

    return {"valid": True, "message": "Token valid!", "accounts": accounts, "token_name": token_info.get("name", "")}


# ── Step 2a: List zones ───────────────────────────────────────
@router.get("/wizard/zones")
async def list_zones(user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": "Selesaikan langkah 1 terlebih dahulu."})

    result = await cf_request("GET", "/zones?per_page=50&status=active", token)
    zones = [
        {"id": z["id"], "name": z["name"], "status": z["status"],
         "account_id": z.get("account", {}).get("id", ""),
         "account_name": z.get("account", {}).get("name", "")}
        for z in (result or [])
    ]

    if not zones:
        raise HTTPException(400, detail={
            "code": "no_zones",
            "message": "Tidak ada domain aktif di akun Cloudflare",
            "hint": "Tambahkan domain ke Cloudflare terlebih dahulu, atau periksa izin Zone DNS (Edit) pada token."
        })

    return {"zones": zones}


# ── Step 2b: List tunnels ─────────────────────────────────────
class ListTunnelsReq(BaseModel):
    account_id: str

@router.post("/wizard/tunnels")
async def list_tunnels(req: ListTunnelsReq, user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": ""})

    result = await cf_request("GET", f"/accounts/{req.account_id}/cfd_tunnel?per_page=20&is_deleted=false", token)
    tunnels = [
        {"id": t["id"], "name": t["name"], "status": t.get("status", "inactive"),
         "created_at": t.get("created_at", "")[:10]}
        for t in (result or [])
    ]
    return {"tunnels": tunnels}


# ── Step 3: Buat tunnel baru ──────────────────────────────────
class CreateTunnelReq(BaseModel):
    account_id:  str
    tunnel_name: str

@router.post("/wizard/create-tunnel")
async def create_tunnel(req: CreateTunnelReq, user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": ""})

    name = req.tunnel_name.strip()
    if not name:
        raise HTTPException(400, detail={"code": "empty_name", "message": "Nama tunnel tidak boleh kosong", "hint": ""})

    result = await cf_request("POST", f"/accounts/{req.account_id}/cfd_tunnel", token,
                              {"name": name, "config_src": "cloudflare"})

    tunnel_id = result["id"]

    # Ambil token tunnel
    token_result = await cf_request("GET", f"/accounts/{req.account_id}/cfd_tunnel/{tunnel_id}/token", token)
    tunnel_token = token_result if isinstance(token_result, str) else str(token_result)

    write_env_key("CLOUDFLARE_TUNNEL_ID",    tunnel_id)
    write_env_key("CLOUDFLARE_TUNNEL_TOKEN", tunnel_token)
    write_env_key("CLOUDFLARE_ACCOUNT_ID",   req.account_id)
    write_env_key("TUNNEL_ENABLED",          "true")
    os.environ.update({
        "CLOUDFLARE_TUNNEL_ID":    tunnel_id,
        "CLOUDFLARE_TUNNEL_TOKEN": tunnel_token,
        "CLOUDFLARE_ACCOUNT_ID":   req.account_id,
    })

    log.info("Tunnel created", tunnel_id=tunnel_id, name=name)
    return {"tunnel_id": tunnel_id, "tunnel_name": result["name"],
            "tunnel_token": tunnel_token, "message": f"Tunnel '{name}' berhasil dibuat!"}


# ── Step 3b: Pakai tunnel existing ───────────────────────────
class UseTunnelReq(BaseModel):
    account_id: str
    tunnel_id:  str

@router.post("/wizard/use-tunnel")
async def use_existing_tunnel(req: UseTunnelReq, user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": ""})

    tunnel_info  = await cf_request("GET", f"/accounts/{req.account_id}/cfd_tunnel/{req.tunnel_id}", token)
    token_result = await cf_request("GET", f"/accounts/{req.account_id}/cfd_tunnel/{req.tunnel_id}/token", token)
    tunnel_token = token_result if isinstance(token_result, str) else str(token_result)

    write_env_key("CLOUDFLARE_TUNNEL_ID",    req.tunnel_id)
    write_env_key("CLOUDFLARE_TUNNEL_TOKEN", tunnel_token)
    write_env_key("CLOUDFLARE_ACCOUNT_ID",   req.account_id)
    os.environ.update({
        "CLOUDFLARE_TUNNEL_ID":    req.tunnel_id,
        "CLOUDFLARE_TUNNEL_TOKEN": tunnel_token,
        "CLOUDFLARE_ACCOUNT_ID":   req.account_id,
    })

    return {"tunnel_id": req.tunnel_id, "tunnel_name": tunnel_info.get("name", ""),
            "tunnel_token": tunnel_token, "message": f"Tunnel '{tunnel_info.get('name','')}' siap digunakan!"}


# ── Step 4: Konfigurasi ingress + DNS CNAME ───────────────────
class ConfigIngressReq(BaseModel):
    account_id:  str
    tunnel_id:   str
    zone_id:     str
    subdomain:   str = ""
    root_domain: str
    local_port:  str = "7860"
    local_path:  str = ""

@router.post("/wizard/configure-ingress")
async def configure_ingress(req: ConfigIngressReq, user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": ""})

    sub         = req.subdomain.strip().lstrip("https://").lstrip("http://").rstrip("/")
    root        = req.root_domain.strip().rstrip("/")
    full_domain = f"{sub}.{root}" if sub else root
    local_url   = f"http://localhost:{req.local_port.strip()}"
    if req.local_path.strip():
        local_url += "/" + req.local_path.strip().lstrip("/")

    steps_done, steps_failed = [], []

    # 4a: Konfigurasi ingress di tunnel
    try:
        await cf_request(
            "PUT",
            f"/accounts/{req.account_id}/cfd_tunnel/{req.tunnel_id}/configurations",
            token,
            {"config": {"ingress": [
                {"hostname": full_domain, "service": local_url,
                 "originRequest": {"noTLSVerify": True, "connectTimeout": "30s"}},
                {"service": "http_status:404"},
            ]}}
        )
        steps_done.append(f"✓ Ingress rule dikonfigurasi: {full_domain} → {local_url}")
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {"message": str(e.detail)}
        steps_failed.append(f"✗ Ingress rule: {d.get('message','error')}")

    # 4b: Buat / update DNS CNAME
    cname_target = f"{req.tunnel_id}.cfargotunnel.com"
    dns_name     = sub if sub else "@"
    try:
        existing = await cf_request("GET", f"/zones/{req.zone_id}/dns_records?type=CNAME&name={full_domain}", token)
        record_payload = {"type": "CNAME", "name": dns_name, "content": cname_target, "proxied": True, "ttl": 1}

        if existing:
            await cf_request("PUT", f"/zones/{req.zone_id}/dns_records/{existing[0]['id']}", token, record_payload)
            steps_done.append(f"✓ DNS CNAME diperbarui: {full_domain} → {cname_target}")
        else:
            await cf_request("POST", f"/zones/{req.zone_id}/dns_records", token, record_payload)
            steps_done.append(f"✓ DNS CNAME dibuat: {full_domain} → {cname_target}")
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {"message": str(e.detail)}
        steps_failed.append(f"✗ DNS CNAME: {d.get('message','error')}")

    # Simpan domain ke .env
    write_env_key("TUNNEL_DOMAIN", full_domain)
    os.environ["TUNNEL_DOMAIN"] = full_domain
    webhook = f"https://{full_domain}/api/integrations/telegram/webhook"
    write_env_key("TELEGRAM_WEBHOOK_URL", webhook)
    os.environ["TELEGRAM_WEBHOOK_URL"] = webhook
    steps_done.append(f"✓ Domain disimpan ke .env")

    return {
        "full_domain":  full_domain,
        "cname_target": cname_target,
        "local_url":    local_url,
        "webhook_url":  webhook,
        "steps_done":   steps_done,
        "steps_failed": steps_failed,
        "success":      len(steps_failed) == 0,
        "message": f"Domain {full_domain} dikonfigurasi!" if not steps_failed else f"Selesai dengan {len(steps_failed)} peringatan",
    }


# ── Step 5: Deploy (install cloudflared + setup service) ──────
@router.post("/wizard/deploy")
async def deploy_service(user: User = Depends(get_current_user)):
    env = read_env()
    tunnel_token = env.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
    if not tunnel_token:
        raise HTTPException(400, detail={
            "code": "no_token",
            "message": "Tunnel token belum ada",
            "hint": "Selesaikan langkah 1-3 wizard terlebih dahulu.",
        })

    steps = []
    has_sudo = await _check_sudo()

    # ── 1. Cek / Install cloudflared ──────────────────────────
    cf_path = shutil.which("cloudflared")
    if not cf_path:
        steps.append({"step": "install", "status": "running", "msg": "Menginstall cloudflared..."})
        installed = False

        # Coba via script
        script = Path(__file__).parent.parent.parent / "scripts" / "install-cloudflare.sh"
        if script.exists():
            rc, out, err = await _run_cmd(["bash", str(script)], timeout=120)
            cf_path = shutil.which("cloudflared")
            if cf_path:
                installed = True
                steps[-1].update({"status": "ok", "msg": f"cloudflared terinstall: {cf_path}"})

        # Fallback: download langsung
        if not installed:
            try:
                import platform
                arch = "amd64" if platform.machine() in ("x86_64", "AMD64") else "arm64"
                url  = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
                rc, out, err = await _run_cmd(
                    ["sudo", "curl", "-fsSL", url, "-o", "/usr/local/bin/cloudflared"], timeout=90)
                if rc == 0:
                    await _run_cmd(["sudo", "chmod", "+x", "/usr/local/bin/cloudflared"], timeout=5)
                    cf_path = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"
                    steps[-1].update({"status": "ok", "msg": f"cloudflared terinstall: {cf_path}"})
                else:
                    steps[-1].update({"status": "error", "msg": f"Download gagal: {err[:200]}",
                                      "hint": "Jalankan manual: bash scripts/install-cloudflare.sh"})
            except Exception as ex:
                steps[-1].update({"status": "error", "msg": str(ex)})
    else:
        rc, ver_out, _ = await _run_cmd([cf_path, "--version"], timeout=5)
        steps.append({"step": "install", "status": "ok", "msg": f"cloudflared sudah ada: {ver_out.strip()}"})

    if not cf_path:
        return {"success": False, "steps": steps, "tunnel_domain": env.get("TUNNEL_DOMAIN", ""),
                "message": "Gagal install cloudflared. Install manual: bash scripts/install-cloudflare.sh"}

    # ── 2. Install / update cloudflared service ───────────────
    steps.append({"step": "service_install", "status": "running", "msg": "Menginstall cloudflared service..."})

    if not has_sudo:
        steps[-1].update({
            "status": "warn",
            "msg": "sudo tidak tersedia tanpa password — coba install service langsung",
        })

    # Coba `cloudflared service install`
    rc, out, err = await _run_cmd(["sudo", "-n", cf_path, "service", "install", tunnel_token], timeout=30)
    err_lower = err.lower()

    if rc == 0:
        steps[-1].update({"status": "ok", "msg": "Service berhasil diinstall"})
    elif "already" in err_lower or "exist" in err_lower:
        # Sudah ada — uninstall dulu lalu install ulang agar token ter-update
        await _run_cmd(["sudo", "-n", cf_path, "service", "uninstall"], timeout=15)
        await asyncio.sleep(1)
        rc2, out2, err2 = await _run_cmd(["sudo", "-n", cf_path, "service", "install", tunnel_token], timeout=30)
        if rc2 == 0:
            steps[-1].update({"status": "ok", "msg": "Service diperbarui (reinstall)"})
        else:
            steps[-1].update({"status": "warn", "msg": f"Reinstall: {err2[:150]}"})
    elif "sudo" in err_lower or "password" in err_lower or rc == 1 and not err.strip():
        # Tidak bisa sudo — buat unit file manual
        steps[-1].update({"status": "warn", "msg": "sudo memerlukan password — membuat unit file manual..."})
        try:
            unit = f"""[Unit]
Description=Cloudflare Tunnel for AI ORCHESTRATOR
After=network.target

[Service]
Type=simple
User={os.environ.get('USER', 'root')}
ExecStart={cf_path} tunnel run --token {tunnel_token}
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""
            unit_path = Path("/etc/systemd/system/cloudflared.service")
            # Tulis via sudo tee
            proc = await asyncio.create_subprocess_exec(
                "sudo", "-n", "tee", str(unit_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, terr = await asyncio.wait_for(proc.communicate(input=unit.encode()), timeout=10)
            if proc.returncode == 0:
                steps[-1].update({"status": "ok", "msg": "Unit file systemd dibuat manual"})
            else:
                steps[-1].update({"status": "warn", "msg": f"Tidak bisa tulis unit file: {terr.decode()[:100]}",
                                   "hint": "Jalankan manual: sudo bash scripts/setup-cloudflare-service.sh"})
        except Exception as ex:
            steps[-1].update({"status": "warn", "msg": str(ex)[:200],
                               "hint": "Jalankan: sudo bash scripts/setup-cloudflare-service.sh"})
    else:
        steps[-1].update({"status": "warn", "msg": f"Install service: {err[:200]}",
                           "hint": "Jalankan: sudo bash scripts/setup-cloudflare-service.sh"})

    # ── 3. Daemon reload + enable + start ─────────────────────
    steps.append({"step": "start", "status": "running", "msg": "Menjalankan cloudflared service..."})

    for cmd in [["sudo", "-n", "systemctl", "daemon-reload"],
                ["sudo", "-n", "systemctl", "enable", "cloudflared"],
                ["sudo", "-n", "systemctl", "start",  "cloudflared"]]:
        rc, out, err = await _run_cmd(cmd, timeout=15)
        log.debug("systemctl", cmd=cmd[-1], rc=rc, err=err[:80])

    await asyncio.sleep(4)

    # ── 4. Verifikasi ─────────────────────────────────────────
    _, active_out, _ = await _run_cmd(["systemctl", "is-active", "cloudflared"], timeout=5)
    is_active = active_out.strip() == "active"

    if is_active:
        steps[-1].update({"status": "ok", "msg": "cloudflared service aktif dan berjalan!"})
    else:
        # Ambil log singkat untuk diagnosis
        _, log_out, _ = await _run_cmd(
            ["journalctl", "-u", "cloudflared", "-n", "8", "--no-pager", "--output=cat"], timeout=5)
        log_lines = [l for l in log_out.strip().splitlines() if l.strip()][-5:]

        # Analisa penyebab umum
        combined = " ".join(log_lines).lower()
        hint = ""
        if "invalid" in combined or "unauthorized" in combined:
            hint = "Token tunnel tidak valid. Ulangi langkah 2 (Buat Tunnel) untuk mendapatkan token baru."
        elif "address already in use" in combined:
            hint = "Port sudah dipakai. Pastikan tidak ada proses cloudflared lain yang berjalan."
        elif "permission" in combined:
            hint = "Masalah izin. Coba jalankan: sudo systemctl start cloudflared"
        elif "no such file" in combined:
            hint = "cloudflared tidak ditemukan. Install ulang: bash scripts/install-cloudflare.sh"

        steps[-1].update({
            "status": "error",
            "msg": "Service tidak aktif setelah start",
            "log": log_lines,
            "hint": hint or "Cek log: sudo journalctl -u cloudflared -n 20",
        })

    domain = env.get("TUNNEL_DOMAIN", "")
    return {
        "success":       is_active,
        "steps":         steps,
        "tunnel_domain": domain,
        "message": f"🎉 Tunnel aktif! Akses: https://{domain}" if is_active and domain
                   else ("🎉 Tunnel aktif!" if is_active else "Setup selesai tapi service belum aktif. Lihat detail di atas."),
    }


# ── Utility: DNS records zona ─────────────────────────────────
@router.get("/wizard/dns-records/{zone_id}")
async def list_dns_records(zone_id: str, user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": ""})
    result = await cf_request("GET", f"/zones/{zone_id}/dns_records?per_page=100", token)
    return {"records": [
        {"id": r["id"], "type": r["type"], "name": r["name"],
         "content": r["content"], "proxied": r.get("proxied", False)}
        for r in (result or [])
    ]}


# ── Utility: Hapus tunnel ─────────────────────────────────────
class DeleteTunnelReq(BaseModel):
    account_id: str
    tunnel_id:  str

@router.post("/wizard/delete-tunnel")
async def delete_tunnel(req: DeleteTunnelReq, user: User = Depends(get_current_user)):
    env = read_env()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(400, detail={"code": "no_token", "message": "API Token belum diset", "hint": ""})
    await cf_request("DELETE", f"/accounts/{req.account_id}/cfd_tunnel/{req.tunnel_id}?cascade=true", token)
    return {"status": "deleted", "message": f"Tunnel {req.tunnel_id} berhasil dihapus"}


# ── Reset / Hapus semua settingan Cloudflare ──────────────────
CF_ENV_KEYS = [
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_TUNNEL_TOKEN",
    "CLOUDFLARE_TUNNEL_ID",
    "CLOUDFLARE_ACCOUNT_ID",
    "TUNNEL_DOMAIN",
    "TUNNEL_ENABLED",
    "TUNNEL_PROVIDER",
    "TUNNEL_AUTO_START",
    "TELEGRAM_WEBHOOK_URL",
]

class ResetRequest(BaseModel):
    stop_service:    bool = True   # stop + uninstall cloudflared service
    delete_cf_tunnel: bool = False  # hapus tunnel di Cloudflare API (permanen)

@router.post("/wizard/reset")
async def reset_cloudflare(req: ResetRequest, user: User = Depends(get_current_user)):
    """
    Reset semua konfigurasi Cloudflare:
    - Hapus key dari .env
    - Stop & uninstall cloudflared systemd service
    - (Opsional) Hapus tunnel di Cloudflare API
    """
    steps = []
    env   = read_env()

    # ── 1. Stop & uninstall cloudflared service ───────────────
    if req.stop_service:
        steps.append({"step": "service", "status": "running", "msg": "Menghentikan cloudflared service..."})
        cf_path = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"

        for cmd in [["sudo", "-n", "systemctl", "stop",    "cloudflared"],
                    ["sudo", "-n", "systemctl", "disable", "cloudflared"]]:
            rc, _, err = await _run_cmd(cmd, timeout=10)

        # Uninstall service
        rc, out, err = await _run_cmd(["sudo", "-n", cf_path, "service", "uninstall"], timeout=15)
        if rc == 0:
            steps[-1].update({"status": "ok", "msg": "cloudflared service dihentikan & di-uninstall"})
        else:
            # Coba hapus unit file manual
            await _run_cmd(["sudo", "-n", "rm", "-f", "/etc/systemd/system/cloudflared.service"], timeout=5)
            await _run_cmd(["sudo", "-n", "systemctl", "daemon-reload"], timeout=5)
            steps[-1].update({"status": "ok", "msg": "cloudflared service dihentikan (unit file dihapus)"})

    # ── 2. Hapus tunnel di Cloudflare API ─────────────────────
    if req.delete_cf_tunnel:
        api_token  = env.get("CLOUDFLARE_API_TOKEN", "").strip()
        account_id = env.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        tunnel_id  = env.get("CLOUDFLARE_TUNNEL_ID",  "").strip()

        if api_token and account_id and tunnel_id:
            steps.append({"step": "cf_delete", "status": "running", "msg": f"Menghapus tunnel {tunnel_id[:8]}... di Cloudflare..."})
            try:
                await cf_request("DELETE", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}?cascade=true", api_token)
                steps[-1].update({"status": "ok", "msg": "Tunnel berhasil dihapus dari Cloudflare"})
            except HTTPException as e:
                d = e.detail if isinstance(e.detail, dict) else {"message": str(e.detail)}
                steps[-1].update({"status": "warn", "msg": f"Gagal hapus tunnel di CF: {d.get('message','')}"})
        else:
            steps.append({"step": "cf_delete", "status": "warn",
                          "msg": "Tunnel ID / API Token tidak lengkap — tunnel di Cloudflare tidak dihapus"})

    # ── 3. Bersihkan .env ─────────────────────────────────────
    steps.append({"step": "env", "status": "running", "msg": "Membersihkan konfigurasi .env..."})
    cleared = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            matched  = next((k for k in CF_ENV_KEYS if stripped.startswith(f"{k}=")), None)
            if matched:
                new_lines.append(f"# {line}")   # comment-out, jangan hapus baris
                cleared.append(matched)
                # Hapus dari os.environ
                os.environ.pop(matched, None)
            else:
                new_lines.append(line)
        ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    steps[-1].update({"status": "ok", "msg": f"Dibersihkan: {', '.join(cleared) if cleared else 'tidak ada key'}"})

    # ── 4. Hapus .domains.json ────────────────────────────────
    domains_file = Path(__file__).parent.parent.parent / ".domains.json"
    if domains_file.exists():
        domains_file.unlink()
        steps.append({"step": "domains", "status": "ok", "msg": "Daftar domain lokal dihapus"})

    log.info("Cloudflare settings reset", cleared_keys=cleared, delete_tunnel=req.delete_cf_tunnel)
    return {
        "success": True,
        "steps":   steps,
        "cleared_keys": cleared,
        "message": "Semua settingan Cloudflare berhasil direset!",
    }

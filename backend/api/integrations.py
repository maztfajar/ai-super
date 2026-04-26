import json
import asyncio
import os
import subprocess
import signal
from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from db.models import User
from core.auth import get_current_user
from core.config import settings
from core.model_manager import model_manager
from core.smart_router import smart_router
from memory.manager import memory_manager
from rag.engine import rag_engine
import structlog

router = APIRouter()
log = structlog.get_logger()

ENV_FILE = Path(__file__).parent.parent.parent / ".env"


def _load_env_file(override: bool = False):
    """Load .env values into os.environ with optional override."""
    if not ENV_FILE.exists():
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(str(ENV_FILE), override=override)
    except ImportError:
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if not k:
                continue
            if override or k not in os.environ:
                os.environ[k] = v


# ── Helper: baca/tulis .env ────────────────────────────────────


# ── Helper: baca/tulis .env ───────────────────────────────────
def read_env() -> Dict[str, str]:
    """Baca semua key dari .env"""
    result = {}
    if not ENV_FILE.exists():
        return result
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _env_key_matches(key: str, line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    return stripped.split("=", 1)[0].strip() == key


def write_env_key(key: str, value: str):
    """Update atau tambah satu key di .env"""
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")

    lines = ENV_FILE.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        if _env_key_matches(key, line):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")


def mask(value: str) -> str:
    """Masking API key untuk ditampilkan di UI"""
    if not value or value in ("", "sk-...", "sk-ant-...", "AIza..."):
        return ""
    if len(value) <= 8:
        return "••••••••"
    return value[:6] + "••••••••" + value[-4:]


# ── GET status semua integrasi ────────────────────────────────

def _get_sa_email(env: dict) -> str:
    """Extract Service Account email from stored credentials."""
    creds_str = env.get("GOOGLE_DRIVE_CREDENTIALS", "")
    if not creds_str:
        return ""
    try:
        import base64
        if creds_str.strip().startswith("{"):
            return json.loads(creds_str).get("client_email", "")
        else:
            return json.loads(base64.b64decode(creds_str).decode("utf-8")).get("client_email", "")
    except Exception:
        return ""


async def _check_ollama_available(env: dict) -> bool:
    """Check if Ollama is actually running and available"""
    # Check if there are models configured in .env
    ollama_models = env.get("OLLAMA_AVAILABLE_MODELS", "").strip()
    
    # Try to ping Ollama API
    try:
        import httpx
        host = env.get("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{host}/api/tags")
            return resp.status_code == 200
    except Exception:
        # If API ping fails, only consider it available if models are in .env
        return bool(ollama_models)

@router.get("/status")
async def integrations_status(user: User = Depends(get_current_user)):
    env = read_env()

    def is_set(key: str) -> bool:
        v = env.get(key, "")
        return bool(v) and not v.startswith("sk-...") and not v.startswith("sk-ant-...") and not v.startswith("AIza...")

    # Check Ollama availability
    ollama_available = await _check_ollama_available(env)

    return {
        "telegram":  {"configured": is_set("TELEGRAM_BOT_TOKEN"),  "token_masked": mask(env.get("TELEGRAM_BOT_TOKEN", "")), "webhook_url": env.get("TELEGRAM_WEBHOOK_URL", "")},
        "whatsapp":  {"configured": is_set("WHATSAPP_ACCESS_TOKEN"), "token_masked": mask(env.get("WHATSAPP_ACCESS_TOKEN", "")), "phone_number_id": env.get("WHATSAPP_PHONE_NUMBER_ID", "") or ""},
        "openai":    {"configured": is_set("OPENAI_API_KEY"),       "key_masked": mask(env.get("OPENAI_API_KEY", "")), "models": env.get("OPENAI_AVAILABLE_MODELS", "")},
        "anthropic": {"configured": is_set("ANTHROPIC_API_KEY"),    "key_masked": mask(env.get("ANTHROPIC_API_KEY", "")), "models": env.get("ANTHROPIC_AVAILABLE_MODELS", "")},
        "google":    {"configured": is_set("GOOGLE_API_KEY"),       "key_masked": mask(env.get("GOOGLE_API_KEY", "")), "models": env.get("GOOGLE_AVAILABLE_MODELS", "")},
        "sumopod":   {"configured": is_set("SUMOPOD_API_KEY"),      "key_masked": mask(env.get("SUMOPOD_API_KEY", "")),
                      "host": env.get("SUMOPOD_HOST", "https://ai.sumopod.com/v1"),
                      "models": env.get("SUMOPOD_AVAILABLE_MODELS", "")},
        "ollama":    {"configured": ollama_available, "host": env.get("OLLAMA_HOST", "http://localhost:11434"),
                      "models": env.get("OLLAMA_AVAILABLE_MODELS", "")},
        "google_drive": {
            "configured": is_set("GOOGLE_DRIVE_CREDENTIALS"),
            "folder_id": env.get("GDRIVE_UPLOAD_FOLDER_ID", ""),
            "service_email": _get_sa_email(env),
        },
    }


# ── POST: simpan API key ke .env ──────────────────────────────
class SaveKeyRequest(BaseModel):
    provider: str
    fields: Dict[str, str]   # key → value


async def _perform_model_reload():
    """Helper untuk reload settings and re-detect models secara sinkron internal"""
    _load_env_file(override=True)
    # reload in-place agar referensi global tetap valid
    settings.reload()
    await model_manager._detect_models()
    return await model_manager.get_status()


@router.post("/save-key")
async def save_key(req: SaveKeyRequest, user: User = Depends(get_current_user)):
    """Simpan API key ke file .env"""
    MODEL_PROVIDERS = ["openai", "anthropic", "google", "sumopod", "ollama"]
    ALLOWED_KEYS = {
        "openai":    ["OPENAI_API_KEY", "OPENAI_AVAILABLE_MODELS"],
        "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_AVAILABLE_MODELS"],
        "google":    ["GOOGLE_API_KEY", "GOOGLE_AVAILABLE_MODELS"],
        "sumopod":   ["SUMOPOD_API_KEY", "SUMOPOD_HOST", "SUMOPOD_AVAILABLE_MODELS", "SUMOPOD_DEFAULT_MODEL"],
        "ollama":    ["OLLAMA_HOST", "OLLAMA_DEFAULT_MODEL", "OLLAMA_AVAILABLE_MODELS"],
        "telegram":  ["TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_URL"],
        "whatsapp":  ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN"],
        "admin":     ["ADMIN_USERNAME", "ADMIN_PASSWORD"],
        "google_drive": ["GOOGLE_DRIVE_CREDENTIALS", "GDRIVE_UPLOAD_FOLDER_ID"],
    }

    allowed = ALLOWED_KEYS.get(req.provider, [])
    saved = []
    for key, value in req.fields.items():
        if key in allowed: # Hapus value.strip() agar bisa mengosongkan nilai
            val = value.strip()
            write_env_key(key, val)
            saved.append(key)
            # Update os.environ langsung
            os.environ[key] = val

    log.info("API keys saved", provider=req.provider, keys=saved)

    # Auto-reload jika provider adalah model provider
    if req.provider in MODEL_PROVIDERS:
        # Reload settings segera
        settings.reload()
        # Tunggu detect_models agar respons berisi data terbaru
        await model_manager._detect_models()
        models = await model_manager.get_status()
        return {
            "status": "saved",
            "keys": saved,
            "models": models,
            "message": f"{len(saved)} key disimpan dan {len(models)} model dimuat"
        }

    return {"status": "saved", "keys": saved, "message": f"{len(saved)} key disimpan ke .env"}


# ── POST: reload model manager tanpa restart full ─────────────
@router.post("/reload-models")
async def reload_models(user: User = Depends(get_current_user)):
    """Reload config dari .env dan re-detect model tanpa restart server"""
    models = await _perform_model_reload()
    log.info("Models reloaded via manual request", count=len(models))
    return {
        "status": "reloaded",
        "models": models,
        "count": len(models),
        "message": f"{len(models)} model terdeteksi setelah reload",
    }


# ── POST: full restart server ─────────────────────────────────
@router.post("/restart")
async def restart_server(user: User = Depends(get_current_user)):
    """Restart uvicorn process (hanya berfungsi jika pakai --reload)"""
    log.info("Restart requested by user", username=user.username)

    async def do_restart():
        await asyncio.sleep(1)
        # Reload env dulu
        env = read_env()
        for k, v in env.items():
            os.environ[k] = v
        
        # Trigger uvicorn reload (paling aman jika pakai dev.sh / --reload)
        try:
            main_py = Path(__file__).resolve().parent.parent / "main.py"
            if main_py.exists():
                main_py.touch()
                return
        except Exception as e:
            log.error("Touch reload failed", error=str(e))

        import sys
        try:
            log.info("Attempting in-place restart via os.execv")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            log.error("os.execv restart failed", error=str(e))
            # Fallback to kill (only if external daemon like pm2/systemctl is monitoring)
            os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(do_restart())
    return {"status": "restarting", "message": "Server akan restart dalam 1 detik..."}


# ── Test koneksi Telegram ─────────────────────────────────────
@router.post("/telegram/test")
async def test_telegram(user: User = Depends(get_current_user)):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN belum diset")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = resp.json()
            if data.get("ok"):
                bot = data["result"]
                return {"status": "ok", "bot_name": bot.get("first_name"), "username": bot.get("username")}
            raise HTTPException(400, data.get("description", "Token tidak valid"))
    except httpx.TimeoutException:
        raise HTTPException(408, "Timeout — cek koneksi internet")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Test koneksi Ollama ───────────────────────────────────────
@router.post("/ollama/test")
async def test_ollama(user: User = Depends(get_current_user)):
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"status": "ok", "host": host, "models": models, "count": len(models)}
            raise HTTPException(400, f"Ollama error: {resp.status_code}")
    except httpx.ConnectError:
        raise HTTPException(503, f"Tidak bisa konek ke {host} — pastikan Ollama berjalan: ollama serve")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Test Sumopod ──────────────────────────────────────────────
@router.post("/sumopod/test")
async def test_sumopod(user: User = Depends(get_current_user)):
    key = os.environ.get("SUMOPOD_API_KEY", "")
    host = os.environ.get("SUMOPOD_HOST", "https://ai.sumopod.com/v1")
    if not key:
        raise HTTPException(400, "SUMOPOD_API_KEY belum diset")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{host}/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])]
                return {"status": "ok", "host": host, "models": models[:10]}
            raise HTTPException(resp.status_code, f"Sumopod error: {resp.text[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Webhook Telegram ──────────────────────────────────────────
@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(400, "Telegram not configured")
    try:
        data = await request.json()
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user_id = str(message.get("from", {}).get("id", "tg_unknown"))
        if chat_id and text:
            asyncio.create_task(_handle_telegram_message(chat_id, user_id, text))
        return {"ok": True}
    except Exception as e:
        log.error("Telegram webhook error", error=str(e))
        return {"ok": False}


async def _handle_telegram_message(chat_id: int, user_id: str, text: str):
    try:
        import httpx
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        route = smart_router.route(text)
        model = route["model"]
        system = await memory_manager.build_system_prompt(user_id, f"tg_{chat_id}")
        rag_results = await rag_engine.query(text, user_id=user_id)
        if rag_results:
            system += "\n\n" + rag_engine.build_context(rag_results)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": text}]
        full = ""
        async for chunk in model_manager.chat_stream(model=model, messages=messages):
            full += chunk
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": full[:4096], "parse_mode": "Markdown"},
            )
        await memory_manager.save_chat_to_redis(f"tg_{chat_id}", "user", text)
        await memory_manager.save_chat_to_redis(f"tg_{chat_id}", "assistant", full)
    except Exception as e:
        log.error("Telegram reply error", error=str(e))


# ── WhatsApp webhook ──────────────────────────────────────────
@router.get("/whatsapp/webhook")
async def whatsapp_verify(request: Request):
    params = dict(request.query_params)
    verify = os.environ.get("WHATSAPP_VERIFY_TOKEN", settings.WHATSAPP_VERIFY_TOKEN)
    if params.get("hub.verify_token") == verify:
        return int(params.get("hub.challenge", 0))
    raise HTTPException(403, "Verification failed")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    if not os.environ.get("WHATSAPP_ACCESS_TOKEN"):
        raise HTTPException(400, "WhatsApp not configured")
    try:
        data = await request.json()
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        for msg in value.get("messages", []):
            if msg.get("type") == "text":
                asyncio.create_task(_handle_whatsapp_message(msg["from"], msg["text"]["body"]))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _handle_whatsapp_message(phone: str, text: str):
    try:
        import httpx
        token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        route = smart_router.route(text)
        msgs = [{"role": "system", "content": "You are AI ORCHESTRATOR."}, {"role": "user", "content": text}]
        full = ""
        from agents.executor import agent_executor
        async for chunk in agent_executor.stream_chat(
            base_model=route["model"],
            messages=msgs,
            include_tool_logs=False # Sembunyikan logs di WhatsApp
        ):
            full += chunk
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://graph.facebook.com/v18.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"messaging_product": "whatsapp", "to": phone,
                      "type": "text", "text": {"body": full[:4096]}},
            )
    except Exception as e:
        log.error("WhatsApp reply error", error=str(e))


# ── Telegram Polling Control ──────────────────────────────────
@router.get("/telegram/polling-status")
async def telegram_polling_status(user: User = Depends(get_current_user)):
    from integrations.telegram_bot import is_running
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return {
        "running": is_running(),
        "configured": bool(token) and not token.startswith("1234567890"),
    }


@router.post("/telegram/start-polling")
async def start_telegram_polling(user: User = Depends(get_current_user)):
    from integrations.telegram_bot import start_polling, is_running
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or token.startswith("1234567890"):
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN belum diset atau tidak valid")
    if is_running():
        return {"status": "already_running", "message": "Bot sudah berjalan"}
    # Verifikasi token dulu
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = resp.json()
            if not data.get("ok"):
                raise HTTPException(400, f"Token tidak valid: {data.get('description')}")
            bot = data["result"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Tidak bisa konek ke Telegram: {e}")

    started = start_polling(token)
    return {
        "status": "started",
        "bot_name": bot.get("first_name"),
        "username": bot.get("username"),
        "message": f"Bot @{bot.get('username')} mulai polling!",
    }


@router.post("/telegram/stop-polling")
async def stop_telegram_polling(user: User = Depends(get_current_user)):
    from integrations.telegram_bot import stop_polling, is_running
    if not is_running():
        return {"status": "not_running", "message": "Bot tidak sedang berjalan"}
    stop_polling()
    return {"status": "stopped", "message": "Bot dihentikan"}


# ══════════════════════════════════════════════════════════════
# WEBHOOK GENERIC — Fonnte, n8n, Make, Zapier, dst
# ══════════════════════════════════════════════════════════════

import uuid as _uuid
import json as _json

WEBHOOKS_FILE = Path(__file__).parent.parent.parent / ".webhooks.json"

def _read_webhooks():
    if not WEBHOOKS_FILE.exists():
        return []
    try:
        return _json.loads(WEBHOOKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _write_webhooks(data):
    WEBHOOKS_FILE.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── GET: list semua webhook ───────────────────────────────────
@router.get("/webhooks")
async def list_webhooks(user: User = Depends(get_current_user)):
    hooks = _read_webhooks()
    return {"webhooks": hooks}


# ── POST: tambah webhook baru ─────────────────────────────────
class WebhookCreateReq(BaseModel):
    name:        str                        # "Fonnte WhatsApp"
    description: Optional[str] = ""
    provider:    str = "custom"             # fonnte | n8n | make | zapier | custom
    url:         str                        # URL endpoint tujuan
    method:      str = "POST"              # POST | GET
    secret:      Optional[str] = ""        # header X-Webhook-Secret
    events:      list = ["message"]        # ["message","session_start","rag_query"]
    headers_json:Optional[str] = "{}"      # JSON extra headers
    body_template:Optional[str] = ""       # template body, kosong = default
    enabled:     bool = True

@router.post("/webhooks")
async def create_webhook(req: WebhookCreateReq, user: User = Depends(get_current_user)):
    hooks = _read_webhooks()
    new_hook = {
        "id":           str(_uuid.uuid4())[:8],
        "name":         req.name.strip(),
        "description":  req.description or "",
        "provider":     req.provider,
        "url":          req.url.strip(),
        "method":       req.method.upper(),
        "secret":       req.secret or "",
        "events":       req.events,
        "headers_json": req.headers_json or "{}",
        "body_template":req.body_template or "",
        "enabled":      req.enabled,
        "created_at":   __import__("datetime").datetime.utcnow().isoformat(),
        "last_triggered":None,
        "trigger_count": 0,
    }
    hooks.append(new_hook)
    _write_webhooks(hooks)
    return {"status": "created", "webhook": new_hook}


# ── PUT: update webhook ───────────────────────────────────────
class WebhookUpdateReq(BaseModel):
    name:         Optional[str] = None
    description:  Optional[str] = None
    url:          Optional[str] = None
    method:       Optional[str] = None
    secret:       Optional[str] = None
    events:       Optional[list] = None
    headers_json: Optional[str] = None
    body_template:Optional[str] = None
    enabled:      Optional[bool] = None

@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, req: WebhookUpdateReq, user: User = Depends(get_current_user)):
    hooks = _read_webhooks()
    hook  = next((h for h in hooks if h["id"] == webhook_id), None)
    if not hook:
        raise HTTPException(404, "Webhook tidak ditemukan")
    for field in ["name","description","url","method","secret","events","headers_json","body_template","enabled"]:
        val = getattr(req, field)
        if val is not None:
            hook[field] = val.upper() if field == "method" else val
    _write_webhooks(hooks)
    return {"status": "updated", "webhook": hook}


# ── DELETE: hapus webhook ─────────────────────────────────────
@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user: User = Depends(get_current_user)):
    hooks    = _read_webhooks()
    new_list = [h for h in hooks if h["id"] != webhook_id]
    if len(new_list) == len(hooks):
        raise HTTPException(404, "Webhook tidak ditemukan")
    _write_webhooks(new_list)
    return {"status": "deleted"}


# ── POST: test webhook (kirim payload test) ───────────────────
@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, user: User = Depends(get_current_user)):
    hooks = _read_webhooks()
    hook  = next((h for h in hooks if h["id"] == webhook_id), None)
    if not hook:
        raise HTTPException(404, "Webhook tidak ditemukan")

    test_payload = {
        "event":   "test",
        "source":  "ai-orchestrator",
        "hook_id": hook["id"],
        "message": {
            "role":    "user",
            "content": "Halo! Ini pesan test dari AI ORCHESTRATOR.",
            "model":   "test",
        },
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }

    try:
        headers = {"Content-Type": "application/json", "X-Source": "ai-orchestrator"}
        if hook.get("secret"):
            headers["X-Webhook-Secret"] = hook["secret"]
        try:
            extra = _json.loads(hook.get("headers_json") or "{}")
            headers.update(extra)
        except Exception:
            pass

        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            if hook["method"] == "GET":
                r = await c.get(hook["url"], headers=headers, params={"event": "test"})
            else:
                body = hook.get("body_template") or ""
                if body:
                    # Ganti placeholder
                    body = body.replace("{{content}}", test_payload["message"]["content"])
                    body = body.replace("{{event}}", "test")
                    r = await c.post(hook["url"], headers=headers, content=body)
                else:
                    r = await c.post(hook["url"], headers=headers, json=test_payload)

        # Update stats
        hook["last_triggered"] = __import__("datetime").datetime.utcnow().isoformat()
        hook["trigger_count"]  = hook.get("trigger_count", 0) + 1
        _write_webhooks(hooks)

        return {
            "status":      "ok" if r.status_code < 400 else "error",
            "http_status": r.status_code,
            "response":    r.text[:500],
            "message":     f"Webhook berhasil dipanggil (HTTP {r.status_code})",
        }
    except Exception as e:
        return {
            "status":  "error",
            "message": f"Gagal kirim: {str(e)[:300]}",
            "hint":    "Pastikan URL bisa diakses dari server ini",
        }


# ── POST: trigger webhook dari chat (dipanggil internal) ──────
async def trigger_webhooks(event: str, payload: dict):
    """Dipanggil dari chat/message handler untuk broadcast event ke semua webhook aktif."""
    hooks = _read_webhooks()
    for hook in hooks:
        if not hook.get("enabled"):
            continue
        if event not in hook.get("events", []):
            continue
        try:
            headers = {"Content-Type": "application/json", "X-Source": "ai-orchestrator", "X-Event": event}
            if hook.get("secret"):
                headers["X-Webhook-Secret"] = hook["secret"]
            try:
                extra = _json.loads(hook.get("headers_json") or "{}")
                headers.update(extra)
            except Exception:
                pass

            body_tmpl = hook.get("body_template", "")
            import httpx
            async with httpx.AsyncClient(timeout=8) as c:
                if body_tmpl:
                    body = body_tmpl
                    for k, v in payload.items():
                        body = body.replace(f"{{{{{k}}}}}", str(v))
                    r = await c.post(hook["url"], headers=headers, content=body)
                else:
                    r = await c.post(hook["url"], headers=headers, json={"event": event, "source": "ai-orchestrator", **payload})

            hook["last_triggered"] = __import__("datetime").datetime.utcnow().isoformat()
            hook["trigger_count"]  = hook.get("trigger_count", 0) + 1
            log.info("Webhook triggered", hook_id=hook["id"], event=event, status=r.status_code)
        except Exception as e:
            log.warning("Webhook trigger failed", hook_id=hook["id"], error=str(e)[:100])

    # Simpan update trigger count
    try:
        _write_webhooks(hooks)
    except Exception:
        pass


# ── GET: template body untuk provider populer ────────────────
@router.get("/webhooks/templates")
async def webhook_templates(user: User = Depends(get_current_user)):
    return {"templates": [
        {
            "provider": "fonnte",
            "name": "Fonnte WhatsApp",
            "description": "Kirim pesan WhatsApp via Fonnte API",
            "url_hint": "https://api.fonnte.com/send",
            "method": "POST",
            "headers": '{"Authorization": "TOKEN_FONNTE_ANDA"}',
            "body": '{"target":"{{phone}}","message":"{{content}}"}',
            "events": ["message"],
            "notes": "Ganti TOKEN_FONNTE_ANDA dengan token dari dashboard.fonnte.com. Gunakan {{phone}} untuk nomor tujuan dan {{content}} untuk isi pesan.",
        },
        {
            "provider": "n8n",
            "name": "n8n Webhook",
            "description": "Trigger workflow n8n dari AI ORCHESTRATOR",
            "url_hint": "https://n8n-anda.com/webhook/xxxx",
            "method": "POST",
            "headers": "{}",
            "body": "",
            "events": ["message", "session_start"],
            "notes": "Salin URL webhook dari node 'Webhook' di n8n. Body akan dikirim otomatis sebagai JSON.",
        },
        {
            "provider": "make",
            "name": "Make (Integromat)",
            "description": "Trigger scenario Make/Integromat",
            "url_hint": "https://hook.eu1.make.com/xxxx",
            "method": "POST",
            "headers": "{}",
            "body": "",
            "events": ["message"],
            "notes": "Gunakan modul 'Webhooks > Custom webhook' di Make.",
        },
        {
            "provider": "zapier",
            "name": "Zapier Webhook",
            "description": "Trigger Zap via Catch Hook",
            "url_hint": "https://hooks.zapier.com/hooks/catch/xxxx/yyyy/",
            "method": "POST",
            "headers": "{}",
            "body": "",
            "events": ["message"],
            "notes": "Gunakan trigger 'Webhooks by Zapier > Catch Hook'.",
        },
        {
            "provider": "custom",
            "name": "Custom Webhook",
            "description": "URL webhook kustom apapun",
            "url_hint": "https://example.com/webhook",
            "method": "POST",
            "headers": "{}",
            "body": "",
            "events": ["message"],
            "notes": "Kirim payload JSON ke endpoint apapun.",
        },
    ]}


# ══════════════════════════════════════════════════════════════
# CUSTOM AI MODEL PROVIDERS — Tambah model tanpa edit .env
# ══════════════════════════════════════════════════════════════

CUSTOM_MODELS_FILE = Path(__file__).parent.parent.parent / ".custom_models.json"

def _read_custom_models():
    if not CUSTOM_MODELS_FILE.exists():
        return []
    try:
        return _json.loads(CUSTOM_MODELS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _write_custom_models(data):
    CUSTOM_MODELS_FILE.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── GET: list semua custom model providers ────────────────────
@router.get("/custom-models")
async def list_custom_models(user: User = Depends(get_current_user)):
    providers = _read_custom_models()
    # Mask API keys
    for p in providers:
        p["api_key_masked"] = mask(p.get("api_key", ""))
    return {"providers": providers}


# ── POST: tambah custom model provider baru ───────────────────
class CustomModelCreateReq(BaseModel):
    name:      str              # "Together AI", "Groq", dll
    base_url:  str              # "https://api.together.xyz/v1"
    api_key:   str              # API key
    models:    str              # comma-separated model IDs
    icon:      Optional[str] = "🔌"

@router.post("/custom-models")
async def create_custom_model(req: CustomModelCreateReq, user: User = Depends(get_current_user)):
    providers = _read_custom_models()

    # Validasi
    if not req.name.strip():
        raise HTTPException(400, "Nama provider wajib diisi")
    if not req.base_url.strip():
        raise HTTPException(400, "Base URL wajib diisi")
    if not req.api_key.strip():
        raise HTTPException(400, "API key wajib diisi")
    if not req.models.strip():
        raise HTTPException(400, "Minimal satu model harus diisi")

    # Cek duplikat nama
    for p in providers:
        if p["name"].lower() == req.name.strip().lower():
            raise HTTPException(400, f"Provider '{req.name}' sudah ada")

    new_provider = {
        "id":          str(_uuid.uuid4())[:8],
        "name":        req.name.strip(),
        "base_url":    req.base_url.strip().rstrip("/"),
        "api_key":     req.api_key.strip(),
        "models":      req.models.strip(),
        "icon":        req.icon or "🔌",
        "status":      "untested",
        "created_at":  __import__("datetime").datetime.utcnow().isoformat(),
        "last_tested": None,
    }
    providers.append(new_provider)
    _write_custom_models(providers)

    # Auto-detect models agar langsung muncul di dropdown
    await model_manager._detect_models()
    models = await model_manager.get_status()

    log.info("Custom model provider added", name=req.name)
    return {
        "status": "created", 
        "provider": {**new_provider, "api_key_masked": mask(new_provider["api_key"])},
        "models": models
    }


# ── PUT: update custom model provider ─────────────────────────
class CustomModelUpdateReq(BaseModel):
    name:      Optional[str] = None
    base_url:  Optional[str] = None
    api_key:   Optional[str] = None
    models:    Optional[str] = None
    icon:      Optional[str] = None

@router.put("/custom-models/{provider_id}")
async def update_custom_model(provider_id: str, req: CustomModelUpdateReq, user: User = Depends(get_current_user)):
    providers = _read_custom_models()
    provider = next((p for p in providers if p["id"] == provider_id), None)
    if not provider:
        raise HTTPException(404, "Provider tidak ditemukan")

    if req.name is not None:     provider["name"]     = req.name.strip()
    if req.base_url is not None: provider["base_url"] = req.base_url.strip().rstrip("/")
    if req.api_key is not None and req.api_key not in ("", "••••••••"):
        provider["api_key"] = req.api_key.strip()
    if req.models is not None:   provider["models"]   = req.models.strip()
    if req.icon is not None:     provider["icon"]     = req.icon

    provider["status"] = "untested"  # Reset status setelah update
    _write_custom_models(providers)

    # Auto-detect models agar perubahan (nama/model list) langsung muncul
    await model_manager._detect_models()
    models = await model_manager.get_status()

    return {
        "status": "updated", 
        "provider": {**provider, "api_key_masked": mask(provider["api_key"])},
        "models": models
    }


# ── DELETE: hapus custom model provider ───────────────────────
@router.delete("/custom-models/{provider_id}")
async def delete_custom_model(provider_id: str, user: User = Depends(get_current_user)):
    providers = _read_custom_models()
    new_list = [p for p in providers if p["id"] != provider_id]
    if len(new_list) == len(providers):
        raise HTTPException(404, "Provider tidak ditemukan")
    _write_custom_models(new_list)

    # Reload models agar hilang dari model_manager
    try:
        await model_manager._detect_models()
    except Exception:
        pass

    models = await model_manager.get_status()
    log.info("Custom model provider deleted", provider_id=provider_id)
    return {"status": "deleted", "models": models}


# ── POST: test koneksi custom model (sebelum simpan) ──────────
class TestConnectionReq(BaseModel):
    base_url:  str
    api_key:   str
    models:    Optional[str] = ""

@router.post("/custom-models/test-connection")
async def test_custom_connection(req: TestConnectionReq, user: User = Depends(get_current_user)):
    """Test koneksi ke provider sebelum menyimpan"""
    base_url = req.base_url.strip().rstrip("/")
    api_key = req.api_key.strip()

    if not base_url or not api_key:
        raise HTTPException(400, "Base URL dan API key wajib diisi")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            # Try /models endpoint (OpenAI compatible)
            resp = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                available_models = [m.get("id", m.get("name", "")) for m in data.get("data", data.get("models", []))]
                return {
                    "status": "ok",
                    "message": f"Berhasil tersambung! {len(available_models)} model ditemukan.",
                    "available_models": available_models[:20],
                }
            elif resp.status_code == 401:
                raise HTTPException(401, "API key tidak valid atau tidak memiliki akses")
            elif resp.status_code == 403:
                raise HTTPException(403, "Akses ditolak. Periksa API key dan permissions.")
            else:
                # Some providers don't have /models, try a simple chat completion
                try:
                    test_model = req.models.split(",")[0].strip() if req.models else "gpt-3.5-turbo"
                    chat_resp = await client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={
                            "model": test_model,
                            "messages": [{"role": "user", "content": "Hi"}],
                            "max_tokens": 5,
                        },
                    )
                    if chat_resp.status_code == 200:
                        return {
                            "status": "ok",
                            "message": "Berhasil tersambung! (via chat test)",
                            "available_models": [test_model] if test_model else [],
                        }
                    raise HTTPException(chat_resp.status_code, f"Gagal: HTTP {chat_resp.status_code} — {chat_resp.text[:200]}")
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(resp.status_code, f"Gagal tersambung: HTTP {resp.status_code} — {resp.text[:200]}")
    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(503, f"Tidak bisa tersambung ke {base_url}. Periksa URL dan pastikan server berjalan.")
    except httpx.TimeoutException:
        raise HTTPException(408, f"Timeout saat menghubungi {base_url}. Server mungkin lambat atau tidak tersedia.")
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)[:300]}")


# ── POST: test koneksi custom model (sudah disimpan) ──────────
@router.post("/custom-models/{provider_id}/test")
async def test_custom_model(provider_id: str, user: User = Depends(get_current_user)):
    """Test koneksi provider yang sudah tersimpan"""
    providers = _read_custom_models()
    provider = next((p for p in providers if p["id"] == provider_id), None)
    if not provider:
        raise HTTPException(404, "Provider tidak ditemukan")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{provider['base_url']}/models",
                headers={"Authorization": f"Bearer {provider['api_key']}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                available = [m.get("id", m.get("name", "")) for m in data.get("data", data.get("models", []))]
                provider["status"] = "connected"
                provider["last_tested"] = __import__("datetime").datetime.utcnow().isoformat()
                _write_custom_models(providers)

                # Reload model_manager
                try:
                    await model_manager._detect_models()
                except Exception:
                    pass

                return {
                    "status": "ok",
                    "message": f"Tersambung! {len(available)} model tersedia.",
                    "available_models": available[:20],
                }
            else:
                provider["status"] = "error"
                provider["last_tested"] = __import__("datetime").datetime.utcnow().isoformat()
                _write_custom_models(providers)
                raise HTTPException(resp.status_code, f"Gagal: HTTP {resp.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        provider["status"] = "error"
        provider["last_tested"] = __import__("datetime").datetime.utcnow().isoformat()
        _write_custom_models(providers)
        raise HTTPException(500, f"Gagal tersambung: {str(e)[:200]}")

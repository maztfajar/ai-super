"""
AI ORCHESTRATOR — AI Orchestrator
Main FastAPI Application
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from core.config import settings
from core.logging import setup_logging
from db.database import init_db
from core.model_manager import model_manager
from rag.engine import rag_engine
from memory.manager import memory_manager
from api.auth import router as auth_router
from api.security import router as security_router
from api.auth2fa import router as auth2fa_router
from api.chat import router as chat_router
from api.rag import router as rag_router
from api.memory import router as memory_router
from api.models import router as models_router
from api.workflow import router as workflow_router
from api.analytics import router as analytics_router
from api.integrations import router as integrations_router
from api.websocket import router as ws_router
from api.settings_api import router as settings_router
from api.cloudflare_wizard import router as cf_wizard_router
from api.update_server import router as update_server_router

from api.export import router as export_router
from api.monitoring import router as monitoring_router
from api.media import router as media_router
from api.tts import router as tts_router
from api.capability import router as capability_router
from api.compliance import router as compliance_router
from api.evolver import router as evolver_router
from api.qmd import router as qmd_router

# Import new systems (untuk initialization di lifespan)
from core.cost_tracking import cost_engine
from core.audit_logging import audit_logger
from core.approval_system import approval_system
from core.self_healing import self_healing_engine

# Timeout middleware configuration
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import asyncio
from contextlib import asynccontextmanager as acm
import time

setup_logging()
log = structlog.get_logger()

class APIMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking request performance to provide objective telemetry."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            error_count = 1 if response.status_code >= 500 else 0
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log objective metrics, but don't spam for static assets
            if not request.url.path.startswith("/assets") and request.url.path != "/api/health":
                log.info(
                    "API Request Completed",
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    execution_time_ms=execution_time_ms,
                    is_error=bool(error_count)
                )
            return response
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            log.error(
                "API Request Failed Unhandled",
                method=request.method,
                path=request.url.path,
                error=str(e),
                execution_time_ms=execution_time_ms
            )
            raise

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware untuk prevent request timeout pada streaming responses"""
    
    async def dispatch(self, request: Request, call_next):
        # Streaming endpoints (SSE) TIDAK diberi timeout di sini — mereka punya
        # idle-timeout internal sendiri (IDLE_TIMEOUT di orchestrator).
        # Middleware ini hanya melindungi non-streaming endpoints dari hang.
        is_streaming = (
            "/api/chat/send" in request.url.path
            or "/execute_pending" in request.url.path
            or "/images" in request.url.path
        )
        if is_streaming:
            # Biarkan streaming berjalan tanpa wrapper timeout (ada guard internal)
            return await call_next(request)

        try:
            return await asyncio.wait_for(call_next(request), timeout=60)
        except asyncio.TimeoutError:
            log.warning(f"Request timeout (non-stream): {request.url.path}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=408,
                content={
                    "error": "Request timeout",
                    "message": "Operasi memerlukan waktu terlalu lama. Silakan coba lagi.",
                    "retry_after": 30,
                },
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ PATCH 1: Validasi konfigurasi keamanan sebelum apapun berjalan
    from core.config import validate_security_config
    validate_security_config()

    log.info("Starting AI ORCHESTRATOR...")

    # Buat direktori data
    for d in ["./data/uploads", "./data/chroma_db", "./data/logs", "./data/audit_logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # ── Security: Harden file permissions at startup ──────────
    import stat, glob as _glob
    _env_file = Path(__file__).parent.parent / ".env"
    if _env_file.exists():
        _env_file.chmod(0o600)  # Owner read/write only
    for _lf in _glob.glob("./data/logs/*.log"):
        try:
            Path(_lf).chmod(0o600)
        except Exception:
            pass
    log.info("File permissions hardened (.env + logs → 600)")

    # Init database tables
    await init_db()
    log.info("Database ready")


    # Buat admin user (di sini — bukan di router)
    from db.database import AsyncSessionLocal
    from core.auth import ensure_admin_exists
    async with AsyncSessionLocal() as db:
        await ensure_admin_exists(db)
    log.info(f"Admin ready: {settings.ADMIN_USERNAME}")

    # Init layanan opsional
    await model_manager.startup()
    await rag_engine.startup()
    await memory_manager.startup()
    
    # Init new compliance systems
    log.info("✅ Approval System initialized")
    log.info("✅ Cost Tracking Engine initialized")
    log.info("✅ Audit Logging System initialized")

    # Init new intelligence systems
    from core.self_correction import self_correction_engine  # noqa
    from core.procedural_memory import procedural_memory  # noqa
    from core.project_indexer import project_indexer  # noqa
    log.info("✅ Self-Correction Engine initialized")
    log.info("✅ Procedural Memory Engine initialized")
    log.info("✅ Project Indexer (Project-Wide Awareness) initialized")

    # ── Self-Healing Engine ───────────────────────────────────────
    await self_healing_engine.start()
    log.info("✅ Self-Healing Engine started")

    # Capability Map — discover model capabilities
    from core.capability_map import capability_map
    import asyncio
    await capability_map.startup_sync()
    # Schedule background re-sync every 30 minutes
    asyncio.create_task(capability_map.sync_background_loop())
    log.info("Capability Map ready", models=len(capability_map._map))

    # Capability Evolver — self-improvement daemon
    from core.capability_evolver import capability_evolver
    capability_evolver.start()
    log.info("✅ Capability Evolver daemon started")

    # Byte Rover — Long-term Memory
    from core.byte_rover import byte_rover
    asyncio.create_task(byte_rover.background_loop())
    log.info("✅ Byte Rover (Long-term Memory) daemon started")

    if settings.TELEGRAM_BOT_TOKEN:
        from integrations.telegram_bot import start_polling, start_watchdog, stop_watchdog, stop_polling
        started = start_polling(settings.TELEGRAM_BOT_TOKEN)
        if started:
            start_watchdog(settings.TELEGRAM_BOT_TOKEN, check_interval=60)
            log.info("Telegram polling watchdog started")

    log.info(f"AI ORCHESTRATOR ready! http://{settings.HOST}:{settings.PORT}")
    yield
    log.info("Shutting down AI ORCHESTRATOR...")
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            from integrations.telegram_bot import stop_watchdog, stop_polling
            stop_watchdog()
            stop_polling()
        except Exception:
            pass

    # Stop self-healing
    self_healing_engine.stop()

    # Stop capability evolver
    try:
        from core.capability_evolver import capability_evolver
        capability_evolver.stop()
    except Exception:
        pass


app = FastAPI(
    title="AI ORCHESTRATOR API",
    description="AI Orchestrator — Personal Orchestrator",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add middlewares
app.add_middleware(TimeoutMiddleware)
app.add_middleware(APIMetricsMiddleware)

# ── CORS: Dynamic origin validation ──────────────────────────
# Allows localhost (dev), same-host requests, and any configured tunnel domain.
# Replaces dangerous allow_origins=["*"] + allow_credentials=True combination.
from starlette.middleware.base import BaseHTTPMiddleware as _BHMW

class SmartCORSMiddleware(_BHMW):
    """
    Allows:
      - localhost / 127.0.0.1 (development)
      - Same host as the server
      - TUNNEL_DOMAIN from .env (e.g. your Cloudflare domain)
    Blocks all other cross-origin requests with credentials.
    """
    _SAFE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}

    def _is_allowed(self, origin: str, request: Request) -> bool:
        if not origin:
            return True  # Same-origin requests have no Origin header
        try:
            from urllib.parse import urlparse
            host = urlparse(origin).hostname or ""
        except Exception:
            return False
        if host in self._SAFE_HOSTS:
            return True
            
        # Automatically allow if origin matches the Host or X-Forwarded-Host header
        # This fixes blank screens when accessed via Cloudflare Tunnel without TUNNEL_DOMAIN set
        req_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        req_host_name = req_host.split(":")[0]
        if host == req_host_name:
            return True
            
        # Allow configured tunnel/custom domain
        import os
        tunnel_domain = os.environ.get("TUNNEL_DOMAIN", "").strip()
        if tunnel_domain and (host == tunnel_domain or host.endswith("." + tunnel_domain)):
            return True
            
        # Automatically allow common tunnel suffixes to prevent lockdown
        if host.endswith(".trycloudflare.com") or host.endswith(".ngrok.io") or host.endswith(".ngrok-free.app") or host.endswith(".loca.lt"):
            return True
            
        return False

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        if origin and not self._is_allowed(origin, request):
            # Reject cross-origin requests from unknown origins
            return JSONResponse(
                status_code=403,
                content={"detail": "CORS: origin not allowed"},
            )
        response = await call_next(request)
        if origin and self._is_allowed(origin, request):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With"
        return response

app.add_middleware(SmartCORSMiddleware)

app.include_router(auth_router,          prefix="/api/auth",         tags=["Auth"])
app.include_router(chat_router,          prefix="/api/chat",         tags=["Chat"])
app.include_router(export_router,        prefix="/api/chat",         tags=["Export"])
app.include_router(rag_router,           prefix="/api/rag",          tags=["RAG"])
app.include_router(memory_router,        prefix="/api/memory",       tags=["Memory"])
app.include_router(models_router,        prefix="/api/models",       tags=["Models"])
app.include_router(workflow_router,      prefix="/api/workflow",     tags=["Workflow"])
app.include_router(analytics_router,     prefix="/api/analytics",    tags=["Analytics"])
app.include_router(integrations_router,  prefix="/api/integrations", tags=["Integrations"])
app.include_router(ws_router,            prefix="/ws",               tags=["WebSocket"])
app.include_router(settings_router,      prefix="/api/settings",     tags=["Settings"])
app.include_router(cf_wizard_router,     prefix="/api/settings",     tags=["Cloudflare Wizard"])
app.include_router(security_router,      prefix="/api/security",     tags=["Security"])
app.include_router(auth2fa_router,       prefix="/api/auth2fa",      tags=["Auth2FA"])
app.include_router(update_server_router,  prefix="/api/public",       tags=["Public Update"])
app.include_router(monitoring_router,    prefix="/api/monitoring",   tags=["Monitoring"])
app.include_router(media_router,         prefix="/api/media",        tags=["Media"])
app.include_router(tts_router,           prefix="/api/media",        tags=["TTS"])
app.include_router(capability_router,    prefix="/api/capability",   tags=["Capability"])
app.include_router(compliance_router,    prefix="/api/compliance",   tags=["Compliance & Security"])
app.include_router(evolver_router,       prefix="/api/evolver",      tags=["Evolver"])
app.include_router(qmd_router,           prefix="/api/qmd",          tags=["QMD Token Killer"])


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "models": await model_manager.get_status(),
    }


# Serve logo file
from fastapi.responses import FileResponse as _FR
from pathlib import Path as _P

@app.get("/app-logo.png")
async def serve_logo():
    logo = _P(__file__).parent.parent / "frontend" / "public" / "app-logo.png"
    if logo.exists():
        return _FR(str(logo), media_type="image/png")
    from fastapi import HTTPException as _H
    raise _H(404)

# Serve React frontend
import mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        from fastapi.responses import FileResponse
        resp = FileResponse(str(frontend_dist / "index.html"))
        # Pastikan browser & CDN (Cloudflare) TIDAK cache index.html
        # agar update frontend selalu langsung terbaca tanpa hard-refresh
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
else:
    @app.get("/")
    async def root():
        return {"message": "AI ORCHESTRATOR API OK. Build frontend: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)

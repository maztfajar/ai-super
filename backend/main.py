"""
AI SUPER ASSISTANT — AI Super Assistant
Main FastAPI Application
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Import new systems (untuk initialization di lifespan)
from core.cost_tracking import cost_engine
from core.audit_logging import audit_logger
from core.approval_system import approval_system

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
        try:
            # Set longer timeout untuk chat creation/image generation (600s / 10 minutes)
            # Set normal timeout untuk other requests (60s)
            if "/api/chat/send" in request.url.path or "/images" in request.url.path or "/execute_pending" in request.url.path:
                timeout = 600  # 10 minutes untuk agent orchestration
            else:
                timeout = 60  # 1 minute untuk normal requests
            
            # Execute dengan timeout
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            log.warning(f"Request timeout: {request.url.path}")
            return {
                "error": "Request timeout - operasi terlalu lama",
                "message": "Chat atau pembuatan konten memerlukan waktu lebih lama. Silakan coba lagi.",
                "retry_after": 60
            }


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting AI SUPER ASSISTANT...")

    # Buat direktori data
    for d in ["./data/uploads", "./data/chroma_db", "./data/logs", "./data/audit_logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)

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

    # Capability Map — discover model capabilities
    from core.capability_map import capability_map
    import asyncio
    await capability_map.startup_sync()
    # Schedule background re-sync every 30 minutes
    asyncio.create_task(capability_map.sync_background_loop())
    log.info("Capability Map ready", models=len(capability_map._map))

    if settings.TELEGRAM_BOT_TOKEN:
        from integrations.telegram_bot import start_polling
        start_polling(settings.TELEGRAM_BOT_TOKEN)

    log.info(f"AI SUPER ASSISTANT ready! http://{settings.HOST}:{settings.PORT}")
    yield
    log.info("Shutting down AI SUPER ASSISTANT...")


app = FastAPI(
    title="AI SUPER ASSISTANT API",
    description="AI Super Assistant — Personal Orchestrator",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add middlewares
app.add_middleware(TimeoutMiddleware)
app.add_middleware(APIMetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "AI SUPER ASSISTANT API OK. Build frontend: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)

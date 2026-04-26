"""
AI ORCHESTRATOR — Public Update Server API
Menyediakan endpoint publik (tanpa auth) untuk OTA update system.
Client app akan mengecek versi terbaru dan mengunduh update dari sini.
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
import structlog

from core.config import settings

router = APIRouter()
log = structlog.get_logger()

# Directory tempat menyimpan file update zip
UPDATE_DIR = Path(__file__).parent.parent / "data" / "updates"
UPDATE_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/latest-version")
async def get_latest_version(request: Request):
    """
    Public endpoint: Mengembalikan informasi versi terbaru.
    Dipanggil oleh client app untuk mengecek apakah ada pembaruan.
    
    Download URL dibangun dari request URL agar portabel —
    jika host pindah domain/IP, URL otomatis menyesuaikan.
    """
    version = getattr(settings, "APP_VERSION", "1.0.0")
    build = int(getattr(settings, "APP_BUILD", 0))

    # Cek apakah file update zip tersedia
    zip_path = UPDATE_DIR / "ai-orchestrator_update.zip"
    has_package = zip_path.exists()

    # Bangun download URL dari request yang masuk (portabel)
    # Client menghubungi via https://domain.com/api/public/latest-version
    # Maka download_url = https://domain.com/api/public/download-update
    download_url = None
    if has_package:
        # Ambil base URL dari request (scheme + host)
        base_url = str(request.base_url).rstrip("/")
        download_url = f"{base_url}/api/public/download-update"

    log.info(
        "Version check requested",
        version=version,
        build=build,
        has_package=has_package,
    )

    return {
        "version": version,
        "build": build,
        "app_name": getattr(settings, "APP_NAME", "AI ORCHESTRATOR"),
        "changelog": f"Update ke versi {version} (build {build})",
        "download_url": download_url,
        "has_package": has_package,
    }


@router.get("/download-update")
async def download_update(request: Request):
    """
    Protected endpoint: Mengunduh file zip update terbaru.
    Membutuhkan autentikasi valid (Bearer token atau API key).
    """
    # Verify Bearer token — allows both browser sessions and machine-to-machine calls
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from core.auth import get_current_user
    from db.database import get_db
    from fastapi import Depends
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required to download update package.")
    try:
        from jose import jwt, JWTError
        from core.config import settings
        token = auth_header.split(" ", 1)[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if not payload.get("sub"):
            raise ValueError("Invalid token payload")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    zip_path = UPDATE_DIR / "ai-orchestrator_update.zip"

    if not zip_path.exists():
        log.warning("Update download requested but no package available")
        raise HTTPException(
            status_code=404,
            detail="Paket update belum tersedia. Jalankan build-update.sh terlebih dahulu.",
        )

    log.info("Serving update package", path=str(zip_path), size=zip_path.stat().st_size)

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename="ai-orchestrator_update.zip",
    )

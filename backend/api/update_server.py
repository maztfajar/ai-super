"""
AI SUPER ASSISTANT — Public Update Server API
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
    zip_path = UPDATE_DIR / "ai-super-assistant_update.zip"
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
        "app_name": getattr(settings, "APP_NAME", "AI SUPER ASSISTANT"),
        "changelog": f"Update ke versi {version} (build {build})",
        "download_url": download_url,
        "has_package": has_package,
    }


@router.get("/download-update")
async def download_update():
    """
    Public endpoint: Mengunduh file zip update terbaru.
    Client app akan memanggil ini setelah mengecek latest-version.
    """
    zip_path = UPDATE_DIR / "ai-super-assistant_update.zip"

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
        filename="ai-super-assistant_update.zip",
    )

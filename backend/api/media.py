"""
AI SUPER ASSISTANT — Media API
Endpoint untuk multimodal: upload gambar dan transkrip audio/suara.
"""
import io
import base64
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from core.auth import get_current_user
from core.model_manager import model_manager
from core.config import settings
from db.models import User
import structlog

log = structlog.get_logger()
router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_AUDIO_TYPES = {"audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4",
                        "audio/webm", "audio/x-m4a", "video/ogg"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024   # 20 MB
MAX_AUDIO_SIZE = 25 * 1024 * 1024   # 25 MB


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Upload gambar → return base64 + mime type.
    Digunakan oleh frontend untuk preview sebelum dikirim ke chat.
    """
    content_type = file.content_type or ""
    if not any(content_type.startswith(t) for t in ["image/"]):
        raise HTTPException(400, "File bukan gambar. Gunakan JPEG, PNG, GIF, atau WebP.")

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(413, "Ukuran gambar melebihi 20 MB.")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    file_path = upload_dir / safe_name
    if file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        count = 1
        while True:
            candidate = upload_dir / f"{stem}-{count}{suffix}"
            if not candidate.exists():
                file_path = candidate
                break
            count += 1

    file_path.write_bytes(data)

    b64 = base64.b64encode(data).decode("utf-8")
    mime = content_type.split(";")[0].strip() or "image/jpeg"
    log.info("Image uploaded", user=user.username, size=len(data), mime=mime, path=str(file_path))

    return {
        "status": "ok",
        "base64": b64,
        "mime_type": mime,
        "filename": file_path.name,
        "size_bytes": len(data),
        "saved_path": str(file_path),
    }


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Transkrip file audio/suara ke teks.
    Mendukung: ogg, mp3, wav, m4a, webm.
    """
    content_type = file.content_type or "audio/ogg"
    data = await file.read()

    if len(data) > MAX_AUDIO_SIZE:
        raise HTTPException(413, "Ukuran audio melebihi 25 MB.")

    if len(data) < 100:
        raise HTTPException(400, "File audio terlalu kecil atau kosong.")

    filename = file.filename or "audio.ogg"
    log.info("Audio transcription request", user=user.username, size=len(data), filename=filename)

    try:
        transcript = await model_manager.transcribe_audio(
            audio_bytes=data,
            filename=filename,
        )
        if not transcript or not transcript.strip():
            return {"status": "empty", "text": "", "message": "Tidak ada suara yang terdeteksi."}

        log.info("Transcription done", user=user.username, chars=len(transcript))
        return {"status": "ok", "text": transcript.strip()}

    except Exception as e:
        log.error("Transcription failed", error=str(e))
        raise HTTPException(500, f"Gagal mentranskrip audio: {e}")


@router.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(None),
    image_base64: str = Form(None),
    mime_type: str = Form("image/jpeg"),
    prompt: str = Form("Deskripsikan gambar ini secara detail dalam Bahasa Indonesia."),
    model: str = Form(None),
    user: User = Depends(get_current_user),
):
    """
    Analisa gambar langsung menggunakan vision model.
    Bisa upload file atau kirim base64.
    """
    image_b64 = image_base64

    if file and not image_b64:
        data = await file.read()
        if len(data) > MAX_IMAGE_SIZE:
            raise HTTPException(413, "Ukuran gambar melebihi 20 MB.")
        image_b64 = base64.b64encode(data).decode("utf-8")
        mime_type = (file.content_type or "image/jpeg").split(";")[0].strip()

    if not image_b64:
        raise HTTPException(400, "Tidak ada gambar yang dikirim (file atau base64).")

    try:
        result = await model_manager.chat_with_image(
            image_b64=image_b64,
            mime_type=mime_type,
            text_prompt=prompt,
            model=model if model else None,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        log.error("Image analysis failed", error=str(e))
        raise HTTPException(500, f"Gagal menganalisa gambar: {e}")


@router.get("/list")
async def list_media(user: User = Depends(get_current_user)):
    """
    List semua file media yang diupload di folder uploads.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        return {"files": []}

    files = []
    try:
        for f in upload_dir.iterdir():
            if f.is_file():
                stat = f.stat()
                files.append({
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "path": str(f.relative_to(upload_dir.parent)),
                })
        # Sort by modified time descending
        files.sort(key=lambda x: x["modified"], reverse=True)
    except Exception as e:
        log.error("Failed to list media files", error=str(e))
        raise HTTPException(500, "Gagal membaca folder uploads")

    total_size_bytes = sum(f["size_bytes"] for f in files)
    return {"files": files, "total_size_bytes": total_size_bytes}


@router.delete("/delete/{filename}")
async def delete_media(filename: str, user: User = Depends(get_current_user)):
    """
    Hapus file media dari folder uploads.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    file_path = upload_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "File tidak ditemukan")

    try:
        file_path.unlink()
        log.info("Media file deleted", user=user.username, filename=filename)
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        log.error("Failed to delete media file", error=str(e), filename=filename)
        raise HTTPException(500, "Gagal menghapus file")

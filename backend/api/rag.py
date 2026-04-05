import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from db.database import get_db
from db.models import KnowledgeDoc, User
from core.auth import get_current_user
from core.config import settings
from rag.engine import rag_engine
from rag.folder_manager import folder_manager
from datetime import datetime

log = structlog.get_logger()
router = APIRouter()


# ── Upload Dokumen ────────────────────────────────────────────────

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload dan index dokumen ke RAG knowledge base."""
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(400, f"Tipe file .{ext} tidak diizinkan. Diizinkan: {settings.ALLOWED_EXTENSIONS}")

    content = await file.read()
    size_kb = len(content) // 1024
    if size_kb > settings.MAX_UPLOAD_SIZE_MB * 1024:
        raise HTTPException(400, f"File terlalu besar. Maksimal {settings.MAX_UPLOAD_SIZE_MB}MB")

    if not content:
        raise HTTPException(400, "File kosong (0 bytes)")

    # Simpan ke disk
    upload_dir = folder_manager.ensure_user_upload_dir(str(user.id))
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = upload_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Verifikasi file tersimpan dengan benar
    actual_size = file_path.stat().st_size
    if actual_size == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(500, "Gagal menyimpan file — file menjadi 0 bytes")

    # Simpan ke database
    doc = KnowledgeDoc(
        user_id=user.id,
        filename=str(file_path),
        original_name=file.filename,
        doc_type=ext,
        file_size_kb=round(actual_size / 1024, 1),
        collection=collection,
        status="indexing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    log.info("File diupload", name=file.filename, size_kb=size_kb, doc_id=doc.id)

    # Background indexing
    import asyncio
    asyncio.create_task(_index_doc(doc.id, str(file_path), {
        "doc_id": doc.id,
        "user_id": str(user.id),
        "original_name": file.filename,
        "collection": collection,
    }))

    return {"doc_id": doc.id, "filename": file.filename, "status": "indexing", "size_kb": round(actual_size / 1024, 1)}


async def _index_doc(doc_id: str, file_path: str, metadata: dict):
    """Background task: index dokumen ke vectorstore."""
    from db.database import AsyncSessionLocal
    from db.models import KnowledgeDoc

    log.info("Mulai indexing background", doc_id=doc_id, file=Path(file_path).name)
    try:
        result = await rag_engine.index_file(file_path, metadata)
        async with AsyncSessionLocal() as db:
            doc = await db.get(KnowledgeDoc, doc_id)
            if doc:
                doc.status = "ready" if result["status"] == "indexed" else "error"
                doc.chunks = result.get("chunks", 0)
                doc.indexed_at = datetime.utcnow()

                if doc.status == "error":
                    log.warning(
                        "Indexing gagal",
                        doc_id=doc_id,
                        name=metadata.get("original_name"),
                        error=result.get("message"),
                    )
                elif doc.chunks == 0:
                    doc.status = "error"
                    log.warning("Indexing menghasilkan 0 chunks", doc_id=doc_id, name=metadata.get("original_name"))
                else:
                    log.info("Indexing sukses", doc_id=doc_id, name=metadata.get("original_name"), chunks=doc.chunks)

                db.add(doc)
                await db.commit()
    except Exception as e:
        log.error("Background indexing exception", doc_id=doc_id, error=str(e))
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            doc = await db.get(KnowledgeDoc, doc_id)
            if doc:
                doc.status = "error"
                db.add(doc)
                await db.commit()


# ── List Dokumen ─────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(KnowledgeDoc)
        .where(KnowledgeDoc.user_id == user.id)
        .order_by(desc(KnowledgeDoc.created_at))
    )
    return result.scalars().all()


# ── Hapus Dokumen ─────────────────────────────────────────────────

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await db.get(KnowledgeDoc, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(404, "Dokumen tidak ditemukan")
    await rag_engine.delete_collection(doc_id)
    if Path(doc.filename).exists():
        os.remove(doc.filename)
    await db.delete(doc)
    await db.commit()
    return {"status": "deleted"}


# ── Query RAG ────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/query")
async def query_rag(
    req: QueryRequest,
    user: User = Depends(get_current_user),
):
    results = await rag_engine.query(req.query, top_k=req.top_k, user_id=str(user.id))
    return {"results": results, "count": len(results)}


# ── Web Scraping ──────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str
    collection: str = "default"


@router.post("/scrape")
async def scrape_website(
    req: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = KnowledgeDoc(
        user_id=user.id,
        filename=req.url,
        original_name=req.url,
        doc_type="web",
        collection=req.collection,
        status="indexing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    result = await rag_engine.scrape_website(req.url, {
        "doc_id": doc.id,
        "user_id": str(user.id),
        "original_name": req.url,
    })

    async with (await get_db().__anext__()) as save_db:
        d = await save_db.get(KnowledgeDoc, doc.id)
        if d:
            d.status = result["status"]
            d.chunks = result.get("chunks", 0)
            d.indexed_at = datetime.utcnow()
            save_db.add(d)
            await save_db.commit()

    return result


# ── Status RAG Engine ─────────────────────────────────────────────

@router.get("/status")
async def rag_status(user: User = Depends(get_current_user)):
    """Return status RAG engine, embedding provider, dan folder."""
    return rag_engine.get_status()


# ── Scan & Index folder rag_documents ────────────────────────────

@router.post("/scan-rag-documents")
async def scan_rag_documents(
    collection: str = "default",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan folder /rag_documents dan index semua file yang belum terindex.
    Berguna untuk bulk import dokumen tanpa upload manual.
    """
    scan = folder_manager.check_rag_documents()

    if not scan["files"]:
        return {
            "status": "ok",
            "message": f"Folder rag_documents kosong atau tidak ada file yang didukung.",
            "directory": scan["directory"],
            "total_files": 0,
        }

    # Filter file yang tidak kosong
    valid_files = [f for f in scan["files"] if not f["is_empty"]]
    empty_files = scan["empty_files"]

    if empty_files:
        log.warning("Ditemukan file kosong (0 bytes) di rag_documents", files=empty_files)

    result = await rag_engine.index_rag_documents_folder(
        user_id=str(user.id),
        collection=collection,
    )
    result["empty_files_skipped"] = empty_files
    result["valid_files_found"] = len(valid_files)
    return result


@router.get("/scan-rag-documents")
async def get_rag_documents_info(user: User = Depends(get_current_user)):
    """Preview isi folder rag_documents tanpa melakukan indexing."""
    scan = folder_manager.check_rag_documents()
    return scan


# ── Google Drive Sync ─────────────────────────────────────────────

@router.get("/google-drive/folders")
async def get_gdrive_folders(user: User = Depends(get_current_user)):
    from integrations.google_drive import list_drive_folders
    try:
        folders = await list_drive_folders()
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class GDriveSyncReq(BaseModel):
    folder_id: str
    collection: str = "default"


@router.post("/google-drive/sync-folder")
async def sync_gdrive_folder(
    req: GDriveSyncReq,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from integrations.google_drive import list_files_in_folder, download_from_drive
    import asyncio

    try:
        files = await list_files_in_folder(req.folder_id)
        if not files:
            return {"status": "ok", "message": "Folder Drive kosong", "synced": 0}

        synced_count = 0
        failed_count = 0
        errors = []

        accepted_mimes = [
            'application/pdf',
            'text/plain', 'text/markdown', 'text/csv',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.spreadsheet',
            'application/vnd.google-apps.presentation',
        ]

        upload_dir = folder_manager.ensure_user_upload_dir(str(user.id))

        for file_item in files:
            mime = file_item.get('mimeType', '')
            name = file_item.get('name', 'Untitled')
            f_id = file_item.get('id')

            ext_check = name.lower()
            is_supported = mime in accepted_mimes or ext_check.endswith(
                ('.pdf', '.txt', '.md', '.csv', '.json', '.docx', '.xlsx', '.xls', '.pptx', '.ppt')
            )
            if not is_supported:
                log.debug("Skip file Drive (tidak didukung)", name=name, mime=mime)
                continue

            temp_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{name}"
            file_path = upload_dir / temp_name

            try:
                log.info("Mengunduh dari Google Drive", name=name, file_id=f_id)
                final_ext = await download_from_drive(f_id, mime, str(file_path))

                # Rename jika ekstensi berubah
                if not str(file_path).endswith(final_ext):
                    new_path = file_path.with_suffix(final_ext)
                    file_path.rename(new_path)
                    file_path = new_path

                # ⚠️ Verifikasi file tidak 0 bytes
                file_size_bytes = file_path.stat().st_size if file_path.exists() else 0
                if file_size_bytes == 0:
                    log.error("File Drive terunduh tapi 0 bytes", name=name, file_id=f_id)
                    file_path.unlink(missing_ok=True)
                    errors.append(f"{name}: File terunduh 0 bytes — kemungkinan permission Drive atau file kosong")
                    failed_count += 1
                    continue

                fsize_kb = round(file_size_bytes / 1024, 1)
                log.info("File Drive berhasil diunduh", name=name, size_kb=fsize_kb)

                doc = KnowledgeDoc(
                    user_id=user.id,
                    filename=str(file_path),
                    original_name=f"[Drive] {name}",
                    doc_type=final_ext.lstrip('.'),
                    file_size_kb=fsize_kb,
                    collection=req.collection,
                    status="indexing",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)

                asyncio.create_task(_index_doc(doc.id, str(file_path), {
                    "doc_id": doc.id,
                    "user_id": str(user.id),
                    "original_name": doc.original_name,
                    "collection": req.collection,
                    "source": "google_drive",
                }))
                synced_count += 1

            except Exception as e:
                err_msg = str(e)
                log.error("Gagal sync file Drive", name=name, error=err_msg)
                errors.append(f"{name}: {err_msg}")
                failed_count += 1
                # Cleanup file jika ada
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                continue

        return {
            "status": "ok",
            "message": f"Berhasil sync {synced_count} file, gagal {failed_count} file",
            "synced": synced_count,
            "failed": failed_count,
            "errors": errors,
        }

    except Exception as e:
        log.error("Google Drive sync gagal total", error=str(e))
        raise HTTPException(500, detail=str(e))

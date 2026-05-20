"""
File Manager API — endpoint untuk membaca direktori, membuat folder,
dan mengelola file yang akan diedit oleh orchestra.

Tambahkan ke main.py:
    from backend.api.file_manager import router as file_manager_router
    app.include_router(file_manager_router, prefix="/api/file-manager")
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(tags=["file-manager"])

# Root directory yang boleh diakses user (atur sesuai setup kamu)
# Bisa diambil dari .env: os.getenv("WORKSPACE_ROOT", "./workspace")
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "./workspace")).resolve()


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class FileItem(BaseModel):
    name: str
    path: str           # path relatif dari WORKSPACE_ROOT
    type: str           # "file" | "folder"
    size: Optional[int] = None
    modified: Optional[str] = None
    extension: Optional[str] = None


class DirectoryResponse(BaseModel):
    current_path: str
    parent_path: Optional[str]
    items: list[FileItem]
    breadcrumbs: list[dict]


class CreateFolderRequest(BaseModel):
    parent_path: str
    folder_name: str


class SavePathRequest(BaseModel):
    directory: str
    filename: str


class IntentRequest(BaseModel):
    message: str


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _safe_path(relative_path: str) -> Path:
    """Pastikan path tidak keluar dari WORKSPACE_ROOT (path traversal protection)."""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    
    clean = relative_path.strip("/").strip("\\")
    full = (WORKSPACE_ROOT / clean).resolve()

    if not str(full).startswith(str(WORKSPACE_ROOT)):
        raise HTTPException(status_code=403, detail="Akses ke luar workspace tidak diizinkan")

    return full


def _build_breadcrumbs(relative_path: str) -> list[dict]:
    parts = [p for p in relative_path.strip("/").split("/") if p]
    crumbs = [{"name": "Workspace", "path": ""}]
    accumulated = ""
    for part in parts:
        accumulated = f"{accumulated}/{part}".strip("/")
        crumbs.append({"name": part, "path": accumulated})
    return crumbs


def _file_to_item(file_path: Path, root: Path) -> FileItem:
    relative = str(file_path.relative_to(root)).replace("\\", "/")
    stat = file_path.stat()
    return FileItem(
        name=file_path.name,
        path=relative,
        type="folder" if file_path.is_dir() else "file",
        size=stat.st_size if file_path.is_file() else None,
        modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        extension=file_path.suffix.lstrip(".").lower() if file_path.is_file() else None,
    )


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.get("/browse", response_model=DirectoryResponse)
async def browse_directory(path: str = Query(default="", description="Relative path dari workspace root")):
    """Ambil isi direktori untuk ditampilkan di popup."""
    full_path = _safe_path(path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Direktori tidak ditemukan: {path}")
    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail="Path bukan direktori")

    items: list[FileItem] = []

    try:
        entries = sorted(
            full_path.iterdir(),
            key=lambda p: (0 if p.is_dir() else 1, p.name.lower())  # folder dulu, lalu file, alfabetis
        )
        for entry in entries:
            if entry.name.startswith("."):  # skip hidden files
                continue
            items.append(_file_to_item(entry, WORKSPACE_ROOT))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Tidak ada izin membaca direktori ini")

    current_relative = str(full_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
    if current_relative == ".":
        current_relative = ""

    parent = None
    if current_relative:
        parent = str(Path(current_relative).parent).replace("\\", "/")
        if parent == ".":
            parent = ""

    return DirectoryResponse(
        current_path=current_relative,
        parent_path=parent,
        items=items,
        breadcrumbs=_build_breadcrumbs(current_relative),
    )


@router.post("/create-folder")
async def create_folder(req: CreateFolderRequest):
    """Buat folder baru di dalam direktori tertentu."""
    # Validasi nama folder
    invalid_chars = r'\/:*?"<>|'
    if any(c in req.folder_name for c in invalid_chars):
        raise HTTPException(status_code=400, detail=f"Nama folder tidak boleh mengandung: {invalid_chars}")

    parent = _safe_path(req.parent_path)
    new_folder = parent / req.folder_name

    if new_folder.exists():
        raise HTTPException(status_code=409, detail="Folder sudah ada")

    new_folder.mkdir(parents=True, exist_ok=False)
    return {"success": True, "created": str(new_folder.relative_to(WORKSPACE_ROOT)).replace("\\", "/")}


@router.post("/validate-save-path")
async def validate_save_path(req: SavePathRequest):
    """
    Validasi lokasi simpan sebelum orchestra mulai build.
    Pastikan folder ada dan tidak ada konflik nama.
    """
    directory = _safe_path(req.directory)
    target = directory / req.filename

    if target.exists():
        return {
            "valid": False,
            "reason": "conflict",
            "message": f"'{req.filename}' sudah ada di lokasi ini",
        }

    if not directory.exists():
        return {
            "valid": False,
            "reason": "not_found",
            "message": "Direktori tujuan tidak ditemukan",
        }

    return {
        "valid": True,
        "full_path": str(target.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
    }


@router.post("/classify-intent")
async def classify_user_intent(req: IntentRequest):
    """
    Endpoint untuk frontend: klasifikasikan intent user sebelum memutuskan tampilkan popup.
    Frontend memanggil ini setiap kali user kirim pesan.
    """
    try:
        from core.intent_classifier import classify_intent
    except ImportError:
        from backend.core.intent_classifier import classify_intent
    result = await classify_intent(req.message)
    return result.to_dict()


@router.delete("/delete")
async def delete_item(path: str = Query(..., description="Relative path item yang akan dihapus")):
    """Hapus file atau folder (dengan konfirmasi dari frontend)."""
    full_path = _safe_path(path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File/folder tidak ditemukan")

    if full_path.is_dir():
        shutil.rmtree(full_path)
    else:
        full_path.unlink()

    return {"success": True, "deleted": path}


@router.patch("/rename")
async def rename_item(path: str = Query(...), new_name: str = Query(...)):
    """Rename file atau folder."""
    full_path = _safe_path(path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File/folder tidak ditemukan")

    new_path = full_path.parent / new_name
    if new_path.exists():
        raise HTTPException(status_code=409, detail="Nama sudah digunakan")

    full_path.rename(new_path)
    return {
        "success": True,
        "new_path": str(new_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
    }

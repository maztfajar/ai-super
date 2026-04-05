"""
Folder Manager — Auto-create dan manage direktori RAG
Memastikan semua folder yang dibutuhkan sistem RAG tersedia.
"""
import os
import stat
from pathlib import Path
from typing import List
import structlog

log = structlog.get_logger()


class FolderManager:
    """
    Manages all RAG-related directories.
    - Auto-creates folders jika belum ada
    - Verifikasi permissions
    - Provides path helpers
    """

    def __init__(self, base_dir: str = None):
        # Base dir = root project (2 level di atas /backend)
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Resolve ke root project dari lokasi file ini
            self.base_dir = Path(__file__).resolve().parent.parent.parent

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def rag_documents_dir(self) -> Path:
        """Folder untuk dokumen RAG yang di-mount dari luar."""
        return self.base_dir / "rag_documents"

    @property
    def chroma_db_dir(self) -> Path:
        return self.backend_dir / "data" / "chroma_db"

    @property
    def uploads_dir(self) -> Path:
        return self.backend_dir / "data" / "uploads"

    @property
    def logs_dir(self) -> Path:
        return self.backend_dir / "data" / "logs"

    @property
    def data_dir(self) -> Path:
        return self.backend_dir / "data"

    def get_user_upload_dir(self, user_id: str) -> Path:
        return self.uploads_dir / str(user_id)

    def get_all_required_dirs(self) -> List[Path]:
        return [
            self.rag_documents_dir,
            self.chroma_db_dir,
            self.uploads_dir,
            self.logs_dir,
            self.data_dir,
        ]

    def ensure_dir(self, path: Path) -> bool:
        """Buat direktori jika belum ada. Return True jika berhasil."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Pastikan writable
            if not os.access(path, os.W_OK):
                log.warning("Direktori tidak writable, mencoba chmod", path=str(path))
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
            log.debug("Direktori OK", path=str(path))
            return True
        except PermissionError as e:
            log.error("Permission denied membuat direktori", path=str(path), error=str(e))
            return False
        except Exception as e:
            log.error("Gagal membuat direktori", path=str(path), error=str(e))
            return False

    def ensure_all_dirs(self) -> dict:
        """
        Buat semua direktori yang dibutuhkan RAG.
        Return summary dict.
        """
        results = {}
        for directory in self.get_all_required_dirs():
            ok = self.ensure_dir(directory)
            results[str(directory)] = "OK" if ok else "FAILED"
            if ok:
                log.info("Folder siap", path=str(directory))
            else:
                log.error("Folder GAGAL dibuat", path=str(directory))

        failed = [k for k, v in results.items() if v == "FAILED"]
        if failed:
            log.warning("Beberapa folder gagal dibuat", failed=failed)
        else:
            log.info("Semua folder RAG siap")

        return results

    def ensure_user_upload_dir(self, user_id: str) -> Path:
        """Buat dan return folder upload untuk user tertentu."""
        user_dir = self.get_user_upload_dir(user_id)
        self.ensure_dir(user_dir)
        return user_dir

    def check_rag_documents(self) -> dict:
        """
        Scan folder rag_documents dan return info file yang ditemukan.
        """
        rag_dir = self.rag_documents_dir
        if not rag_dir.exists():
            self.ensure_dir(rag_dir)

        supported_exts = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".xlsx", ".xls", ".pptx", ".ppt"}
        files = []

        for f in rag_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in supported_exts:
                size_bytes = f.stat().st_size
                files.append({
                    "path": str(f),
                    "name": f.name,
                    "extension": f.suffix.lower(),
                    "size_bytes": size_bytes,
                    "size_kb": round(size_bytes / 1024, 1),
                    "is_empty": size_bytes == 0,
                })

        return {
            "directory": str(rag_dir),
            "exists": rag_dir.exists(),
            "total_files": len(files),
            "files": files,
            "empty_files": [f["name"] for f in files if f["is_empty"]],
        }

    def get_status(self) -> dict:
        """Return status semua folder yang dikelola."""
        status = {}
        for directory in self.get_all_required_dirs():
            exists = directory.exists()
            writable = os.access(directory, os.W_OK) if exists else False
            status[directory.name] = {
                "path": str(directory),
                "exists": exists,
                "writable": writable,
            }
        return status


# Singleton
folder_manager = FolderManager()

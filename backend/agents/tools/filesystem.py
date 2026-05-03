"""
Filesystem Tools — Full File System Access for AI Orchestrator
==============================================================
12 tools lengkap agar orchestrator tidak pernah lupa letak projectnya:

  list_directory    — ls -la terstruktur dengan metadata
  file_tree         — tampilkan struktur folder seperti `tree`
  find_files        — cari file by name / extension / pattern
  search_in_files   — grep -r dalam project (cari isi file)
  make_directory    — mkdir -p
  move_file         — mv (rename / pindah)
  copy_file         — cp (salin file atau folder)
  delete_file       — rm dengan safety check
  get_project_path  — ambil path project aktif dari session
  set_project_path  — set / update path project untuk session ini
  list_all_projects — lihat semua project yang pernah dibuat
  get_file_info     — stat file: size, modified, permissions
"""

import os
import shutil
import asyncio
import fnmatch
from pathlib import Path
from typing import Optional
import structlog

log = structlog.get_logger()

# ── Safety: paths yang tidak boleh dimodifikasi ─────────────────────────────
_PROTECTED_ROOTS = [
    "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
    "/boot", "/sys", "/proc", "/dev",
    "/root/.ssh", "/root/.env",
]
_PROTECTED_EXTENSIONS = [".env", ".pem", ".key", ".p12", ".pfx"]

# ── Direktori yang diabaikan saat scan ──────────────────────────────────────
_IGNORE_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv", "env",
    ".next", "dist", "build", ".cache", "vendor", "target",
    ".idea", ".vscode", "coverage", ".mypy_cache", ".tox",
}


def _is_protected(path: str) -> bool:
    """Cek apakah path termasuk protected zone."""
    abs_path = os.path.realpath(os.path.abspath(path))
    for root in _PROTECTED_ROOTS:
        if abs_path.startswith(root):
            return True
    for ext in _PROTECTED_EXTENSIONS:
        if abs_path.endswith(ext):
            return True
    return False


def _resolve_path(path: str, session_id: Optional[str] = None) -> str:
    """
    Resolve path relatif terhadap project aktif dari session.
    Jika path sudah absolut, gunakan langsung.
    """
    if os.path.isabs(path):
        return path

    # Coba ambil project path dari registry
    if session_id:
        try:
            from core.project_registry import project_registry
            project_path = project_registry.get_sync(session_id)
            if project_path:
                return os.path.join(project_path, path)
        except Exception:
            pass

    # Fallback ke ~/projects/SESSION
    safe_folder = session_id[:8] if session_id else "agent"
    base = os.path.expanduser(f"~/projects/{safe_folder}")
    return os.path.join(base, path)


# ── 1. list_directory ────────────────────────────────────────────────────────

async def list_directory(path: str = ".", session_id: Optional[str] = None) -> str:
    """
    Tampilkan isi direktori dengan metadata lengkap.
    Seperti `ls -la` tapi terstruktur dan mudah dibaca AI.
    """
    try:
        resolved = _resolve_path(path, session_id)
        if not os.path.exists(resolved):
            return f"❌ Path tidak ditemukan: {resolved}"
        if not os.path.isdir(resolved):
            return f"❌ Bukan direktori: {resolved}"

        entries = []
        total_size = 0

        for entry in sorted(os.scandir(resolved), key=lambda e: (not e.is_dir(), e.name)):
            try:
                stat = entry.stat()
                size = stat.st_size
                total_size += size
                is_dir = entry.is_dir()

                # Format size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/1024/1024:.1f}MB"

                import datetime
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                icon = "📁" if is_dir else _get_file_icon(entry.name)
                entries.append(f"  {icon} {'[DIR]' if is_dir else '     '} {entry.name:<40} {size_str:>8}  {mtime}")
            except Exception:
                entries.append(f"  ❓ {entry.name} (error reading)")

        if not entries:
            return f"📂 Direktori kosong: {resolved}"

        total_str = f"{total_size/1024:.1f}KB" if total_size < 1024*1024 else f"{total_size/1024/1024:.1f}MB"
        header = f"📂 {resolved}  ({len(entries)} items, {total_str} total)\n"
        header += "  " + "-" * 75 + "\n"
        return header + "\n".join(entries)

    except PermissionError:
        return f"❌ Permission denied: {path}"
    except Exception as e:
        return f"❌ Error list_directory: {str(e)}"


# ── 2. file_tree ─────────────────────────────────────────────────────────────

async def file_tree(
    path: str = ".",
    max_depth: int = 4,
    session_id: Optional[str] = None,
) -> str:
    """
    Tampilkan struktur folder seperti perintah `tree`.
    Otomatis skip node_modules, __pycache__, .git, dll.
    """
    try:
        resolved = _resolve_path(path, session_id)
        if not os.path.exists(resolved):
            return f"❌ Path tidak ditemukan: {resolved}"

        lines = [f"📁 {resolved}"]
        file_count = [0]
        dir_count = [0]

        def _walk(current_path: str, prefix: str, depth: int):
            if depth > max_depth:
                return
            try:
                entries = sorted(os.scandir(current_path), key=lambda e: (not e.is_dir(), e.name))
                entries = [e for e in entries if e.name not in _IGNORE_DIRS and not e.name.startswith(".")]
            except PermissionError:
                return

            for i, entry in enumerate(entries):
                is_last = (i == len(entries) - 1)
                connector = "└── " if is_last else "├── "
                icon = "📁 " if entry.is_dir() else _get_file_icon(entry.name) + " "

                if entry.is_dir():
                    dir_count[0] += 1
                    lines.append(f"{prefix}{connector}{icon}{entry.name}/")
                    extension = "    " if is_last else "│   "
                    _walk(entry.path, prefix + extension, depth + 1)
                else:
                    file_count[0] += 1
                    try:
                        size = entry.stat().st_size
                        size_str = f" ({size/1024:.1f}KB)" if size > 1024 else f" ({size}B)"
                    except Exception:
                        size_str = ""
                    lines.append(f"{prefix}{connector}{icon}{entry.name}{size_str}")

        _walk(resolved, "", 0)
        lines.append(f"\n{dir_count[0]} direktori, {file_count[0]} file")
        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error file_tree: {str(e)}"


# ── 3. find_files ─────────────────────────────────────────────────────────────

async def find_files(
    pattern: str,
    search_path: str = ".",
    file_type: str = "any",
    session_id: Optional[str] = None,
) -> str:
    """
    Cari file berdasarkan nama/pattern/extension.
    Args:
      pattern   — nama file atau glob pattern (mis: "*.py", "index.*", "config")
      search_path — folder tempat mencari (default: project root)
      file_type — "file" | "dir" | "any"
    """
    try:
        resolved = _resolve_path(search_path, session_id)
        if not os.path.exists(resolved):
            return f"❌ Path tidak ditemukan: {resolved}"

        results = []
        count = 0
        MAX_RESULTS = 200

        for root, dirs, files in os.walk(resolved):
            # Prune ignored dirs
            dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".")]

            if file_type in ("file", "any"):
                for fname in files:
                    if fnmatch.fnmatch(fname.lower(), pattern.lower()) or fnmatch.fnmatch(fname, pattern):
                        fpath = os.path.join(root, fname)
                        rel = os.path.relpath(fpath, resolved)
                        try:
                            size = os.path.getsize(fpath)
                            size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
                        except Exception:
                            size_str = "?"
                        results.append(f"  {_get_file_icon(fname)} {rel}  ({size_str})")
                        count += 1
                        if count >= MAX_RESULTS:
                            break

            if file_type in ("dir", "any"):
                for dname in dirs:
                    if fnmatch.fnmatch(dname.lower(), pattern.lower()):
                        dpath = os.path.join(root, dname)
                        rel = os.path.relpath(dpath, resolved)
                        results.append(f"  📁 {rel}/")
                        count += 1

            if count >= MAX_RESULTS:
                break

        if not results:
            return f"🔍 Tidak ditemukan file yang cocok dengan '{pattern}' di {resolved}"

        header = f"🔍 Hasil pencarian '{pattern}' di {resolved} ({len(results)} ditemukan"
        if count >= MAX_RESULTS:
            header += f", dibatasi {MAX_RESULTS}"
        header += "):\n"
        return header + "\n".join(results)

    except Exception as e:
        return f"❌ Error find_files: {str(e)}"


# ── 4. search_in_files ───────────────────────────────────────────────────────

async def search_in_files(
    keyword: str,
    search_path: str = ".",
    extensions: str = "",
    session_id: Optional[str] = None,
) -> str:
    """
    Cari teks/keyword di dalam isi file (seperti grep -r).
    Args:
      keyword     — teks yang dicari
      search_path — folder tempat mencari
      extensions  — filter ekstensi (mis: ".py,.js") — kosong = semua teks
    """
    try:
        resolved = _resolve_path(search_path, session_id)
        if not os.path.exists(resolved):
            return f"❌ Path tidak ditemukan: {resolved}"

        ext_filter = set()
        if extensions:
            ext_filter = {e.strip().lower() for e in extensions.split(",") if e.strip()}

        results = []
        files_searched = 0
        MAX_RESULTS = 100
        MAX_FILE_SIZE = 500 * 1024  # 500KB

        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".")]

            for fname in files:
                if len(results) >= MAX_RESULTS:
                    break
                fpath = os.path.join(root, fname)
                _, ext = os.path.splitext(fname)

                if ext_filter and ext.lower() not in ext_filter:
                    continue
                if ext.lower() in (".png", ".jpg", ".gif", ".ico", ".woff",
                                    ".ttf", ".pdf", ".zip", ".gz", ".db"):
                    continue

                try:
                    if os.path.getsize(fpath) > MAX_FILE_SIZE:
                        continue
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    rel = os.path.relpath(fpath, resolved)
                    file_matches = []
                    for lineno, line in enumerate(lines, 1):
                        if keyword.lower() in line.lower():
                            file_matches.append(
                                f"    L{lineno}: {line.rstrip()[:100]}"
                            )
                            if len(file_matches) >= 5:
                                file_matches.append("    ...")
                                break

                    if file_matches:
                        results.append(
                            f"  📄 {rel} ({len(file_matches)} baris):\n" +
                            "\n".join(file_matches)
                        )
                    files_searched += 1
                except Exception:
                    continue

        if not results:
            return (
                f"🔍 Keyword '{keyword}' tidak ditemukan di {resolved}\n"
                f"   ({files_searched} file dicari)"
            )

        header = (
            f"🔍 Ditemukan '{keyword}' di {len(results)} file "
            f"({files_searched} file dicari di {resolved}):\n"
        )
        if len(results) >= MAX_RESULTS:
            header += f"   ⚠️ Dibatasi {MAX_RESULTS} hasil pertama\n"
        return header + "\n".join(results)

    except Exception as e:
        return f"❌ Error search_in_files: {str(e)}"


# ── 5. make_directory ────────────────────────────────────────────────────────

async def make_directory(path: str, session_id: Optional[str] = None) -> str:
    """
    Buat direktori baru (termasuk parent) — seperti `mkdir -p`.
    """
    try:
        resolved = _resolve_path(path, session_id)
        if _is_protected(resolved):
            return f"❌ Path protected, tidak bisa dibuat: {resolved}"
        os.makedirs(resolved, exist_ok=True)
        return f"✅ Direktori dibuat: {resolved}"
    except Exception as e:
        return f"❌ Error make_directory: {str(e)}"


# ── 6. move_file ─────────────────────────────────────────────────────────────

async def move_file(
    source: str,
    destination: str,
    session_id: Optional[str] = None,
) -> str:
    """
    Pindahkan atau rename file/folder — seperti `mv`.
    Bisa digunakan untuk:
      - Rename: move_file("old.py", "new.py")
      - Pindah:  move_file("file.py", "subdir/file.py")
    """
    try:
        src = _resolve_path(source, session_id)
        dst = _resolve_path(destination, session_id)

        if _is_protected(src):
            return f"❌ Source protected: {src}"
        if _is_protected(dst):
            return f"❌ Destination protected: {dst}"
        if not os.path.exists(src):
            return f"❌ Source tidak ditemukan: {src}"

        # Buat parent dir jika belum ada
        os.makedirs(os.path.dirname(dst) if not dst.endswith("/") else dst, exist_ok=True)

        shutil.move(src, dst)
        return f"✅ Dipindahkan: {src}\n   → {dst}"
    except Exception as e:
        return f"❌ Error move_file: {str(e)}"


# ── 7. copy_file ─────────────────────────────────────────────────────────────

async def copy_file(
    source: str,
    destination: str,
    session_id: Optional[str] = None,
) -> str:
    """
    Salin file atau folder — seperti `cp -r`.
    """
    try:
        src = _resolve_path(source, session_id)
        dst = _resolve_path(destination, session_id)

        if _is_protected(dst):
            return f"❌ Destination protected: {dst}"
        if not os.path.exists(src):
            return f"❌ Source tidak ditemukan: {src}"

        os.makedirs(os.path.dirname(dst) if os.path.isfile(src) else dst, exist_ok=True)

        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("node_modules", ".git", "__pycache__"))
            return f"✅ Folder disalin: {src}\n   → {dst}"
        else:
            shutil.copy2(src, dst)
            return f"✅ File disalin: {src}\n   → {dst}"
    except Exception as e:
        return f"❌ Error copy_file: {str(e)}"


# ── 8. delete_file ───────────────────────────────────────────────────────────

async def delete_file(
    path: str,
    confirm: bool = False,
    session_id: Optional[str] = None,
) -> str:
    """
    Hapus file atau folder.
    WAJIB set confirm=True untuk folder atau file >100KB.
    Safety: tidak bisa hapus file di luar ~/projects/
    """
    try:
        resolved = _resolve_path(path, session_id)

        # Safety: hanya izinkan hapus di dalam ~/projects/
        projects_base = os.path.expanduser("~/projects")
        if not resolved.startswith(projects_base):
            return (
                f"❌ Security: Hanya bisa hapus file di dalam ~/projects/\n"
                f"   Path yang dicoba: {resolved}"
            )

        if _is_protected(resolved):
            return f"❌ Path protected, tidak bisa dihapus: {resolved}"

        if not os.path.exists(resolved):
            return f"❌ Path tidak ditemukan: {resolved}"

        # Check size untuk folder
        is_dir = os.path.isdir(resolved)
        if is_dir:
            if not confirm:
                # Hitung jumlah file
                file_count = sum(1 for _ in Path(resolved).rglob("*"))
                return (
                    f"⚠️ Folder '{resolved}' berisi {file_count} items.\n"
                    f"   Untuk konfirmasi hapus, panggil dengan confirm=True"
                )
            shutil.rmtree(resolved)
            return f"✅ Folder dihapus: {resolved}"
        else:
            size = os.path.getsize(resolved)
            if size > 100 * 1024 and not confirm:
                return (
                    f"⚠️ File '{resolved}' berukuran {size/1024:.1f}KB.\n"
                    f"   Untuk konfirmasi hapus, panggil dengan confirm=True"
                )
            os.remove(resolved)
            return f"✅ File dihapus: {resolved}"

    except Exception as e:
        return f"❌ Error delete_file: {str(e)}"


# ── 9. get_project_path ──────────────────────────────────────────────────────

async def get_project_path(session_id: Optional[str] = None) -> str:
    """
    Ambil path project aktif untuk session ini.
    Orchestrator harus panggil ini saat tidak yakin dimana projectnya.
    """
    if not session_id:
        return "❌ session_id diperlukan"

    try:
        from core.project_registry import project_registry
        path = await project_registry.get(session_id)
        if path:
            # Verifikasi path masih ada
            if os.path.exists(path):
                # Tampilkan info singkat
                try:
                    files = [f for f in os.listdir(path) if not f.startswith(".")][:10]
                    file_list = ", ".join(files)
                    return (
                        f"📁 Project aktif: {path}\n"
                        f"   Files: {file_list}"
                        f"{'...' if len(files) == 10 else ''}"
                    )
                except Exception:
                    return f"📁 Project aktif: {path}"
            else:
                return (
                    f"⚠️ Path project '{path}' tidak lagi ada di disk.\n"
                    f"   Gunakan set_project_path untuk update."
                )
        else:
            # Coba auto-detect dari ~/projects/SESSION
            safe_folder = session_id[:8]
            default_path = os.path.expanduser(f"~/projects/{safe_folder}")
            if os.path.exists(default_path):
                # Auto-register
                await project_registry.set(session_id, default_path)
                return (
                    f"📁 Project path auto-detected: {default_path}\n"
                    f"   (path ini telah disimpan untuk session ini)"
                )
            return (
                f"ℹ️ Belum ada project path tersimpan untuk session ini.\n"
                f"   Default path: ~/projects/{safe_folder}\n"
                f"   Gunakan set_project_path untuk menyimpan path project."
            )
    except Exception as e:
        return f"❌ Error get_project_path: {str(e)}"


# ── 10. set_project_path ─────────────────────────────────────────────────────

async def set_project_path(path: str, session_id: Optional[str] = None) -> str:
    """
    Set atau update path project untuk session ini.
    Path ini akan diingat permanen — orchestrator tidak akan lupa lagi.
    """
    if not session_id:
        return "❌ session_id diperlukan"

    try:
        resolved = os.path.realpath(os.path.abspath(
            os.path.expanduser(path)
        ))

        # Buat direktori jika belum ada
        os.makedirs(resolved, exist_ok=True)

        from core.project_registry import project_registry
        await project_registry.set(session_id, resolved)

        # Trigger index update di background
        try:
            from core.project_indexer import project_indexer
            asyncio.create_task(project_indexer.scan_project(session_id, resolved))
        except Exception:
            pass

        return (
            f"✅ Project path disimpan: {resolved}\n"
            f"   Session: {session_id}\n"
            f"   Semua operasi file relatif akan menggunakan path ini."
        )
    except Exception as e:
        return f"❌ Error set_project_path: {str(e)}"


# ── 11. list_all_projects ────────────────────────────────────────────────────

async def list_all_projects(session_id: Optional[str] = None) -> str:
    """
    Tampilkan semua project yang pernah dibuat oleh semua session.
    Berguna untuk orchestrator menemukan project lama.
    """
    try:
        from core.project_registry import project_registry
        all_projects = await project_registry.get_all()

        if not all_projects:
            # Fallback: scan ~/projects/
            projects_dir = os.path.expanduser("~/projects")
            if os.path.exists(projects_dir):
                entries = []
                for item in sorted(os.scandir(projects_dir), key=lambda e: e.name):
                    if item.is_dir():
                        try:
                            files = [f for f in os.listdir(item.path)
                                     if not f.startswith(".")]
                            entries.append(
                                f"  📁 {item.path}  ({len(files)} files)"
                            )
                        except Exception:
                            entries.append(f"  📁 {item.path}")
                if entries:
                    return (
                        f"📂 Projects di ~/projects/ ({len(entries)} folder):\n" +
                        "\n".join(entries)
                    )
            return "ℹ️ Belum ada project yang tercatat."

        lines = [f"📂 Semua project tercatat ({len(all_projects)} session):\n"]
        for sess_id, proj_path in all_projects.items():
            exists = "✅" if os.path.exists(proj_path) else "❌ (tidak ada)"
            short_sess = sess_id[:8] + "..."
            try:
                files = [f for f in os.listdir(proj_path) if not f.startswith(".")]
                file_info = f"  {len(files)} files"
            except Exception:
                file_info = ""
            lines.append(f"  {exists} [{short_sess}] {proj_path}{file_info}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error list_all_projects: {str(e)}"


# ── 12. get_file_info ────────────────────────────────────────────────────────

async def get_file_info(path: str, session_id: Optional[str] = None) -> str:
    """
    Tampilkan informasi detail sebuah file atau folder.
    Berguna sebelum edit/hapus untuk memastikan file yang benar.
    """
    try:
        resolved = _resolve_path(path, session_id)
        if not os.path.exists(resolved):
            return f"❌ Path tidak ditemukan: {resolved}"

        stat = os.stat(resolved)
        import datetime
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        ctime = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

        is_dir = os.path.isdir(resolved)
        size = stat.st_size

        info = [
            f"📄 Info: {resolved}",
            f"   Tipe:     {'Direktori' if is_dir else 'File'}",
            f"   Ukuran:   {size:,} bytes ({size/1024:.1f} KB)",
            f"   Modified: {mtime}",
            f"   Created:  {ctime}",
            f"   Mode:     {oct(stat.st_mode)[-3:]}",
        ]

        if is_dir:
            try:
                items = os.listdir(resolved)
                files = [i for i in items if os.path.isfile(os.path.join(resolved, i))]
                dirs = [i for i in items if os.path.isdir(os.path.join(resolved, i))]
                info.append(f"   Contents: {len(dirs)} dirs, {len(files)} files")
            except Exception:
                pass
        else:
            _, ext = os.path.splitext(resolved)
            info.append(f"   Ekstensi: {ext or '(none)'}")

        return "\n".join(info)

    except Exception as e:
        return f"❌ Error get_file_info: {str(e)}"


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_file_icon(filename: str) -> str:
    """Emoji icon berdasarkan ekstensi file."""
    ext = os.path.splitext(filename)[1].lower()
    icons = {
        ".py":    "🐍", ".js":   "📜", ".jsx":  "⚛️",
        ".ts":    "📘", ".tsx":  "⚛️", ".html": "🌐",
        ".css":   "🎨", ".scss": "🎨", ".json": "📋",
        ".md":    "📝", ".txt":  "📄", ".sh":   "⚙️",
        ".env":   "🔐", ".yml":  "⚙️", ".yaml": "⚙️",
        ".sql":   "🗄️",  ".db":   "🗄️",  ".png":  "🖼️",
        ".jpg":   "🖼️",  ".gif":  "🖼️",  ".svg":  "🖼️",
        ".mp4":   "🎬", ".mp3":  "🎵", ".pdf":  "📕",
        ".zip":   "📦", ".tar":  "📦", ".lock": "🔒",
        ".go":    "🐹", ".rs":   "🦀", ".java": "☕",
        ".rb":    "💎", ".php":  "🐘", ".vue":  "💚",
    }
    return icons.get(ext, "📄")

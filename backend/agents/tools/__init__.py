"""
agents/tools/__init__.py — Tool Registry untuk AI Orchestrator
==============================================================
Semua tools yang tersedia untuk dieksekusi oleh AgentExecutor.
"""

from .core_tools import (
    execute_bash,
    read_file,
    write_file,
    ask_model,
    find_safe_port,
)

# Legacy aliases (tetap ada agar tidak breaking)
try:
    from .core_tools import list_dir, search_files
except ImportError:
    list_dir = None
    search_files = None

from .web_search import web_search

# ── Filesystem tools baru ────────────────────────────────────────────────────
from .filesystem import (
    list_directory,
    file_tree,
    find_files,
    search_in_files,
    make_directory,
    move_file,
    copy_file,
    delete_file,
    get_project_path,
    set_project_path,
    list_all_projects,
    get_file_info,
)

# ── Tool registry — mapping nama → fungsi ────────────────────────────────────
TOOLS = {
    # ── Core tools ────────────────────────────────────────────
    "execute_bash":          execute_bash,
    "read_file":             read_file,
    "write_file":            write_file,
    "ask_model":             ask_model,
    "find_safe_port":        find_safe_port,
    "web_search":            web_search,

    # ── Filesystem tools ──────────────────────────────────────
    "list_directory":        list_directory,    # ls -la terstruktur
    "file_tree":             file_tree,         # tampilkan struktur folder
    "find_files":            find_files,        # cari file by name/pattern
    "search_in_files":       search_in_files,   # grep -r dalam project
    "make_directory":        make_directory,    # mkdir -p
    "move_file":             move_file,         # mv (rename/pindah)
    "copy_file":             copy_file,         # cp -r
    "delete_file":           delete_file,       # rm dengan safety
    "get_project_path":      get_project_path,  # ambil path project aktif
    "set_project_path":      set_project_path,  # simpan path project
    "list_all_projects":     list_all_projects, # lihat semua project
    "get_file_info":         get_file_info,     # stat file detail
}

__all__ = ["TOOLS"] + list(TOOLS.keys())

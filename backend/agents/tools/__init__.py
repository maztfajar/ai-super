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
    read_document,
    replace_in_file,
    schedule_task,
    # ── Office & Computer Use Tools (v5.0) ──────────────────────
    excel_read,
    excel_write,
    excel_formula,
    word_read,
    word_write,
    ppt_create,
    ppt_add_slide,
    sql_query,
    sql_execute,
    screenshot_screen,
    app_plan_generate,
)

# Legacy aliases (tetap ada agar tidak breaking)
try:
    from .core_tools import list_dir, search_files
except ImportError:
    list_dir = None
    search_files = None

from .web_search import web_search
from .workflow import update_task_status

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

# ── Browser Automation tools ───────────────────────────────────────────────
from .browser_automation import (
    browser_navigate,
    browser_click,
    browser_type,
    browser_extract_text,
    browser_screenshot,
)

# ── Google Ecosystem tools (GOG CLI) ────────────────────────────────────────
try:
    from .google_tools import (
        gog_read_emails,
        gog_send_email,
        gog_create_calendar_event,
        gog_list_calendar_events,
        gog_read_sheet,
        gog_append_sheet_row,
        gog_list_drive_files,
    )
    _GOOGLE_TOOLS_AVAILABLE = True
except ImportError:
    _GOOGLE_TOOLS_AVAILABLE = False

# ── Media tools ───────────────────────────────────────────────
from .media import (
    generate_image,
)

# ── Tool registry — mapping nama → fungsi ────────────────────────────────────
TOOLS = {
    # ── Core tools ────────────────────────────────────────────
    "execute_bash":          execute_bash,
    "read_file":             read_file,
    "write_file":            write_file,
    "ask_model":             ask_model,
    "find_safe_port":        find_safe_port,
    "schedule_task":         schedule_task,
    "web_search":            web_search,
    "read_document":         read_document,
    "replace_in_file":       replace_in_file,
    "generate_image":        generate_image,

    # ── Office Tools (v5.0) ───────────────────────────────────
    "excel_read":            excel_read,        # Baca file Excel
    "excel_write":           excel_write,       # Buat/tulis file Excel
    "excel_formula":         excel_formula,     # Masukkan formula Excel
    "word_read":             word_read,         # Baca file Word (.docx)
    "word_write":            word_write,        # Buat file Word dari teks
    "ppt_create":            ppt_create,        # Buat file PowerPoint baru
    "ppt_add_slide":         ppt_add_slide,     # Tambah slide ke PPT
    "sql_query":             sql_query,         # Query SELECT ke SQLite
    "sql_execute":           sql_execute,       # DDL/DML ke SQLite
    "screenshot_screen":     screenshot_screen, # Tangkap layar desktop
    "app_plan_generate":     app_plan_generate, # Generate rencana aplikasi

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

    # ── Browser Automation tools ──────────────────────────────
    "browser_navigate":      browser_navigate,
    "browser_click":         browser_click,
    "browser_type":          browser_type,
    "browser_extract_text":  browser_extract_text,
    "browser_screenshot":    browser_screenshot,

    # ── Workflow tools ────────────────────────────────────────
    "update_task_status":    update_task_status,
}

# Inject Google tools jika library tersedia
if _GOOGLE_TOOLS_AVAILABLE:
    TOOLS.update({
        # ── GOG CLI: Google Ecosystem ──────────────────────────
        "gog_read_emails":           gog_read_emails,
        "gog_send_email":            gog_send_email,
        "gog_create_calendar_event": gog_create_calendar_event,
        "gog_list_calendar_events":  gog_list_calendar_events,
        "gog_read_sheet":            gog_read_sheet,
        "gog_append_sheet_row":      gog_append_sheet_row,
        "gog_list_drive_files":      gog_list_drive_files,
    })

__all__ = ["TOOLS"] + list(TOOLS.keys())


# Legacy aliases (tetap ada agar tidak breaking)
try:
    from .core_tools import list_dir, search_files
except ImportError:
    list_dir = None
    search_files = None

from .web_search import web_search
from .workflow import update_task_status

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

# ── Browser Automation tools ───────────────────────────────────────────────
from .browser_automation import (
    browser_navigate,
    browser_click,
    browser_type,
    browser_extract_text,
    browser_screenshot,
)

# ── Google Ecosystem tools (GOG CLI) ────────────────────────────────────────
try:
    from .google_tools import (
        gog_read_emails,
        gog_send_email,
        gog_create_calendar_event,
        gog_list_calendar_events,
        gog_read_sheet,
        gog_append_sheet_row,
        gog_list_drive_files,
    )
    _GOOGLE_TOOLS_AVAILABLE = True
except ImportError:
    _GOOGLE_TOOLS_AVAILABLE = False

# ── Media tools ───────────────────────────────────────────────
from .media import (
    generate_image,
)

# ── Tool registry — mapping nama → fungsi ────────────────────────────────────
TOOLS = {
    # ── Core tools ────────────────────────────────────────────
    "execute_bash":          execute_bash,
    "read_file":             read_file,
    "write_file":            write_file,
    "ask_model":             ask_model,
    "find_safe_port":        find_safe_port,
    "schedule_task":         schedule_task,
    "web_search":            web_search,
    "read_document":         read_document,
    "replace_in_file":       replace_in_file,
    "generate_image":        generate_image,

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
    
    # ── Browser Automation tools ──────────────────────────────
    "browser_navigate":      browser_navigate,
    "browser_click":         browser_click,
    "browser_type":          browser_type,
    "browser_extract_text":  browser_extract_text,
    "browser_screenshot":    browser_screenshot,

    # ── Workflow tools ────────────────────────────────────────
    "update_task_status":    update_task_status,
}

# Inject Google tools jika library tersedia
if _GOOGLE_TOOLS_AVAILABLE:
    TOOLS.update({
        # ── GOG CLI: Google Ecosystem ──────────────────────────
        "gog_read_emails":           gog_read_emails,
        "gog_send_email":            gog_send_email,
        "gog_create_calendar_event": gog_create_calendar_event,
        "gog_list_calendar_events":  gog_list_calendar_events,
        "gog_read_sheet":            gog_read_sheet,
        "gog_append_sheet_row":      gog_append_sheet_row,
        "gog_list_drive_files":      gog_list_drive_files,
    })

__all__ = ["TOOLS"] + list(TOOLS.keys())

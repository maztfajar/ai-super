#!/usr/bin/env python3
"""
Setup script untuk sistem RAG AI ORCHESTRATOR.
Membuat semua folder yang diperlukan, verifikasi dependencies, dan print panduan setup.
Jalankan: python scripts/setup_rag.py
"""
import sys
import os
import subprocess

# Tambahkan path backend ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(env_path)


def ok(msg): print(f"  ✅ {msg}")
def err(msg): print(f"  ❌ {msg}")
def info(msg): print(f"  ℹ️  {msg}")
def warn(msg): print(f"  ⚠️  {msg}")
def header(t): print(f"\n{'═'*55}\n  {t}\n{'═'*55}")


def setup_folders():
    header("1. Setup Folder Struktur")
    try:
        from rag.folder_manager import folder_manager
        results = folder_manager.ensure_all_dirs()
        all_ok = True
        for path, status in results.items():
            if status == "OK":
                ok(path)
            else:
                err(path)
                all_ok = False
        return all_ok
    except Exception as e:
        err(f"Folder setup gagal: {e}")
        return False


def check_dependencies():
    header("2. Cek Python Dependencies")
    required = {
        "chromadb": "chromadb>=0.5.0",
        "langchain": "langchain>=0.2.0",
        "langchain_community": "langchain-community>=0.2.0",
        "langchain_openai": "langchain-openai>=0.1.0",
        "pypdf": "pypdf>=4.2.0",
        "docx": "python-docx>=1.1.2",
        "openpyxl": "openpyxl>=3.1.0",
        "pptx": "python-pptx>=0.6.23",
        "requests": "requests>=2.32.0",
        "structlog": "structlog>=24.2.0",
    }

    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            ok(f"{module}")
        except ImportError:
            err(f"{module} — belum terinstall ({package})")
            missing.append(package)

    if missing:
        warn(f"\n  Install dengan perintah:")
        print(f"\n  pip install {' '.join(missing)}\n")
    else:
        ok("Semua dependencies OK!")

    return len(missing) == 0


def check_env_config():
    header("3. Cek Konfigurasi .env")
    checks = {
        "SUMOPOD_API_KEY": os.environ.get("SUMOPOD_API_KEY", ""),
        "SUMOPOD_HOST": os.environ.get("SUMOPOD_HOST", ""),
        "EMBEDDING_PROVIDER": os.environ.get("EMBEDDING_PROVIDER", "sumopod"),
        "SUMOPOD_EMBEDDING_MODEL": os.environ.get("SUMOPOD_EMBEDDING_MODEL", "text-embedding-3-small"),
        "CHROMA_PERSIST_DIR": os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma_db"),
    }

    issues = []
    for key, val in checks.items():
        if val:
            masked = val if "KEY" not in key else val[:8] + "..." + val[-4:]
            ok(f"{key} = {masked}")
        else:
            if key == "SUMOPOD_API_KEY":
                err(f"{key} = (kosong/tidak ada!)")
                issues.append(key)
            else:
                warn(f"{key} = (menggunakan default)")

    return len(issues) == 0


def check_rag_documents():
    header("4. Cek Folder rag_documents")
    try:
        from rag.folder_manager import folder_manager
        scan = folder_manager.check_rag_documents()

        info(f"Direktori: {scan['directory']}")
        info(f"Total file: {scan['total_files']}")

        if scan["total_files"] == 0:
            warn("Folder rag_documents kosong.")
            info("Taruh file PDF/DOCX/XLSX/PPTX/CSV di folder ini agar bisa di-scan.")
        else:
            for f in scan["files"]:
                status = "⚠️ KOSONG" if f["is_empty"] else f"{f['size_kb']} KB"
                print(f"    {f['name']} ({status})")

        if scan["empty_files"]:
            warn(f"File dengan 0 bytes (akan dilewati): {scan['empty_files']}")

        return True
    except Exception as e:
        err(f"Gagal scan rag_documents: {e}")
        return False


def update_env_file():
    """Tambahkan EMBEDDING_PROVIDER=sumopod ke .env jika belum ada."""
    header("5. Update .env")
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")

    try:
        with open(env_file, "r") as f:
            content = f.read()

        updated = False

        # Update EMBEDDING_PROVIDER ke sumopod
        if "EMBEDDING_PROVIDER=" in content:
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.startswith("EMBEDDING_PROVIDER=") and "sumopod" not in line:
                    new_lines.append("EMBEDDING_PROVIDER=sumopod")
                    warn(f"EMBEDDING_PROVIDER diupdate ke 'sumopod' (dari: {line})")
                    updated = True
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)
        else:
            content += "\n# RAG Embedding Provider\nEMBEDDING_PROVIDER=sumopod\n"
            warn("Menambahkan EMBEDDING_PROVIDER=sumopod ke .env")
            updated = True

        # Tambahkan SUMOPOD_EMBEDDING_MODEL jika belum ada
        if "SUMOPOD_EMBEDDING_MODEL=" not in content:
            content += "\nSUMOPOD_EMBEDDING_MODEL=text-embedding-3-small\n"
            warn("Menambahkan SUMOPOD_EMBEDDING_MODEL=text-embedding-3-small ke .env")
            updated = True

        if updated:
            with open(env_file, "w") as f:
                f.write(content)
            ok(".env berhasil diupdate!")
        else:
            ok(".env sudah benar, tidak perlu diupdate")

        return True
    except Exception as e:
        err(f"Gagal update .env: {e}")
        return False


def print_next_steps(all_ok: bool):
    header("LANGKAH SELANJUTNYA")
    if all_ok:
        print("""
  ✅ Setup selesai! Sistem RAG siap.

  Cara penggunaan:
  ─────────────────────────────────────────────────
  📁 Upload lewat UI:
     → Buka app → Knowledge → Upload File
     → Format: PDF, DOCX, XLSX, PPTX, CSV, TXT

  📂 Bulk import via folder:
     → Taruh file di folder: ../rag_documents/
     → Di UI: Knowledge → Scan RAG Documents
     → Atau via API: POST /api/rag/scan-rag-documents

  🔄 Sync Google Drive:
     → Knowledge → Google Drive → Pilih folder → Sync

  📊 Cek status RAG:
     → API: GET /api/rag/status

  🔁 Restart server setelah setup:
     → sudo systemctl restart ai_orchestrator
     → atau: cd backend && python main.py
""")
    else:
        print("""
  ⚠️  Ada masalah yang perlu diselesaikan dulu.
  Lihat pesan error di atas dan perbaiki sebelum restart server.

  Install dependencies yang hilang:
     pip install -r requirements.txt

  Cek konfigurasi .env:
     nano /home/maztfajar/Downloads/ai_orchestrator/.env

  Test ulang koneksi Sumopod:
     python scripts/test_sumopod_connection.py
""")


def main():
    print("\n" + "█" * 55)
    print("  AI ORCHESTRATOR — RAG System Setup")
    print("█" * 55)

    r1 = setup_folders()
    r2 = check_dependencies()
    r3 = check_env_config()
    r4 = check_rag_documents()
    r5 = update_env_file()

    all_ok = r1 and r3  # r2 (deps) hanya warning, tidak blockers
    print_next_steps(all_ok)


if __name__ == "__main__":
    main()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import os

# Resolve path ke .env di root project
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _load_env_file(override: bool = False):
    """Load .env values into os.environ with optional override."""
    if not _ENV_FILE.exists():
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(str(_ENV_FILE), override=override)
    except ImportError:
        for line in _ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if not k:
                continue
            if override or k not in os.environ:
                os.environ[k] = v


# Load .env values into os.environ when the app starts.
_load_env_file(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "AI ORCHESTRATOR"
    APP_VERSION: str = "1.0.0"
    APP_BUILD: int = 1009
    UPDATE_SERVER_URL: str = "https://eai-orchestrator.kapanewonpengasih.my.id"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 7860

    # ── PATCH: Flag untuk allow/disable registrasi publik ──────
    ALLOW_PUBLIC_REGISTER: bool = False

    # Database
    DATABASE_URL: str = ""

    @property
    def get_db_url(self) -> str:
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            url = self.DATABASE_URL.strip()
            # FIX: Convert relative SQLite path to absolute based on backend directory 
            # to prevent split-brain databases if scripts are executed from different CWDs.
            if url.startswith("sqlite+aiosqlite:///./"):
                root = Path(__file__).resolve().parent.parent.parent
                relative_path = url.replace("sqlite+aiosqlite:///./", "")
                db_path = root / relative_path
                db_path.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite+aiosqlite:///{db_path}"
            return url
        
        # Selalu gunakan absolute path ke root/data/ai-orchestrator.db jika kosong
        root = Path(__file__).resolve().parent.parent.parent
        db_path = root / "data" / "ai-orchestrator.db"
        # Pastikan folder exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI APIs
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_AVAILABLE_MODELS: str = ""

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_AVAILABLE_MODELS: str = ""

    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_AVAILABLE_MODELS: str = ""

    # Ollama (Local)
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = ""
    OLLAMA_AVAILABLE_MODELS: str = ""

    # ── SUMOPOD ───────────────────────────────────────────────
    SUMOPOD_API_KEY: Optional[str] = None
    SUMOPOD_HOST: str = "https://ai.sumopod.com/v1"
    SUMOPOD_DEFAULT_MODEL: str = ""
    SUMOPOD_AVAILABLE_MODELS: str = ""
    SUMOPOD_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Default model
    DEFAULT_MODEL: str = "ollama/llama3.1"

    # RAG
    @property
    def CHROMA_PERSIST_DIR(self) -> str:
        root = Path(__file__).resolve().parent.parent.parent
        return str(root / "data" / "chroma_db")

    RAG_DOCUMENTS_DIR: str = "../rag_documents"
    RAG_TIMEOUT_SECONDS: int = 45
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Google Drive
    GDRIVE_UPLOAD_FOLDER_ID: str = ""
    GOOGLE_DRIVE_CREDENTIALS: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    ADMIN_TELEGRAM_CHAT_ID: str = ""  # Chat ID untuk laporan self-healing

    # WhatsApp
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: str = "ai-orchestrator-verify"

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_EMAIL: str = "admin@ai-orchestrator.local"

    # Files
    @property
    def UPLOAD_DIR(self) -> str:
        root = Path(__file__).resolve().parent.parent.parent
        return str(root / "data" / "uploads")

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,csv,md,json,xlsx,xls,pptx,ppt"

    # ── Email (SMTP) ──────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS:  bool = True
    APP_URL:   str = "http://localhost:7860"

    # Rate limit
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Logging
    LOG_LEVEL: str = "IMPORTANT"
    @property
    def LOG_FILE(self) -> str:
        root = Path(__file__).resolve().parent.parent.parent
        return str(root / "data" / "logs" / "ai-orchestrator.log")

    # Tunnel / Cloudflare
    CLOUDFLARE_TUNNEL_ID: Optional[str] = None
    CLOUDFLARE_TUNNEL_TOKEN: Optional[str] = None
    CLOUDFLARE_API_TOKEN: Optional[str] = None

    # AI Role Mappings
    AI_ROLE_CODING: Optional[str] = None
    AI_ROLE_REASONING: Optional[str] = None
    AI_ROLE_CHAT: Optional[str] = None

    @property
    def allowed_extensions_list(self) -> list:
        return [e.strip().lower() for e in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def sumopod_models_list(self) -> list:
        if not self.SUMOPOD_AVAILABLE_MODELS:
            return [self.SUMOPOD_DEFAULT_MODEL] if self.SUMOPOD_DEFAULT_MODEL else []
        return [m.strip() for m in self.SUMOPOD_AVAILABLE_MODELS.split(",") if m.strip()]

    @property
    def ollama_models_list(self) -> list:
        if not self.OLLAMA_AVAILABLE_MODELS:
            return []
        return [m.strip() for m in self.OLLAMA_AVAILABLE_MODELS.split(",") if m.strip()]

    def reload(self):
        """Reload configuration from .env and environment variables in-place"""
        _load_env_file(override=True)
        new_settings = Settings()
        for field in self.model_fields:
            try:
                setattr(self, field, getattr(new_settings, field))
            except Exception:
                pass


settings = Settings()


# ══════════════════════════════════════════════════════════════
# PATCH 1: Validasi keamanan konfigurasi saat startup
# Mencegah aplikasi berjalan dengan kredensial default berbahaya
# ══════════════════════════════════════════════════════════════
_DANGEROUS_DEFAULTS = {
    "SECRET_KEY": ("change-me-in-production",
                   "SECRET_KEY masih menggunakan nilai default! "
                   "Ganti dengan string acak 32+ karakter di file .env Anda. "
                   "Contoh: python3 -c \"import secrets; print(secrets.token_hex(32))\""),
    "ADMIN_PASSWORD": ("admin",
                       "ADMIN_PASSWORD masih 'admin'! "
                       "Ganti dengan password yang kuat di file .env Anda."),
}


def validate_security_config() -> None:
    """
    Validasi konfigurasi keamanan kritis saat startup.
    Raise RuntimeError jika ada nilai default berbahaya yang belum diganti.
    Hanya aktif jika DEBUG=False (production mode).
    """
    if settings.DEBUG:
        # Di mode debug/development, hanya tampilkan peringatan
        import warnings
        for field, (default_val, msg) in _DANGEROUS_DEFAULTS.items():
            current = getattr(settings, field, "")
            if current == default_val:
                warnings.warn(
                    f"\n⚠️  PERINGATAN KEAMANAN [{field}]: {msg}\n",
                    stacklevel=2,
                )
        return

    errors = []
    for field, (default_val, msg) in _DANGEROUS_DEFAULTS.items():
        current = getattr(settings, field, "")
        if current == default_val:
            errors.append(f"\n  ❌ [{field}]: {msg}")

    if errors:
        raise RuntimeError(
            "\n\n🔴 STARTUP DITOLAK — Konfigurasi keamanan tidak aman:"
            + "".join(errors)
            + "\n\nEdit file .env Anda dan restart aplikasi.\n"
        )

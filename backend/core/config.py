from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

# Resolve path ke .env di root project (bukan relative ke CWD)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI SUPER ASSISTANT"
    APP_VERSION: str = "1.0.0"
    APP_BUILD: int = 1009
    UPDATE_SERVER_URL: str = "https://eai-super-assistant.kapanewonpengasih.my.id"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 7860

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ai-super-assistant.db"

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
    OLLAMA_AVAILABLE_MODELS: str = ""   # comma-separated, kosong = auto-detect

    # ── SUMOPOD ───────────────────────────────────────────────
    SUMOPOD_API_KEY: Optional[str] = None
    SUMOPOD_HOST: str = "https://ai.sumopod.com/v1"
    SUMOPOD_DEFAULT_MODEL: str = ""
    SUMOPOD_AVAILABLE_MODELS: str = ""
    # Embedding via Sumopod (OpenAI-compatible endpoint)
    SUMOPOD_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Default model
    DEFAULT_MODEL: str = "ollama/llama3.1"

    # RAG
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    RAG_DOCUMENTS_DIR: str = "../rag_documents"  # Folder dokumen RAG (relative to backend/)
    RAG_TIMEOUT_SECONDS: int = 45                # Timeout per dokumen processing
    EMBEDDING_PROVIDER: str = "sumopod"          # options: sumopod, openai, google, local
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Google Drive
    GDRIVE_UPLOAD_FOLDER_ID: str = ""  # Folder ID tujuan upload (Service Account butuh shared folder)

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None

    # WhatsApp
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: str = "ai-super-assistant-verify"

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "ai-super-assistant2024"
    ADMIN_EMAIL: str = "admin@ai-super-assistant.local"

    # Files
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,csv,md,json,xlsx,xls,pptx,ppt"

    # ── Email (SMTP) ──────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""           # From address, default = SMTP_USER
    SMTP_TLS:  bool = True         # True = STARTTLS (587), False = SSL (465)
    APP_URL:   str = "http://localhost:7860"  # Base URL untuk link email

    # Rate limit
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./data/logs/ai-super-assistant.log"

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"

    @property
    def allowed_extensions_list(self) -> list:
        return [e.strip().lower() for e in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def sumopod_models_list(self) -> list:
        """Return list of Sumopod models from env"""
        if not self.SUMOPOD_AVAILABLE_MODELS:
            return [self.SUMOPOD_DEFAULT_MODEL] if self.SUMOPOD_DEFAULT_MODEL else []
        return [m.strip() for m in self.SUMOPOD_AVAILABLE_MODELS.split(",") if m.strip()]

    @property
    def ollama_models_list(self) -> list:
        """Return Ollama models dari env (jika diset manual)"""
        if not self.OLLAMA_AVAILABLE_MODELS:
            return []
        return [m.strip() for m in self.OLLAMA_AVAILABLE_MODELS.split(",") if m.strip()]

    def reload(self):
        """Reload configuration from .env and environment variables in-place"""
        new_settings = Settings()
        for field in self.model_fields:
            setattr(self, field, getattr(new_settings, field))


settings = Settings()

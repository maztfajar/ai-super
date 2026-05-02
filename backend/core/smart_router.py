"""Smart Router — auto-pilih model terbaik untuk setiap task"""
from typing import Optional
from core.model_manager import model_manager
from core.config import settings


ROUTING_RULES = {
    "coding": {
        "keywords": ["code", "python", "javascript", "debug", "function", "class",
                     "error", "bug", "program", "script", "api", "sql", "kode",
                     "coding", "pemrograman", "syntax"],
        "preferred": ["deepseek-v4-pro", "qwen3.6-flash"],
    },
    "writing": {
        "keywords": ["write", "essay", "article", "blog", "email", "letter",
                     "tulis", "artikel", "laporan", "report", "summary", "rangkum",
                     "cerita", "puisi"],
        "preferred": ["qwen3.6-flash", "deepseek-v4-pro"],
    },
    "analysis": {
        "keywords": ["analyze", "analysis", "compare", "data", "chart", "statistic",
                     "analisa", "bandingkan", "grafik", "tren", "insight"],
        "preferred": ["deepseek-v4-pro", "qwen3.6-flash"],
    },
    "translation": {
        "keywords": ["translate", "terjemah", "bahasa", "language", "indonesian", "english"],
        "preferred": ["qwen3.6-flash", "deepseek-v4-pro"],
    },
    "simple": {
        "keywords": ["hello", "halo", "hi", "thanks", "terima kasih", "apa kabar",
                     "hei", "selamat", "oke", "ok"],
        "preferred": [f"ollama/{settings.OLLAMA_DEFAULT_MODEL}", "gpt-5-nano"],
    },
}


class SmartRouter:
    def detect_task(self, message: str) -> str:
        msg_lower = message.lower()
        for task, config in ROUTING_RULES.items():
            if any(kw in msg_lower for kw in config["keywords"]):
                return task
        return "default"

    def pick_model(self, task: str, user_preferred: Optional[str] = None) -> str:
        """Pilih model terbaik yang tersedia"""
        # User pilih sendiri → langsung pakai
        if user_preferred and user_preferred in model_manager.available_models:
            return user_preferred

        # Coba preferred list untuk task ini
        config = ROUTING_RULES.get(task, {})
        candidates = list(config.get("preferred", []))

        # Tambah semua model yang ada sebagai fallback
        candidates += list(model_manager.available_models.keys())

        for model in candidates:
            if model in model_manager.available_models:
                return model
            for k in model_manager.available_models:
                if model in k:
                    return k

        # Last resort
        return settings.DEFAULT_MODEL

    def route(self, message: str, user_preferred: Optional[str] = None) -> dict:
        task = self.detect_task(message)
        model = self.pick_model(task, user_preferred)
        return {"task_type": task, "model": model}


smart_router = SmartRouter()

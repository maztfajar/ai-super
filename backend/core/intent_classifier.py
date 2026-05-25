"""
Intent Classifier — menentukan apakah user butuh File Manager popup atau tidak.
Dijalankan SEBELUM orchestra/orchestrator memproses pesan.

Integrasi: import dan panggil classify_intent(message) di chat.py endpoint.
"""

import re
from enum import Enum
from typing import Optional
import httpx
import json
from core.config import settings

# ─────────────────────────────────────────────
# Intent types
# ─────────────────────────────────────────────

class IntentType(str, Enum):
    FILE_SYSTEM   = "FILE_SYSTEM"     # → popup browse/edit file existing
    BUILD_APP     = "BUILD_APP"       # → popup pilih lokasi project baru
    GENERATE      = "GENERATE"        # → tidak perlu popup, langsung proses
    CONVERSATION  = "CONVERSATION"    # → tidak perlu popup, langsung proses


class ClassifyResult:
    def __init__(self, intent: IntentType, confidence: float, reason: str):
        self.intent = intent
        self.confidence = confidence
        self.reason = reason
        self.needs_popup = intent in (IntentType.FILE_SYSTEM, IntentType.BUILD_APP)
        self.popup_mode = self._get_popup_mode()

    def _get_popup_mode(self) -> Optional[str]:
        if self.intent == IntentType.FILE_SYSTEM:
            return "browse"       # navigasi / edit file yang sudah ada
        if self.intent == IntentType.BUILD_APP:
            return "save_new"     # pilih folder untuk project baru
        return None

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "needs_popup": self.needs_popup,
            "popup_mode": self.popup_mode,
        }


# ─────────────────────────────────────────────
# Fast keyword pre-filter (sebelum LLM call)
# Hemat token untuk kasus yang sangat jelas
# ─────────────────────────────────────────────

# Kata kunci yang PASTI butuh popup file manager
_FILE_KEYWORDS = [
    r"\bedit\s+(file|kode|script|komponen|component)\b",
    r"\bbuka\s+(file|folder|direktori|directory|project)\b",
    r"\bsimpan\s+(ke|di|dalam)\s+folder\b",
    r"\bpindahkan?\s+file\b",
    r"\bhapus\s+file\b",
    r"\bganti\s+nama\s+file\b",
    r"\bmodifikasi\s+file\b",
    r"\bupdate\s+file\b",
    r"\bopen\s+file\b",
]

# Kata kunci yang PASTI TIDAK butuh popup
_NO_POPUP_KEYWORDS = [
    r"\bbuatkan?\b.*\b(artikel|berita|cerita|puisi|konten|caption|post)\b",
    r"\bgenerate\b.*\b(gambar|image|foto)\b",
    r"\bbikin(kan)?\b.*\b(artikel|berita|cerita|puisi|caption)\b",
    r"\bringkas(kan)?\b",
    r"\banalisis\b",
    r"\bjelaskan?\b",
    r"\bterjemahkan?\b",
    r"\bapa\s+(itu|yang)\b",
    r"\bbagaimana\s+cara\b",
    r"\btolong\s+jawab\b",
]

# Kata kunci BUILD_APP — butuh popup pilih lokasi
_BUILD_KEYWORDS = [
    r"\bbuatkan?\s+(app|aplikasi|website|web|dashboard|sistem|platform|api|backend|frontend)\b",
    r"\bbuat\s+(project|proyek)\s+baru\b",
    r"\bbikin(kan)?\s+(app|aplikasi|website|web|dashboard|api)\b",
    r"\bcoding(kan)?\s+(app|aplikasi|website)\b",
    r"\bdevelopment\s+(app|website)\b",
    r"\bbuild\s+(app|website|project)\b",
    r"\bsetup\s+(project|proyek)\b",
    r"\binisialisasi\s+project\b",
]


def _keyword_precheck(message: str) -> Optional[IntentType]:
    """Cek keyword dulu sebelum panggil LLM. Return None kalau tidak yakin."""
    msg = message.lower()

    for pattern in _NO_POPUP_KEYWORDS:
        if re.search(pattern, msg):
            return IntentType.GENERATE

    for pattern in _FILE_KEYWORDS:
        if re.search(pattern, msg):
            return IntentType.FILE_SYSTEM

    for pattern in _BUILD_KEYWORDS:
        if re.search(pattern, msg):
            return IntentType.BUILD_APP

    return None  # tidak yakin → serahkan ke LLM


# ─────────────────────────────────────────────
# LLM Classifier (gemini-2.0-flash-lite — cepat, murah)
# ─────────────────────────────────────────────

_CLASSIFIER_SYSTEM = """Kamu adalah classifier intent. Tugasmu HANYA mengklasifikasikan pesan user ke salah satu dari 4 kategori.

Definisi:
- FILE_SYSTEM: user ingin membuka, mengedit, menyimpan, memindahkan, atau menghapus file/folder yang SUDAH ADA di direktori
- BUILD_APP: user ingin membuat aplikasi, website, dashboard, API, atau project coding BARU (memerlukan lokasi penyimpanan)
- GENERATE: user ingin membuat konten teks (artikel, berita, cerita, ringkasan, analisis), gambar, atau output non-file
- CONVERSATION: pertanyaan, diskusi, permintaan informasi, atau hal lain yang tidak masuk kategori di atas

PENTING:
- "buatkan artikel/berita/gambar/cerita" → selalu GENERATE, bukan BUILD_APP
- "buatkan app/website/dashboard/API" → selalu BUILD_APP
- "edit file X / buka folder Y" → selalu FILE_SYSTEM
- "apa itu X / jelaskan Y / bagaimana cara Z" → selalu CONVERSATION

Balas dengan JSON satu baris:
{"intent": "FILE_SYSTEM|BUILD_APP|GENERATE|CONVERSATION", "confidence": 0.0-1.0, "reason": "alasan singkat"}"""


async def classify_intent(message: str) -> ClassifyResult:
    """
    Klasifikasikan intent user. Panggil ini di endpoint chat sebelum proses pesan.
    
    Returns ClassifyResult dengan .needs_popup dan .popup_mode.
    """

    # 1. Cek keyword dulu (lebih cepat, gratis)
    keyword_result = _keyword_precheck(message)
    if keyword_result is not None:
        return ClassifyResult(
            intent=keyword_result,
            confidence=0.95,
            reason="keyword match"
        )

    # 2. Kalau tidak yakin → tanya LLM
    try:
        headers = {
            "Authorization": f"Bearer {settings.SUMOPOD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Gunakan model sumopod
        model = "gemini/gemini-2.0-flash-lite"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": message}
            ],
            "max_tokens": 150,
            "temperature": 0.1
        }

        async with httpx.AsyncClient(timeout=10.0) as httpx_client:
            response = await httpx_client.post(
                f"{settings.SUMOPOD_HOST}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            res_data = response.json()
            text = res_data["choices"][0]["message"]["content"].strip()

        # Parse JSON safely
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]
        data = json.loads(text)

        return ClassifyResult(
            intent=IntentType(data["intent"]),
            confidence=float(data.get("confidence", 0.8)),
            reason=data.get("reason", "LLM classification")
        )

    except Exception as e:
        # Fallback kalau LLM gagal → anggap CONVERSATION (aman, tidak popup)
        print(f"[IntentClassifier] Error: {e}, fallback to CONVERSATION")
        return ClassifyResult(
            intent=IntentType.CONVERSATION,
            confidence=0.5,
            reason=f"fallback: {str(e)}"
        )


# ─────────────────────────────────────────────
# Versi sync (kalau endpoint-mu tidak async)
# ─────────────────────────────────────────────

def classify_intent_sync(message: str) -> ClassifyResult:
    """Versi synchronous dari classify_intent."""
    keyword_result = _keyword_precheck(message)
    if keyword_result is not None:
        return ClassifyResult(
            intent=keyword_result,
            confidence=0.95,
            reason="keyword match"
        )

    try:
        headers = {
            "Authorization": f"Bearer {settings.SUMOPOD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        model = "gemini/gemini-2.0-flash-lite"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": message}
            ],
            "max_tokens": 150,
            "temperature": 0.1
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.SUMOPOD_HOST}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            res_data = response.json()
            text = res_data["choices"][0]["message"]["content"].strip()
            
        # Parse JSON safely
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]
        data = json.loads(text)

        return ClassifyResult(
            intent=IntentType(data["intent"]),
            confidence=float(data.get("confidence", 0.8)),
            reason=data.get("reason", "LLM classification")
        )
    except Exception as e:
        print(f"[IntentClassifier] Sync Error: {e}, fallback to CONVERSATION")
        return ClassifyResult(
            intent=IntentType.CONVERSATION,
            confidence=0.5,
            reason=f"fallback: {str(e)}"
        )

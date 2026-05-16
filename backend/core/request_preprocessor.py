"""
AI Orchestrator — Request Preprocessor (v3.0 — Human Logic Engine)
===================================================================
Perubahan dari v2.1:
  1. [BARU] HumanContextLayer: deteksi emosi, urgensi, dan niat tersirat pengguna
  2. [BARU] EmotionalState dataclass: menyimpan kondisi emosional pengguna
  3. TaskSpecification diperluas: + emotional_state, + implied_need, + tone_hint
  4. PREPROCESSOR_PROMPT diperbarui: LLM kini juga menganalisis emosi & niat tersirat
  5. _enrich() diperluas: sesuaikan respons berdasarkan kondisi emosional
  6. Semua fitur v2.1 dipertahankan (fast-path, cache, fallback, dll)
"""

import json
import time
import hashlib
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()

_CLASSIFICATION_CACHE: Dict[str, tuple] = {}
_CACHE_TTL_SECONDS = 1800
_CACHE_MAX_SIZE = 512


# ══════════════════════════════════════════════════════════════════════════════
# HUMAN LOGIC ENGINE — Struktur Data Emosional
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionalState:
    """
    Representasi kondisi emosional dan konteks manusiawi pengguna.
    Diisi oleh HumanContextLayer sebelum klasifikasi intent teknis.
    """
    # Emosi dominan yang terdeteksi
    dominant_emotion: str = "neutral"
    # Contoh: "neutral", "frustrated", "excited", "anxious", "confused",
    #          "tired", "urgent", "happy", "sad", "grateful", "curious"

    # Intensitas emosi: 0.0 (tidak ada) – 1.0 (sangat kuat)
    intensity: float = 0.0

    # Niat tersirat yang tidak diucapkan secara eksplisit
    # Contoh: "needs_validation", "needs_reassurance", "wants_quick_fix",
    #          "exploring_options", "venting", "seeking_clarity"
    implied_need: str = "none"

    # Petunjuk nada respons yang sebaiknya digunakan Orchestra
    # Contoh: "warm", "concise", "enthusiastic", "calm", "professional", "playful"
    tone_hint: str = "balanced"

    # Apakah pengguna terlihat terburu-buru / ada urgensi waktu
    has_time_pressure: bool = False

    # Apakah pengguna terlihat butuh konfirmasi / validasi dulu sebelum dilanjutkan
    needs_acknowledgment: bool = False

    # Sinyal kata-kata yang memicu deteksi ini
    detected_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskSpecification:
    """Structured output from the request preprocessor (v3.0)."""
    original_message: str = ""
    intents: List[str] = field(default_factory=list)
    primary_intent: str = "general"
    action_type: str = "execute"
    complexity_score: float = 0.0
    is_simple: bool = True
    requires_multi_agent: bool = False
    quality_priority: str = "balanced"
    max_cost_preference: str = "normal"
    urgency: str = "normal"
    entities: Dict[str, List[str]] = field(default_factory=dict)
    mentioned_models: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    user_id: str = ""
    session_id: str = ""
    preprocessing_time_ms: int = 0
    raw_classification: Optional[Dict] = None

    # ── HUMAN LOGIC ENGINE — Field baru ──────────────────────────────────────
    # Kondisi emosional pengguna yang terdeteksi
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    # Niat tersirat (ringkasan cepat untuk dipakai oleh orchestrator)
    implied_need: str = "none"
    # Petunjuk nada untuk model yang akan merespons
    tone_hint: str = "balanced"
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HUMAN CONTEXT LAYER — Deteksi Emosi & Niat Tersirat
# ══════════════════════════════════════════════════════════════════════════════

class HumanContextLayer:
    """
    Lapisan pemahaman manusiawi.
    Menganalisis pesan dan history untuk mendeteksi emosi, urgensi,
    dan niat tersirat pengguna — sebelum klasifikasi intent teknis dilakukan.
    """

    # ── Sinyal emosi ─────────────────────────────────────────────────────────

    EMOTION_SIGNALS = {
        "frustrated": [
            "kenapa", "kok", "masa", "tidak bisa", "nggak bisa", "gagal terus",
            "error terus", "masih error", "tetap error", "sudah coba", "udah coba",
            "capek", "bosen", "bete", "kesel", "pusing", "nyerah", "gak ngerti",
            "tidak mengerti", "bingung banget", "ribet banget", "susah banget",
            "why", "why is", "doesn't work", "not working", "keeps failing",
            "i give up", "frustrated", "annoying", "ugh", "argh",
        ],
        "excited": [
            "wah", "wow", "mantap", "keren", "luar biasa", "asik", "seru",
            "amazing", "awesome", "excited", "dapat ide", "ide bagus", "mau coba",
            "pengen bikin", "mau bikin", "bisa gak", "bisa nggak", "ayo",
            "yuk", "let's", "let's go", "semangat", "siap", "gas",
        ],
        "anxious": [
            "takut", "khawatir", "was-was", "nervous", "deadline", "urgent",
            "segera", "cepat", "harus sekarang", "besok", "hari ini", "jam berapa",
            "masih ada waktu", "kira-kira", "mungkin tidak", "apa bisa",
            "worried", "concern", "asap", "right now", "immediately",
        ],
        "confused": [
            "bingung", "tidak paham", "nggak paham", "kurang mengerti",
            "maksudnya apa", "apa maksudnya", "gimana caranya", "bagaimana cara",
            "tidak ngerti", "confused", "don't understand", "what does",
            "apa bedanya", "bedanya apa", "perbedaan", "yang mana",
        ],
        "tired": [
            "capek", "lelah", "exhausted", "ngantuk", "malam-malam", "sudah lama",
            "dari tadi", "sejak tadi", "berjam-jam", "lama banget", "sudah lama",
            "tired", "exhausted", "all day", "hours",
        ],
        "grateful": [
            "terima kasih", "makasih", "thanks", "thank you", "helpful", "membantu",
            "berguna", "great help", "appreciate", "terimakasih", "syukur",
        ],
        "curious": [
            "penasaran", "ingin tahu", "seperti apa", "bagaimana jika", "what if",
            "gimana kalau", "kalau misalnya", "wonder", "curious", "interesting",
            "menarik", "hmm", "oh iya", "eh",
        ],
        "urgent": [
            "urgent", "darurat", "asap", "sekarang juga", "harus segera",
            "production down", "down", "crash", "tidak bisa akses", "client marah",
            "boss marah", "meeting sebentar lagi", "presentasi", "deadline besok",
        ],
    }

    # ── Sinyal kebutuhan tersirat ─────────────────────────────────────────────

    IMPLIED_NEED_SIGNALS = {
        "needs_validation": [
            "sudah benar", "betul nggak", "apakah ini benar", "benar bukan",
            "is this right", "is this correct", "am i right", "right?",
            "menurut kamu", "menurut anda", "pendapatmu", "what do you think",
        ],
        "needs_reassurance": [
            "bisa nggak", "kira-kira bisa", "mungkin bisa", "masih bisa",
            "apa mungkin", "is it possible", "can we", "will it work",
            "berhasil nggak", "akan berhasil",
        ],
        "wants_quick_fix": [
            "cepat", "singkat", "langsung", "quickly", "fast", "just",
            "hanya", "saja", "tinggal", "simple", "sederhana saja",
        ],
        "exploring_options": [
            "atau", "alternatif", "pilihan lain", "cara lain", "option",
            "alternative", "other way", "instead", "versus", "vs",
            "lebih baik mana", "mending mana",
        ],
        "venting": [
            "ugh", "argh", "capek banget", "sudah coba semua", "nggak ada yang berhasil",
            "nothing works", "i've tried everything", "impossible",
        ],
        "seeking_clarity": [
            "maksudnya", "artinya", "jelaskan", "explain", "apa itu",
            "what is", "define", "definisi", "pengertian",
        ],
    }

    # ── Sinyal tekanan waktu ──────────────────────────────────────────────────

    TIME_PRESSURE_SIGNALS = [
        "segera", "sekarang", "urgent", "asap", "cepat", "deadline",
        "besok", "hari ini", "jam ini", "menit ini", "right now",
        "immediately", "as soon as", "quickly", "production down",
        "client menunggu", "boss menunggu", "meeting sebentar",
    ]

    # ── Sinyal butuh pengakuan dulu ───────────────────────────────────────────

    ACKNOWLEDGMENT_SIGNALS = [
        "capek", "lelah", "frustrasi", "stressed", "susah", "sulit",
        "bingung banget", "pusing", "tidak mengerti sama sekali",
        "sudah coba berkali-kali", "dari tadi", "berjam-jam",
    ]

    # ── Mapping: emosi → tone hint ────────────────────────────────────────────

    EMOTION_TO_TONE = {
        "frustrated":  "warm_and_direct",
        "excited":     "enthusiastic",
        "anxious":     "calm_and_focused",
        "confused":    "patient_and_clear",
        "tired":       "warm_and_concise",
        "grateful":    "warm",
        "curious":     "engaging",
        "urgent":      "fast_and_focused",
        "neutral":     "balanced",
    }

    def analyze(self, message: str, history: List[Dict] = None) -> EmotionalState:
        """
        Analisis pesan (dan history singkat) untuk menghasilkan EmotionalState.
        Ini adalah langkah pertama sebelum klasifikasi intent teknis.
        """
        history = history or []
        msg_lower = message.lower()
        state = EmotionalState()
        detected_signals = []

        # ── Deteksi emosi ────────────────────────────────────────────────────
        emotion_scores: Dict[str, float] = {}
        for emotion, signals in self.EMOTION_SIGNALS.items():
            score = 0.0
            for sig in signals:
                if sig in msg_lower:
                    score += 1.0
                    detected_signals.append(sig)
            # Sinyal dari history juga dihitung (bobot lebih rendah)
            if history:
                recent_text = " ".join(
                    m.get("content", "")[:200].lower()
                    for m in history[-4:]
                    if m.get("role") == "user"
                )
                for sig in signals:
                    if sig in recent_text:
                        score += 0.4
            if score > 0:
                emotion_scores[emotion] = score

        if emotion_scores:
            dominant = max(emotion_scores, key=lambda e: emotion_scores[e])
            max_score = emotion_scores[dominant]
            state.dominant_emotion = dominant
            # Normalisasi intensitas: cap di 1.0, tiap sinyal = ~0.25
            state.intensity = min(1.0, max_score * 0.25)
        else:
            state.dominant_emotion = "neutral"
            state.intensity = 0.0

        # ── Deteksi kebutuhan tersirat ───────────────────────────────────────
        for need, signals in self.IMPLIED_NEED_SIGNALS.items():
            for sig in signals:
                if sig in msg_lower:
                    state.implied_need = need
                    break
            if state.implied_need != "none":
                break

        # ── Tekanan waktu ────────────────────────────────────────────────────
        state.has_time_pressure = any(sig in msg_lower for sig in self.TIME_PRESSURE_SIGNALS)

        # ── Butuh pengakuan dulu ─────────────────────────────────────────────
        state.needs_acknowledgment = any(sig in msg_lower for sig in self.ACKNOWLEDGMENT_SIGNALS)

        # ── Tone hint ────────────────────────────────────────────────────────
        if state.has_time_pressure:
            state.tone_hint = "fast_and_focused"
        else:
            state.tone_hint = self.EMOTION_TO_TONE.get(state.dominant_emotion, "balanced")

        state.detected_signals = list(set(detected_signals))[:10]

        log.debug(
            "HumanContextLayer",
            emotion=state.dominant_emotion,
            intensity=round(state.intensity, 2),
            implied_need=state.implied_need,
            tone_hint=state.tone_hint,
            time_pressure=state.has_time_pressure,
        )

        return state


# ══════════════════════════════════════════════════════════════════════════════
# LLM CLASSIFICATION PROMPT (v3.0 — dengan analisis emosi)
# ══════════════════════════════════════════════════════════════════════════════

PREPROCESSOR_PROMPT = """Kamu adalah AI Orchestrator Request Preprocessor dengan kemampuan memahami manusia.
Analisis permintaan user secara komprehensif: intent teknis DAN kondisi emosional/manusiawi.

== ATURAN PALING PENTING ==
Bedakan antara BERTANYA tentang sesuatu vs MEMERINTAHKAN untuk melakukan sesuatu:
- "Gimana cara buat website?" → action_type: "explain"
- "Buatkan website portfolio" → action_type: "execute"
- "Apa itu React?" → action_type: "explain"
- "Install React di project saya" → action_type: "execute"

Output HANYA valid JSON dalam format PERSIS ini:
{
    "intents": ["coding", "analysis"],
    "primary_intent": "coding",
    "action_type": "execute",
    "complexity_score": 0.7,
    "requires_multi_agent": false,
    "quality_priority": "balanced",
    "urgency": "normal",
    "requires_web_search": false,
    "entities": {
        "languages": ["python"],
        "files": [],
        "urls": [],
        "tools": ["bash"]
    },
    "success_criteria": ["Script Python yang berjalan..."],
    "reasoning": "Ini tugas coding kompleks karena...",
    "emotional_context": {
        "dominant_emotion": "neutral",
        "implied_need": "none",
        "tone_hint": "balanced",
        "needs_acknowledgment": false
    }
}

== PANDUAN emotional_context ==
dominant_emotion: neutral | frustrated | excited | anxious | confused | tired | urgent | grateful | curious
implied_need: none | needs_validation | needs_reassurance | wants_quick_fix | exploring_options | venting | seeking_clarity
tone_hint: balanced | warm_and_direct | enthusiastic | calm_and_focused | patient_and_clear | warm_and_concise | fast_and_focused | engaging
needs_acknowledgment: true jika user terlihat frustrasi, lelah, atau butuh validasi emosional sebelum dijawab

Kategori intent (boleh MULTIPLE):
- coding: menulis, debug, refactor kode
- analysis: analisis data, penalaran, matematika, logika
- research: pengumpulan info, pencarian web
- writing: pembuatan konten, dokumentasi, terjemahan
- system: manajemen VPS, perintah terminal, server admin
- file_operation: CRUD file di filesystem lokal
- creative: brainstorming, desain, ideasi
- planning: strategi, penjadwalan, manajemen proyek
- image_generation: user ingin MEMBUAT gambar/foto/ilustrasi
- audio_generation: user ingin MEMBUAT audio, TTS, atau output suara
- real_time_search: user bertanya tentang berita, harga terkini, data live
- general: obrolan biasa, salam, pertanyaan sederhana, PENJELASAN konsep

action_type:
- "execute": User memerintahkan AI untuk MELAKUKAN sesuatu
- "explain": User hanya BERTANYA, minta penjelasan, atau diskusi

Panduan kompleksitas:
- 0.0-0.2: trivial (salam, pertanyaan ya/tidak)
- 0.2-0.4: sederhana (pencarian fakta, terjemahan pendek)
- 0.4-0.6: sedang (tugas penulisan, coding tunggal)
- 0.6-0.8: kompleks (coding multi-langkah, analisis mendalam)
- 0.8-1.0: sangat kompleks (proyek penuh, multi-domain)
"""


# ══════════════════════════════════════════════════════════════════════════════
# FAST-PATH PATTERNS (dari v2.1, tidak berubah)
# ══════════════════════════════════════════════════════════════════════════════

LIGHT_PATTERNS = {
    "greetings": ["halo", "hai", "hi", "hello", "hey", "selamat pagi", "selamat siang",
                   "selamat sore", "selamat malam", "good morning", "good evening", "hei"],
    "acknowledgments": ["ok", "oke", "sip", "siap", "ya", "tidak", "terima kasih",
                         "makasih", "thanks", "thank you", "baik", "noted", "iya", "yap",
                         "nggak", "engga", "gpp", "ga papa"],
    "tests": ["test", "tes", "ping", "p", "hm", "hmm", "oh"],
}

COMPLEX_TRIGGERS = [
    "buat", "bikin", "install", "setup", "deploy", "analisa", "analyze",
    "bandingkan", "compare", "kode", "code", "sistem", "system", "vps",
    "server", "file", "tulis", "write", "riset", "research", "rencana",
    "plan", "desain", "design", "debug", "fix", "perbaiki", "optimasi",
    "optimize", "migrasi", "migrate", "refactor", "arsitektur", "architecture",
    "cek", "check", "status", "ram", "cpu", "disk", "memory", "monitor",
    "uptime", "proses", "process", "port", "service", "log", "restart",
    "berapa", "tampilkan", "lihat", "show", "info", "nginx", "docker",
    "jalankan", "execute", "run", "terminal", "perintah", "command",
    "hapus", "delete", "download", "upload", "update", "upgrade",
    "spek", "spesifikasi", "memori", "df", "free", "top", "htop",
    "hardisk", "space", "penyimpanan", "jaringan", "network", "ip",
    "cuaca", "weather", "iklim", "cari", "search",
    "gimana", "bagaimana", "kenapa", "mengapa", "apa itu", "jelaskan",
    "explain", "cara", "langkah", "step", "panduan", "guide", "tutorial",
    "contoh", "example", "perbedaan", "difference", "kelebihan", "kekurangan",
    "pros", "cons", "rekomen", "suggest", "saran", "solusi", "solution",
    "masalah", "problem", "error", "bug", "issue", "gagal", "fail",
    "tidak bisa", "tidak berjalan", "not working", "help", "bantu",
    "buatkan", "tolong", "please", "kalkulasi", "hitung", "calculate",
    "konversi", "convert", "translate", "terjemah", "rangkum", "summarize",
    "baca", "read", "edit", "ubah", "modify", "tambah", "add",
    "move", "copy", "rename", "mkdir", "chmod", "chown", "grep",
    "cat", "ls", "pwd", "find", "which", "ps", "kill", "pkill",
    "siapa", "kapan", "dimana", "berapa banyak", "berapa lama",
    "apakah", "apakah bisa", "bisa tidak", "boleh tidak",
]

IMAGE_GEN_PATTERNS = [
    "buatkan gambar", "bikin gambar", "buat foto", "buat ilustrasi", "generate image",
    "generate picture", "buat gambar", "bikin foto", "create image", "create picture",
    "gambarkan", "ilustrasikan", "buatkan foto", "bikin ilustrasi", "make image",
    "draw", "sketch", "render gambar", "lukiskan", "desainkan gambar",
]

REAL_TIME_PATTERNS = [
    "harga", "hari ini", "terkini", "terbaru", "sekarang", "berita", "live",
    "today", "latest", "current price", "stock price", "crypto", "bitcoin",
    "btc", "eth", "saham", "kurs", "nilai tukar", "update terbaru",
    "news", "breaking", "trending", "real time", "real-time",
    "cuaca", "weather", "iklim", "suhu",
]

AUDIO_GEN_PATTERNS = [
    "balas dengan suara", "kirim suara", "buat audio", "jadikan audio",
    "ubah jadi suara", "text to speech", "tts", "bacakan", "suarakan",
    "voice note", "rekam suara",
]

FAST_CODING_PATTERNS = [
    "buatkan aplikasi", "bikin aplikasi", "buat aplikasi",
    "buatkan kode", "bikin kode", "buat kode",
    "buatkan program", "bikin program", "buat program",
    "buatkan website", "bikin website", "buat website",
    "buatkan fungsi", "bikin fungsi", "buat fungsi",
    "buatkan script", "bikin script", "buat script",
    "buatkan kalkulator", "bikin kalkulator",
    "buatkan todo", "bikin todo", "buatkan game", "bikin game",
    "create app", "create website", "create function", "create script",
    "write code", "write a function", "write a script",
    "generate code", "tampilkan kode lengkap", "kode lengkap", "full code", "complete code",
    "buatkan api", "bikin api", "buat api",
    "buatkan bot", "bikin bot", "buat bot",
    "buatkan class", "bikin class",
]

FAST_SYSTEM_PATTERNS = [
    "cek ram", "cek cpu", "cek disk", "cek memory", "cek status",
    "check ram", "check cpu", "check disk", "check memory", "check status",
    "berapa ram", "berapa cpu", "berapa disk", "berapa memory",
    "tampilkan proses", "tampilkan port", "tampilkan log", "tampilkan ip",
    "show processes", "show ports", "show logs", "show ip",
    "jalankan perintah", "run command", "execute command",
    "install nginx", "install docker", "install python", "install node",
    "restart nginx", "restart apache", "restart service",
    "nginx status", "docker status", "systemctl status",
    "neofetch", "htop", "df -h", "free -h", "ps aux", "netstat",
    "lihat disk", "lihat ram", "lihat cpu", "spek server", "spek vps",
    "ping ", "traceroute", "nslookup", "dig ", "curl ", "wget ",
]

FAST_ANALYSIS_PATTERNS = [
    "jelaskan", "explain", "apa itu", "what is", "bagaimana cara", "how to",
    "perbedaan antara", "difference between",
    "rangkum", "summarize", "translate", "terjemahkan",
    "apa perbedaan",
]

OFFICE_FILE_PATTERNS = [
    "buatkan laporan", "bikin laporan", "catatan rapat", "buatkan excel",
    "bikin excel", "buatkan word", "bikin word", "tugas kantor",
    "rekap data", "edit file", "pindahkan file", "hapus file", "bikin csv",
    "buat spreadsheet", "buat dokumen",
]

LOCAL_PATH_PATTERNS = [
    "/home/", "/var/", "/etc/", "/usr/", "/tmp/", "./", "../", "c:\\", "d:\\", "e:\\",
    "cek project", "check project", "buka project", "open project",
    "cek folder", "check folder", "buka folder", "open folder",
]

AMBIGUOUS_TRIGGERS = [
    "gimana", "bagaimana", "kenapa", "mengapa", "apa itu", "apa sih",
    "jelaskan", "explain", "cara", "how to", "what is", "apakah",
    "perbedaan", "difference", "kapan", "siapa", "dimana",
    "apa perbedaan", "apa kelebihan", "apa kekurangan",
    "kenapa harus", "mengapa perlu", "bisa tidak", "boleh tidak",
    "rekomendasi", "saran", "suggest", "recommend",
]


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST PREPROCESSOR v3.0
# ══════════════════════════════════════════════════════════════════════════════

class RequestPreprocessor:
    """
    Intelligent request preprocessing pipeline dengan Human Logic Engine.
    """

    def __init__(self):
        self.human_context = HumanContextLayer()

    async def process(
        self,
        message: str,
        user_id: str = "",
        session_id: str = "",
        user_model_choice: Optional[str] = None,
        image_b64: Optional[str] = None,
        image_mime: Optional[str] = None,
        history: List[Dict] = None,
    ) -> TaskSpecification:
        start = time.time()
        spec = TaskSpecification(
            original_message=message,
            user_id=user_id,
            session_id=session_id,
        )
        history = history or []

        # ── HUMAN LOGIC ENGINE: Analisis konteks manusiawi terlebih dahulu ───
        # Ini selalu berjalan, sebelum apapun, untuk semua pesan
        emotional_state = self.human_context.analyze(message, history)
        spec.emotional_state = emotional_state
        spec.implied_need = emotional_state.implied_need
        spec.tone_hint = emotional_state.tone_hint

        # Jika ada urgensi emosional yang terdeteksi, naikkan urgency
        if emotional_state.dominant_emotion == "urgent" or emotional_state.has_time_pressure:
            spec.urgency = "immediate"

        # ── User pilih model spesifik (bukan orchestrator) ───────────────────
        if user_model_choice and "orchestrator" not in user_model_choice.lower():
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.mentioned_models = [user_model_choice]
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # ── Priority 0: Vision ───────────────────────────────────────────────
        if image_b64 and image_mime:
            spec.primary_intent = "vision"
            spec.intents = ["vision"]
            spec.is_simple = True
            spec.complexity_score = 0.3
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: vision intent", mime=image_mime[:20], msg=message[:50])
            return spec

        msg_lower = message.lower().strip()
        is_ambiguous = any(t in msg_lower for t in AMBIGUOUS_TRIGGERS)

        # ── Fast-path: Sistem ────────────────────────────────────────────────
        if not is_ambiguous and any(p in msg_lower for p in FAST_SYSTEM_PATTERNS):
            spec.primary_intent = "system"
            spec.intents = ["system"]
            spec.action_type = "execute"
            spec.complexity_score = 0.4
            spec.is_simple = True
            spec.quality_priority = "balanced"
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path system", msg=message[:60])
            return spec

        # ── Fast-path: Coding ────────────────────────────────────────────────
        if not is_ambiguous and any(p in msg_lower for p in FAST_CODING_PATTERNS):
            is_complex_app = any(p in msg_lower for p in [
                "aplikasi", "app", "website", "program", "game", "sistem",
                "kalkulator", "todo", "full code", "bot", "api"
            ])
            spec.primary_intent = "coding"
            spec.intents = ["coding"]
            spec.action_type = "execute"
            spec.complexity_score = 0.8 if is_complex_app else 0.5
            spec.is_simple = not is_complex_app
            spec.requires_multi_agent = is_complex_app
            spec.quality_priority = "balanced"
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path coding", msg=message[:60])
            return spec

        # ── Fast-path: Office/File ───────────────────────────────────────────
        if not is_ambiguous and any(p in msg_lower for p in OFFICE_FILE_PATTERNS):
            spec.primary_intent = "file_operation"
            spec.intents = ["file_operation", "writing"]
            spec.action_type = "execute"
            spec.complexity_score = 0.5
            spec.is_simple = True
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # ── Fast-path: Local Paths ───────────────────────────────────────────
        if not is_ambiguous and any(p in msg_lower for p in LOCAL_PATH_PATTERNS):
            spec.primary_intent = "file_operation"
            spec.intents = ["file_operation", "coding"]
            spec.action_type = "execute"
            spec.complexity_score = 0.6
            spec.is_simple = False
            spec.requires_multi_agent = True
            spec.quality_priority = "balanced"
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # ── Fast-path: Analisis sederhana ────────────────────────────────────
        if (any(p in msg_lower for p in FAST_ANALYSIS_PATTERNS) and len(message) < 250):
            spec.primary_intent = "general"
            spec.intents = ["general"]
            spec.action_type = "explain"
            spec.complexity_score = 0.3
            spec.is_simple = True
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # ── Trivial check ────────────────────────────────────────────────────
        if self._is_trivial(message, history):
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.complexity_score = 0.1
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # ── Cache check ──────────────────────────────────────────────────────
        has_history = len(history) > 0
        cache_key = hashlib.md5(
            f"{message.lower().strip()}|{has_history}".encode()
        ).hexdigest()
        now = time.time()
        if cache_key in _CLASSIFICATION_CACHE:
            cached_data, cached_ts = _CLASSIFICATION_CACHE[cache_key]
            if (now - cached_ts) < _CACHE_TTL_SECONDS:
                self._apply_cache(spec, cached_data)
                spec.preprocessing_time_ms = int((time.time() - start) * 1000)
                return spec
            else:
                del _CLASSIFICATION_CACHE[cache_key]

        # ── LLM Classification ───────────────────────────────────────────────
        try:
            import asyncio as _asyncio
            classification = await _asyncio.wait_for(
                self._classify_with_llm(message, history), timeout=6.0
            )
            spec.intents = classification.get("intents", ["general"])
            spec.primary_intent = classification.get("primary_intent", "general")
            spec.complexity_score = min(1.0, max(0.0, classification.get("complexity_score", 0.3)))
            spec.requires_multi_agent = classification.get("requires_multi_agent", False)
            spec.quality_priority = classification.get("quality_priority", "balanced")
            # Hanya override urgency jika LLM lebih tinggi dari deteksi emosi
            llm_urgency = classification.get("urgency", "normal")
            if llm_urgency == "immediate" or spec.urgency != "immediate":
                spec.urgency = llm_urgency
            spec.entities = classification.get("entities", {})
            spec.success_criteria = classification.get("success_criteria", [])
            spec.action_type = classification.get("action_type", "execute")
            spec.raw_classification = classification

            # Ambil emotional context dari LLM jika ada dan lebih kuat dari heuristik
            llm_emotion = classification.get("emotional_context", {})
            if llm_emotion and llm_emotion.get("dominant_emotion", "neutral") != "neutral":
                if spec.emotional_state.dominant_emotion == "neutral":
                    spec.emotional_state.dominant_emotion = llm_emotion.get("dominant_emotion", "neutral")
                    spec.emotional_state.implied_need = llm_emotion.get("implied_need", "none")
                    spec.emotional_state.tone_hint = llm_emotion.get("tone_hint", "balanced")
                    spec.tone_hint = spec.emotional_state.tone_hint
                # needs_acknowledgment: OR antara LLM dan heuristik
                spec.emotional_state.needs_acknowledgment = (
                    spec.emotional_state.needs_acknowledgment
                    or llm_emotion.get("needs_acknowledgment", False)
                )

            if classification.get("requires_web_search", False):
                if "real_time_search" not in spec.intents:
                    spec.intents.append("real_time_search")

            spec.is_simple = (
                spec.complexity_score < 0.45
                and not spec.requires_multi_agent
                and len(spec.intents) <= 1
            )

            self._save_to_cache(cache_key, spec, now)

        except Exception as e:
            log.warning("Preprocessor: LLM error, using fallback", error=str(e)[:100])
            spec = self._fallback_classify(message, spec, history)

        # ── Post-processing ──────────────────────────────────────────────────
        spec = self._enrich(spec)

        if any(p in msg_lower for p in IMAGE_GEN_PATTERNS):
            spec.primary_intent = "image_generation"
            if "image_generation" not in spec.intents:
                spec.intents.insert(0, "image_generation")
            spec.is_simple = True
        elif any(p in msg_lower for p in AUDIO_GEN_PATTERNS):
            spec.primary_intent = "audio_generation"
            if "audio_generation" not in spec.intents:
                spec.intents.insert(0, "audio_generation")
            spec.is_simple = True
        elif any(p in msg_lower for p in REAL_TIME_PATTERNS):
            if "real_time_search" not in spec.intents:
                spec.intents.append("real_time_search")
            spec.is_simple = False

        spec.preprocessing_time_ms = int((time.time() - start) * 1000)
        log.info(
            "Preprocessor complete",
            intent=spec.primary_intent,
            complexity=round(spec.complexity_score, 2),
            simple=spec.is_simple,
            multi_agent=spec.requires_multi_agent,
            emotion=spec.emotional_state.dominant_emotion,
            tone=spec.tone_hint,
            time_ms=spec.preprocessing_time_ms,
        )
        return spec

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _is_trivial(self, message: str, history: List[Dict]) -> bool:
        if history and len(history) > 0:
            return False
        msg = message.lower().strip()
        if len(msg) < 60 and not any(t in msg for t in COMPLEX_TRIGGERS):
            import string
            words = msg.translate(str.maketrans('', '', string.punctuation)).split()
            if not words:
                return True
            first_word = words[0]
            for patterns in LIGHT_PATTERNS.values():
                if first_word in patterns or msg in patterns:
                    return True
            return True
        return False

    async def _classify_with_llm(self, message: str, history: List[Dict]) -> Dict:
        fast_model = self._get_fast_model()

        context_str = ""
        if history:
            recent = history[-4:]
            context_str = "\n[KONTEKS PERCAKAPAN]\n"
            for m in recent:
                role = "User" if m["role"] == "user" else "AI"
                content = m["content"]
                if len(content) > 100:
                    content = content[:100] + "..."
                context_str += f"{role}: {content}\n"
            context_str += "\n"

        messages = [
            {"role": "system", "content": PREPROCESSOR_PROMPT},
            {"role": "user", "content": f"{context_str}Permintaan User (terbaru):\n{message}"},
        ]

        result_str = await model_manager.chat_completion(
            model=fast_model,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )

        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(result_str)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            log.warning("Preprocessor: Gagal mem-parse JSON dari LLM", result=result_str[:100])
            return {}

    def _fallback_classify(self, message: str, spec: TaskSpecification,
                            history: List[Dict] = None) -> TaskSpecification:
        msg = message.lower()

        intent_keywords = {
            "coding": ["code", "kode", "python", "javascript", "debug", "class",
                        "function", "script", "api", "sql", "program", "bug",
                        "error", "coding", "typescript", "react", "vue", "flask", "fastapi"],
            "analysis": ["analyze", "analisa", "compare", "bandingkan", "data",
                          "statistik", "insight", "logic", "math", "reason", "hitung"],
            "research": ["cari", "search", "riset", "research", "info", "temukan",
                          "find", "jelaskan", "explain"],
            "writing": ["tulis", "write", "essay", "artikel", "report", "laporan",
                         "email", "translate", "terjemah", "rangkum", "summarize"],
            "system": ["install", "sudo", "terminal", "server", "vps", "restart",
                        "deploy", "nginx", "systemctl", "docker", "linux", "bash",
                        "cek", "check", "status", "ram", "cpu", "disk", "memory",
                        "proses", "port", "service", "log", "jalankan", "run"],
            "file_operation": ["file", "baca", "read", "edit", "hapus", "delete",
                                "folder", "direktori", "directory"],
            "creative": ["desain", "design", "ide", "brainstorm", "kreatif"],
            "planning": ["rencana", "plan", "jadwal", "schedule", "strategy"],
            "image_generation": ["buatkan gambar", "bikin gambar", "generate image"],
            "audio_generation": ["balas dengan suara", "buat audio", "tts"],
            "real_time_search": ["harga", "hari ini", "terkini", "terbaru",
                                   "berita", "live", "crypto", "saham", "cuaca"],
        }

        detected = []
        for intent, keywords in intent_keywords.items():
            if any(kw in msg for kw in keywords):
                detected.append(intent)

        if not detected:
            detected = ["research"] if history and len(history) > 0 else ["general"]

        spec.intents = detected
        spec.primary_intent = detected[0]

        n_intents = len(detected)
        msg_len = len(message)

        if msg_len > 400 or n_intents > 2:
            spec.complexity_score = 0.75
            spec.requires_multi_agent = True
        elif msg_len > 150 or n_intents > 1:
            spec.complexity_score = 0.55
        elif msg_len > 80:
            spec.complexity_score = 0.4
        else:
            spec.complexity_score = 0.25

        if spec.primary_intent in ("image_generation", "audio_generation"):
            spec.is_simple = True
        else:
            spec.is_simple = (
                spec.complexity_score < 0.45
                and not spec.requires_multi_agent
                and n_intents <= 1
            )

        return spec

    def _enrich(self, spec: TaskSpecification) -> TaskSpecification:
        if spec.complexity_score > 0.7:
            spec.max_cost_preference = "expensive_ok"
        elif spec.complexity_score < 0.3:
            spec.max_cost_preference = "cheap"

        if spec.primary_intent in ("system", "file_operation"):
            spec.urgency = "immediate"

        if len(spec.intents) > 1 and spec.complexity_score >= 0.45:
            spec.is_simple = False

        # ── HUMAN LOGIC: Jika user frustrasi/lelah/butuh validasi,
        # naikkan quality priority agar respons lebih matang dan empatik
        if spec.emotional_state.dominant_emotion in ("frustrated", "tired", "anxious"):
            spec.quality_priority = "high"

        # Jika ada tekanan waktu, pastikan urgency immediate
        if spec.emotional_state.has_time_pressure and spec.urgency != "immediate":
            spec.urgency = "immediate"

        return spec

    def _apply_cache(self, spec: TaskSpecification, cached_data: Dict) -> None:
        spec.intents = cached_data.get("intents", ["general"])
        spec.primary_intent = cached_data.get("primary_intent", "general")
        spec.complexity_score = cached_data.get("complexity_score", 0.3)
        spec.requires_multi_agent = cached_data.get("requires_multi_agent", False)
        spec.quality_priority = cached_data.get("quality_priority", "balanced")
        spec.urgency = cached_data.get("urgency", "normal")
        spec.is_simple = cached_data.get("is_simple", True)
        # Catatan: emotional_state TIDAK di-cache karena emosi bisa berubah per pesan

    def _save_to_cache(self, key: str, spec: TaskSpecification, ts: float) -> None:
        if len(_CLASSIFICATION_CACHE) >= _CACHE_MAX_SIZE:
            oldest = min(_CLASSIFICATION_CACHE, key=lambda k: _CLASSIFICATION_CACHE[k][1])
            del _CLASSIFICATION_CACHE[oldest]
        _CLASSIFICATION_CACHE[key] = ({
            "intents":              spec.intents,
            "primary_intent":       spec.primary_intent,
            "complexity_score":     spec.complexity_score,
            "requires_multi_agent": spec.requires_multi_agent,
            "quality_priority":     spec.quality_priority,
            "urgency":              spec.urgency,
            "is_simple":            spec.is_simple,
        }, ts)

    def _get_fast_model(self) -> str:
        try:
            from agents.agent_registry import agent_registry as _ar
            model = _ar.resolve_model_for_agent("general")
            if model and model in model_manager.available_models:
                return model
        except Exception:
            pass
        return model_manager.get_default_model()


request_preprocessor = RequestPreprocessor()

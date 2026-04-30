"""
Super Agent Orchestrator — Request Preprocessor (v2.1 — Performance Optimized)
=================================================================================
Perbaikan dari v1:
  1. Threshold trivial diturunkan: 120 → 60 chars (lebih konservatif, hanya skip yg benar2 trivial)
  2. COMPLEX_TRIGGERS diperluas dengan lebih banyak kata bahasa Indonesia
  3. Cache mempertimbangkan history presence (bukan hanya teks pesan)
  4. FAST_SYSTEM_PATTERNS baru: bypass LLM untuk perintah server yang jelas
  5. Timeout LLM classifier dikurangi 6s → 4s (lebih responsif)
  6. Fallback classifier diperbaiki untuk intents ganda
  7. _enrich() lebih cerdas: set is_simple=False untuk task multi-intent
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()

_CLASSIFICATION_CACHE: Dict[str, tuple] = {}
_CACHE_TTL_SECONDS = 1800    # 30 menit (diturunkan dari 1 jam agar lebih fresh)
_CACHE_MAX_SIZE = 512


@dataclass
class TaskSpecification:
    """Structured output from the request preprocessor."""
    original_message: str = ""
    intents: List[str] = field(default_factory=list)
    primary_intent: str = "general"
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

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


PREPROCESSOR_PROMPT = """Kamu adalah AI Orchestrator Request Preprocessor.
Analisis permintaan user secara komprehensif dan ekstrak informasi terstruktur.

Output HANYA valid JSON dalam format PERSIS ini:
{
    "intents": ["coding", "analysis"],
    "primary_intent": "coding",
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
    "success_criteria": ["Script Python yang berjalan...", "Output diformat sebagai..."],
    "reasoning": "Ini tugas coding kompleks karena..."
}

Kategori intent (boleh MULTIPLE):
- coding: menulis, debug, refactor kode
- analysis: analisis data, penalaran, matematika, logika
- research: pengumpulan info, pencarian web, perbandingan
- writing: pembuatan konten, dokumentasi, terjemahan
- system: manajemen VPS, perintah terminal, server admin
- file_operation: CRUD file di filesystem lokal
- creative: brainstorming, desain, ideasi
- planning: strategi, penjadwalan, manajemen proyek
- image_generation: user ingin MEMBUAT atau MENGHASILKAN gambar/foto/ilustrasi
- audio_generation: user ingin MEMBUAT audio, TTS, atau output suara
- real_time_search: user bertanya tentang berita, harga terkini, data live, "hari ini", "terbaru"
- general: obrolan biasa, salam, pertanyaan sederhana

Panduan kompleksitas:
- 0.0-0.2: trivial (salam, pertanyaan ya/tidak)
- 0.2-0.4: sederhana (pencarian fakta, terjemahan pendek)
- 0.4-0.6: sedang (tugas penulisan, coding tunggal)
- 0.6-0.8: kompleks (coding multi-langkah, analisis mendalam)
- 0.8-1.0: sangat kompleks (proyek penuh, multi-domain)

requires_multi_agent = true HANYA JIKA:
- Kompleksitas > 0.6 DAN ada beberapa intent berbeda
- Tugas eksplisit membutuhkan perspektif berbeda
- Tugas punya sub-deliverable yang benar-benar independen

requires_web_search = true JIKA:
- User bertanya tentang kejadian terkini, berita terbaru, harga live, atau data real-time
- Pertanyaan mengandung: "hari ini", "terkini", "terbaru", "sekarang", "harga", "berita", "today", "latest", "current"
"""


# ── Fast-path patterns ────────────────────────────────────────────────────────

LIGHT_PATTERNS = {
    "greetings": ["halo", "hai", "hi", "hello", "hey", "selamat pagi", "selamat siang",
                   "selamat sore", "selamat malam", "good morning", "good evening", "hei"],
    "acknowledgments": ["ok", "oke", "sip", "siap", "ya", "tidak", "terima kasih",
                         "makasih", "thanks", "thank you", "baik", "noted", "iya", "yap",
                         "nggak", "engga", "gpp", "ga papa"],
    "tests": ["test", "tes", "ping", "p", "hm", "hmm", "oh"],
}

# DIPERLUAS: trigger yang menandakan pesan bukan trivial
COMPLEX_TRIGGERS = [
    # Aksi utama
    "buat", "bikin", "install", "setup", "deploy", "analisa", "analyze",
    "bandingkan", "compare", "kode", "code", "sistem", "system", "vps",
    "server", "file", "tulis", "write", "riset", "research", "rencana",
    "plan", "desain", "design", "debug", "fix", "perbaiki", "optimasi",
    "optimize", "migrasi", "migrate", "refactor", "arsitektur", "architecture",
    # Monitoring & system
    "cek", "check", "status", "ram", "cpu", "disk", "memory", "monitor",
    "uptime", "proses", "process", "port", "service", "log", "restart",
    "berapa", "tampilkan", "lihat", "show", "info", "nginx", "docker",
    "jalankan", "execute", "run", "terminal", "perintah", "command",
    "hapus", "delete", "download", "upload", "update", "upgrade",
    "spek", "spesifikasi", "memori", "df", "free", "top", "htop",
    "hardisk", "space", "penyimpanan", "jaringan", "network", "ip",
    "cuaca", "weather", "iklim", "cari", "search",
    # Tambahan yang sebelumnya hilang
    "gimana", "bagaimana", "kenapa", "mengapa", "apa itu", "jelaskan",
    "explain", "cara", "langkah", "step", "panduan", "guide", "tutorial",
    "contoh", "example", "perbedaan", "difference", "kelebihan", "kekurangan",
    "pros", "cons", "rekomen", "suggest", "saran", "solusi", "solution",
    "masalah", "problem", "error", "bug", "issue", "gagal", "fail",
    "tidak bisa", "tidak berjalan", "not working", "help", "bantu",
    "buatkan", "tolong", "please", "kalkulasi", "hitung", "calculate",
    "konversi", "convert", "translate", "terjemah", "rangkum", "summarize",
    "baca", "read", "edit", "ubah", "modify", "tambah", "add", "hapus",
    "move", "copy", "rename", "mkdir", "chmod", "chown", "grep", "awk",
    "sed", "cat", "ls", "pwd", "find", "which", "ps", "kill", "pkill",
    # Kata tanya yang membutuhkan penjelasan
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

# Fast-path coding: skip LLM classifier
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
    "generate code",
    "tampilkan kode lengkap", "kode lengkap", "full code", "complete code",
    "buatkan api", "bikin api", "buat api",
    "buatkan bot", "bikin bot", "buat bot",
    "buatkan class", "bikin class",
]

# NEW: Fast-path untuk perintah sistem yang jelas
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

# Fast-path untuk analisis sederhana
FAST_ANALYSIS_PATTERNS = [
    "jelaskan", "explain", "apa itu", "what is", "bagaimana cara", "how to",
    "perbedaan antara", "difference between",
    "rangkum", "summarize", "translate", "terjemahkan",
    "apa perbedaan",
]

# Fast-path untuk tugas kantor & file
OFFICE_FILE_PATTERNS = [
    "buatkan laporan", "bikin laporan", "catatan rapat", "buatkan excel",
    "bikin excel", "buatkan word", "bikin word", "tugas kantor",
    "rekap data", "edit file", "pindahkan file", "hapus file", "bikin csv",
    "buat spreadsheet", "buat dokumen",
]


class RequestPreprocessor:
    """
    Intelligent request preprocessing pipeline.
    """

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

        # Jika user pilih model spesifik (bukan orchestrator), langsung treat sebagai simple
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
            log.info("Preprocessor: vision intent (image present)",
                     mime=image_mime[:20], msg=message[:50])
            return spec

        msg_lower = message.lower().strip()

        # ── Fast-path: Sistem ────────────────────────────────────────────────
        if any(p in msg_lower for p in FAST_SYSTEM_PATTERNS):
            spec.primary_intent = "system"
            spec.intents = ["system"]
            spec.complexity_score = 0.4
            spec.is_simple = True
            spec.quality_priority = "balanced"
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path system", msg=message[:60])
            return spec

        # ── Fast-path: Coding ────────────────────────────────────────────────
        if any(p in msg_lower for p in FAST_CODING_PATTERNS):
            is_complex_app = any(p in msg_lower for p in [
                "aplikasi", "app", "website", "program", "game", "sistem",
                "kalkulator", "todo", "full code", "bot", "api"
            ])
            spec.primary_intent = "coding"
            spec.intents = ["coding"]
            spec.complexity_score = 0.8 if is_complex_app else 0.5
            spec.is_simple = not is_complex_app
            spec.requires_multi_agent = is_complex_app
            spec.quality_priority = "balanced"
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path coding", msg=message[:60], is_simple=spec.is_simple)
            return spec

        # ── Fast-path: Office/File ───────────────────────────────────────────
        if any(p in msg_lower for p in OFFICE_FILE_PATTERNS):
            spec.primary_intent = "file_operation"
            spec.intents = ["file_operation", "writing"]
            spec.complexity_score = 0.5
            spec.is_simple = True
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path office/file", msg=message[:60])
            return spec

        # ── Fast-path: Analisis sederhana ────────────────────────────────────
        if (any(p in msg_lower for p in FAST_ANALYSIS_PATTERNS) and len(message) < 250):
            spec.primary_intent = "analysis"
            spec.intents = ["analysis"]
            spec.complexity_score = 0.3
            spec.is_simple = True
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path analysis", msg=message[:60])
            return spec

        # ── Trivial check ────────────────────────────────────────────────────
        # PERBAIKAN: hanya skip jika BENAR-BENAR trivial (tidak ada history)
        if self._is_trivial(message, history):
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.complexity_score = 0.1
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.debug("Preprocessor: trivial message", msg=message[:50])
            return spec

        # ── Cache check ──────────────────────────────────────────────────────
        # PERBAIKAN: key cache menyertakan bool "ada history" agar pesan sama
        # dengan konteks yang berbeda tidak ter-cache salah.
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
                log.debug("Preprocessor: cache hit", key=cache_key[:8], msg=message[:40])
                return spec
            else:
                del _CLASSIFICATION_CACHE[cache_key]

        # ── LLM Classification ───────────────────────────────────────────────
        try:
            import asyncio as _asyncio
            # PERBAIKAN: timeout diturunkan 6s → 4s untuk lebih responsif
            classification = await _asyncio.wait_for(
                self._classify_with_llm(message, history), timeout=4.0
            )
            spec.intents = classification.get("intents", ["general"])
            spec.primary_intent = classification.get("primary_intent", "general")
            spec.complexity_score = min(1.0, max(0.0, classification.get("complexity_score", 0.3)))
            spec.requires_multi_agent = classification.get("requires_multi_agent", False)
            spec.quality_priority = classification.get("quality_priority", "balanced")
            spec.urgency = classification.get("urgency", "normal")
            spec.entities = classification.get("entities", {})
            spec.success_criteria = classification.get("success_criteria", [])
            spec.raw_classification = classification

            if classification.get("requires_web_search", False):
                if "real_time_search" not in spec.intents:
                    spec.intents.append("real_time_search")

            # PERBAIKAN: threshold is_simple lebih ketat: 0.55 → 0.45
            spec.is_simple = (
                spec.complexity_score < 0.45
                and not spec.requires_multi_agent
                and len(spec.intents) <= 1
            )

            # Simpan ke cache
            self._save_to_cache(cache_key, spec, now)

        except _asyncio.TimeoutError:
            log.warning("Preprocessor: LLM timeout (>4s), using fallback")
            spec = self._fallback_classify(message, spec, history)
        except Exception as e:
            log.warning("Preprocessor: LLM error, using fallback", error=str(e)[:100])
            spec = self._fallback_classify(message, spec, history)

        # ── Post-processing ──────────────────────────────────────────────────
        spec = self._enrich(spec)

        # Override dengan heuristic patterns
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
            spec.is_simple = False  # perlu web search + analisis

        spec.preprocessing_time_ms = int((time.time() - start) * 1000)
        log.info("Preprocessor complete",
                 intent=spec.primary_intent,
                 complexity=round(spec.complexity_score, 2),
                 simple=spec.is_simple,
                 multi_agent=spec.requires_multi_agent,
                 time_ms=spec.preprocessing_time_ms)
        return spec

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _is_trivial(self, message: str, history: List[Dict]) -> bool:
        """Cek apakah pesan benar-benar trivial yang tidak perlu analisis."""
        # Ada history → tidak pernah trivial (konteks penting)
        if history and len(history) > 0:
            return False

        msg = message.lower().strip()

        # PERBAIKAN: threshold diturunkan 120 → 60 chars
        # Pesan pendek tanpa trigger kompleks = trivial
        if len(msg) < 60 and not any(t in msg for t in COMPLEX_TRIGGERS):
            import string
            words = msg.translate(str.maketrans('', '', string.punctuation)).split()
            if not words:
                return True
            first_word = words[0]
            for patterns in LIGHT_PATTERNS.values():
                if first_word in patterns or msg in patterns:
                    return True
            # Pesan < 60 chars tanpa trigger kompleks = trivial
            return True

        return False

    async def _classify_with_llm(self, message: str, history: List[Dict]) -> Dict:
        """Gunakan LLM cepat untuk mengklasifikasikan request."""
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
            max_tokens=400,
        )

        # Ekstrak JSON dari respons
        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()

        # Coba parse, jika gagal kembalikan dict kosong
        try:
            return json.loads(result_str)
        except json.JSONDecodeError:
            # Coba ekstrak JSON dari teks yang tidak bersih
            import re
            json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise

    def _fallback_classify(self, message: str, spec: TaskSpecification,
                            history: List[Dict] = None) -> TaskSpecification:
        """Keyword-based fallback jika LLM classification gagal."""
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
            "creative": ["desain", "design", "ide", "brainstorm", "kreatif", "inovatif"],
            "planning": ["rencana", "plan", "jadwal", "schedule", "strategy", "roadmap"],
            "image_generation": ["buatkan gambar", "bikin gambar", "buat foto",
                                   "generate image", "gambarkan", "draw"],
            "audio_generation": ["balas dengan suara", "buat audio", "tts",
                                   "bacakan", "suarakan", "voice note"],
            "real_time_search": ["harga", "hari ini", "terkini", "terbaru",
                                   "berita", "live", "today", "latest", "crypto",
                                   "saham", "cuaca", "weather"],
        }

        detected = []
        for intent, keywords in intent_keywords.items():
            if any(kw in msg for kw in keywords):
                detected.append(intent)

        # Jika ada history dan belum ada intent, cenderung ke research/general
        if not detected:
            if history and len(history) > 0:
                detected = ["research"]
            else:
                detected = ["general"]

        spec.intents = detected
        spec.primary_intent = detected[0]

        # Estimasi kompleksitas
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

        # Pengecualian khusus
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
        """Post-processing: tambahkan info turunan."""
        # Set cost preference
        if spec.complexity_score > 0.7:
            spec.max_cost_preference = "expensive_ok"
        elif spec.complexity_score < 0.3:
            spec.max_cost_preference = "cheap"

        # System/file operation → urgent (user sedang menunggu)
        if spec.primary_intent in ("system", "file_operation"):
            spec.urgency = "immediate"

        # PERBAIKAN: task multi-intent tidak boleh is_simple
        if len(spec.intents) > 1 and spec.complexity_score >= 0.45:
            spec.is_simple = False

        return spec

    def _apply_cache(self, spec: TaskSpecification, cached_data: Dict) -> None:
        """Terapkan data cache ke spec."""
        spec.intents = cached_data.get("intents", ["general"])
        spec.primary_intent = cached_data.get("primary_intent", "general")
        spec.complexity_score = cached_data.get("complexity_score", 0.3)
        spec.requires_multi_agent = cached_data.get("requires_multi_agent", False)
        spec.quality_priority = cached_data.get("quality_priority", "balanced")
        spec.urgency = cached_data.get("urgency", "normal")
        spec.is_simple = cached_data.get("is_simple", True)

    def _save_to_cache(self, key: str, spec: TaskSpecification, ts: float) -> None:
        """Simpan hasil klasifikasi ke cache."""
        if len(_CLASSIFICATION_CACHE) >= _CACHE_MAX_SIZE:
            oldest = min(_CLASSIFICATION_CACHE, key=lambda k: _CLASSIFICATION_CACHE[k][1])
            del _CLASSIFICATION_CACHE[oldest]
        _CLASSIFICATION_CACHE[key] = ({
            "intents":            spec.intents,
            "primary_intent":     spec.primary_intent,
            "complexity_score":   spec.complexity_score,
            "requires_multi_agent": spec.requires_multi_agent,
            "quality_priority":   spec.quality_priority,
            "urgency":            spec.urgency,
            "is_simple":          spec.is_simple,
        }, ts)

    def _get_fast_model(self) -> str:
        """Pilih model tercepat untuk klasifikasi."""
        # Prioritas: model speed/flash untuk klasifikasi
        priorities = [
            "sumopod/gemini-2.5-flash-lite",
            "sumopod/claude-haiku-4-5",
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ]
        available = model_manager.available_models
        for p in priorities:
            if p in available:
                return p
        return model_manager.get_default_model()


request_preprocessor = RequestPreprocessor()

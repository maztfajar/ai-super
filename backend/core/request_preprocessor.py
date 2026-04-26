"""
Super Agent Orchestrator — Request Preprocessor & Parser
Replaces the simple keyword-matching smart_router with intelligent preprocessing.
Handles: intent classification, constraint extraction, complexity assessment,
entity recognition, and success criteria generation.
"""
import json
import time
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()

# In-memory cache untuk hasil klasifikasi LLM — menghindari panggil AI untuk pesan berulang
# Format: { hash_pesan: (TaskSpecification, timestamp) }
_CLASSIFICATION_CACHE: Dict[str, tuple] = {}
_CACHE_TTL_SECONDS = 3600   # 1 jam
_CACHE_MAX_SIZE = 512       # Maks 512 entri


@dataclass
class TaskSpecification:
    """Structured output from the request preprocessor."""
    # Core
    original_message: str = ""
    intents: List[str] = field(default_factory=list)         # multi-label: coding, analysis, writing, research, etc
    primary_intent: str = "general"                          # main intent
    complexity_score: float = 0.0                            # 0.0-1.0 (0=trivial, 1=extremely complex)
    is_simple: bool = True                                   # True = skip orchestration
    requires_multi_agent: bool = False                       # True = needs decomposition

    # Constraints
    quality_priority: str = "balanced"                       # speed | balanced | quality
    max_cost_preference: str = "normal"                      # cheap | normal | expensive_ok
    urgency: str = "normal"                                  # immediate | normal | can_wait

    # Entities extracted
    entities: Dict[str, List[str]] = field(default_factory=dict)  # files, urls, models, etc
    mentioned_models: List[str] = field(default_factory=list)

    # Success Criteria
    success_criteria: List[str] = field(default_factory=list)

    # Metadata
    user_id: str = ""
    session_id: str = ""
    preprocessing_time_ms: int = 0
    raw_classification: Optional[Dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


PREPROCESSOR_PROMPT = """You are the AI Orchestrator Request Preprocessor.
Analyze the user's request comprehensively and extract structured information.

You MUST output ONLY valid JSON in exactly this format:
{
    "intents": ["coding", "analysis"],
    "primary_intent": "coding",
    "complexity_score": 0.7,
    "requires_multi_agent": true,
    "quality_priority": "balanced",
    "urgency": "normal",
    "requires_web_search": false,
    "entities": {
        "languages": ["python"],
        "files": [],
        "urls": [],
        "tools": ["bash"]
    },
    "success_criteria": ["Working Python script that...", "Output formatted as..."],
    "reasoning": "This is a complex coding task because..."
}

Intent categories (can be MULTIPLE):
- coding: writing, debugging, refactoring code
- analysis: data analysis, reasoning, math, logic
- research: information gathering, web search, comparison
- writing: content creation, documentation, translation
- system: VPS management, terminal commands, server admin
- file_operation: file CRUD on local filesystem
- creative: brainstorming, design, ideation
- planning: strategy, scheduling, project management
- image_generation: user wants to CREATE or GENERATE an image/photo/picture/illustration
- audio_generation: user wants to CREATE audio, TTS, or voice output
- real_time_search: user asks about news, current prices, live data, "hari ini", "terkini", "terbaru"
- general: casual chat, greetings, simple questions

Complexity scoring guide:
- 0.0-0.2: trivial (greetings, yes/no questions)
- 0.2-0.4: simple (factual lookups, short translations)
- 0.4-0.6: moderate (writing tasks, single coding tasks)
- 0.6-0.8: complex (multi-step coding, deep analysis)
- 0.8-1.0: very complex (full project, multi-domain work)

requires_multi_agent = true ONLY IF:
- Complexity > 0.6 AND multiple intents
- Task explicitly requires different perspectives
- Task has multiple independent sub-deliverables

requires_web_search = true IF:
- User asks about current events, latest news, live prices, or real-time data
- Question contains: "hari ini", "terkini", "terbaru", "sekarang", "harga", "berita", "today", "latest", "current"

quality_priority options:
- speed: user wants fast response (use cheaper/faster models)
- balanced: normal balance (default)
- quality: user wants best possible answer (use premium models, ensemble)

urgency options:
- immediate: user is waiting, time-sensitive
- normal: standard request
- can_wait: batch processing, background task
"""


# Fast heuristic patterns to skip LLM classification entirely
LIGHT_PATTERNS = {
    "greetings": ["halo", "hai", "hi", "hello", "hey", "selamat pagi", "selamat siang",
                   "selamat sore", "selamat malam", "good morning", "good evening"],
    "acknowledgments": ["ok", "oke", "sip", "siap", "ya", "tidak", "terima kasih",
                         "makasih", "thanks", "thank you", "baik", "noted"],
    "tests": ["test", "tes", "ping", "p"],
}

COMPLEX_TRIGGERS = [
    "buat", "bikin", "install", "setup", "deploy", "analisa", "analyze",
    "bandingkan", "compare", "kode", "code", "sistem", "system", "vps",
    "server", "file", "tulis", "write", "riset", "research", "rencana",
    "plan", "desain", "design", "debug", "fix", "perbaiki", "optimasi",
    "optimize", "migrasi", "migrate", "refactor", "arsitektur", "architecture",
    # System monitoring & server queries
    "cek", "check", "status", "ram", "cpu", "disk", "memory", "monitor",
    "uptime", "proses", "process", "port", "service", "log", "restart",
    "berapa", "tampilkan", "lihat", "show", "info", "nginx", "docker",
    "jalankan", "execute", "run", "terminal", "perintah", "command",
    "hapus", "delete", "download", "upload", "update", "upgrade",
    "spek", "spesifikasi", "memori", "df", "free", "top", "htop", "neofetch",
    "hardisk", "space", "penyimpanan", "jaringan", "network", "ping", "ip",
    "cuaca", "weather", "iklim", "cari", "search",
]

# Heuristic: detect image generation
IMAGE_GEN_PATTERNS = [
    "buatkan gambar", "bikin gambar", "buat foto", "buat ilustrasi", "generate image",
    "generate picture", "buat gambar", "bikin foto", "create image", "create picture",
    "gambarkan", "ilustrasikan", "buatkan foto", "bikin ilustrasi", "make image",
    "draw", "sketch", "render gambar",
]

# Heuristic: detect real-time search needs
REAL_TIME_PATTERNS = [
    "harga", "hari ini", "terkini", "terbaru", "sekarang", "berita", "live",
    "today", "latest", "current price", "stock price", "crypto", "bitcoin",
    "btc", "eth", "saham", "kurs", "nilai tukar", "update terbaru",
    "news", "breaking", "trending", "real time", "real-time",
    "cuaca", "weather", "iklim",
]

# Heuristic: detect audio/TTS generation requests
AUDIO_GEN_PATTERNS = [
    "balas dengan suara", "kirim suara", "buat audio", "jadikan audio",
    "ubah jadi suara", "text to speech", "tts", "bacakan", "suarakan",
    "voice note", "rekam suara",
]

# Fast-path: skip LLM classifier untuk permintaan coding/app yang jelas
# Langsung assign intent + is_simple=True agar time-to-first-token cepat
FAST_CODING_PATTERNS = [
    "buatkan aplikasi", "bikin aplikasi", "buat aplikasi",
    "buatkan kode", "bikin kode", "buat kode",
    "buatkan program", "bikin program", "buat program",
    "buatkan website", "bikin website", "buat website",
    "buatkan fungsi", "bikin fungsi", "buat fungsi",
    "buatkan script", "bikin script",
    "buatkan kalkulator", "bikin kalkulator",
    "buatkan todo", "bikin todo", "buatkan game", "bikin game",
    "create app", "create website", "create function", "create script",
    "write code", "write a function", "write a script",
    "generate code", "generate a",
    "tampilkan kode lengkap", "kode lengkap", "full code", "complete code",
]

# Fast-path untuk tugas kantor (Office) & operasi file
OFFICE_FILE_PATTERNS = [
    "buatkan laporan", "bikin laporan", "catatan rapat", "buatkan excel", 
    "bikin excel", "buatkan word", "bikin word", "tugas kantor", 
    "rekap data", "edit file", "pindahkan file", "hapus file", "bikin csv"
]

# Fast-path: skip LLM classifier untuk permintaan analisis sederhana
FAST_ANALYSIS_PATTERNS = [
    "jelaskan", "explain", "apa itu", "what is", "bagaimana cara", "how to",
    "perbedaan antara", "difference between", "compare", "bandingkan",
    "rangkum", "summarize", "translate", "terjemahkan",
]


class RequestPreprocessor:
    """
    Intelligent request preprocessing pipeline.
    Replaces the keyword-based smart_router.
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
        """
        Full preprocessing pipeline:
        1. Fast heuristic check (skip LLM for trivial messages)
        2. Cache check (skip LLM for repeated messages)
        3. LLM-based deep analysis
        4. Post-processing & enrichment
        """
        start = time.time()
        spec = TaskSpecification(
            original_message=message,
            user_id=user_id,
            session_id=session_id,
        )

        # If user explicitly selected a model (not orchestrator), treat as simple
        if user_model_choice and "orchestrator" not in user_model_choice.lower():
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.mentioned_models = [user_model_choice]
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # Step 0: Priority-check for special intents (before any LLM classification)
        # VISION has highest priority — if image present, always analyze as vision
        if image_b64 and image_mime:
            spec.primary_intent = "vision"
            spec.intents = ["vision"]
            spec.is_simple = True
            spec.complexity_score = 0.3
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: vision intent detected (image present)",
                    image_mime=image_mime[:20], msg=message[:50])
            return spec

        # Step 0b: Fast-path untuk coding/writing — skip LLM classifier sepenuhnya
        msg_lower_fast = message.lower()
        if any(p in msg_lower_fast for p in FAST_CODING_PATTERNS):
            spec.primary_intent = "coding"
            spec.intents = ["coding"]
            
            # Jika user minta bikin full app/website, paksa dekomposisi agar tidak timeout/hit token limit
            is_complex_app = any(p in msg_lower_fast for p in ["aplikasi", "app", "website", "program", "game", "sistem", "kalkulator", "todo", "full code"])
            
            spec.complexity_score = 0.8 if is_complex_app else 0.5
            spec.is_simple = not is_complex_app
            spec.requires_multi_agent = is_complex_app
            spec.quality_priority = "balanced"
            
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path coding detected", msg=message[:60], is_simple=spec.is_simple)
            return spec

        # Step 0c: Fast-path untuk tugas kantor & file operations
        if any(p in msg_lower_fast for p in OFFICE_FILE_PATTERNS):
            spec.primary_intent = "file_operation"
            spec.intents = ["file_operation", "writing"]
            spec.complexity_score = 0.5
            spec.is_simple = True  # File operations usually don't need complex multi-agent breakdown
            spec.quality_priority = "balanced"
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path office/file detected", msg=message[:60])
            return spec

        if any(p in msg_lower_fast for p in FAST_ANALYSIS_PATTERNS) and len(message) < 300:
            spec.primary_intent = "analysis"
            spec.intents = ["analysis"]
            spec.complexity_score = 0.3
            spec.is_simple = True
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.info("Preprocessor: fast-path analysis detected", msg=message[:60])
            return spec

        # Step 1: Fast heuristic check
        # If there is history, NEVER treat a message as trivial. Context is key!
        if self._is_trivial(message, history):
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.complexity_score = 0.1
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.debug("Preprocessor: trivial message detected", msg=message[:50])
            return spec

        # Step 1b: In-memory cache check — skip LLM untuk pesan yang identik/berulang
        cache_key = hashlib.md5(message.lower().strip().encode()).hexdigest()
        now = time.time()
        if cache_key in _CLASSIFICATION_CACHE:
            cached_data, cached_ts = _CLASSIFICATION_CACHE[cache_key]
            if (now - cached_ts) < _CACHE_TTL_SECONDS:
                # Cache hit — rebuild spec dari data tersimpan
                spec.intents = cached_data.get("intents", ["general"])
                spec.primary_intent = cached_data.get("primary_intent", "general")
                spec.complexity_score = cached_data.get("complexity_score", 0.3)
                spec.requires_multi_agent = cached_data.get("requires_multi_agent", False)
                spec.quality_priority = cached_data.get("quality_priority", "balanced")
                spec.urgency = cached_data.get("urgency", "normal")
                spec.is_simple = cached_data.get("is_simple", True)
                spec.preprocessing_time_ms = int((time.time() - start) * 1000)
                log.debug("Preprocessor: cache hit", key=cache_key[:8], msg=message[:40])
                return spec
            else:
                # Stale — hapus dari cache
                del _CLASSIFICATION_CACHE[cache_key]

        # Step 2: LLM-based classification — with 6s timeout to prevent hangs
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
            spec.urgency = classification.get("urgency", "normal")
            spec.entities = classification.get("entities", {})
            spec.success_criteria = classification.get("success_criteria", [])
            spec.raw_classification = classification

            # Override: if LLM detected real_time_search — inject it into intents
            if classification.get("requires_web_search", False):
                if "real_time_search" not in spec.intents:
                    spec.intents.append("real_time_search")

            # Determine if simple (skip orchestration overhead)
            spec.is_simple = spec.complexity_score < 0.55 and not spec.requires_multi_agent

            # Simpan ke cache — jaga agar cache tidak kebesaran
            if len(_CLASSIFICATION_CACHE) >= _CACHE_MAX_SIZE:
                # Hapus entri tertua
                oldest_key = min(_CLASSIFICATION_CACHE, key=lambda k: _CLASSIFICATION_CACHE[k][1])
                del _CLASSIFICATION_CACHE[oldest_key]
            _CLASSIFICATION_CACHE[cache_key] = ({
                "intents": spec.intents,
                "primary_intent": spec.primary_intent,
                "complexity_score": spec.complexity_score,
                "requires_multi_agent": spec.requires_multi_agent,
                "quality_priority": spec.quality_priority,
                "urgency": spec.urgency,
                "is_simple": spec.is_simple,
            }, now)

        except _asyncio.TimeoutError:
            log.warning("Preprocessor LLM classification timed out (>6s), using fallback")
            spec = self._fallback_classify(message, spec)
        except Exception as e:
            log.warning("Preprocessor LLM classification failed, using fallback", error=str(e)[:100])
            spec = self._fallback_classify(message, spec)

        # Step 3: Post-processing
        spec = self._enrich(spec)

        # Step 4: Fast heuristic check for special intents (override LLM if patterns found)
        msg_lower = message.lower()
        if any(p in msg_lower for p in IMAGE_GEN_PATTERNS):
            spec.primary_intent = "image_generation"
            if "image_generation" not in spec.intents:
                spec.intents.insert(0, "image_generation")
            spec.is_simple = True  # handled separately by orchestrator

        elif any(p in msg_lower for p in AUDIO_GEN_PATTERNS):
            spec.primary_intent = "audio_generation"
            if "audio_generation" not in spec.intents:
                spec.intents.insert(0, "audio_generation")
            spec.is_simple = True

        elif any(p in msg_lower for p in REAL_TIME_PATTERNS):
            if "real_time_search" not in spec.intents:
                spec.intents.append("real_time_search")
            # Not simple — needs search + analysis
            spec.is_simple = False

        spec.preprocessing_time_ms = int((time.time() - start) * 1000)
        log.info("Preprocessor complete",
                 intent=spec.primary_intent,
                 complexity=spec.complexity_score,
                 simple=spec.is_simple,
                 multi_agent=spec.requires_multi_agent,
                 time_ms=spec.preprocessing_time_ms)

        return spec

    def _is_trivial(self, message: str, history: List[Dict] = None) -> bool:
        """Fast check: is this a trivial/light message that needs no analysis?"""
        if history and len(history) > 0:
            return False  # If there is a conversation context, it is not trivial.

        msg = message.lower().strip()

        # Very short messages
        if len(msg) < 15:
            # Check against light patterns
            import string
            words = msg.translate(str.maketrans('', '', string.punctuation)).split()
            if not words:
                return True
            first_word = words[0]
            for category, patterns in LIGHT_PATTERNS.items():
                if first_word in patterns or msg in patterns:
                    return True

        # Short message with no complex triggers — raised 50→120 to avoid unnecessary LLM calls
        if len(msg) < 120 and not any(t in msg for t in COMPLEX_TRIGGERS):
            return True

        return False

    async def _classify_with_llm(self, message: str, history: List[Dict] = None) -> Dict:
        """Use a fast LLM to classify the request, injecting context if available."""
        fast_model = self._get_fast_model()
        
        context_str = ""
        if history:
            # Append last 4 messages to give context for ambiguous short messages
            recent_hist = history[-4:]
            context_str = "\n[CONVERSATION CONTEXT]\n"
            for m in recent_hist:
                role = "User" if m["role"] == "user" else "AI"
                content = m["content"]
                if len(content) > 100:
                    content = content[:100] + "..."
                context_str += f"{role}: {content}\n"
            context_str += "\n"

        messages = [
            {"role": "system", "content": PREPROCESSOR_PROMPT},
            {"role": "user", "content": f"{context_str}User Request (Newest):\n{message}"},
        ]

        result_str = await model_manager.chat_completion(
            model=fast_model,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )

        # Extract JSON
        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()

        return json.loads(result_str)

    def _fallback_classify(self, message: str, spec: TaskSpecification) -> TaskSpecification:
        """Keyword-based fallback if LLM classification fails."""
        msg = message.lower()

        # Detect intents by keywords
        intent_keywords = {
            "coding": ["code", "kode", "python", "javascript", "debug", "class", "function",
                        "script", "api", "sql", "program", "bug", "error", "coding"],
            "analysis": ["analyze", "analisa", "compare", "bandingkan", "data", "statistik",
                          "insight", "logic", "math", "reason"],
            "research": ["cari", "search", "riset", "research", "info", "temukan", "find"],
            "writing": ["tulis", "write", "essay", "artikel", "report", "laporan", "email",
                         "translate", "terjemah"],
            "system": ["install", "sudo", "terminal", "server", "vps", "restart", "deploy",
                        "nginx", "systemctl", "docker"],
            "file_operation": ["file", "baca", "read", "edit", "hapus", "delete", "folder"],
            "creative": ["desain", "design", "ide", "brainstorm", "kreatif"],
            "planning": ["rencana", "plan", "jadwal", "schedule", "strategy", "roadmap"],
            "image_generation": ["buatkan gambar", "bikin gambar", "buat foto", "generate image",
                                   "gambarkan", "ilustrasikan", "buatkan foto", "draw"],
            "audio_generation": ["balas dengan suara", "buat audio", "text to speech",
                                   "tts", "bacakan", "suarakan", "voice note"],
            "real_time_search": ["harga", "hari ini", "terkini", "terbaru", "berita", "live",
                                   "today", "latest", "current price", "crypto", "btc", "saham"],
        }

        detected_intents = []
        for intent, keywords in intent_keywords.items():
            if any(kw in msg for kw in keywords):
                detected_intents.append(intent)

        spec.intents = detected_intents or ["general"]
        spec.primary_intent = detected_intents[0] if detected_intents else "general"

        # Rough complexity estimate
        if len(message) > 300 or len(detected_intents) > 2:
            spec.complexity_score = 0.7
            spec.requires_multi_agent = True
        elif len(message) > 100 or len(detected_intents) > 1:
            spec.complexity_score = 0.5
        else:
            spec.complexity_score = 0.3

        # Special cases
        if spec.primary_intent == "image_generation":
            spec.is_simple = True
        elif spec.primary_intent == "audio_generation":
            spec.is_simple = True
        else:
            spec.is_simple = spec.complexity_score < 0.4

        return spec

    def _enrich(self, spec: TaskSpecification) -> TaskSpecification:
        """Post-processing: enrich the specification with derived info."""
        # Set cost preference based on complexity
        if spec.complexity_score > 0.7:
            spec.max_cost_preference = "expensive_ok"
        elif spec.complexity_score < 0.3:
            spec.max_cost_preference = "cheap"

        # If system/file operation, enforce confirmation
        if spec.primary_intent in ("system", "file_operation"):
            spec.urgency = "immediate"  # user is watching

        return spec

    def _get_fast_model(self) -> str:
        """Pick the fastest available model for classification."""
        # Prefer ringan/cepat: flash atau haiku
        priorities = [
            "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash",
            "qwen3.6-flash", "gpt-4o-mini", "claude-haiku", "llama3.1"
        ]
        for p in priorities:
            for k in model_manager.available_models.keys():
                if p in k:
                    return k
        return model_manager.get_default_model()


request_preprocessor = RequestPreprocessor()

"""
Super Agent Orchestrator — Agent Registry (v2.1 — Performance Optimized)
==========================================================================
Perbaikan dari v1:
  1. preferred_models kini pakai full key "sumopod/..." agar resolve tepat
  2. Model TTS diperbaiki: sumopod/minimax/speech-2.8-hd
  3. Confidence scoring di resolve_model_for_agent()
  4. Fallback chain eksplisit per agent type
  5. Agent "vision" ditambahkan sebagai type mandiri
  6. resolve_model_for_agent() tidak lagi silent-fail jika capability_map error
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import structlog
import threading
import time as _time

log = structlog.get_logger()

# ── Capability map: model → tags (sinkron dengan .capability_map.json) ──────
# Ini adalah "single source of truth" untuk routing tanpa import circular.
MODEL_CAPABILITY_MAP: Dict[str, List[str]] = {
    "sumopod/qwen3.6-flash":           ["coding", "speed", "text", "vision"],
    "sumopod/deepseek-v4-pro":           ["coding", "reasoning", "text"],
    "sumopod/gemini-2.5-flash-lite":   ["speed", "text", "vision"],
    "sumopod/minimax/speech-2.8-hd":   ["audio", "speed", "tts"],
    "sumopod/claude-haiku-4-5":        ["speed"],
    "sumopod/gpt-4o-mini":             ["analysis", "coding", "reasoning", "speed", "text", "vision", "writing"],
}

# Urutan preferensi global jika agent tidak punya preferred_models tersendiri
_DEFAULT_FALLBACK_ORDER = [
    "sumopod/deepseek-v4-pro",
    "sumopod/qwen3.6-flash",
    "sumopod/gpt-4o-mini",
    "sumopod/gemini-2.5-flash-lite",
    "sumopod/claude-haiku-4-5",
]


@dataclass
class AgentCapability:
    """Defines what an agent type can do."""
    agent_type: str
    display_name: str
    description: str
    skills: List[str]
    # Full model key — harus sama persis dengan key di model_manager.available_models
    preferred_models: List[str]
    fallback_models: List[str] = field(default_factory=list)
    tools_allowed: List[str] = field(default_factory=list)
    max_concurrent: int = 3
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    system_prompt_addon: str = ""
    # Tag kapabilitas yang dibutuhkan dari MODEL_CAPABILITY_MAP
    required_capabilities: List[str] = field(default_factory=list)


# ── Agent Registry ────────────────────────────────────────────────────────────
AGENT_REGISTRY: Dict[str, AgentCapability] = {

    "reasoning": AgentCapability(
        agent_type="reasoning",
        display_name="🧠 Reasoning Agent",
        description="Logika kompleks, matematika, analisis mendalam, perencanaan strategis",
        skills=["logic", "math", "analysis", "planning", "strategy", "reasoning",
                "problem_solving", "critical_thinking"],
        preferred_models=[
            "sumopod/deepseek-v4-pro",
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ],
        fallback_models=["sumopod/gemini-2.5-flash-lite", "sumopod/claude-haiku-4-5"],
        required_capabilities=["reasoning"],
        default_temperature=0.3,
        system_prompt_addon=(
            "Fokus pada penalaran logis. Tunjukkan proses berpikir secara bertahap. "
            "Prioritaskan akurasi di atas kecepatan."
        ),
    ),

    "coding": AgentCapability(
        agent_type="coding",
        display_name="💻 Coding Agent",
        description="Pengembangan software, debugging, code review, refactoring",
        skills=["python", "javascript", "typescript", "sql", "bash", "api",
                "debug", "refactor", "code_review", "testing", "web_development"],
        preferred_models=[
            "sumopod/deepseek-v4-pro",
            "sumopod/qwen3.6-flash",
            "sumopod/gpt-4o-mini",
        ],
        fallback_models=["sumopod/gemini-2.5-flash-lite", "sumopod/claude-haiku-4-5"],
        required_capabilities=["coding"],
        tools_allowed=["execute_bash", "read_file", "write_file", "write_multiple_files"],
        default_temperature=0.2,
        default_max_tokens=8192,
        system_prompt_addon=(
            "Tulis kode yang bersih dan production-quality. Sertakan error handling. "
            "Gunakan type hints dan docstring."
        ),
    ),

    "research": AgentCapability(
        agent_type="research",
        display_name="🔍 Research Agent",
        description="Pengumpulan informasi, pencarian web, fact-checking, perbandingan data",
        skills=["search", "gather", "compare", "summarize", "fact_check", "data_collection"],
        preferred_models=[
            "sumopod/gemini-2.5-flash-lite",
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ],
        fallback_models=["sumopod/claude-haiku-4-5", "sumopod/deepseek-v4-pro"],
        required_capabilities=["text"],
        default_temperature=0.5,
        system_prompt_addon=(
            "Lakukan riset secara menyeluruh. Sebutkan sumber bila memungkinkan. "
            "Sajikan temuan dalam format terstruktur."
        ),
    ),

    "writing": AgentCapability(
        agent_type="writing",
        display_name="✍️ Writing Agent",
        description="Pembuatan konten, dokumentasi, terjemahan, penyuntingan",
        skills=["writing", "editing", "translation", "documentation",
                "content_creation", "copywriting", "email"],
        preferred_models=[
            "sumopod/claude-haiku-4-5",
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ],
        fallback_models=["sumopod/gemini-2.5-flash-lite", "sumopod/deepseek-v4-pro"],
        required_capabilities=["writing"],
        default_temperature=0.7,
        system_prompt_addon=(
            "Tulis dalam bahasa yang jelas dan profesional. Sesuaikan nada dan gaya yang diminta. "
            "Gunakan format yang tepat."
        ),
    ),

    "system": AgentCapability(
        agent_type="system",
        display_name="🖥️ System Agent",
        description="Manajemen VPS, admin server, perintah terminal, networking, DevOps",
        skills=["bash", "linux", "docker", "nginx", "systemd", "networking",
                "monitoring", "deployment", "ssh", "cron"],
        preferred_models=[
            "sumopod/deepseek-v4-pro",
            "sumopod/qwen3.6-flash",
            "sumopod/gpt-4o-mini",
        ],
        fallback_models=["sumopod/gemini-2.5-flash-lite", "sumopod/claude-haiku-4-5"],
        required_capabilities=["coding"],
        tools_allowed=["execute_bash", "read_file", "write_file", "write_multiple_files"],
        default_temperature=0.2,
        system_prompt_addon=(
            "Prioritaskan keamanan. Selalu jelaskan apa yang dilakukan perintah sebelum mengeksekusi. "
            "Gunakan sudo hanya jika diperlukan."
        ),
    ),

    "creative": AgentCapability(
        agent_type="creative",
        display_name="🎨 Creative Agent",
        description="Brainstorming, generasi ide, design thinking, inovasi",
        skills=["brainstorming", "ideation", "design", "creativity",
                "innovation", "storytelling"],
        preferred_models=[
            "sumopod/claude-haiku-4-5",
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ],
        fallback_models=["sumopod/gemini-2.5-flash-lite"],
        required_capabilities=["text"],
        default_temperature=0.9,
        system_prompt_addon=(
            "Berpikir di luar kotak. Tawarkan beberapa opsi kreatif. "
            "Dorong pendekatan yang novel dan inovatif."
        ),
    ),

    "validation": AgentCapability(
        agent_type="validation",
        display_name="✅ Validation Agent",
        description="Quality assurance, pengujian, verifikasi, fact-checking",
        skills=["testing", "verification", "qa", "fact_checking",
                "code_review", "proofreading"],
        preferred_models=[
            "sumopod/deepseek-v4-pro",
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ],
        fallback_models=["sumopod/claude-haiku-4-5"],
        required_capabilities=["reasoning"],
        default_temperature=0.1,
        system_prompt_addon=(
            "Bersikap kritis dan teliti. Periksa kesalahan, inkonsistensi, dan edge case. "
            "Berikan umpan balik yang spesifik."
        ),
    ),

    "general": AgentCapability(
        agent_type="general",
        display_name="💬 General Agent",
        description="Percakapan umum, FAQ, pertanyaan sederhana, salam",
        skills=["conversation", "faq", "general_knowledge"],
        preferred_models=[
            "sumopod/gemini-2.5-flash-lite",
            "sumopod/claude-haiku-4-5",
            "sumopod/gpt-4o-mini",
        ],
        fallback_models=["sumopod/qwen3.6-flash"],
        required_capabilities=["speed"],
        default_temperature=0.7,
        system_prompt_addon="",
    ),

    "image_gen": AgentCapability(
        agent_type="image_gen",
        display_name="🖼️ Image Generation Agent",
        description="Membuat gambar dari deskripsi teks menggunakan model vision",
        skills=["image_gen", "vision", "creative", "design"],
        preferred_models=[
            "sumopod/gpt-4o-mini",
            "sumopod/qwen3.6-flash",
        ],
        fallback_models=["sumopod/gemini-2.5-flash-lite"],
        required_capabilities=["vision"],
        default_temperature=0.7,
        default_max_tokens=1024,
        system_prompt_addon=(
            "Anda membantu membuat gambar. Jika API mendukung, gunakan image generation. "
            "Jika tidak, berikan deskripsi gambar yang sangat detail dan saran prompt untuk tools seperti "
            "DALL-E, Midjourney, atau Stable Diffusion."
        ),
    ),

    "audio_gen": AgentCapability(
        agent_type="audio_gen",
        display_name="🔊 Audio/TTS Agent",
        description="Konversi teks ke suara atau membuat audio menggunakan speech models",
        skills=["tts", "audio", "speech", "voice"],
        # FIXED: sebelumnya "minimax/speech-2.8-hd" — sekarang pakai full key
        preferred_models=[
            "sumopod/minimax/speech-2.8-hd",
        ],
        fallback_models=["sumopod/gpt-4o-mini"],
        required_capabilities=["tts"],
        default_temperature=0.5,
        default_max_tokens=512,
        system_prompt_addon=(
            "Anda adalah asisten Text-to-Speech. Konfirmasi permintaan TTS dan pastikan "
            "teks akan diproses dengan benar."
        ),
    ),

    "multimodal": AgentCapability(
        agent_type="multimodal",
        display_name="🌐 Multimodal Agent",
        description="Menangani teks, gambar, dan audio secara bersamaan",
        skills=["vision", "audio", "text", "analysis", "reasoning"],
        preferred_models=[
            "sumopod/qwen3.6-flash",
            "sumopod/gpt-4o-mini",
            "sumopod/gemini-2.5-flash-lite",
        ],
        fallback_models=["sumopod/deepseek-v4-pro"],
        required_capabilities=["vision"],
        default_temperature=0.7,
        system_prompt_addon=(
            "Anda dapat memproses teks, gambar, dan audio. Tangani input multimodal secara akurat."
        ),
    ),

    "vision": AgentCapability(
        agent_type="vision",
        display_name="👁️ Vision Agent",
        description="Analisis gambar, OCR, deteksi objek, deskripsi visual",
        skills=["vision", "image_analysis", "ocr", "object_detection"],
        preferred_models=[
            "sumopod/qwen3.6-flash",
            "sumopod/gpt-4o-mini",
            "sumopod/gemini-2.5-flash-lite",
        ],
        fallback_models=["sumopod/deepseek-v4-pro"],
        required_capabilities=["vision"],
        default_temperature=0.5,
        system_prompt_addon=(
            "Analisis gambar secara detail. Sebutkan semua objek, aktivitas, teks, "
            "dan konteks yang terlihat dalam gambar."
        ),
    ),
}


def _find_model_by_capability(required_caps: List[str], available: set) -> Optional[str]:
    """
    Cari model terbaik berdasarkan capability tag.
    Scoring: jumlah required_caps yang dimiliki model.
    Mengembalikan model dengan score tertinggi yang tersedia.
    """
    best_model = None
    best_score = -1

    for model_id, caps in MODEL_CAPABILITY_MAP.items():
        if model_id not in available:
            continue
        # Hitung berapa required_caps yang dipenuhi model ini
        score = sum(1 for cap in required_caps if cap in caps)
        if score > best_score:
            best_score = score
            best_model = model_id

    return best_model if best_score > 0 else None


class AgentRegistryManager:
    """
    Manages the agent registry and provides lookup/matching functionality.
    Tracks real-time active agents for monitoring dashboard.
    """

    def __init__(self):
        self.registry = AGENT_REGISTRY
        self._active_agents: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()
        self._model_manager = None

    @property
    def model_manager(self):
        if self._model_manager is None:
            from core.model_manager import model_manager as mm
            self._model_manager = mm
        return self._model_manager

    # ── Real-time Status Tracking ────────────────────────────────────────────

    def mark_busy(self, agent_type: str, task_id: str) -> None:
        with self._lock:
            if agent_type not in self._active_agents:
                self._active_agents[agent_type] = {}
            self._active_agents[agent_type][task_id] = _time.time()

    def mark_idle(self, agent_type: str, task_id: str) -> None:
        with self._lock:
            if agent_type in self._active_agents:
                self._active_agents[agent_type].pop(task_id, None)
                if not self._active_agents[agent_type]:
                    del self._active_agents[agent_type]

    def get_active_agents(self) -> List[str]:
        now = _time.time()
        with self._lock:
            stale_agents = []
            for agent_type, tasks in self._active_agents.items():
                stale_tasks = [tid for tid, ts in tasks.items() if now - ts > 300]
                for tid in stale_tasks:
                    tasks.pop(tid)
                if not tasks:
                    stale_agents.append(agent_type)
            for agent_type in stale_agents:
                del self._active_agents[agent_type]
            return list(self._active_agents.keys())

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_agent(self, agent_type: str) -> Optional[AgentCapability]:
        return self.registry.get(agent_type)

    def get_all_agents(self) -> Dict[str, AgentCapability]:
        return self.registry

    def find_agents_for_skill(self, skill: str) -> List[AgentCapability]:
        return [
            agent for agent in self.registry.values()
            if skill.lower() in [s.lower() for s in agent.skills]
        ]

    def find_best_agent_type(self, task_type: str,
                              required_skills: List[str] = None) -> str:
        """
        Temukan agent type terbaik untuk task_type + required_skills.
        Priority: direct match → skill overlap → fallback ke "general".
        """
        if task_type in self.registry:
            return task_type

        if required_skills:
            best_match = None
            best_score = 0
            for agent_type, agent in self.registry.items():
                agent_skills = {s.lower() for s in agent.skills}
                req_skills = {s.lower() for s in required_skills}
                overlap = len(agent_skills & req_skills)
                if overlap > best_score:
                    best_score = overlap
                    best_match = agent_type
            if best_match:
                return best_match

        return "general"

    def resolve_model_for_agent(
        self,
        agent_type: str,
        user_preferred: Optional[str] = None,
    ) -> str:
        """
        Pilih model terbaik untuk agent_type.
        Priority:
          1. User explicitly chose a model → gunakan langsung
          2. preferred_models agent (exact key match, urutan pertama yang tersedia)
          3. Capability-based search dari MODEL_CAPABILITY_MAP
          4. Fallback model agent
          5. Global fallback order
          6. Model pertama yang tersedia
        Setiap langkah dicek terhadap available_models.
        """
        mm = self.model_manager
        available = set(mm.available_models.keys())

        # 1. User explicitly chose a model
        if user_preferred and user_preferred in available:
            log.debug("resolve_model: user_preferred", model=user_preferred)
            return user_preferred

        agent = self.registry.get(agent_type)
        if not agent:
            return mm.get_default_model()

        # 2. preferred_models (exact key match)
        for model_id in agent.preferred_models:
            if model_id in available:
                log.debug("resolve_model: preferred match",
                          agent=agent_type, model=model_id)
                return model_id

        # 3. Capability-based search
        if agent.required_capabilities:
            cap_model = _find_model_by_capability(agent.required_capabilities, available)
            if cap_model:
                log.debug("resolve_model: capability match",
                          agent=agent_type, model=cap_model,
                          caps=agent.required_capabilities)
                return cap_model

        # 4. Fallback models
        for model_id in agent.fallback_models:
            if model_id in available:
                log.debug("resolve_model: fallback match",
                          agent=agent_type, model=model_id)
                return model_id

        # 5. Global fallback order
        for model_id in _DEFAULT_FALLBACK_ORDER:
            if model_id in available:
                log.debug("resolve_model: global fallback",
                          agent=agent_type, model=model_id)
                return model_id

        # 6. Absolutely anything available
        fallback = mm.get_default_model()
        log.warning("resolve_model: using default fallback",
                    agent=agent_type, model=fallback)
        return fallback

    def get_agent_system_prompt(self, agent_type: str,
                                 base_prompt: str = "") -> str:
        """Build complete system prompt: base + agent-specific addon."""
        agent = self.registry.get(agent_type)
        if not agent or not agent.system_prompt_addon:
            return base_prompt

        addon = agent.system_prompt_addon
        if base_prompt:
            return f"{base_prompt}\n\n[Agent Role: {agent.display_name}] {addon}"
        return addon

    def list_for_api(self) -> List[Dict]:
        return [
            {
                "type":        agent.agent_type,
                "name":        agent.display_name,
                "description": agent.description,
                "skills":      agent.skills,
                "tools":       agent.tools_allowed,
            }
            for agent in self.registry.values()
        ]


agent_registry = AgentRegistryManager()

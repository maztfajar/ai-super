"""
Super Agent Orchestrator — Agent Registry (v3.0 — Dynamic Model Routing)
==========================================================================
v3.0 Changes:
  1. Zero hardcoded model names — model dipilih dari Integrasi/env secara dinamis
  2. AI Roles Mapping: AI_ROLE_<AGENT_TYPE> env var dibaca sebagai prioritas utama
  3. Auto-learning: perf_cache dibangun dari tabel AgentPerformance (success rate)
  4. Fallback: capability-based routing dari model yang tersedia
  5. Public API identik dengan v2.1 — tidak ada breaking change
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import os
import time
import asyncio
import threading
import structlog

log = structlog.get_logger()

# ── Lazy imports ─────────────────────────────────────────────────────────────

def _get_classifier():
    try:
        from agents import model_classifier
        return model_classifier
    except ImportError:
        return None

def _get_capability_map():
    try:
        from core.capability_map import capability_map
        return capability_map
    except ImportError:
        return None


# ── Performance-based routing cache ──────────────────────────────────────────
# Diisi oleh refresh_perf_cache() secara async.
# { agent_type → model_id }
_perf_cache: Dict[str, str] = {}
_perf_cache_lock = threading.Lock()
_perf_cache_time: float = 0.0
_PERF_CACHE_TTL: float = 300.0  # Refresh setiap 5 menit


def _read_role_mapping(agent_type: str) -> Optional[str]:
    """Baca AI_ROLE_<AGENT_TYPE> dari env. Return None jika tidak dikonfigurasi."""
    key = f"AI_ROLE_{agent_type.upper()}"
    val = os.environ.get(key, "").strip()
    return val if val else None


def _get_perf_model(agent_type: str) -> Optional[str]:
    """Ambil model terbaik dari performance cache (sync, non-blocking)."""
    with _perf_cache_lock:
        return _perf_cache.get(agent_type)


async def refresh_perf_cache():
    """
    Rebuild performance-based routing cache dari AgentPerformance.
    Fail-safe: jika DB error atau tidak ada data, cache lama tetap dipakai.
    Dipanggil saat startup dan setiap _PERF_CACHE_TTL detik.
    """
    global _perf_cache, _perf_cache_time
    try:
        from db.database import AsyncSessionLocal
        from db.models import AgentPerformance
        from sqlmodel import select
        from core.model_manager import model_manager

        available = set(model_manager.available_models.keys())
        if not available:
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AgentPerformance)
                .order_by(AgentPerformance.created_at.desc())
                .limit(1000)
            )
            records = result.scalars().all()

        # Aggregate: agent_type → { model_id → [confidence scores for successful runs] }
        stats: Dict[str, Dict[str, list]] = {}
        for rec in records:
            if rec.model_used not in available:
                continue
            stats.setdefault(rec.agent_type, {}).setdefault(rec.model_used, [])
            if rec.success:
                stats[rec.agent_type][rec.model_used].append(rec.confidence)

        new_cache: Dict[str, str] = {}
        for agent_type, model_stats in stats.items():
            best_model, best_score = None, -1.0
            for model_id, confidences in model_stats.items():
                if len(confidences) < 2:        # Minimal 2 sampel sukses
                    continue
                avg = sum(confidences) / len(confidences)
                if avg > best_score:
                    best_score = avg
                    best_model = model_id
            if best_model:
                new_cache[agent_type] = best_model

        with _perf_cache_lock:
            _perf_cache = new_cache
            _perf_cache_time = time.time()

        if new_cache:
            log.info("AgentRegistry: perf_cache updated", entries=len(new_cache))
    except Exception as e:
        log.debug("AgentRegistry: perf_cache refresh skipped", error=str(e)[:80])


async def perf_cache_background_loop():
    """Background loop — refresh perf_cache setiap _PERF_CACHE_TTL detik."""
    while True:
        await asyncio.sleep(_PERF_CACHE_TTL)
        await refresh_perf_cache()


def _find_model_by_capability(required_caps: List[str], available: set) -> Optional[str]:
    """
    Temukan model terbaik berdasarkan capability tags dari model yang tersedia.
    Menggunakan CapabilityMapEngine (interview-based) dan model_classifier (keyword-based).
    Tidak ada hardcoded nama model.
    """
    cap_engine = _get_capability_map()
    classifier = _get_classifier()
    best_model, best_score = None, -1

    for model_id in available:
        model_caps: set = set()
        # Prioritas 1: CapabilityMap (interview-based, lebih akurat)
        if cap_engine:
            try:
                model_caps = cap_engine.get_capabilities(model_id)
            except Exception:
                pass
        # Prioritas 2: model_classifier (keyword-based, lebih cepat)
        if not model_caps and classifier:
            try:
                model_caps = classifier.get_model_tags(model_id)
            except Exception:
                pass

        if not model_caps:
            continue

        score = sum(1 for cap in required_caps if cap in model_caps)
        if score > best_score:
            best_score = score
            best_model = model_id

    return best_model if best_score > 0 else None


# ── AgentCapability dataclass ─────────────────────────────────────────────────

@dataclass
class AgentCapability:
    """Defines what an agent type can do."""
    agent_type: str
    display_name: str
    description: str
    skills: List[str]
    # Capability tags yang dibutuhkan — dipakai untuk auto capability-based routing
    required_capabilities: List[str] = field(default_factory=list)
    # preferred_models & fallback_models dikosongkan — tidak ada hardcode model
    preferred_models: List[str] = field(default_factory=list)
    fallback_models: List[str] = field(default_factory=list)
    tools_allowed: List[str] = field(default_factory=list)
    max_concurrent: int = 3
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    system_prompt_addon: str = ""


# ── Agent Registry ────────────────────────────────────────────────────────────

AGENT_REGISTRY: Dict[str, AgentCapability] = {

    "reasoning": AgentCapability(
        agent_type="reasoning",
        display_name="🧠 Reasoning Agent",
        description="Logika kompleks, matematika, analisis mendalam, perencanaan strategis",
        skills=["logic", "math", "analysis", "planning", "strategy", "reasoning",
                "problem_solving", "critical_thinking"],
        required_capabilities=["reasoning", "analysis"],
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
        skills=["search", "gather", "compare", "summarize", "fact_check",
                "data_collection", "browser_automation"],
        required_capabilities=["text", "speed"],
        tools_allowed=["web_search", "browser_navigate", "browser_click",
                       "browser_type", "browser_extract_text", "browser_screenshot"],
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
        required_capabilities=["writing", "text"],
        default_temperature=0.7,
        system_prompt_addon=(
            "Tulis dalam bahasa yang jelas dan profesional. Sesuaikan nada dan gaya. "
            "Gunakan format yang tepat."
        ),
    ),

    "system": AgentCapability(
        agent_type="system",
        display_name="🖥️ System Agent",
        description="Manajemen VPS, admin server, perintah terminal, networking, DevOps",
        skills=["bash", "linux", "docker", "nginx", "systemd", "networking",
                "monitoring", "deployment", "ssh", "cron"],
        required_capabilities=["coding", "reasoning"],
        tools_allowed=["execute_bash", "read_file", "write_file", "write_multiple_files"],
        default_temperature=0.2,
        system_prompt_addon=(
            "Prioritaskan keamanan. Selalu jelaskan apa yang dilakukan perintah. "
            "Gunakan sudo hanya jika diperlukan."
        ),
    ),

    "creative": AgentCapability(
        agent_type="creative",
        display_name="🎨 Creative Agent",
        description="Brainstorming, generasi ide, design thinking, inovasi, storytelling",
        skills=["brainstorming", "ideation", "design", "creativity",
                "innovation", "storytelling"],
        required_capabilities=["writing", "text"],
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
        required_capabilities=["reasoning", "analysis"],
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
        required_capabilities=["text", "speed"],
        default_temperature=0.7,
        system_prompt_addon="",
    ),

    "image_gen": AgentCapability(
        agent_type="image_gen",
        display_name="🖼️ Image Generation Agent",
        description="Membuat gambar dari deskripsi teks menggunakan model vision",
        skills=["image_gen", "vision", "creative", "design"],
        required_capabilities=["vision"],
        default_temperature=0.7,
        default_max_tokens=1024,
        system_prompt_addon=(
            "Anda membantu membuat gambar. Gunakan image generation API jika tersedia. "
            "Jika tidak, berikan deskripsi gambar yang sangat detail."
        ),
    ),

    "audio_gen": AgentCapability(
        agent_type="audio_gen",
        display_name="🔊 Audio/TTS Agent",
        description="Konversi teks ke suara atau membuat audio menggunakan speech models",
        skills=["tts", "audio", "speech", "voice"],
        required_capabilities=["tts", "audio"],
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
        required_capabilities=["vision"],
        default_temperature=0.5,
        system_prompt_addon=(
            "Analisis gambar secara detail. Sebutkan semua objek, aktivitas, teks, "
            "dan konteks yang terlihat."
        ),
    ),

    "orchestrator": AgentCapability(
        agent_type="orchestrator",
        display_name="⚙️ Orchestrator Core",
        description="Layanan background otomatis yang mengoptimasi sistem dan output AI",
        skills=["QMD (Token Killer)", "Capability Evolver", "Humanizer (Anti-Slop)",
                "Byte Rover (Memory)", "Browser Automation", "Command Center",
                "GOG CLI (Google Ecosystem)"],
        required_capabilities=[],
        default_temperature=0.0,
        system_prompt_addon="",
    ),
}


# ── AgentRegistryManager ──────────────────────────────────────────────────────

class AgentRegistryManager:
    """
    Manages the agent registry and provides dynamic model resolution.
    Public API identik dengan v2.1 — tidak ada breaking change untuk code lain.
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
            self._active_agents.setdefault(agent_type, {})[task_id] = time.time()

    def mark_idle(self, agent_type: str, task_id: str) -> None:
        with self._lock:
            if agent_type in self._active_agents:
                self._active_agents[agent_type].pop(task_id, None)
                if not self._active_agents[agent_type]:
                    del self._active_agents[agent_type]

    def get_active_agents(self) -> List[str]:
        now = time.time()
        with self._lock:
            for agent_type in list(self._active_agents):
                stale = [tid for tid, ts in self._active_agents[agent_type].items()
                         if now - ts > 300]
                for tid in stale:
                    self._active_agents[agent_type].pop(tid)
                if not self._active_agents[agent_type]:
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
        if task_type in self.registry:
            return task_type
        if required_skills:
            best_match, best_score = None, 0
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
        Pilih model terbaik untuk agent_type secara dinamis.

        Priority (dari tertinggi ke terendah):
          1. User explicitly chose a model (user_preferred)
          2. AI_ROLE_<AGENT_TYPE> env var — dari menu Integrasi → AI Roles Mapping
          3. Performance-based cache (dari AgentPerformance table, diperbarui tiap 5 menit)
          4. Dynamic routing cache dari model_classifier (capability keyword matching)
          5. Capability-based search dari available models (menggunakan required_capabilities)
          6. Model pertama yang tersedia (any available model)
          7. Default model fallback terakhir
        """
        mm = self.model_manager
        available = set(mm.available_models.keys())

        # 1. User explicitly chose a model
        if user_preferred and user_preferred in available:
            log.debug("resolve_model: user_preferred", model=user_preferred, agent=agent_type)
            return user_preferred

        agent = self.registry.get(agent_type)

        # 2. AI Roles Mapping dari env (menu Integrasi)
        role_model = _read_role_mapping(agent_type)
        if role_model and role_model in available:
            log.debug("resolve_model: role_mapping env", model=role_model, agent=agent_type)
            return role_model

        # 3. Performance-based cache (auto-learning dari riwayat eksekusi)
        perf_model = _get_perf_model(agent_type)
        if perf_model and perf_model in available:
            log.debug("resolve_model: perf_cache hit", model=perf_model, agent=agent_type)
            return perf_model

        # 4. Dynamic routing cache dari model_classifier
        classifier = _get_classifier()
        if classifier and classifier.is_cache_ready():
            for model_id in classifier.get_preferred_models(agent_type):
                if model_id in available:
                    log.debug("resolve_model: classifier cache", model=model_id, agent=agent_type)
                    return model_id

        # 5. Capability-based search dari available models
        if agent and agent.required_capabilities:
            cap_model = _find_model_by_capability(agent.required_capabilities, available)
            if cap_model:
                log.debug("resolve_model: capability match",
                          model=cap_model, agent=agent_type, caps=agent.required_capabilities)
                return cap_model

        # 6. Model pertama yang tersedia (exclude audio-only models untuk non-audio tasks)
        if available:
            # Hindari model TTS/audio untuk agent non-audio
            non_audio_agents = {"reasoning", "coding", "writing", "research",
                                 "system", "creative", "validation", "general",
                                 "vision", "multimodal", "image_gen"}
            if agent_type in non_audio_agents:
                for m in available:
                    if "speech" not in m.lower() and "tts" not in m.lower() and "audio" not in m.lower():
                        log.debug("resolve_model: first_available", model=m, agent=agent_type)
                        return m
            else:
                return next(iter(available))

        # 7. Absolute fallback
        fallback = mm.get_default_model()
        log.warning("resolve_model: default fallback", model=fallback, agent=agent_type)
        return fallback

    def get_agent_system_prompt(self, agent_type: str, base_prompt: str = "") -> str:
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

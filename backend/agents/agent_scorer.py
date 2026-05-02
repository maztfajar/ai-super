"""
Agent Scorer (v2.1 — Performance Optimized)
============================================
Perbaikan dari v1:
  1. _compute_capability(): matching model key sekarang exact-first, bukan substring saja
  2. _compute_capability_map_score(): pakai MODEL_CAPABILITY_MAP dari agent_registry
     (tidak perlu import capability_map yang bisa circular)
  3. quality_priority "speed" / "quality" boost menggunakan full key "sumopod/..."
  4. _find_alternative_model(): pilih berdasarkan task_type, bukan random
  5. Score caching per (model_id, agent_type, task_type) untuk menghindari kalkulasi berulang
  6. assign_all() reset _active_executions setelah selesai agar tidak akumulasi terus
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import structlog

from core.model_manager import model_manager
from core.metrics import metrics_engine
from agents.agent_registry import agent_registry, AgentCapability, MODEL_CAPABILITY_MAP
from core.dag_builder import SubTask

log = structlog.get_logger()


@dataclass
class AgentScore:
    """Score breakdown untuk kombinasi model/agent."""
    model_id: str
    agent_type: str
    capability_score: float = 0.0
    historical_score: float = 0.0
    specialization_score: float = 0.0
    availability_score: float = 0.0
    capability_map_score: float = 0.0
    total_score: float = 0.0
    reasoning: str = ""

    def compute_total(
        self,
        w_capability:     float = 0.35,
        w_cap_map:        float = 0.25,
        w_historical:     float = 0.22,
        w_specialization: float = 0.13,
        w_availability:   float = 0.05,
    ) -> float:
        self.total_score = (
            self.capability_score     * w_capability +
            self.capability_map_score * w_cap_map +
            self.historical_score     * w_historical +
            self.specialization_score * w_specialization +
            self.availability_score   * w_availability
        )
        return self.total_score


# Model aktif saat ini (untuk availability scoring)
_active_executions: Dict[str, int] = {}

# Cache score: (model_id, agent_type, task_type) → AgentScore
# TTL: 60 detik — cukup untuk satu sesi orchestration tanpa stale terlalu lama
_SCORE_CACHE: Dict[tuple, Tuple[AgentScore, float]] = {}
_SCORE_CACHE_TTL = 60.0


# ── Quality priority config ─────────────────────────────────────────────────
# Model yang dianggap "cepat/murah" (boost jika priority = speed)
_SPEED_MODELS = [
    "sumopod/gemini-2.5-flash-lite",
    "sumopod/claude-haiku-4-5",
    "sumopod/gpt-4o-mini",
]
# Model yang dianggap "premium/kuat" (boost jika priority = quality)
_QUALITY_MODELS = [
    "sumopod/deepseek-v4-pro",
    "sumopod/gpt-4o-mini",
    "sumopod/qwen3.6-flash",
]

# Agent type → capability tags yang dibutuhkan (sinkron dengan agent_registry)
_AGENT_TO_CAPS: Dict[str, set] = {
    "image_gen":   {"image_gen"},
    "audio_gen":   {"tts", "audio"},
    "multimodal":  {"vision"},
    "vision":      {"vision"},
    "coding":      {"coding"},
    "reasoning":   {"reasoning"},
    "analysis":    {"analysis", "reasoning"},
    "writing":     {"writing", "text"},
    "research":    {"text"},
    "system":      {"coding", "text"},
    "creative":    {"text", "writing"},
    "validation":  {"reasoning", "text"},
    "general":     {"text"},
    "planning":    {"reasoning", "text"},
}


class AgentScorer:
    """
    Scoring & selection engine.
    Score = capability(0.35) + cap_map(0.25) + historical(0.22) + spec(0.13) + avail(0.05)
    """

    def score_model(
        self,
        model_id: str,
        subtask: SubTask,
        agent_cap: AgentCapability,
    ) -> AgentScore:
        """Score model tertentu untuk subtask tertentu. Dengan cache."""
        cache_key = (model_id, agent_cap.agent_type, subtask.task_type)
        now = time.time()
        if cache_key in _SCORE_CACHE:
            cached_score, cached_ts = _SCORE_CACHE[cache_key]
            if now - cached_ts < _SCORE_CACHE_TTL:
                # Update availability saja (berubah cepat)
                cached_score.availability_score = self._compute_availability(
                    model_id, agent_cap
                )
                cached_score.compute_total()
                return cached_score

        score = AgentScore(model_id=model_id, agent_type=agent_cap.agent_type)
        score.capability_score     = self._compute_capability(model_id, subtask, agent_cap)
        score.capability_map_score = self._compute_capability_map_score(model_id, agent_cap)
        score.historical_score     = metrics_engine.get_model_score(model_id, subtask.task_type)
        score.specialization_score = self._compute_specialization(model_id, agent_cap)
        score.availability_score   = self._compute_availability(model_id, agent_cap)
        score.compute_total()
        score.reasoning = (
            f"cap={score.capability_score:.2f} "
            f"cap_map={score.capability_map_score:.2f} "
            f"hist={score.historical_score:.2f} "
            f"spec={score.specialization_score:.2f} "
            f"avail={score.availability_score:.2f} "
            f"→ {score.total_score:.3f}"
        )

        # Simpan ke cache
        _SCORE_CACHE[cache_key] = (score, now)
        return score

    def select_best_model(
        self,
        subtask: SubTask,
        quality_priority: str = "balanced",
    ) -> Tuple[str, str, AgentScore]:
        """
        Pilih model + agent type terbaik untuk subtask.
        Returns (model_id, agent_type, best_score).
        """
        agent_type = agent_registry.find_best_agent_type(
            subtask.task_type, subtask.required_skills
        )
        agent_cap = agent_registry.get_agent(agent_type) or agent_registry.get_agent("general")
        if not agent_cap:
            agent_type = "general"
            agent_cap  = agent_registry.registry["general"]

        candidates: List[AgentScore] = []
        for model_id in model_manager.available_models:
            s = self.score_model(model_id, subtask, agent_cap)
            candidates.append(s)

        if not candidates:
            default = model_manager.get_default_model()
            return default, agent_type, AgentScore(model_id=default, agent_type=agent_type)

        # ── Quality priority boosts ─────────────────────────────────────────
        if quality_priority == "speed":
            for c in candidates:
                if c.model_id in _SPEED_MODELS:
                    c.total_score = min(1.0, c.total_score * 1.3)
        elif quality_priority == "quality":
            for c in candidates:
                if c.model_id in _QUALITY_MODELS:
                    c.total_score = min(1.0, c.total_score * 1.3)

        # ── Hard block: model yang tidak bisa handle task type ini ──────────
        required_caps = _AGENT_TO_CAPS.get(agent_type, set())
        if agent_type in ("image_gen", "audio_gen", "vision"):
            # Kalau tidak punya cap yang dibutuhkan → score = 0
            for c in candidates:
                model_caps = set(MODEL_CAPABILITY_MAP.get(c.model_id, []))
                if required_caps and not (required_caps & model_caps):
                    c.total_score = 0.0

        candidates.sort(key=lambda c: c.total_score, reverse=True)
        best = candidates[0]

        log.debug(
            "Agent scored",
            task=subtask.id,
            type=agent_type,
            model=best.model_id,
            score=f"{best.total_score:.3f}",
            reasoning=best.reasoning,
        )
        return best.model_id, agent_type, best

    def assign_all(
        self,
        subtasks: List[SubTask],
        quality_priority: str = "balanced",
    ) -> List[SubTask]:
        """
        Assign model + agent ke semua subtasks.
        PERBAIKAN: reset _active_executions sebelum assign agar tidak akumulasi dari sesi lama.
        """
        _active_executions.clear()

        for st in subtasks:
            model_id, agent_type, score = self.select_best_model(st, quality_priority)
            st.assigned_model  = model_id
            st.assigned_agent  = agent_type
            _active_executions[model_id] = _active_executions.get(model_id, 0) + 1

        return subtasks

    def release_model(self, model_id: str):
        if model_id in _active_executions:
            _active_executions[model_id] = max(0, _active_executions[model_id] - 1)

    # ── Scoring sub-functions ─────────────────────────────────────────────────

    def _compute_capability(
        self,
        model_id: str,
        subtask: SubTask,
        agent_cap: AgentCapability,
    ) -> float:
        """
        Seberapa baik model ini cocok dengan requirements?
        PERBAIKAN: exact match dulu → baru partial match.
        """
        position_score = 0.0
        for idx, preferred in enumerate(agent_cap.preferred_models):
            # Exact match (full key)
            if model_id == preferred:
                position_score = 1.0 - (idx * 0.12)
                break
            # Partial match (backward compat untuk model yang tidak pakai prefix)
            if preferred in model_id or model_id in preferred:
                position_score = max(position_score, 0.7 - (idx * 0.1))

        # Skill overlap
        if subtask.required_skills:
            agent_skills = {s.lower() for s in agent_cap.skills}
            req_skills   = {s.lower() for s in subtask.required_skills}
            overlap = len(agent_skills & req_skills) / len(req_skills) if req_skills else 0.5
        else:
            overlap = 0.5

        return min(1.0, position_score * 0.6 + overlap * 0.4)

    def _compute_specialization(self, model_id: str, agent_cap: AgentCapability) -> float:
        """Seberapa ter-spesialisasi agent ini untuk task ini?"""
        if agent_cap.agent_type == "general":
            return 0.3
        if agent_cap.preferred_models:
            # Exact match dengan model pertama (paling direkomendasikan)
            if model_id == agent_cap.preferred_models[0]:
                return 1.0
            # Ada di top-3 preferred
            if model_id in agent_cap.preferred_models[:3]:
                return 0.75
            # Partial match
            if any(p in model_id or model_id in p for p in agent_cap.preferred_models[:3]):
                return 0.6
        return 0.4

    def _compute_availability(self, model_id: str, agent_cap: AgentCapability) -> float:
        """Availability berdasarkan active executions."""
        active = _active_executions.get(model_id, 0)
        max_c  = agent_cap.max_concurrent
        if active >= max_c:
            return 0.1
        if active == 0:
            return 1.0
        return 1.0 - (active / max_c) * 0.8

    def _compute_capability_map_score(
        self,
        model_id: str,
        agent_cap: AgentCapability,
    ) -> float:
        """
        Score berdasarkan capability tags.
        PERBAIKAN: pakai MODEL_CAPABILITY_MAP dari agent_registry (tidak ada circular import).
        Fallback ke core.capability_map jika tersedia.
        """
        # Coba pakai MODEL_CAPABILITY_MAP (selalu tersedia, tidak circular)
        model_caps = set(MODEL_CAPABILITY_MAP.get(model_id, []))

        # Jika tidak ada di local map, coba capability_map engine
        if not model_caps:
            try:
                from core.capability_map import capability_map
                model_caps = set(capability_map.get_capabilities(model_id) or [])
            except Exception:
                return 0.5  # netral

        if not model_caps:
            return 0.5  # model tidak dikenal → netral

        required = _AGENT_TO_CAPS.get(agent_cap.agent_type, {"text"})

        # Hard block untuk task yang butuh capability spesifik
        if agent_cap.agent_type in ("image_gen", "audio_gen", "vision"):
            if not (required & model_caps):
                return 0.0  # model tidak bisa handle task ini

        overlap = len(required & model_caps)
        return min(1.0, overlap / len(required)) if required else 0.5


agent_scorer = AgentScorer()

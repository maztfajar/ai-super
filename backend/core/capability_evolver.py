"""
Capability Evolver (v1.0)
=========================
Otak dari sistem self-improvement. Berjalan secara periodik (tiap 30 menit)
dan menganalisis riwayat aktivitas untuk menghasilkan EvolutionRule baru.

Tiga sumber data yang dianalisis:
  1. AgentPerformance — rekaman setiap eksekusi agent (sukses/gagal, latency, confidence)
  2. TaskExecution    — rekaman pipeline orchestrator end-to-end
  3. ErrorRecovery    — pola error dan strategi recovery yang berhasil

Enam jenis pelajaran yang bisa dihasilkan:
  A. Model mana yang paling cocok untuk task type tertentu
  B. Routing mana yang konsisten gagal (redirect ke agent lain)
  C. Error yang bisa diantisipasi sebelum terjadi
  D. Task yang harus selalu di-decompose (tidak bisa simple path)
  E. Prompt enhancement yang meningkatkan kualitas output
  F. Threshold complexity yang perlu dikalibrasi ulang
"""

import asyncio
import time
import uuid
import json
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass
import structlog

from core.evolution_store import (
    evolution_store, EvolutionRule, RuleType, RuleStatus
)

log = structlog.get_logger()

# Threshold untuk generate rule
MIN_SAMPLES           = 5
FAIL_THRESHOLD        = 0.40
SUCCESS_THRESHOLD     = 0.80
MIN_CONFIDENCE_INIT   = 0.55
LATENCY_WARN_MS       = 8000


@dataclass
class PerformanceGroup:
    """Agregasi performa untuk kombinasi (task_type, agent_type, model)."""
    task_type:  str
    agent_type: str
    model_id:   str
    successes:  int = 0
    failures:   int = 0
    total_time_ms: int = 0
    avg_confidence: float = 0.0
    error_messages: List[str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def win_rate(self) -> float:
        return self.successes / self.total if self.total > 0 else 0.5

    @property
    def avg_latency_ms(self) -> float:
        return self.total_time_ms / self.total if self.total > 0 else 0


class CapabilityEvolver:
    """
    Engine self-improvement yang menganalisis performa historis
    dan menghasilkan EvolutionRule secara otomatis.
    """

    def __init__(self):
        self._last_evolution: float = 0
        self._evolution_count: int = 0
        self._is_running: bool = False

    async def evolve(self, force: bool = False) -> dict:
        if self._is_running and not force:
            return {"status": "already_running", "rules_created": 0}

        self._is_running = True
        start = time.time()
        summary = {
            "rules_created": 0, "rules_activated": 0,
            "rules_deprecated": 0, "insights": [], "duration_ms": 0,
        }

        try:
            log.info("Capability Evolver: mulai siklus evolusi",
                     cycle=self._evolution_count + 1)

            perf_groups    = await self._load_performance_data()
            error_patterns = await self._load_error_patterns()
            task_patterns  = await self._load_task_patterns()

            if not perf_groups:
                log.info("Evolver: data historis belum cukup, skip")
                return {"status": "insufficient_data", "rules_created": 0}

            new_rules: List[EvolutionRule] = []

            model_rules, insights_a = self._analyze_model_performance(perf_groups)
            new_rules.extend(model_rules)
            summary["insights"].extend(insights_a)

            routing_rules, insights_b = self._analyze_routing_failures(perf_groups)
            new_rules.extend(routing_rules)
            summary["insights"].extend(insights_b)

            error_rules, insights_c = self._analyze_error_patterns(error_patterns)
            new_rules.extend(error_rules)
            summary["insights"].extend(insights_c)

            decomp_rules, insights_d = self._analyze_decomposition(task_patterns)
            new_rules.extend(decomp_rules)
            summary["insights"].extend(insights_d)

            latency_rules, insights_e = self._analyze_latency(perf_groups)
            new_rules.extend(latency_rules)
            summary["insights"].extend(insights_e)

            for rule in new_rules:
                added = await evolution_store.add_rule(rule)
                if added:
                    summary["rules_created"] += 1
                    if rule.confidence >= 0.6:
                        await evolution_store.activate_rule(rule.id)
                        summary["rules_activated"] += 1

            deprecated = await self._cleanup_stale_rules(perf_groups)
            summary["rules_deprecated"] = deprecated

            self._last_evolution = time.time()
            self._evolution_count += 1
            summary["duration_ms"] = int((time.time() - start) * 1000)
            summary["status"] = "success"

            log.info("Evolver: siklus selesai",
                     created=summary["rules_created"],
                     activated=summary["rules_activated"],
                     deprecated=summary["rules_deprecated"],
                     duration_ms=summary["duration_ms"])

        except Exception as e:
            log.error("Evolver: error saat evolusi", error=str(e)[:150])
            summary["status"] = "error"
            summary["error"]  = str(e)[:150]
        finally:
            self._is_running = False

        return summary

    async def apply_rules_to_scoring(
        self, task_type: str, agent_type: str, model_id: str,
    ) -> Tuple[float, List[str]]:
        rules = await evolution_store.get_rules_for_context(
            task_type=task_type, agent_type=agent_type,
            model_id=model_id, min_confidence=0.5,
        )
        modifier = 0.0
        applied  = []

        for rule in rules:
            if rule.rule_type == RuleType.MODEL_PREFERENCE:
                preferred = rule.action.get("prefer_model", "")
                avoid     = rule.action.get("avoid_model", "")
                if preferred and preferred in model_id:
                    boost = rule.action.get("boost", 0.2) * rule.confidence
                    modifier += boost
                    applied.append(rule.id)
                elif avoid and avoid in model_id:
                    penalty = rule.action.get("penalty", 0.3) * rule.confidence
                    modifier -= penalty
                    applied.append(rule.id)
            elif rule.rule_type == RuleType.ROUTING_OVERRIDE:
                target_agent = rule.action.get("redirect_to", "")
                if target_agent and target_agent != agent_type:
                    modifier -= 0.25 * rule.confidence
                    applied.append(rule.id)

        return max(-0.5, min(0.5, modifier)), applied

    async def get_prompt_patches(self, task_type: str) -> List[str]:
        rules = await evolution_store.get_active_rules(
            rule_type=RuleType.PROMPT_PATCH, min_confidence=0.55,
        )
        patches = []
        for rule in rules:
            cond = rule.condition
            if cond.get("task_type") in (task_type, "*"):
                patch = rule.action.get("append_to_prompt", "")
                if patch:
                    patches.append(patch)
        return patches

    async def get_retry_strategy(self, error_message: str, model_id: str) -> Optional[dict]:
        rules = await evolution_store.get_active_rules(
            rule_type=RuleType.RETRY_STRATEGY, min_confidence=0.5,
        )
        err_lower = error_message.lower()
        for rule in rules:
            cond = rule.condition
            err_pattern = cond.get("error_pattern", "").lower()
            model_pat   = cond.get("model_pattern", "")
            if err_pattern and err_pattern not in err_lower:
                continue
            if model_pat and model_pat not in model_id:
                continue
            return rule.action
        return None

    def get_status(self) -> dict:
        return {
            "last_evolution":  self._last_evolution,
            "evolution_count": self._evolution_count,
            "is_running":      self._is_running,
        }

    # ── Data Loading ──────────────────────────────────────────────────────────

    async def _load_performance_data(self) -> List[PerformanceGroup]:
        try:
            from db.database import AsyncSessionLocal
            from db.models import AgentPerformance
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AgentPerformance)
                    .order_by(AgentPerformance.created_at.desc())
                    .limit(500)
                )
                records = result.scalars().all()

            if not records:
                return []

            groups: Dict[tuple, PerformanceGroup] = {}
            for rec in records:
                key = (rec.task_type or "general", rec.agent_type, rec.model_used)
                if key not in groups:
                    groups[key] = PerformanceGroup(
                        task_type=key[0], agent_type=key[1], model_id=key[2]
                    )
                g = groups[key]
                if rec.success:
                    g.successes += 1
                else:
                    g.failures += 1
                    if rec.error_message:
                        g.error_messages.append(rec.error_message[:100])
                g.total_time_ms += rec.execution_time_ms
                g.avg_confidence = (
                    (g.avg_confidence * (g.total - 1) + rec.confidence) / g.total
                )

            return list(groups.values())
        except Exception as e:
            log.warning("Evolver: gagal load performance data", error=str(e)[:80])
            return []

    async def _load_error_patterns(self) -> Dict[str, List[str]]:
        try:
            from db.database import AsyncSessionLocal
            from db.models import AgentPerformance
            from sqlmodel import select, and_

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AgentPerformance).where(
                        and_(
                            AgentPerformance.success == False,
                            AgentPerformance.error_message.isnot(None),
                        )
                    ).limit(200)
                )
                records = result.scalars().all()

            patterns: Dict[str, List[str]] = defaultdict(list)
            for rec in records:
                if rec.error_message:
                    patterns[rec.model_used].append(rec.error_message[:150])
            return dict(patterns)
        except Exception as e:
            log.warning("Evolver: gagal load error patterns", error=str(e)[:80])
            return {}

    async def _load_task_patterns(self) -> List[dict]:
        try:
            from db.database import AsyncSessionLocal
            from db.models import TaskExecution
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(TaskExecution)
                    .order_by(TaskExecution.created_at.desc())
                    .limit(200)
                )
                records = result.scalars().all()

            patterns = []
            for rec in records:
                if not rec.task_spec_json:
                    continue
                try:
                    spec = json.loads(rec.task_spec_json)
                    patterns.append({
                        "primary_intent":       spec.get("primary_intent", "general"),
                        "complexity_score":     spec.get("complexity_score", 0.5),
                        "is_simple":            spec.get("is_simple", True),
                        "requires_multi_agent": spec.get("requires_multi_agent", False),
                        "status":               rec.status,
                        "total_time_ms":        rec.total_time_ms,
                        "had_error":            rec.status == "failed",
                    })
                except Exception:
                    pass
            return patterns
        except Exception as e:
            log.warning("Evolver: gagal load task patterns", error=str(e)[:80])
            return []

    # ── Rule Generation ───────────────────────────────────────────────────────

    def _analyze_model_performance(
        self, groups: List[PerformanceGroup]
    ) -> Tuple[List[EvolutionRule], List[str]]:
        rules, insights = [], []
        by_task_model: Dict[str, Dict[str, PerformanceGroup]] = defaultdict(dict)
        for g in groups:
            if g.total >= MIN_SAMPLES:
                by_task_model[g.task_type][g.model_id] = g

        for task_type, models in by_task_model.items():
            if len(models) < 2:
                continue
            sorted_models = sorted(models.values(), key=lambda g: g.win_rate, reverse=True)
            best, worst = sorted_models[0], sorted_models[-1]

            if best.win_rate - worst.win_rate >= 0.30:
                rule_id = f"mp_{task_type}_{best.model_id.split('/')[-1]}_{int(time.time())}"
                rule = EvolutionRule(
                    id=rule_id, rule_type=RuleType.MODEL_PREFERENCE,
                    condition={"task_type": task_type},
                    action={
                        "prefer_model": best.model_id, "avoid_model": worst.model_id,
                        "boost": 0.25, "penalty": 0.20,
                    },
                    confidence=MIN_CONFIDENCE_INIT + (best.win_rate - 0.5) * 0.3,
                    source="evolver_model_analysis",
                    explanation=(
                        f"Untuk task '{task_type}': {best.model_id.split('/')[-1]} "
                        f"menang {best.win_rate:.0%} ({best.total} task) vs "
                        f"{worst.model_id.split('/')[-1]} hanya {worst.win_rate:.0%} "
                        f"({worst.total} task)."
                    ),
                )
                rules.append(rule)
                insights.append(
                    f"📊 Model terbaik untuk '{task_type}': "
                    f"{best.model_id.split('/')[-1]} ({best.win_rate:.0%} win rate)"
                )
        return rules, insights

    def _analyze_routing_failures(
        self, groups: List[PerformanceGroup]
    ) -> Tuple[List[EvolutionRule], List[str]]:
        rules, insights = [], []
        for g in groups:
            if g.total < MIN_SAMPLES or g.win_rate >= FAIL_THRESHOLD:
                continue
            better_agent = self._suggest_better_agent(g.task_type, g.agent_type)
            if not better_agent or better_agent == g.agent_type:
                continue

            rule_id = f"ro_{g.task_type}_{g.agent_type}_{int(time.time())}"
            rule = EvolutionRule(
                id=rule_id, rule_type=RuleType.ROUTING_OVERRIDE,
                condition={"task_type": g.task_type, "agent_type": g.agent_type},
                action={"redirect_to": better_agent, "reason": f"Win rate {g.win_rate:.0%} terlalu rendah"},
                confidence=MIN_CONFIDENCE_INIT, source="evolver_routing_analysis",
                explanation=(
                    f"Agent '{g.agent_type}' gagal {g.failures}/{g.total} kali "
                    f"untuk task '{g.task_type}'. Redirect ke '{better_agent}'."
                ),
            )
            rules.append(rule)
            insights.append(
                f"🔀 Routing fix: '{g.task_type}' sebaiknya ke agent "
                f"'{better_agent}' bukan '{g.agent_type}'"
            )
        return rules, insights

    def _analyze_error_patterns(
        self, error_patterns: Dict[str, List[str]]
    ) -> Tuple[List[EvolutionRule], List[str]]:
        rules, insights = [], []
        KNOWN_PATTERNS = [
            ("model output must contain", "empty_output",    {"skip_same": True, "reduce_tokens": False}),
            ("timeout",                   "timeout",         {"skip_same": False, "reduce_tokens": True, "max_tokens_override": 2048}),
            ("rate limit",                "rate_limit",      {"skip_same": True, "delay_seconds": 5}),
            ("connection refused",        "connection",      {"skip_same": True}),
            ("401",                       "auth_error",      {"skip_same": True, "alert_admin": True}),
            ("context length",            "context_too_long",{"reduce_tokens": True, "max_tokens_override": 2048}),
        ]

        for model_id, errors in error_patterns.items():
            if len(errors) < 3:
                continue
            for pattern, label, action in KNOWN_PATTERNS:
                count = sum(1 for e in errors if pattern in e.lower())
                if count < 3:
                    continue
                rule_id = f"rs_{label}_{model_id.split('/')[-1]}_{int(time.time())}"
                rule = EvolutionRule(
                    id=rule_id, rule_type=RuleType.RETRY_STRATEGY,
                    condition={"error_pattern": pattern, "model_pattern": model_id.split("/")[-1]},
                    action=action,
                    confidence=min(0.8, MIN_CONFIDENCE_INIT + count * 0.05),
                    source="evolver_error_analysis",
                    explanation=(
                        f"Model '{model_id.split('/')[-1]}' mengalami error "
                        f"'{label}' sebanyak {count}x."
                    ),
                )
                rules.append(rule)
                insights.append(f"🔧 Error pattern '{label}' terdeteksi {count}x di {model_id.split('/')[-1]}")
        return rules, insights

    def _analyze_decomposition(
        self, task_patterns: List[dict]
    ) -> Tuple[List[EvolutionRule], List[str]]:
        rules, insights = [], []
        simple_but_failed = [p for p in task_patterns if p.get("is_simple") and p.get("had_error")]
        by_intent: Dict[str, List[dict]] = defaultdict(list)
        for p in simple_but_failed:
            by_intent[p["primary_intent"]].append(p)

        for intent, cases in by_intent.items():
            if len(cases) < MIN_SAMPLES:
                continue
            avg_complexity = sum(c["complexity_score"] for c in cases) / len(cases)
            rule_id = f"dt_{intent}_{int(time.time())}"
            rule = EvolutionRule(
                id=rule_id, rule_type=RuleType.DECOMPOSE_THRESHOLD,
                condition={"task_type": intent, "min_complexity": round(avg_complexity - 0.1, 2)},
                action={"force_decompose": True, "reason": f"{len(cases)} task '{intent}' gagal meski ditandai simple"},
                confidence=MIN_CONFIDENCE_INIT, source="evolver_decomp_analysis",
                explanation=f"Task '{intent}' dengan complexity ≥{avg_complexity - 0.1:.2f} sering gagal jika tidak di-decompose ({len(cases)} kasus).",
            )
            rules.append(rule)
            insights.append(f"📋 Task '{intent}' dengan complexity >{avg_complexity - 0.1:.2f} sebaiknya selalu di-decompose")
        return rules, insights

    def _analyze_latency(
        self, groups: List[PerformanceGroup]
    ) -> Tuple[List[EvolutionRule], List[str]]:
        rules, insights = [], []
        for g in groups:
            if g.total < MIN_SAMPLES or g.avg_latency_ms <= LATENCY_WARN_MS or g.win_rate < 0.5:
                continue
            rule_id = f"lat_{g.task_type}_{g.model_id.split('/')[-1]}_{int(time.time())}"
            rule = EvolutionRule(
                id=rule_id, rule_type=RuleType.MODEL_PREFERENCE,
                condition={"task_type": g.task_type, "quality_priority": "speed", "model_pattern": g.model_id.split("/")[-1]},
                action={"avoid_model": g.model_id, "penalty": 0.15, "reason": "latency_too_high"},
                confidence=0.50, source="evolver_latency_analysis",
                explanation=f"Model '{g.model_id.split('/')[-1]}' rata-rata {g.avg_latency_ms:.0f}ms untuk task '{g.task_type}' (threshold: {LATENCY_WARN_MS}ms).",
            )
            rules.append(rule)
            insights.append(f"⏱️ {g.model_id.split('/')[-1]} lambat untuk '{g.task_type}': avg {g.avg_latency_ms:.0f}ms")
        return rules, insights

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def _cleanup_stale_rules(self, groups: List[PerformanceGroup]) -> int:
        deprecated = 0
        try:
            from core.model_manager import model_manager
            available = set(model_manager.available_models.keys())
            active_rules = await evolution_store.get_active_rules()
            for rule in active_rules:
                if rule.rule_type == RuleType.MODEL_PREFERENCE:
                    prefer = rule.action.get("prefer_model", "")
                    avoid  = rule.action.get("avoid_model", "")
                    if prefer and prefer not in available:
                        await evolution_store.deprecate_rule(rule.id, f"Model {prefer} tidak lagi tersedia")
                        deprecated += 1
                        continue
                    if avoid and avoid not in available:
                        await evolution_store.deprecate_rule(rule.id, f"Avoid model {avoid} tidak lagi tersedia")
                        deprecated += 1
        except Exception as e:
            log.warning("Evolver: cleanup error", error=str(e)[:80])
        return deprecated

    def _suggest_better_agent(self, task_type: str, current_agent: str) -> Optional[str]:
        TASK_AGENT_MAP = {
            "coding": "coding", "system": "system", "file_operation": "system",
            "research": "research", "writing": "writing", "creative": "creative",
            "analysis": "reasoning", "planning": "reasoning", "general": "general",
            "image_generation": "image_gen", "audio_generation": "audio_gen", "vision": "vision",
        }
        better = TASK_AGENT_MAP.get(task_type)
        if better and better != current_agent:
            return better
        return None


# ── Background Daemon ─────────────────────────────────────────────────────────

class CapabilityEvolverDaemon:
    def __init__(self, interval_minutes: int = 30):
        self._interval = interval_minutes * 60
        self._task: Optional[asyncio.Task] = None
        self._evolver = CapabilityEvolver()

    def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="capability_evolver")
        log.info("CapabilityEvolver daemon started", interval_min=self._interval // 60)

    def stop(self):
        if self._task:
            self._task.cancel()

    async def evolve_now(self, force: bool = True) -> dict:
        return await self._evolver.evolve(force=force)

    async def get_rules_for_scoring(self, task_type, agent_type, model_id):
        return await self._evolver.apply_rules_to_scoring(task_type, agent_type, model_id)

    async def get_prompt_patches(self, task_type: str) -> List[str]:
        return await self._evolver.get_prompt_patches(task_type)

    async def get_retry_strategy(self, error_message: str, model_id: str):
        return await self._evolver.get_retry_strategy(error_message, model_id)

    def get_status(self) -> dict:
        return {
            **self._evolver.get_status(),
            "interval_minutes": self._interval // 60,
            "task_running": self._task is not None and not self._task.done(),
        }

    async def _loop(self):
        await asyncio.sleep(120)  # delay awal
        while True:
            try:
                await self._evolver.evolve()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("CapabilityEvolver loop error", error=str(e)[:100])
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break


capability_evolver = CapabilityEvolverDaemon(interval_minutes=30)

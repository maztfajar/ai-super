"""
AI ORCHESTRATOR — Evolution Store (v1.0)
=========================================
Persistence layer untuk EvolutionRule.
Menyimpan, mengambil, dan mengelola lifecycle rules yang dipelajari
oleh Capability Evolver.

Rule lifecycle: proposed → active → deprecated
Setiap rule memiliki win/loss tracking untuk self-calibration.
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import structlog

log = structlog.get_logger()


class RuleType(str, Enum):
    """Jenis-jenis EvolutionRule."""
    MODEL_PREFERENCE    = "model_preference"      # Model X lebih baik dari Y untuk task Z
    ROUTING_OVERRIDE    = "routing_override"       # Redirect agent A ke agent B untuk task Z
    RETRY_STRATEGY      = "retry_strategy"         # Jika error X di model Y → strategy Z
    DECOMPOSE_THRESHOLD = "decompose_threshold"    # Task type Z harus selalu di-decompose
    PROMPT_PATCH        = "prompt_patch"            # Tambahkan instruksi ke prompt untuk task Z
    COMPLEXITY_CALIBRATION = "complexity_calibration"  # Kalibrasi ulang threshold complexity


class RuleStatus(str, Enum):
    """Status lifecycle rule."""
    PROPOSED   = "proposed"     # Baru dibuat, belum aktif
    ACTIVE     = "active"       # Aktif dan digunakan dalam scoring/routing
    DEPRECATED = "deprecated"   # Tidak lagi relevan atau terbukti salah


@dataclass
class EvolutionRule:
    """
    Satu unit pelajaran yang dipelajari oleh Capability Evolver.
    """
    id: str = ""
    rule_type: RuleType = RuleType.MODEL_PREFERENCE
    condition: Dict = field(default_factory=dict)   # Kapan rule berlaku
    action: Dict = field(default_factory=dict)       # Apa yang dilakukan
    confidence: float = 0.5                          # 0.0 - 1.0
    wins: int = 0                                    # Berapa kali terbukti benar
    losses: int = 0                                  # Berapa kali terbukti salah
    status: RuleStatus = RuleStatus.PROPOSED
    source: str = ""                                  # Sumber rule (evolver_v1, manual, dll)
    explanation: str = ""                             # Penjelasan human-readable
    created_at: float = 0.0
    updated_at: float = 0.0
    last_used_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.last_used_at:
            self.last_used_at = now

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.5

    @property
    def total_uses(self) -> int:
        return self.wins + self.losses

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "rule_type":    self.rule_type.value if isinstance(self.rule_type, RuleType) else self.rule_type,
            "condition":    self.condition,
            "action":       self.action,
            "confidence":   round(self.confidence, 3),
            "wins":         self.wins,
            "losses":       self.losses,
            "win_rate":     round(self.win_rate, 3),
            "total_uses":   self.total_uses,
            "status":       self.status.value if isinstance(self.status, RuleStatus) else self.status,
            "source":       self.source,
            "explanation":  self.explanation,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
            "last_used_at": self.last_used_at,
        }


# ── Threshold untuk auto-deprecation ─────────────────────────────────────────
MIN_USES_FOR_DEPRECATION = 5     # Minimal pakai sebelum bisa di-deprecate
DEPRECATION_WIN_RATE     = 0.30  # Win rate di bawah ini → auto-deprecate


class EvolutionStore:
    """
    In-memory + DB persistence store untuk EvolutionRules.
    Thread-safe melalui single-threaded asyncio event loop.
    """

    def __init__(self):
        # In-memory cache: {rule_id: EvolutionRule}
        self._rules: Dict[str, EvolutionRule] = {}
        self._loaded: bool = False

    # ── Public API ────────────────────────────────────────────────────────────

    async def add_rule(self, rule: EvolutionRule) -> bool:
        """
        Tambahkan rule baru. Return True jika berhasil (tidak duplikat).
        Cek duplikat berdasarkan (rule_type, condition) yang sama.
        """
        # Cek duplikat
        for existing in self._rules.values():
            if (existing.rule_type == rule.rule_type and
                existing.condition == rule.condition and
                existing.status != RuleStatus.DEPRECATED):
                # Update confidence jika rule baru lebih tinggi
                if rule.confidence > existing.confidence:
                    existing.confidence = rule.confidence
                    existing.explanation = rule.explanation
                    existing.updated_at = time.time()
                    await self._persist_rule(existing)
                    log.debug("Evolution rule updated (higher confidence)",
                              rule_id=existing.id, confidence=existing.confidence)
                return False

        self._rules[rule.id] = rule
        await self._persist_rule(rule)
        log.info("Evolution rule added",
                 rule_id=rule.id, type=rule.rule_type.value if isinstance(rule.rule_type, RuleType) else rule.rule_type,
                 confidence=rule.confidence)
        return True

    async def activate_rule(self, rule_id: str) -> bool:
        """Aktivasi rule (proposed → active)."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        if rule.status == RuleStatus.DEPRECATED:
            return False
        rule.status = RuleStatus.ACTIVE
        rule.updated_at = time.time()
        await self._persist_rule(rule)
        log.info("Evolution rule activated", rule_id=rule_id)
        return True

    async def deprecate_rule(self, rule_id: str, reason: str = "") -> bool:
        """Deprecated rule (active → deprecated)."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.status = RuleStatus.DEPRECATED
        rule.updated_at = time.time()
        if reason:
            rule.explanation += f" [DEPRECATED: {reason}]"
        await self._persist_rule(rule)
        log.info("Evolution rule deprecated", rule_id=rule_id, reason=reason)
        return True

    async def update_rule_outcome(self, rule_id: str, success: bool) -> None:
        """
        Update win/loss tracking setelah rule digunakan.
        Auto-deprecate jika win rate terlalu rendah.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return

        if success:
            rule.wins += 1
            # Boost confidence sedikit setiap kali berhasil
            rule.confidence = min(0.95, rule.confidence + 0.02)
        else:
            rule.losses += 1
            # Turunkan confidence setiap kali gagal
            rule.confidence = max(0.1, rule.confidence - 0.05)

        rule.last_used_at = time.time()
        rule.updated_at = time.time()

        # Auto-deprecate jika win rate terlalu rendah setelah cukup banyak penggunaan
        if (rule.total_uses >= MIN_USES_FOR_DEPRECATION and
            rule.win_rate < DEPRECATION_WIN_RATE):
            rule.status = RuleStatus.DEPRECATED
            rule.explanation += (
                f" [AUTO-DEPRECATED: win_rate {rule.win_rate:.0%} "
                f"setelah {rule.total_uses} penggunaan]"
            )
            log.info("Evolution rule auto-deprecated",
                     rule_id=rule_id, win_rate=rule.win_rate,
                     uses=rule.total_uses)

        await self._persist_rule(rule)

    async def get_rules_for_context(
        self,
        task_type: str = "",
        agent_type: str = "",
        model_id: str = "",
        min_confidence: float = 0.5,
    ) -> List[EvolutionRule]:
        """
        Ambil semua active rules yang relevan untuk konteks tertentu.
        """
        await self._ensure_loaded()
        matched = []
        for rule in self._rules.values():
            if rule.status != RuleStatus.ACTIVE:
                continue
            if rule.confidence < min_confidence:
                continue

            cond = rule.condition
            # Match task_type
            cond_task = cond.get("task_type", "*")
            if cond_task != "*" and task_type and cond_task != task_type:
                continue

            # Match agent_type (jika ada di condition)
            cond_agent = cond.get("agent_type", "")
            if cond_agent and agent_type and cond_agent != agent_type:
                continue

            # Match model_pattern (jika ada)
            cond_model = cond.get("model_pattern", "")
            if cond_model and model_id and cond_model not in model_id:
                continue

            matched.append(rule)

        return matched

    async def get_active_rules(
        self,
        rule_type: Optional[RuleType] = None,
        min_confidence: float = 0.0,
    ) -> List[EvolutionRule]:
        """Ambil semua active rules, opsional filter by type."""
        await self._ensure_loaded()
        results = []
        for rule in self._rules.values():
            if rule.status != RuleStatus.ACTIVE:
                continue
            if rule.confidence < min_confidence:
                continue
            if rule_type and rule.rule_type != rule_type:
                continue
            results.append(rule)
        return results

    def list_rules_sync(self) -> List[dict]:
        """Sinkron: list semua rules sebagai dict (untuk API)."""
        return [r.to_dict() for r in self._rules.values()]

    async def get_all_stats(self) -> dict:
        """Statistik lengkap store."""
        await self._ensure_loaded()
        stats = {
            "total_rules": len(self._rules),
            "by_status": {},
            "by_type": {},
            "avg_confidence": 0.0,
            "total_wins": 0,
            "total_losses": 0,
        }

        confidences = []
        for rule in self._rules.values():
            # By status
            status_key = rule.status.value if isinstance(rule.status, RuleStatus) else rule.status
            stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1

            # By type
            type_key = rule.rule_type.value if isinstance(rule.rule_type, RuleType) else rule.rule_type
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            confidences.append(rule.confidence)
            stats["total_wins"] += rule.wins
            stats["total_losses"] += rule.losses

        if confidences:
            stats["avg_confidence"] = round(sum(confidences) / len(confidences), 3)

        return stats

    # ── Persistence (DB) ──────────────────────────────────────────────────────

    async def _ensure_loaded(self):
        """Lazy load dari DB saat pertama kali dibutuhkan."""
        if self._loaded:
            return
        try:
            await self._load_from_db()
        except Exception as e:
            log.warning("EvolutionStore: failed to load from DB", error=str(e)[:100])
        self._loaded = True

    async def _load_from_db(self):
        """Load semua rules dari database ke memory."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import EvolutionRuleModel
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(EvolutionRuleModel))
                records = result.scalars().all()

            for rec in records:
                rule = EvolutionRule(
                    id=rec.id,
                    rule_type=RuleType(rec.rule_type) if rec.rule_type in [e.value for e in RuleType] else RuleType.MODEL_PREFERENCE,
                    condition=json.loads(rec.condition_json or "{}"),
                    action=json.loads(rec.action_json or "{}"),
                    confidence=rec.confidence,
                    wins=rec.wins,
                    losses=rec.losses,
                    status=RuleStatus(rec.status) if rec.status in [e.value for e in RuleStatus] else RuleStatus.PROPOSED,
                    source=rec.source or "",
                    explanation=rec.explanation or "",
                    created_at=rec.created_at.timestamp() if rec.created_at else time.time(),
                    updated_at=rec.updated_at.timestamp() if rec.updated_at else time.time(),
                    last_used_at=rec.last_used_at.timestamp() if rec.last_used_at else time.time(),
                )
                self._rules[rule.id] = rule

            log.info("EvolutionStore loaded from DB", rules=len(self._rules))

        except Exception as e:
            log.warning("EvolutionStore: DB load failed", error=str(e)[:100])

    async def _persist_rule(self, rule: EvolutionRule):
        """Simpan atau update satu rule ke database."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import EvolutionRuleModel
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                # Cek apakah sudah ada
                result = await db.execute(
                    select(EvolutionRuleModel).where(EvolutionRuleModel.id == rule.id)
                )
                existing = result.scalars().first()

                now = datetime.now(timezone.utc).replace(tzinfo=None)

                if existing:
                    # Update
                    existing.rule_type = rule.rule_type.value if isinstance(rule.rule_type, RuleType) else rule.rule_type
                    existing.condition_json = json.dumps(rule.condition, ensure_ascii=False)
                    existing.action_json = json.dumps(rule.action, ensure_ascii=False)
                    existing.confidence = rule.confidence
                    existing.wins = rule.wins
                    existing.losses = rule.losses
                    existing.status = rule.status.value if isinstance(rule.status, RuleStatus) else rule.status
                    existing.source = rule.source
                    existing.explanation = rule.explanation
                    existing.updated_at = now
                    existing.last_used_at = now
                    db.add(existing)
                else:
                    # Insert baru
                    db_rule = EvolutionRuleModel(
                        id=rule.id,
                        rule_type=rule.rule_type.value if isinstance(rule.rule_type, RuleType) else rule.rule_type,
                        condition_json=json.dumps(rule.condition, ensure_ascii=False),
                        action_json=json.dumps(rule.action, ensure_ascii=False),
                        confidence=rule.confidence,
                        wins=rule.wins,
                        losses=rule.losses,
                        status=rule.status.value if isinstance(rule.status, RuleStatus) else rule.status,
                        source=rule.source,
                        explanation=rule.explanation,
                        created_at=now,
                        updated_at=now,
                        last_used_at=now,
                    )
                    db.add(db_rule)

                await db.commit()

        except Exception as e:
            log.warning("EvolutionStore: persist failed", rule_id=rule.id, error=str(e)[:100])


# Global singleton
evolution_store = EvolutionStore()

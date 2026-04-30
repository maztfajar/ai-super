"""
Error Recovery Engine (v2.1 — Performance Optimized)
=====================================================
Perbaikan dari v1:
  1. _find_alternative_model(): pilih berdasarkan task_type + MODEL_CAPABILITY_MAP
     (bukan random model pertama yang tersedia)
  2. execute_with_recovery(): backoff lebih cerdas — immediate retry untuk transient,
     slow retry untuk recoverable
  3. CircuitBreakerState: half_open_after dikurangi 300s → 120s (lebih cepat recover)
  4. Tambah _classify_error() untuk bedakan transient vs fatal di level recovery
  5. get_health_status() return info yang lebih berguna untuk monitoring
  6. Tambah reset_circuit_breaker() untuk manual reset via API
"""

import time
import asyncio
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog

log = structlog.get_logger()


class RecoveryStrategy(Enum):
    RETRY_SAME            = "retry_same"
    RETRY_DIFFERENT_PARAMS = "retry_diff_params"
    ALTERNATIVE_MODEL     = "alternative_model"
    SKIP                  = "skip"


@dataclass
class CircuitBreakerState:
    model_id: str
    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False
    half_open_after: float = 120.0   # PERBAIKAN: 300s → 120s (2 menit)
    failure_threshold: int = 3

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            log.warning("Circuit breaker OPENED", model=self.model_id,
                        failures=self.failure_count)

    def record_success(self):
        self.failure_count = 0
        self.is_open = False

    def should_allow(self) -> bool:
        if not self.is_open:
            return True
        elapsed = time.time() - self.last_failure_time
        if elapsed > self.half_open_after:
            log.info("Circuit breaker HALF-OPEN", model=self.model_id)
            return True
        return False

    @property
    def remaining_cooldown(self) -> float:
        if not self.is_open:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.half_open_after - elapsed)


@dataclass
class RecoveryAttempt:
    strategy: RecoveryStrategy
    model_used: str
    success: bool
    error: Optional[str] = None
    attempt_number: int = 0
    time_ms: int = 0


# ── Error classifier ─────────────────────────────────────────────────────────

def _classify_recovery_error(err_str: str) -> str:
    """
    Klasifikasi error untuk strategi recovery.
    Returns: 'fatal' | 'transient' | 'recoverable'
    """
    err_lower = err_str.lower()

    fatal = [
        "401", "unauthorized", "invalid_api_key", "authentication",
        "403", "forbidden", "overdue balance", "insufficient_quota",
        "billing", "account deactivated", "model not found",
        "invalid model", "model_not_found",
    ]
    if any(s in err_lower for s in fatal):
        return "fatal"

    transient = [
        "timeout", "timed out", "connection", "network",
        "rate limit", "429", "too many requests",
        "model output must contain", "output text or tool calls",
        "cannot both be empty", "502", "503", "504",
        "gateway", "overloaded", "capacity", "empty",
    ]
    if any(s in err_lower for s in transient):
        return "transient"

    return "recoverable"


# ── Task type → required capability tags ────────────────────────────────────
_TASK_CAPABILITY_NEEDS: Dict[str, List[str]] = {
    "coding":          ["coding"],
    "system":          ["coding"],
    "file_operation":  ["coding"],
    "reasoning":       ["reasoning"],
    "analysis":        ["reasoning", "text"],
    "research":        ["text"],
    "writing":         ["writing", "text"],
    "creative":        ["text"],
    "planning":        ["reasoning"],
    "image_generation": ["image_gen"],
    "audio_generation": ["tts"],
    "vision":          ["vision"],
    "multimodal":      ["vision"],
    "general":         ["text", "speed"],
}


class ErrorRecoveryEngine:

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._recovery_history: List[RecoveryAttempt] = []
        self._max_history = 500

    # ── Circuit breaker API ──────────────────────────────────────────────────

    def get_circuit_breaker(self, model_id: str) -> CircuitBreakerState:
        if model_id not in self._circuit_breakers:
            self._circuit_breakers[model_id] = CircuitBreakerState(model_id=model_id)
        return self._circuit_breakers[model_id]

    def is_model_available(self, model_id: str) -> bool:
        return self.get_circuit_breaker(model_id).should_allow()

    def record_success(self, model_id: str):
        self.get_circuit_breaker(model_id).record_success()

    def record_failure(self, model_id: str, error: str = ""):
        cb = self.get_circuit_breaker(model_id)
        cb.record_failure()
        log.warning("Model failure recorded",
                    model=model_id, failures=cb.failure_count, open=cb.is_open)

    def reset_circuit_breaker(self, model_id: str):
        """Manual reset — untuk endpoint admin."""
        if model_id in self._circuit_breakers:
            self._circuit_breakers[model_id].record_success()
            log.info("Circuit breaker manually reset", model=model_id)

    # ── Main recovery loop ──────────────────────────────────────────────────

    async def execute_with_recovery(
        self,
        execute_fn: Callable,
        model_id: str,
        task_type: str = "",
        max_retries: int = 3,
        **kwargs,
    ) -> Tuple[Optional[str], List[RecoveryAttempt]]:
        """
        Eksekusi fungsi dengan auto-recovery.
        Returns (result, attempts_list).

        Recovery order:
          0 → retry same (immediate, backoff kecil)
          1 → retry dengan params berbeda (temperature↓, tokens↑)
          2 → coba model alternatif yang sesuai task_type
        """
        attempts: List[RecoveryAttempt] = []

        for attempt_num in range(max_retries):
            strategy     = self._decide_strategy(attempt_num, model_id)
            current_model = model_id
            current_kwargs = dict(kwargs)

            if strategy == RecoveryStrategy.RETRY_DIFFERENT_PARAMS:
                # Turunkan temperature, naikkan max_tokens
                current_kwargs["temperature"] = max(
                    0.1, current_kwargs.get("temperature", 0.7) - 0.3
                )
                current_kwargs["max_tokens"] = min(
                    8192, current_kwargs.get("max_tokens", 4096) + 2048
                )

            elif strategy == RecoveryStrategy.ALTERNATIVE_MODEL:
                alt = self._find_alternative_model(model_id, task_type)
                if alt:
                    current_model = alt
                    log.info("Switching model",
                             from_model=model_id, to_model=alt, task=task_type)

            # Cek circuit breaker
            if not self.is_model_available(current_model):
                log.warning("Circuit broken — trying alternative", model=current_model)
                alt = self._find_alternative_model(current_model, task_type)
                if alt:
                    current_model = alt
                else:
                    log.error("No available model found", original=model_id)
                    continue

            # Backoff delay
            if attempt_num > 0:
                err_type = _classify_recovery_error(
                    attempts[-1].error or "" if attempts else ""
                )
                if err_type == "transient":
                    delay = 1.0   # transient → retry cepat
                else:
                    delay = min(30, 2 ** attempt_num)   # recoverable → exponential
                log.info(f"Retry {attempt_num + 1}/{max_retries}",
                         model=current_model, delay=delay, strategy=strategy.value)
                await asyncio.sleep(delay)

            start = time.time()
            try:
                result = await execute_fn(model=current_model, **current_kwargs)
                self.record_success(current_model)

                attempt = RecoveryAttempt(
                    strategy=strategy,
                    model_used=current_model,
                    success=True,
                    attempt_number=attempt_num,
                    time_ms=int((time.time() - start) * 1000),
                )
                attempts.append(attempt)
                self._record_attempt(attempt)
                return result, attempts

            except Exception as e:
                err_str = str(e)[:200]
                err_type = _classify_recovery_error(err_str)
                self.record_failure(current_model, err_str)

                attempt = RecoveryAttempt(
                    strategy=strategy,
                    model_used=current_model,
                    success=False,
                    error=err_str,
                    attempt_number=attempt_num,
                    time_ms=int((time.time() - start) * 1000),
                )
                attempts.append(attempt)
                self._record_attempt(attempt)

                log.warning(f"Attempt {attempt_num + 1} failed",
                            strategy=strategy.value, model=current_model,
                            error_type=err_type, error=err_str[:80])

                # Fatal error → stop immediately, jangan retry
                if err_type == "fatal":
                    log.error("Fatal error — stopping recovery", model=current_model)
                    break

        log.error("All recovery attempts exhausted", model=model_id, attempts=len(attempts))
        return None, attempts

    # ── Strategy & model selection ───────────────────────────────────────────

    def _decide_strategy(self, attempt_num: int, model_id: str) -> RecoveryStrategy:
        if attempt_num == 0:
            return RecoveryStrategy.RETRY_SAME
        elif attempt_num == 1:
            return RecoveryStrategy.RETRY_DIFFERENT_PARAMS
        else:
            return RecoveryStrategy.ALTERNATIVE_MODEL

    def _find_alternative_model(
        self,
        current_model: str,
        task_type: str = "",
    ) -> Optional[str]:
        """
        PERBAIKAN: pilih model alternatif berdasarkan task_type + capability,
        bukan random model pertama yang tersedia.
        """
        from core.model_manager import model_manager
        from agents.agent_registry import MODEL_CAPABILITY_MAP

        # Capability yang dibutuhkan untuk task_type ini
        required_caps = set(_TASK_CAPABILITY_NEEDS.get(task_type, ["text"]))

        available = model_manager.available_models
        scored: List[Tuple[float, str]] = []

        for model_id in available:
            if model_id == current_model:
                continue
            if not self.is_model_available(model_id):
                continue

            model_caps = set(MODEL_CAPABILITY_MAP.get(model_id, []))
            # Score: berapa required caps yang dipenuhi
            overlap = len(required_caps & model_caps) if model_caps else 0
            # Bonus jika punya "speed" (fallback model biasanya lebih stabil)
            bonus = 0.5 if "speed" in model_caps else 0.0
            score = overlap + bonus
            scored.append((score, model_id))

        if not scored:
            return None

        # Pilih yang paling cocok
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_model = scored[0]

        log.debug("Alternative model selected",
                  original=current_model,
                  alternative=best_model,
                  score=best_score,
                  task=task_type)
        return best_model

    # ── History & monitoring ─────────────────────────────────────────────────

    def _record_attempt(self, attempt: RecoveryAttempt):
        self._recovery_history.append(attempt)
        if len(self._recovery_history) > self._max_history:
            self._recovery_history = self._recovery_history[-self._max_history:]

    def get_health_status(self) -> Dict:
        """Health status semua model — untuk monitoring dashboard."""
        from core.model_manager import model_manager

        status = {}
        for model_id in model_manager.available_models:
            cb = self.get_circuit_breaker(model_id)
            status[model_id] = {
                "available":         cb.should_allow(),
                "circuit_open":      cb.is_open,
                "failure_count":     cb.failure_count,
                "cooldown_remaining": round(cb.remaining_cooldown, 1),
            }
        return status

    def get_recovery_stats(self) -> Dict:
        if not self._recovery_history:
            return {"total_attempts": 0, "success_rate": 0.0, "strategy_breakdown": {}}

        total     = len(self._recovery_history)
        successes = sum(1 for a in self._recovery_history if a.success)
        by_model  = {}
        for a in self._recovery_history:
            if a.model_used not in by_model:
                by_model[a.model_used] = {"attempts": 0, "successes": 0}
            by_model[a.model_used]["attempts"] += 1
            if a.success:
                by_model[a.model_used]["successes"] += 1

        return {
            "total_attempts":    total,
            "success_rate":      round(successes / total, 3) if total else 0.0,
            "strategy_breakdown": {
                s.value: sum(1 for a in self._recovery_history if a.strategy == s)
                for s in RecoveryStrategy
            },
            "per_model": by_model,
        }


error_recovery = ErrorRecoveryEngine()

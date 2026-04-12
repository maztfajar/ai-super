"""
Super Agent Orchestrator — Error Recovery Engine
Automated error detection and multi-strategy recovery.
Implements circuit breaker pattern and graceful degradation.
"""
import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

log = structlog.get_logger()


class RecoveryStrategy(Enum):
    RETRY_SAME = "retry_same"                    # Retry same agent/model
    RETRY_DIFFERENT_PARAMS = "retry_diff_params"  # Same agent, different temp/tokens
    ALTERNATIVE_AGENT = "alternative_agent"       # Different agent type
    ALTERNATIVE_MODEL = "alternative_model"       # Same agent, different model
    ENSEMBLE = "ensemble"                         # Try multiple agents
    DECOMPOSE_FURTHER = "decompose_further"       # Break task into smaller parts
    ESCALATE_USER = "escalate_user"              # Ask user for help
    SKIP = "skip"                                 # Skip this subtask (non-critical)


@dataclass
class CircuitBreakerState:
    """Track failure state for a model to implement circuit breaker pattern."""
    model_id: str
    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False                 # True = broken, skip this model
    half_open_after: float = 300.0        # seconds before trying again (5 min)
    failure_threshold: int = 3            # failures before opening circuit

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
        """Check if we should try this model (circuit breaker logic)."""
        if not self.is_open:
            return True
        # Check if enough time has passed for half-open state
        elapsed = time.time() - self.last_failure_time
        if elapsed > self.half_open_after:
            log.info("Circuit breaker HALF-OPEN, allowing test request",
                      model=self.model_id)
            return True
        return False


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt."""
    strategy: RecoveryStrategy
    model_used: str
    success: bool
    error: Optional[str] = None
    attempt_number: int = 0
    time_ms: int = 0


class ErrorRecoveryEngine:
    """
    Handles automatic error detection and recovery.
    Implements: retry with backoff, alternative agents, circuit breaker,
    and graceful degradation.
    """

    def __init__(self):
        # Circuit breakers per model
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        # Recovery history for learning
        self._recovery_history: List[RecoveryAttempt] = []
        self._max_history = 500

    def get_circuit_breaker(self, model_id: str) -> CircuitBreakerState:
        """Get or create circuit breaker for a model."""
        if model_id not in self._circuit_breakers:
            self._circuit_breakers[model_id] = CircuitBreakerState(model_id=model_id)
        return self._circuit_breakers[model_id]

    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available (not circuit-broken)."""
        cb = self.get_circuit_breaker(model_id)
        return cb.should_allow()

    def record_success(self, model_id: str):
        """Record a successful execution — resets circuit breaker."""
        cb = self.get_circuit_breaker(model_id)
        cb.record_success()

    def record_failure(self, model_id: str, error: str = ""):
        """Record a failed execution — updates circuit breaker."""
        cb = self.get_circuit_breaker(model_id)
        cb.record_failure()
        log.warning("Model failure recorded", model=model_id,
                     failures=cb.failure_count, circuit_open=cb.is_open)

    async def execute_with_recovery(
        self,
        execute_fn: Callable,
        model_id: str,
        task_type: str = "",
        max_retries: int = 3,
        **kwargs,
    ) -> tuple:
        """
        Execute a function with automatic recovery on failure.
        Returns (result, attempts_list).

        Recovery order:
        1. Retry same model with backoff
        2. Retry with different parameters
        3. Try alternative model
        4. Return error
        """
        attempts: List[RecoveryAttempt] = []

        for attempt_num in range(max_retries):
            strategy = self._decide_strategy(attempt_num, model_id)
            current_model = model_id

            # Adjust based on strategy
            if strategy == RecoveryStrategy.RETRY_DIFFERENT_PARAMS:
                # Modify kwargs for different params (lower temperature, more tokens)
                kwargs = dict(kwargs)
                kwargs["temperature"] = max(0.1, kwargs.get("temperature", 0.7) - 0.3)
                kwargs["max_tokens"] = min(8192, kwargs.get("max_tokens", 4096) + 2048)

            elif strategy == RecoveryStrategy.ALTERNATIVE_MODEL:
                # Find alternative model
                alt = self._find_alternative_model(model_id, task_type)
                if alt:
                    current_model = alt
                    log.info("Switching to alternative model", original=model_id, alternative=alt)

            # Check circuit breaker
            if not self.is_model_available(current_model):
                log.warning("Model circuit-broken, skipping", model=current_model)
                alt = self._find_alternative_model(current_model, task_type)
                if alt:
                    current_model = alt
                else:
                    continue

            start = time.time()
            try:
                # Exponential backoff for retries
                if attempt_num > 0:
                    delay = min(30, 2 ** attempt_num)
                    log.info(f"Retry attempt {attempt_num + 1}, waiting {delay}s",
                              model=current_model)
                    await asyncio.sleep(delay)

                result = await execute_fn(model=current_model, **kwargs)

                # Success
                self.record_success(current_model)
                elapsed = int((time.time() - start) * 1000)
                attempt = RecoveryAttempt(
                    strategy=strategy,
                    model_used=current_model,
                    success=True,
                    attempt_number=attempt_num,
                    time_ms=elapsed,
                )
                attempts.append(attempt)
                self._record_attempt(attempt)
                return result, attempts

            except Exception as e:
                elapsed = int((time.time() - start) * 1000)
                error_str = str(e)[:200]
                self.record_failure(current_model, error_str)

                attempt = RecoveryAttempt(
                    strategy=strategy,
                    model_used=current_model,
                    success=False,
                    error=error_str,
                    attempt_number=attempt_num,
                    time_ms=elapsed,
                )
                attempts.append(attempt)
                self._record_attempt(attempt)
                log.warning(f"Attempt {attempt_num + 1} failed",
                             strategy=strategy.value,
                             model=current_model,
                             error=error_str[:100])

        # All retries exhausted
        log.error("All recovery attempts exhausted",
                   model=model_id, attempts=len(attempts))
        return None, attempts

    def _decide_strategy(self, attempt_num: int, model_id: str) -> RecoveryStrategy:
        """Decide which recovery strategy to use based on attempt number."""
        if attempt_num == 0:
            return RecoveryStrategy.RETRY_SAME
        elif attempt_num == 1:
            return RecoveryStrategy.RETRY_DIFFERENT_PARAMS
        else:
            return RecoveryStrategy.ALTERNATIVE_MODEL

    def _find_alternative_model(self, current_model: str,
                                  task_type: str = "") -> Optional[str]:
        """Find an alternative model that's available."""
        from core.model_manager import model_manager

        for model_id in model_manager.available_models:
            if model_id == current_model:
                continue
            if not self.is_model_available(model_id):
                continue
            return model_id

        return None

    def _record_attempt(self, attempt: RecoveryAttempt):
        """Record attempt for learning."""
        self._recovery_history.append(attempt)
        if len(self._recovery_history) > self._max_history:
            self._recovery_history = self._recovery_history[-self._max_history:]

    def get_health_status(self) -> Dict:
        """Get health status of all models (for monitoring)."""
        status = {}
        for model_id, cb in self._circuit_breakers.items():
            status[model_id] = {
                "failures": cb.failure_count,
                "circuit_open": cb.is_open,
                "available": cb.should_allow(),
            }
        return status

    def get_recovery_stats(self) -> Dict:
        """Get recovery statistics."""
        if not self._recovery_history:
            return {"total_attempts": 0, "success_rate": 0.0}

        total = len(self._recovery_history)
        successes = sum(1 for a in self._recovery_history if a.success)
        return {
            "total_attempts": total,
            "success_rate": successes / total if total else 0,
            "strategy_breakdown": {
                s.value: sum(1 for a in self._recovery_history if a.strategy == s)
                for s in RecoveryStrategy
            },
        }


error_recovery = ErrorRecoveryEngine()

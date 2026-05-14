"""
Error Recovery Engine (v3.0 — Per-Tool Circuit Breaker + Actionable Errors)
===========================================================================
Perbaikan dari v2.1:
  1. ToolCircuitBreaker: circuit breaker per-tool (bukan hanya per-model).
     Jika tool gagal 3x beruntun, auto-suspend sementara + fallback.
  2. ActionableErrorTranslator: terjemahkan error mentah menjadi pesan
     yang bisa langsung ditindaklanjuti user.
  3. ExponentialBackoff terpisah: delay 1s → 2s → 4s → 8s (max 30s)
  4. Dead Letter Queue helper: tandai task ke DLQ jika semua recovery gagal.
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Circuit Breaker — Per Model
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CircuitBreakerState:
    model_id: str
    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False
    half_open_after: float = 120.0   # 2 menit cooldown
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Circuit Breaker — Per Tool
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolCircuitBreaker:
    """
    Melacak kegagalan per-tool (execute_bash, write_file, dll).
    Jika tool gagal 3x beruntun, tool disuspend sementara.
    """
    tool_name: str
    failure_count: int = 0
    last_failure_time: float = 0.0
    is_suspended: bool = False
    suspend_duration: float = 60.0    # suspend selama 60 detik
    failure_threshold: int = 3
    total_failures: int = 0           # lifetime counter

    def record_failure(self, error: str = ""):
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_suspended = True
            log.warning("Tool circuit breaker SUSPENDED",
                        tool=self.tool_name,
                        failures=self.failure_count,
                        suspend_sec=self.suspend_duration)

    def record_success(self):
        self.failure_count = 0
        self.is_suspended = False

    def should_allow(self) -> bool:
        if not self.is_suspended:
            return True
        elapsed = time.time() - self.last_failure_time
        if elapsed > self.suspend_duration:
            log.info("Tool circuit breaker RESUMED", tool=self.tool_name)
            self.is_suspended = False
            self.failure_count = 0
            return True
        return False

    @property
    def remaining_suspend(self) -> float:
        if not self.is_suspended:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.suspend_duration - elapsed)


# ═══════════════════════════════════════════════════════════════════════════════
#  Actionable Error Translator
# ═══════════════════════════════════════════════════════════════════════════════

class ActionableErrorTranslator:
    """
    Terjemahkan error mentah (FileNotFoundError, ENOENT, dsb)
    menjadi pesan yang langsung actionable untuk user.
    """

    _TRANSLATION_MAP = [
        # (pattern_in_error, actionable_message, suggested_command)
        (
            "FileNotFoundError",
            "File tidak ditemukan.",
            "Pastikan path benar. Gunakan `find_files` untuk mencari.",
        ),
        (
            "No such file or directory",
            "File atau direktori tidak ada.",
            "Buat dulu dengan `mkdir -p /path/to/dir` atau `write_file`.",
        ),
        (
            "ENOENT",
            "Path target tidak ada di filesystem.",
            "Buat direktori dulu: `mkdir -p /path/to/dir`.",
        ),
        (
            "EADDRINUSE",
            "Port sudah dipakai oleh proses lain.",
            "Kill proses lama: `kill $(lsof -t -i:PORT)` atau gunakan `find_safe_port`.",
        ),
        (
            "address already in use",
            "Port sudah dipakai oleh proses lain.",
            "Jalankan: `lsof -i :PORT` untuk lihat proses, lalu `kill PID`.",
        ),
        (
            "ModuleNotFoundError",
            "Python module belum terinstall.",
            "Jalankan: `pip install NAMA_MODULE`.",
        ),
        (
            "MODULE_NOT_FOUND",
            "Node.js package belum terinstall.",
            "Jalankan: `cd PROJECT && npm install`.",
        ),
        (
            "Cannot find module",
            "Node.js dependency tidak ditemukan.",
            "Jalankan: `npm install` di direktori project.",
        ),
        (
            "Permission denied",
            "Tidak punya izin akses.",
            "Gunakan `chmod` untuk ubah permission, atau `sudo` jika diperlukan.",
        ),
        (
            "SyntaxError",
            "Ada kesalahan sintaksis di file.",
            "Baca file dengan `read_file`, temukan dan perbaiki baris yang error.",
        ),
        (
            "connection refused",
            "Server belum berjalan atau port salah.",
            "Cek status server: `tail -30 app.log` atau `ps aux | grep server`.",
        ),
        (
            "missing script",
            "Script tidak terdaftar di package.json.",
            "Periksa `package.json` → bagian `scripts`. Gunakan nama script yang benar.",
        ),
        (
            "EACCES",
            "Akses file ditolak oleh sistem.",
            "Ubah permission: `chmod 755 /path/to/file`.",
        ),
        (
            "disk quota",
            "Ruang disk penuh.",
            "Bersihkan file tidak terpakai: `du -sh /* | sort -rh | head`.",
        ),
        (
            "timeout",
            "Operasi melebihi batas waktu.",
            "Coba lagi, atau pecah task menjadi bagian lebih kecil.",
        ),
        (
            "rate limit",
            "API rate limit tercapai.",
            "Tunggu sebentar lalu coba lagi (sistem auto-backoff aktif).",
        ),
        (
            "429",
            "Terlalu banyak permintaan ke API.",
            "Sistem akan retry otomatis dengan exponential backoff.",
        ),
        (
            "config.yaml tidak ditemukan",
            "File konfigurasi belum ada.",
            "Salin dari template: `cp config.example.yaml config.yaml`.",
        ),
    ]

    @classmethod
    def translate(cls, raw_error: str) -> str:
        """
        Terjemahkan error mentah ke pesan actionable.
        Returns: pesan actionable, atau raw_error jika tidak cocok pattern apapun.
        """
        err_lower = raw_error.lower()
        for pattern, description, suggestion in cls._TRANSLATION_MAP:
            if pattern.lower() in err_lower:
                return (
                    f"❌ **{description}**\n"
                    f"💡 **Solusi:** {suggestion}\n"
                    f"📋 Detail: `{raw_error[:200]}`"
                )
        # Tidak cocok pattern — kembalikan versi yang sedikit lebih rapi
        return f"❌ Error: {raw_error[:300]}"

    @classmethod
    def get_hint(cls, raw_error: str) -> str:
        """Returns just the suggestion hint, or empty string."""
        err_lower = raw_error.lower()
        for pattern, _, suggestion in cls._TRANSLATION_MAP:
            if pattern.lower() in err_lower:
                return f"\n[HINT: {suggestion}]"
        return ""


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Engine
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorRecoveryEngine:

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._tool_breakers: Dict[str, ToolCircuitBreaker] = {}
        self._recovery_history: List[RecoveryAttempt] = []
        self._max_history = 500

    # ── Model Circuit breaker API ────────────────────────────────────────────

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

    # ── Tool Circuit breaker API ─────────────────────────────────────────────

    def get_tool_breaker(self, tool_name: str, session_id: str = "global") -> ToolCircuitBreaker:
        if session_id not in self._tool_breakers:
            self._tool_breakers[session_id] = {}
        if tool_name not in self._tool_breakers[session_id]:
            self._tool_breakers[session_id][tool_name] = ToolCircuitBreaker(tool_name=tool_name)
        return self._tool_breakers[session_id][tool_name]

    def is_tool_available(self, tool_name: str, session_id: str = "global") -> bool:
        return self.get_tool_breaker(tool_name, session_id).should_allow()

    def record_tool_success(self, tool_name: str, session_id: str = "global"):
        self.get_tool_breaker(tool_name, session_id).record_success()

    def record_tool_failure(self, tool_name: str, error: str = "", session_id: str = "global"):
        tb = self.get_tool_breaker(tool_name, session_id)
        tb.record_failure(error)

    def get_tool_fallback_message(self, tool_name: str, session_id: str = "global") -> str:
        """Pesan untuk user ketika tool di-suspend."""
        tb = self.get_tool_breaker(tool_name, session_id)
        return (
            f"⚠️ Tool `{tool_name}` di-suspend sementara di sesi ini "
            f"({tb.failure_count} kegagalan beruntun). "
            f"Akan dicoba lagi dalam {tb.remaining_suspend:.0f} detik. "
            f"Sistem beralih ke strategi alternatif."
        )

    # ── Dead Letter Queue helper ─────────────────────────────────────────────

    async def send_to_dlq(self, task_exec_id: str, reason: str):
        """Tandai task execution sebagai DLQ entry di database."""
        if not task_exec_id:
            return
        try:
            from db.database import AsyncSessionLocal
            from db.models import TaskExecution
            async with AsyncSessionLocal() as db:
                task = await db.get(TaskExecution, task_exec_id)
                if task:
                    task.status = "dlq"
                    task.dlq_reason = reason[:500]
                    db.add(task)
                    await db.commit()
                    log.warning("Task sent to DLQ",
                                task_id=task_exec_id, reason=reason[:100])
        except Exception as e:
            log.debug("DLQ write failed", error=str(e)[:80])

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
        Eksekusi fungsi dengan auto-recovery + exponential backoff.
        Returns (result, attempts_list).

        Recovery order:
          0 → retry same (backoff 1s)
          1 → retry dengan params berbeda (backoff 2s)
          2 → coba model alternatif (backoff 4s)
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

            # Exponential backoff delay: 1s → 2s → 4s → 8s (max 30s)
            if attempt_num > 0:
                err_type = _classify_recovery_error(
                    attempts[-1].error or "" if attempts else ""
                )
                if err_type == "transient":
                    delay = min(30, 2 ** attempt_num)    # 2, 4, 8...
                else:
                    delay = min(30, 2 ** (attempt_num + 1))  # 4, 8, 16...
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
        Pilih model alternatif berdasarkan task_type + capability.
        """
        from core.model_manager import model_manager
        from agents.agent_registry import MODEL_CAPABILITY_MAP

        required_caps = set(_TASK_CAPABILITY_NEEDS.get(task_type, ["text"]))

        available = model_manager.available_models
        scored: List[Tuple[float, str]] = []

        for model_id in available:
            if model_id == current_model:
                continue
            if not self.is_model_available(model_id):
                continue

            model_caps = set(MODEL_CAPABILITY_MAP.get(model_id, []))
            overlap = len(required_caps & model_caps) if model_caps else 0
            bonus = 0.5 if "speed" in model_caps else 0.0
            score = overlap + bonus
            scored.append((score, model_id))

        if not scored:
            return None

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
        """Health status semua model + tools — untuk monitoring dashboard."""
        from core.model_manager import model_manager

        models = {}
        for model_id in model_manager.available_models:
            cb = self.get_circuit_breaker(model_id)
            models[model_id] = {
                "available":         cb.should_allow(),
                "circuit_open":      cb.is_open,
                "failure_count":     cb.failure_count,
                "cooldown_remaining": round(cb.remaining_cooldown, 1),
            }

        tools = {}
        for tool_name, tb in self._tool_breakers.items():
            tools[tool_name] = {
                "available":         tb.should_allow(),
                "suspended":         tb.is_suspended,
                "failure_count":     tb.failure_count,
                "total_failures":    tb.total_failures,
                "suspend_remaining": round(tb.remaining_suspend, 1),
            }

        return {"models": models, "tools": tools}

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

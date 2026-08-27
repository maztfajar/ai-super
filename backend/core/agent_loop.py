"""
Agent Loop v1.0 — Explicit ReAct Execution Engine
====================================================
Mengimplementasikan siklus ReAct (Reason + Act) yang eksplisit:

  Think -> Act -> Observe -> Reflect -> [Continue | Done]

Streaming events emitted:
  {"type": "loop_step", "step": "think", "iteration": 1, "detail": "..."}
  {"type": "loop_step", "step": "act", "action": "tool_name", ...}
  {"type": "loop_step", "step": "observe", "detail": "..."}
  {"type": "loop_step", "step": "reflect", "confidence": 0.87, ...}
  {"type": "loop_done", "iterations": 3, "answer": "...", "reason": "done"}
"""

import json
import time
import asyncio
import re
from typing import AsyncGenerator, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog

log = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────────────────
MAX_ITERATIONS = 10
EARLY_STOP_CONFIDENCE = 0.92
MIN_ITERATIONS = 1
TOOL_TIMEOUT_SECS = 30


class LoopStep(str, Enum):
    THINK   = "think"
    ACT     = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"
    DONE    = "done"
    ERROR   = "error"


@dataclass
class LoopState:
    iteration: int = 0
    step: LoopStep = LoopStep.THINK
    thought: str = ""
    action: Optional[str] = None
    action_args: Dict = field(default_factory=dict)
    observation: str = ""
    reflection: str = ""
    confidence: float = 0.0
    should_continue: bool = True
    error: Optional[str] = None
    start_ts: float = field(default_factory=time.time)


@dataclass
class LoopResult:
    answer: str = ""
    iterations_used: int = 0
    total_actions: int = 0
    final_confidence: float = 0.0
    stopped_reason: str = ""
    duration_ms: int = 0
    states: List[LoopState] = field(default_factory=list)


class AgentLoop:
    """
    Mesin eksekusi ReAct per-session.

    Cara pakai:
        loop = AgentLoop(tool_executor=my_executor)
        async for event in loop.run(query, messages, model_caller):
            yield f"data: {json.dumps(event)}\n\n"
    """

    def __init__(
        self,
        tool_executor: Optional[Callable] = None,
        max_iterations: int = MAX_ITERATIONS,
        early_stop_confidence: float = EARLY_STOP_CONFIDENCE,
        session_id: str = "",
    ):
        self.tool_executor = tool_executor
        self.max_iterations = max_iterations
        self.early_stop_confidence = early_stop_confidence
        self.session_id = session_id

    async def run(
        self,
        query: str,
        messages: List[Dict],
        model_caller: Callable,
        tools: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Jalankan ReAct loop. Yield dict events setiap langkah.
        """
        start_time = time.time()
        result = LoopResult()
        working_messages = list(messages)

        log.info("AgentLoop.run start", session=self.session_id, query=query[:80])

        for iteration in range(1, self.max_iterations + 1):
            state = LoopState(iteration=iteration)
            result.iterations_used = iteration

            # ── THINK ──────────────────────────────────────────────────
            state.step = LoopStep.THINK
            yield self._step_event(state, "Menganalisis dan merencanakan...")

            try:
                think_msgs = self._build_think_prompt(query, working_messages, iteration)
                think_response = await model_caller(think_msgs, tools=tools)
                state.thought = think_response if isinstance(think_response, str) else str(think_response)
            except Exception as e:
                state.step = LoopStep.ERROR
                state.error = str(e)
                yield self._step_event(state, f"Error: {e}")
                break

            yield self._step_event(state, state.thought[:300])

            tool_call = self._extract_tool_call(think_response)

            if not tool_call:
                result.answer = state.thought
                result.stopped_reason = "done"
                result.final_confidence = 0.95
                yield {"type": "loop_done", "iterations": iteration,
                       "answer": state.thought, "reason": "direct_answer"}
                break

            # ── ACT ────────────────────────────────────────────────────
            state.step = LoopStep.ACT
            state.action = tool_call.get("name", "unknown")
            state.action_args = tool_call.get("arguments", {})
            result.total_actions += 1
            yield self._step_event(state, f"Memanggil tool: {state.action}")

            observation = ""
            if self.tool_executor:
                try:
                    obs = await asyncio.wait_for(
                        self.tool_executor(state.action, state.action_args),
                        timeout=TOOL_TIMEOUT_SECS,
                    )
                    observation = str(obs) if obs is not None else "(kosong)"
                except asyncio.TimeoutError:
                    observation = f"[TIMEOUT] {state.action} melebihi {TOOL_TIMEOUT_SECS}s"
                except Exception as e:
                    observation = f"[ERROR] {state.action}: {e}"
            else:
                observation = f"[Tool executor tidak tersedia: {state.action}]"

            # ── OBSERVE ────────────────────────────────────────────────
            state.step = LoopStep.OBSERVE
            state.observation = observation
            working_messages.append({
                "role": "tool",
                "name": state.action,
                "content": observation[:2000],
            })
            yield self._step_event(state, observation[:300])

            # ── REFLECT ────────────────────────────────────────────────
            state.step = LoopStep.REFLECT
            confidence = self._estimate_confidence(observation, query, iteration)
            state.confidence = confidence
            state.reflection = self._build_reflection(confidence, iteration)
            state.should_continue = (
                confidence < self.early_stop_confidence
                and iteration < self.max_iterations
            )

            yield self._step_event(state, state.reflection)
            result.states.append(state)

            if not state.should_continue and iteration >= MIN_ITERATIONS:
                try:
                    final = await model_caller(
                        working_messages + [{"role": "user", "content":
                            f"Berdasarkan semua hasil di atas, berikan jawaban final lengkap untuk: {query}"}],
                        tools=None,
                    )
                    result.answer = final if isinstance(final, str) else str(final)
                except Exception as e:
                    result.answer = f"Error saat menyusun jawaban: {e}"

                result.stopped_reason = (
                    "early_stop" if confidence >= self.early_stop_confidence else "max_iter"
                )
                result.final_confidence = confidence
                yield {"type": "loop_done", "iterations": iteration,
                       "answer": result.answer, "reason": result.stopped_reason,
                       "confidence": round(confidence, 2)}
                break
        else:
            result.stopped_reason = "max_iter"
            result.final_confidence = 0.5
            if not result.answer:
                result.answer = "Batas iterasi tercapai. Hasil terbaik telah dikumpulkan."
            yield {"type": "loop_done", "iterations": self.max_iterations,
                   "answer": result.answer, "reason": "max_iter"}

        result.duration_ms = int((time.time() - start_time) * 1000)
        log.info("AgentLoop.run done",
                 session=self.session_id,
                 iterations=result.iterations_used,
                 actions=result.total_actions,
                 reason=result.stopped_reason,
                 duration_ms=result.duration_ms)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _step_event(self, state: LoopState, detail: str) -> Dict:
        return {
            "type": "loop_step",
            "step": state.step.value,
            "iteration": state.iteration,
            "action": state.action,
            "confidence": round(state.confidence, 2),
            "detail": detail[:500],
        }

    def _build_think_prompt(self, query: str, messages: List[Dict], iteration: int) -> List[Dict]:
        if iteration == 1:
            suffix = (
                f"\n\n[THINK] Iterasi 1: Buat rencana untuk menjawab: {query}\n"
                "Jika butuh tool, tentukan tool apa. Jika bisa dijawab langsung, jawab sekarang."
            )
        else:
            suffix = (
                f"\n\n[THINK] Iterasi {iteration}: Evaluasi hasil sebelumnya. "
                "Apakah tugas selesai? Jika belum, langkah selanjutnya apa? "
                "Jika sudah cukup informasi, berikan jawaban final."
            )
        return messages + [{"role": "user", "content": suffix}]

    def _extract_tool_call(self, response: Any) -> Optional[Dict]:
        if isinstance(response, dict) and "tool_calls" in response:
            try:
                tc = response["tool_calls"][0]
                return {
                    "name": tc["function"]["name"],
                    "arguments": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"],
                }
            except Exception:
                pass

        if isinstance(response, str):
            # Format 1: [TOOL: name] {args}
            pattern = r'\[TOOL:\s*(\w+)\]\s*(\{.*?\})'
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return {
                        "name": match.group(1),
                        "arguments": json.loads(match.group(2)),
                    }
                except json.JSONDecodeError:
                    pass

            # Format 2: <tool>{"name": "...", "arguments": {...}}</tool>
            tool_tag = re.search(r'<tool>\s*(\{.*?\})\s*</tool>', response, re.DOTALL)
            if tool_tag:
                try:
                    data = json.loads(tool_tag.group(1))
                    if "name" in data:
                        args = data.get("arguments", data.get("args", {}))
                        return {"name": data["name"], "arguments": args}
                except json.JSONDecodeError:
                    pass

            # Format 3: ```json with tool call
            json_block = re.search(r'```(?:json)?\s*(\{[^`]*"name"\s*:[^`]*\})\s*```', response, re.DOTALL)
            if json_block:
                try:
                    data = json.loads(json_block.group(1))
                    if "name" in data:
                        args = data.get("arguments", data.get("args", {}))
                        return {"name": data["name"], "arguments": args}
                except json.JSONDecodeError:
                    pass

        return None

    def _estimate_confidence(self, observation: str, query: str, iteration: int) -> float:
        if not observation or "[ERROR]" in observation or "[TIMEOUT]" in observation:
            return 0.2

        success_signals = [
            "berhasil", "sukses", "selesai", "done", "success", "completed",
            "created", "dibuat", "saved", "tersimpan", "ok", "true",
        ]
        obs_lower = observation.lower()
        signal_count = sum(1 for s in success_signals if s in obs_lower)
        base = min(0.85, 0.4 + (signal_count * 0.1))
        iteration_bonus = min(0.1, iteration * 0.02)
        return min(0.99, base + iteration_bonus)

    def _build_reflection(self, confidence: float, iteration: int) -> str:
        if confidence >= self.early_stop_confidence:
            return f"Tugas selesai dengan confidence {confidence:.0%}. Menyiapkan jawaban final."
        elif confidence >= 0.7:
            return f"Progress baik ({confidence:.0%}). Lanjut ke langkah berikutnya."
        elif iteration >= self.max_iterations - 1:
            return f"Mendekati batas iterasi. Menyiapkan jawaban terbaik."
        else:
            return f"Confidence {confidence:.0%}. Butuh informasi lebih lanjut."


# ── Factory ───────────────────────────────────────────────────────────────────
def create_agent_loop(
    tool_executor: Optional[Callable] = None,
    session_id: str = "",
    max_iterations: int = MAX_ITERATIONS,
) -> AgentLoop:
    """Factory untuk membuat AgentLoop per-session."""
    return AgentLoop(
        tool_executor=tool_executor,
        session_id=session_id,
        max_iterations=max_iterations,
    )

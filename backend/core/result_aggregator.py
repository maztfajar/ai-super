"""
Super Agent Orchestrator — Result Aggregator & Synthesizer
Merges outputs from multiple agents/subtasks into a coherent final response.
Handles: parallel result merging, conflict reconciliation, format standardization.
"""
import json
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()


@dataclass
class SubTaskResult:
    """Result from a single subtask execution."""
    task_id: str
    description: str
    agent_type: str
    model_used: str
    response: str
    confidence: float = 0.8
    execution_time_ms: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class AggregatedResult:
    """Final aggregated result from all subtasks."""
    final_response: str = ""
    subtask_results: List[SubTaskResult] = field(default_factory=list)
    overall_confidence: float = 0.0
    total_time_ms: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    agents_used: List[str] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    synthesis_method: str = "direct"       # direct | merge | synthesize | voting
    had_failures: bool = False
    failure_count: int = 0


SYNTHESIS_PROMPT = """You are the AI Orchestrator Result Synthesizer.
Multiple AI agents have worked on parts of a user request. Your job is to merge their outputs into ONE coherent, final response.

RULES:
1. Combine all subtask results into a single, well-structured response
2. Remove redundancy — don't repeat the same information
3. Maintain logical flow and readability
4. Preserve ALL important details and data
5. Use proper Markdown formatting
6. If subtasks had different conclusions, present the most well-supported one
7. Credit specific insights where appropriate
8. Write in the same language as the original request

The user should NOT see any orchestration internals — present it as ONE unified answer.
"""


class ResultAggregator:
    """
    Aggregates results from multiple subtasks into a coherent final response.
    """

    async def aggregate(
        self,
        results: List[SubTaskResult],
        original_request: str = "",
        synthesis_model: Optional[str] = None,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> AggregatedResult:
        """
        Aggregate multiple subtask results into a final response.
        Chooses the appropriate aggregation strategy based on the results.
        """
        agg = AggregatedResult(subtask_results=results)

        # Track agents and models used
        agg.agents_used = list(set(r.agent_type for r in results))
        agg.models_used = list(set(r.model_used for r in results))
        agg.total_time_ms = sum(r.execution_time_ms for r in results)

        # Count failures
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        agg.had_failures = len(failed) > 0
        agg.failure_count = len(failed)

        if not successful:
            # All failed
            error_msgs = [f"- {r.task_id}: {r.error}" for r in failed]
            agg.final_response = (
                "❌ **Semua sub-tugas gagal dieksekusi.**\n\n"
                "Detail error:\n" + "\n".join(error_msgs)
            )
            agg.overall_confidence = 0.0
            return agg

        # Choose aggregation strategy
        if len(successful) == 1:
            # Single result — use directly
            agg.final_response = successful[0].response
            agg.overall_confidence = successful[0].confidence
            agg.synthesis_method = "direct"

        elif self._results_are_sequential(successful):
            # Sequential results — concatenate in order
            agg.final_response = self._merge_sequential(successful)
            agg.overall_confidence = sum(r.confidence for r in successful) / len(successful)
            agg.synthesis_method = "merge"

        else:
            # Complex merge — use LLM synthesis
            agg.final_response = await self._synthesize_with_llm(
                successful, original_request, synthesis_model, event_queue
            )
            agg.overall_confidence = sum(r.confidence for r in successful) / len(successful)
            agg.synthesis_method = "synthesize"

        # Append failure notices if any
        if failed:
            failure_note = "\n\n---\n⚠️ *Beberapa sub-tugas gagal:*\n"
            for f in failed:
                failure_note += f"- {f.description}: {f.error}\n"
            agg.final_response += failure_note

        log.info("Results aggregated",
                 method=agg.synthesis_method,
                 subtasks=len(results),
                 successful=len(successful),
                 failed=len(failed))

        return agg

    def _results_are_sequential(self, results: List[SubTaskResult]) -> bool:
        """
        Check if results should be treated as sequential steps.
        Sequential if task IDs suggest ordering (task_0, task_1, ...).
        """
        ids = [r.task_id for r in results]
        try:
            nums = [int(tid.split("_")[-1]) for tid in ids]
            return nums == sorted(nums) and len(set(nums)) == len(nums)
        except (ValueError, IndexError):
            return False

    def _merge_sequential(self, results: List[SubTaskResult]) -> str:
        """Merge sequential results by concatenating them with section headers."""
        # Sort by task ID
        sorted_results = sorted(results, key=lambda r: r.task_id)

        if len(sorted_results) == 1:
            return sorted_results[0].response

        # For 2-3 results, simple concatenation with separators
        parts = []
        for i, r in enumerate(sorted_results):
            if len(sorted_results) <= 3:
                # Simple merge — no headers needed if short enough
                parts.append(r.response)
            else:
                # Add section context
                parts.append(f"### {r.description}\n\n{r.response}")

        return "\n\n---\n\n".join(parts)

    async def _synthesize_with_llm(
        self,
        results: List[SubTaskResult],
        original_request: str,
        synthesis_model: Optional[str] = None,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> str:
        """Use LLM to synthesize multiple results into one coherent response."""
        try:
            model = synthesis_model or self._get_synthesis_model()

            # Build prompt with all results
            results_text = ""
            for r in results:
                results_text += f"\n### Sub-task: {r.description}\n"
                results_text += f"Agent: {r.agent_type} | Model: {r.model_used}\n"
                results_text += f"Confidence: {r.confidence:.2f}\n"
                results_text += f"Response:\n{r.response}\n\n---\n"

            messages = [
                {"role": "system", "content": SYNTHESIS_PROMPT},
                {"role": "user", "content": (
                    f"Original User Request:\n{original_request}\n\n"
                    f"Sub-task Results to Merge:\n{results_text}"
                )},
            ]

            synthesized = ""
            async for chunk in model_manager.chat_stream(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=4096,
            ):
                synthesized += chunk
                if event_queue is not None:
                    event_queue.put_nowait(chunk)

            return synthesized.strip()

        except Exception as e:
            log.warning("LLM synthesis failed, using sequential merge", error=str(e)[:100])
            return self._merge_sequential(results)

    def _get_synthesis_model(self) -> str:
        """Pick a model for synthesis (needs to be good at summarization)."""
        priorities = ["deepseek-v4-pro", "qwen3.6-flash", "gemini-2.5-flash-lite"]
        for p in priorities:
            for k in model_manager.available_models.keys():
                if p in k:
                    return k
        return model_manager.get_default_model()


result_aggregator = ResultAggregator()

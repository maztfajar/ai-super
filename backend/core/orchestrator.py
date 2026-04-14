"""
Super Agent Orchestrator — Core Orchestration Engine
The heart of the system. Coordinates request preprocessing, task decomposition,
agent selection, parallel execution, quality validation, and result aggregation.

Pipeline:
  Request → Preprocess → Decompose → Build DAG → Assign Agents →
  Execute (parallel/sequential) → Validate → Aggregate → Response
"""
import json
import time
import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from core.model_manager import model_manager
from core.request_preprocessor import request_preprocessor, TaskSpecification
from core.task_decomposer import task_decomposer
from core.dag_builder import dag_builder, ExecutionDAG, SubTask, ExecutionGroup
from core.capability_map import capability_map
from agents.agent_registry import agent_registry
from agents.agent_scorer import agent_scorer
from core.quality_engine import quality_engine
from core.error_recovery import error_recovery
from core.result_aggregator import result_aggregator, SubTaskResult, AggregatedResult
from core.metrics import metrics_engine, AgentMetric
from memory.manager import memory_manager

log = structlog.get_logger()


@dataclass
class OrchestratorEvent:
    """Event streamed back to the client during orchestration."""
    type: str          # status | chunk | error | done | dag_update | agent_assigned
    content: str = ""
    data: Optional[Dict] = None

    def to_sse(self) -> str:
        payload = {"type": self.type, "content": self.content}
        if self.data:
            payload.update(self.data)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class Orchestrator:
    """
    Central orchestration engine that coordinates the entire pipeline.
    """

    async def process(
        self,
        message: str,
        user_id: str,
        session_id: str,
        user_model_choice: Optional[str] = None,
        system_prompt: str = "",
        history: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_rag: bool = True,
        include_tool_logs: bool = True,
        image_b64: Optional[str] = None,
        image_mime: Optional[str] = None,
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Main orchestration pipeline. Yields events as the orchestration progresses.
        """
        start_time = time.time()
        task_exec_id = None
        history = history or []

        # ─── PHASE 1: PREPROCESSING ──────────────────────────────
        yield OrchestratorEvent("status", "🔍 Menganalisa permintaan...")

        try:
            spec = await request_preprocessor.process(
                message=message,
                user_id=user_id,
                session_id=session_id,
                user_model_choice=user_model_choice,
                image_b64=image_b64,
                image_mime=image_mime,
            )
        except Exception as e:
            log.error("Preprocessing failed", error=str(e)[:100])
            spec = TaskSpecification(
                original_message=message,
                is_simple=True,
                primary_intent="general",
            )

        # ─── PHASE 0: CAPABILITY-AWARE ROUTING ───────────────────
        # Fast-path for special intents before full orchestration
        primary = spec.primary_intent

        if primary == "image_generation":
            async for event in self._handle_image_gen(spec, system_prompt, history):
                yield event
            return

        if primary == "vision":
            async for event in self._handle_vision(spec, image_b64, image_mime, system_prompt, history):
                yield event
            return

        if primary == "audio_generation":
            # Delegate to simple handler with audio_gen agent
            async for event in self._handle_simple(
                spec, system_prompt, history, temperature, max_tokens,
                user_model_choice, include_tool_logs, force_agent="audio_gen"
            ):
                yield event
            return

        # Pre-inject web search results for real-time queries
        search_context = ""
        if "real_time_search" in spec.intents:
            yield OrchestratorEvent("status", "🔍 Mencari data terkini di internet...")
            try:
                from agents.tools.web_search import web_search_realtime
                query = spec.original_message[:200]
                search_results = await asyncio.wait_for(
                    web_search_realtime(query, max_results=5),
                    timeout=15.0
                )
                if search_results:
                    snippets = []
                    for r in search_results:
                        snippets.append(
                            f"- **{r['title']}**: {r['snippet']} ({r['url']})"
                        )
                    search_context = (
                        "\n\n[DATA REAL-TIME DARI INTERNET]\n" +
                        "\n".join(snippets) +
                        "\n[/DATA REAL-TIME]"
                    )
                    system_prompt = system_prompt + search_context
                    yield OrchestratorEvent("status",
                        f"  ✅ {len(search_results)} hasil ditemukan dari web")
            except asyncio.TimeoutError:
                yield OrchestratorEvent("status", "  ⚠️ Web search timeout, lanjut tanpa data real-time")
            except Exception as e:
                log.warning("Web search failed in orchestrator", error=str(e)[:80])
                yield OrchestratorEvent("status", "  ⚠️ Web search gagal, lanjut tanpa data terkini")

        # ─── FAST PATH: Simple messages ──────────────────────────
        if spec.is_simple:
            async for event in self._handle_simple(
                spec, system_prompt, history, temperature, max_tokens,
                user_model_choice, include_tool_logs
            ):
                yield event
            return

        # ─── PHASE 2: TASK DECOMPOSITION ─────────────────────────
        yield OrchestratorEvent("status", "📋 Memecah tugas menjadi sub-tasks...")

        try:
            subtasks = await task_decomposer.decompose(spec)
        except Exception as e:
            log.warning("Decomposition failed, single task fallback", error=str(e)[:100])
            subtasks = [SubTask(
                id="task_0", description=message,
                task_type=spec.primary_intent,
                required_skills=spec.intents,
            )]

        # ─── PHASE 3: BUILD EXECUTION DAG ────────────────────────
        dag = dag_builder.build(subtasks)

        if not dag.is_valid:
            yield OrchestratorEvent("status",
                f"⚠️ DAG memiliki masalah: {'; '.join(dag.validation_errors[:2])}")

        # Create TaskExecution record
        task_exec_id = await self._create_task_execution(
            session_id, user_id, message, spec, subtasks, dag
        )

        # ─── PHASE 4: ASSIGN AGENTS ──────────────────────────────
        yield OrchestratorEvent("status",
            f"🤖 Menugaskan {len(subtasks)} sub-task ke AI agents...")

        assigned_subtasks = agent_scorer.assign_all(subtasks, spec.quality_priority)

        # Report assignments
        for st in assigned_subtasks:
            agent_info = agent_registry.get_agent(st.assigned_agent)
            agent_name = agent_info.display_name if agent_info else st.assigned_agent
            yield OrchestratorEvent("status",
                f"  → {agent_name}: {st.description[:80]}...")

        # ─── PHASE 5: EXECUTE ─────────────────────────────────────
        yield OrchestratorEvent("status", "⚡ Mengeksekusi sub-tasks...")

        results: List[SubTaskResult] = []
        for group in dag.execution_order:
            group_tasks = [dag.subtasks[tid] for tid in group.task_ids if tid in dag.subtasks]

            if len(group_tasks) == 1:
                # Single task — execute directly
                # Mark agent as active for monitoring
                agent_type = group_tasks[0].assigned_agent or "general"
                agent_registry.mark_busy(agent_type, group_tasks[0].id)
                result = await self._execute_subtask(
                    group_tasks[0], system_prompt, history, spec
                )
                agent_registry.mark_idle(agent_type, group_tasks[0].id)
                results.append(result)
                # Stream progress
                if result.success:
                    yield OrchestratorEvent("status",
                        f"  ✅ {result.task_id}: selesai (confidence: {result.confidence:.0%})")
                else:
                    yield OrchestratorEvent("status",
                        f"  ❌ {result.task_id}: gagal — {result.error}")
            else:
                # Multiple tasks — execute in parallel
                yield OrchestratorEvent("status",
                    f"  🔀 Menjalankan {len(group_tasks)} task secara paralel...")

                # Mark all agents as busy
                for st in group_tasks:
                    agent_registry.mark_busy(st.assigned_agent or "general", st.id)

                parallel_results = await asyncio.gather(*(
                    self._execute_subtask(st, system_prompt, history, spec)
                    for st in group_tasks
                ), return_exceptions=True)

                # Mark all agents as idle
                for st in group_tasks:
                    agent_registry.mark_idle(st.assigned_agent or "general", st.id)

                for pr in parallel_results:
                    if isinstance(pr, Exception):
                        results.append(SubTaskResult(
                            task_id="error",
                            description="Execution error",
                            agent_type="unknown",
                            model_used="unknown",
                            response="",
                            success=False,
                            error=str(pr)[:200],
                        ))
                    else:
                        results.append(pr)

            # Inject successful results into context for next group
            for r in results:
                if r.success and r.response:
                    history = history + [
                        {"role": "assistant", "content": f"[Sub-task Result: {r.description}]\n{r.response[:500]}"}
                    ]

        # ─── PHASE 6: VALIDATE ────────────────────────────────────
        yield OrchestratorEvent("status", "🔎 Memvalidasi kualitas hasil...")

        for result in results:
            if result.success:
                qa_report = await quality_engine.validate(
                    task_id=result.task_id,
                    agent_type=result.agent_type,
                    model_used=result.model_used,
                    output=result.response,
                    original_request=message,
                )
                result.confidence = qa_report.overall_score

                # If quality too low and we have budget, try to refine
                if qa_report.needs_refinement and len(results) < 6:
                    yield OrchestratorEvent("status",
                        f"  🔄 Refining {result.task_id} (quality: {qa_report.overall_score:.0%})...")
                    refined = await self._refine_result(result, message, system_prompt)
                    if refined:
                        result.response = refined
                        result.confidence = min(1.0, qa_report.overall_score + 0.2)

        # ─── PHASE 7: AGGREGATE ───────────────────────────────────
        yield OrchestratorEvent("status", "📝 Menyusun jawaban akhir...")

        aggregated = await result_aggregator.aggregate(
            results=results,
            original_request=message,
        )

        # Yield the final response as chunks
        # Split into manageable chunks for streaming feel
        response = aggregated.final_response
        chunk_size = 50  # characters per chunk
        for i in range(0, len(response), chunk_size):
            yield OrchestratorEvent("chunk", response[i:i + chunk_size])
            await asyncio.sleep(0.01)  # small delay for streaming feel

        # ─── PHASE 8: RECORD METRICS ─────────────────────────────
        total_time = int((time.time() - start_time) * 1000)

        # Record per-agent metrics
        for result in results:
            await metrics_engine.record(AgentMetric(
                agent_type=result.agent_type,
                model_used=result.model_used,
                task_type=spec.primary_intent,
                success=result.success,
                confidence=result.confidence,
                execution_time_ms=result.execution_time_ms,
            ), task_id=task_exec_id)

        # Update TaskExecution record
        await self._update_task_execution(
            task_exec_id, aggregated, total_time, results
        )

        yield OrchestratorEvent("done", "", {
            "confidence": round(aggregated.overall_confidence, 2),
            "agents_used": aggregated.agents_used,
            "models_used": aggregated.models_used,
            "subtasks": len(results),
            "total_time_ms": total_time,
            "synthesis_method": aggregated.synthesis_method,
            "drive_prompt": aggregated.final_response[:2000] if aggregated.final_response else None,
        })

    # ─── Simple Message Handler ───────────────────────────────

    async def _handle_simple(
        self,
        spec: TaskSpecification,
        system_prompt: str,
        history: list,
        temperature: float,
        max_tokens: int,
        user_model_choice: Optional[str],
        include_tool_logs: bool,
        force_agent: Optional[str] = None,
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Handle simple messages without full orchestration overhead."""

        # Determine model
        if user_model_choice and user_model_choice in model_manager.available_models:
            model = user_model_choice
        elif force_agent:
            # Use capability-aware model selection for forced agent types
            model = agent_registry.resolve_model_for_agent(force_agent, None)
            yield OrchestratorEvent("status",
                f"🤖 Capability routing: {force_agent} → {model}")
        else:
            # Use agent registry for model selection
            model = agent_registry.resolve_model_for_agent(
                spec.primary_intent, user_model_choice
            )

        # Check if VPS safety protocol needed
        if spec.primary_intent in ("system", "file_operation"):
            yield OrchestratorEvent("status", "⚠️ Tindakan sistem terdeteksi...")
            # Will be handled by chat.py confirmation flow
            yield OrchestratorEvent("pending_confirmation", "", {
                "command": spec.original_message,
                "purpose": f"Detected {spec.primary_intent} action",
                "risk": "MEDIUM",
            })
            return

        is_orchestrator = not user_model_choice or "orchestrator" in (user_model_choice or "").lower()

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages += history
        messages.append({"role": "user", "content": spec.original_message})

        yield OrchestratorEvent("status", "Merespons...")

        if is_orchestrator:
            # Use agent executor for tool access
            from agents.executor import agent_executor
            async for chunk in agent_executor.stream_chat(
                base_model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                include_tool_logs=include_tool_logs,
            ):
                yield OrchestratorEvent("chunk", chunk)
        else:
            # Direct model call — no tools
            async for chunk in model_manager.chat_stream(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield OrchestratorEvent("chunk", chunk)

        yield OrchestratorEvent("done")

    # ─── Image Generation Handler ─────────────────────────────

    async def _handle_image_gen(
        self,
        spec: TaskSpecification,
        system_prompt: str,
        history: list,
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Handle image generation requests with capability-aware model selection."""

        # Find best model for image generation
        image_model = capability_map.find_best_model({"image_gen"})
        if not image_model:
            # Fall back to mimo-v2-omni as the most capable multimodal model
            image_model = agent_registry.resolve_model_for_agent("image_gen", None)

        yield OrchestratorEvent("status",
            f"🖼️ Merutekan ke model image: {image_model}...")

        # Try image generation via OpenAI-compatible /images/generations endpoint
        generated_url = None
        try:
            generated_url = await model_manager.generate_image(
                model=image_model,
                prompt=spec.original_message,
            )
        except Exception as e:
            log.warning("Image generation API failed", error=str(e)[:120])

        if generated_url:
            # Image generated successfully
            response_text = (
                f"✅ **Gambar berhasil dibuat!**\n\n"
                f"🖼️ [Lihat Gambar]({generated_url})\n\n"
                f"Model yang digunakan: `{image_model}`\n"
                f"Prompt: _{spec.original_message[:200]}_"
            )
            for chunk in [response_text]:
                yield OrchestratorEvent("chunk", chunk)
            yield OrchestratorEvent("done", "", {
                "image_url": generated_url,
                "model_used": image_model,
                "capability_used": "image_gen",
            })
        else:
            # Image gen not supported by this endpoint — provide detailed description
            yield OrchestratorEvent("status",
                f"ℹ️ Model {image_model} tidak mendukung generate gambar via API ini. "
                "Memberikan deskripsi visual detail...")

            messages = [
                {"role": "system", "content": (
                    system_prompt +
                    "\n\nUser meminta gambar/foto. Karena endpoint image generation "
                    "tidak tersedia saat ini, berikan:\n"
                    "1. Deskripsi visual yang sangat detail dari gambar yang diminta\n"
                    "2. Saran untuk menggunakan tools seperti DALL-E, Midjourney, atau "
                    "Stable Diffusion dengan prompt yang dioptimasi\n"
                    "3. Prompt yang sudah dioptimasi untuk image generator tersebut"
                )},
            ] + history[-6:] + [{"role": "user", "content": spec.original_message}]

            full_response = ""
            async for chunk in model_manager.chat_stream(
                model=image_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            ):
                full_response += chunk
                yield OrchestratorEvent("chunk", chunk)

            yield OrchestratorEvent("done", "", {
                "model_used": image_model,
                "note": "image_gen_api_not_available",
            })

    async def _handle_vision(
        self,
        spec: TaskSpecification,
        image_b64: str,
        image_mime: str,
        system_prompt: str,
        history: list,
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Handle vision/image analysis requests with VISION_GATE engine."""

        if not image_b64:
            yield OrchestratorEvent("error", "❌ Tidak ada gambar yang terdeteksi. Silakan unggah gambar terlebih dahulu.")
            return

        yield OrchestratorEvent("status", "🔍 Menganalisa gambar dengan VISION_GATE engine...")

        # Find best model for vision
        vision_model = capability_map.find_best_model({"vision"})
        if not vision_model:
            vision_model = agent_registry.resolve_model_for_agent("vision", None)

        if not vision_model:
            vision_model = model_manager.get_default_model()

        yield OrchestratorEvent("status", f"🔍 Analisis visual menggunakan: {vision_model}")

        try:
            # Call vision model with image + text prompt
            response = await model_manager.chat_with_image(
                image_b64=image_b64,
                mime_type=image_mime,
                text_prompt=spec.original_message or "Jelaskan secara detail apa yang ada dalam gambar ini. Sebutkan semua objek, aktivitas, situasi, konteks, dan detail penting yang terlihat.",
                system_prompt=system_prompt,
                history=history,
                model=vision_model,
            )

            # Stream response in chunks
            for chunk in [response]:  # Simple line-by-line for now
                yield OrchestratorEvent("chunk", chunk)

            yield OrchestratorEvent("done", "", {
                "model_used": vision_model,
                "capability_used": "vision",
                "image_analyzed": True,
            })

        except Exception as e:
            error_msg = str(e)
            log.error("Vision analysis failed", model=vision_model, error=error_msg[:200])

            if "api" in error_msg.lower() or "model" in error_msg.lower():
                yield OrchestratorEvent("error",
                    f"❌ Gagal menganalisis gambar: {error_msg}\n\n"
                    f"Silakan coba lagi atau gunakan model berbeda.")
            else:
                yield OrchestratorEvent("error",
                    f"❌ Terjadi kesalahan saat menganalisis gambar.\n\n"
                    f"Detail: {error_msg}")

    # ─── Subtask Execution ────────────────────────────────────

    async def _execute_subtask(
        self,
        subtask: SubTask,
        system_prompt: str,
        history: list,
        spec: TaskSpecification,
    ) -> SubTaskResult:
        """Execute a single subtask using its assigned agent and model."""
        start = time.time()
        model = subtask.assigned_model or model_manager.get_default_model()
        agent_type = subtask.assigned_agent or "general"

        # Build agent-specific system prompt
        agent_prompt = agent_registry.get_agent_system_prompt(agent_type, system_prompt)

        messages = [
            {"role": "system", "content": agent_prompt},
        ]
        # Include relevant history (trimmed)
        messages += history[-10:]
        # Task-specific instruction
        messages.append({"role": "user", "content": (
            f"You are working on a specific sub-task as part of a larger request.\n\n"
            f"Original Request: {spec.original_message}\n\n"
            f"Your Sub-task: {subtask.description}\n\n"
            f"Focus ONLY on this sub-task. Provide a clear, complete answer."
        )})

        try:
            # Execute with error recovery
            async def _exec(model, **kwargs):
                return await model_manager.chat_completion(
                    model=model, messages=messages,
                    temperature=kwargs.get("temperature", 0.5),
                    max_tokens=kwargs.get("max_tokens", 4096),
                )

            response, attempts = await error_recovery.execute_with_recovery(
                execute_fn=_exec,
                model_id=model,
                task_type=subtask.task_type,
                max_retries=subtask.max_retries,
                temperature=0.5,
                max_tokens=4096,
            )

            if response is None:
                return SubTaskResult(
                    task_id=subtask.id,
                    description=subtask.description,
                    agent_type=agent_type,
                    model_used=model,
                    response="",
                    success=False,
                    error="All execution attempts failed",
                    execution_time_ms=int((time.time() - start) * 1000),
                )

            elapsed = int((time.time() - start) * 1000)
            return SubTaskResult(
                task_id=subtask.id,
                description=subtask.description,
                agent_type=agent_type,
                model_used=model,
                response=str(response),
                confidence=0.8,
                success=True,
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return SubTaskResult(
                task_id=subtask.id,
                description=subtask.description,
                agent_type=agent_type,
                model_used=model,
                response="",
                success=False,
                error=str(e)[:200],
                execution_time_ms=elapsed,
            )

    # ─── Result Refinement ────────────────────────────────────

    async def _refine_result(self, result: SubTaskResult,
                               original_request: str,
                               system_prompt: str) -> Optional[str]:
        """Attempt to refine a low-quality result using a different model."""
        try:
            # Pick a premium model for refinement
            refine_model = None
            for p in ["gpt-4o", "claude-3-5-sonnet", "seed-2-0-pro"]:
                for k in model_manager.available_models:
                    if p in k and k != result.model_used:
                        refine_model = k
                        break
                if refine_model:
                    break

            if not refine_model:
                return None

            messages = [
                {"role": "system", "content": "You are a quality improvement agent. Improve the following AI response to be more accurate, complete, and well-structured."},
                {"role": "user", "content": (
                    f"Original Request: {original_request}\n\n"
                    f"Current Response (needs improvement):\n{result.response}\n\n"
                    f"Please provide an improved version."
                )},
            ]

            refined = await model_manager.chat_completion(
                model=refine_model, messages=messages,
                temperature=0.3, max_tokens=4096,
            )

            return refined.strip() if refined and len(refined) > len(result.response) * 0.5 else None

        except Exception as e:
            log.debug("Refinement failed", error=str(e)[:80])
            return None

    # ─── Database Helpers ─────────────────────────────────────

    async def _create_task_execution(
        self, session_id: str, user_id: str, message: str,
        spec: TaskSpecification, subtasks: List[SubTask],
        dag: ExecutionDAG,
    ) -> Optional[str]:
        """Create a TaskExecution record in the database."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import TaskExecution

            async with AsyncSessionLocal() as db:
                te = TaskExecution(
                    session_id=session_id,
                    user_id=user_id,
                    original_request=message[:1000],
                    task_spec_json=spec.to_json(),
                    subtasks_json=json.dumps([s.to_dict() for s in subtasks], ensure_ascii=False),
                    dag_json=dag.to_json(),
                    status="executing",
                )
                db.add(te)
                await db.commit()
                await db.refresh(te)
                return te.id
        except Exception as e:
            log.warning("Failed to create task execution record", error=str(e)[:100])
            return None

    async def _update_task_execution(
        self, task_id: Optional[str],
        aggregated: AggregatedResult,
        total_time_ms: int,
        results: List[SubTaskResult],
    ):
        """Update TaskExecution record with results."""
        if not task_id:
            return
        try:
            from db.database import AsyncSessionLocal
            from db.models import TaskExecution

            async with AsyncSessionLocal() as db:
                te = await db.get(TaskExecution, task_id)
                if te:
                    te.status = "completed" if not aggregated.had_failures else "completed_with_errors"
                    te.result_summary = aggregated.final_response[:500]
                    te.total_time_ms = total_time_ms
                    te.total_cost_usd = aggregated.total_cost
                    te.agents_used = json.dumps(aggregated.agents_used)
                    te.completed_at = datetime.utcnow()
                    db.add(te)
                    await db.commit()
        except Exception as e:
            log.warning("Failed to update task execution", error=str(e)[:100])


orchestrator = Orchestrator()

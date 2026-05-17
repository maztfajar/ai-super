"""
AI Orchestrator Orchestrator — Core Orchestration Engine
The heart of the system. Coordinates request preprocessing, task decomposition,
agent selection, parallel execution, quality validation, and result aggregation.

Pipeline:
  Request → Preprocess → Decompose → Build DAG → Assign Agents →
  Execute (parallel/sequential) → Validate → Aggregate → Response
"""
import json
from core.process_emitter import process_emitter
from core.process_emitter import PROCESS_EVENT_PREFIX
import time
import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from core.model_manager import model_manager
from core.chain_of_thought import cot_engine, should_use_cot, format_cot_for_ui
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

# ── Pending Plans Registry ───────────────────────────────────────────────────
# Stores plan confirmation futures keyed by session_id.
# When orchestrator emits a plan for approval, it creates an asyncio.Event
# here and awaits it. The /chat/confirm_plan endpoint sets the event.
_pending_plans: Dict[str, asyncio.Event] = {}


@dataclass
class OrchestratorEvent:
    """Event streamed back to the client during orchestration.
    type: status | chunk | error | done | process
    """
    type: str
    content: str = ""
    data: Optional[Dict] = None

    def to_sse(self) -> str:
        if self.type == "process":
            # Process events carry structured step data
            payload = {"type": "process"}
            if self.data:
                payload.update(self.data)
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        payload = {"type": self.type, "content": self.content}
        if self.data:
            payload.update(self.data)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @classmethod
    def proc(cls, action: str, detail: str = "", count: int = None, **extra) -> "OrchestratorEvent":
        """Shorthand for building a structured process-step event.
        extra kwargs (code, language, truncated) are passed through to the SSE payload.
        """
        data = process_emitter.make(action, detail, count)
        if extra:
            data.update(extra)
        return cls(type="process", data=data)


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
        emit_thinking: bool = True,
        auto_execute: bool = False,
        project_path: str = None,
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Main orchestration pipeline. Yields events as the orchestration progresses.
        """
        start_time = time.time()
        task_exec_id = None
        history = history or []
        
        # Collect all thinking/status messages for expandable thinking section
        thinking_steps = []

        # ─── DEBUG: Log image parameters ──────────────────────────
        if image_b64 or image_mime:
            log.info("Orchestrator received image",
                    image_mime=image_mime,
                    image_b64_len=len(image_b64) if image_b64 else 0,
                    message_preview=message[:100])

        # ─── PHASE 1: PREPROCESSING ──────────────────────────────
        yield OrchestratorEvent.proc("Thinking", "memulai analisis", extra={
            "result": (
                f"📥 Pesan masuk: \"{message[:200]}\"\n\n"
                f"⏳ Menjalankan preprocessing...\n"
                f"   • Klasifikasi intent\n"
                f"   • Pengukuran kompleksitas\n"
                f"   • Routing model"
            )
        })
        yield OrchestratorEvent("status", "🔍 Menganalisa permintaan...")

        try:
            spec = await request_preprocessor.process(
                message=message,
                user_id=user_id,
                session_id=session_id,
                user_model_choice=user_model_choice,
                image_b64=image_b64,
                image_mime=image_mime,
                history=history,
            )
        except Exception as e:
            log.error("Preprocessing failed", error=str(e)[:100])
            spec = TaskSpecification(
                original_message=message,
                is_simple=True,
                primary_intent="general",
            )

        yield OrchestratorEvent.proc("Analyzed", f"intent: {spec.primary_intent} ({spec.action_type})", extra={
            "result": (
                f"Intent: {spec.primary_intent}\n"
                f"Action: {spec.action_type}\n"
                f"Kompleksitas: {spec.complexity_score:.2f}\n"
                f"Is Simple: {spec.is_simple}\n"
                f"Intents: {', '.join(spec.intents) if spec.intents else '-'}"
            )
        })

        # ─── HUMAN LOGIC ENGINE: Injeksi Konteks Emosi ───────────────
        emotional_hint = ""
        if hasattr(spec, "emotional_state"):
            if spec.emotional_state.needs_acknowledgment:
                emotional_hint += f"\n[CATATAN INTERNAL: Pengguna terlihat {spec.emotional_state.dominant_emotion}. "
                emotional_hint += f"Akui kondisi mereka dulu sebelum menjawab. "
                emotional_hint += f"Gunakan nada: {spec.tone_hint}]\n"

            if spec.emotional_state.has_time_pressure:
                emotional_hint += "[CATATAN INTERNAL: Pengguna sedang terburu-buru. Berikan jawaban ringkas dan langsung ke solusi.]\n"

            if emotional_hint:
                system_prompt += f"\n{emotional_hint}"

        # ─── PHASE 1.5: PROCEDURAL MEMORY RECALL ─────────────────
        # Injeksi "Buku Resep" dari tugas sukses sebelumnya ke system prompt
        try:
            from core.procedural_memory import procedural_memory
            recipe_context = await procedural_memory.build_recipe_context(
                category=spec.primary_intent,
                query=message[:300],
            )
            if recipe_context:
                system_prompt = system_prompt + recipe_context
                yield OrchestratorEvent("status", "📋 Procedural memory: resep sukses sebelumnya ditemukan")
        except Exception as e:
            log.debug("Procedural memory recall skipped", error=str(e)[:80])

        # ─── PHASE 1.6: SKILL LOOKUP — cek apakah ada skill permanen ──
        # Skill = kristalisasi dari ProceduralMemory yang sudah terbukti N kali
        skill_context = ""
        try:
            from core.skill_evolution import skill_evolution
            matched_skill = await skill_evolution.find_matching_skill(
                category=spec.primary_intent,
                query=message[:300],
            )
            if matched_skill:
                skill_context = skill_evolution.build_skill_context(matched_skill)
                system_prompt = system_prompt + skill_context
                yield OrchestratorEvent("status",
                    f"⚡ Skill '{matched_skill['name']}' aktif "
                    f"(v{matched_skill['version']}, "
                    f"hemat ~{matched_skill['avg_tokens_saved']} token)"
                )
                yield OrchestratorEvent.proc("Worked",
                    f"skill: {matched_skill['name']}",
                    extra={"result": skill_evolution.build_skill_context(matched_skill)}
                )
        except Exception as e:
            log.debug("Skill lookup skipped", error=str(e)[:80])

        # ─── PHASE 1.7: CHAIN OF THOUGHT ENGINE ──────────────────
        # Jalankan CoT reasoning sebelum routing & eksekusi utama.
        # CoT menghasilkan enriched_prompt yang menjadi fondasi jawaban.
        cot_result_obj = None
        if should_use_cot(spec):
            try:
                async for cot_event in cot_engine.stream_reason(
                    spec          = spec,
                    history       = history,
                    system_prompt = system_prompt,
                ):
                    if cot_event.type == "cot_done":
                        # Ganti system_prompt dengan versi yang diperkaya CoT
                        system_prompt   = cot_event.data["enriched_prompt"]
                        cot_result_obj  = cot_event.data["cot_result"]
                        log.info("CoT enriched prompt applied",
                                 depth      = cot_event.data["depth"],
                                 confidence = cot_event.data["confidence"],
                                 stages_run = cot_event.data["stages_run"],
                                 ms         = cot_event.data["total_ms"])
                    else:
                        # Forward status CoT ke frontend (SSE stream)
                        yield cot_event
            except Exception as _cot_err:
                log.warning("CoT Engine error — skipped", error=str(_cot_err)[:120])
                # CoT gagal → lanjut dengan system_prompt original, tidak masalah

        # ─── PHASE 0: CAPABILITY-AWARE ROUTING ───────────────────
        # Fast-path for special intents before full orchestration
        primary = spec.primary_intent

        log.info("Orchestrator routing decision",
                primary_intent=primary,
                action_type=spec.action_type,
                intents=spec.intents,
                is_simple=spec.is_simple,
                complexity=spec.complexity_score)

        # ─── PROJECT LOCATION POPUP (ONLY FOR NEW PROJECTS) ───────
        # Jika user meminta membuat aplikasi/project baru dan project_path kosong,
        # kita hentikan sementara dan minta user menentukan foldernya (muncul popup).
        import re
        CREATE_PROJECT_PATTERN = r"\b(buat|bikin|create|build|buatkan|bikinkan|bangun)\s+(aplikasi|web|website|project|program|sistem|bot|script)\b"
        is_create_project = bool(re.search(CREATE_PROJECT_PATTERN, message.lower()))
        
        # Kesadaran mirip manusia (Human-like awareness):
        # Jangan minta project path jika user sedang melakukan analisa file, research, 
        # atau vision/image processing, KECUALI mereka benar-benar ingin membangun aplikasi (requires_multi_agent = True).
        is_document_processing = primary in ["analysis", "research", "writing", "vision", "general"] or image_b64 is not None
        
        if is_create_project and not project_path:
            if is_document_processing and not spec.requires_multi_agent:
                log.info("Orchestrator bypassed project location popup due to document processing intent.")
            else:
                yield OrchestratorEvent("status", "📂 Membutuhkan lokasi penyimpanan project...")
                yield OrchestratorEvent("require_project_location", "")
                return

        # Auto-continue without explicit project_path for other normal tasks (executor will use get_project_path tool)
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
                user_model_choice, include_tool_logs, force_agent="audio_gen",
                emit_thinking=emit_thinking, session_id=session_id
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

        # ── CONTINUATION INTENT DETECTION ────────────────────────────
        # Deteksi jika user meminta lanjutkan task sebelumnya
        _CONTINUATION_PATTERNS = [
            r'\b(lanjut|lanjutkan|teruskan|continue|next|eksekusi|kerjakan|mulai|start)\b',
            r'\b(sudah|oke|ok|ya|yes|silakan|silahkan|langsung)\b.*\b(kerjakan|lakukan|buat|eksekusi)\b',
            r'^(ya|ok|oke|yep|yup|lanjut|go|mulai)[\s!.]*$',
        ]

        import re as _re
        is_continuation = any(
            _re.search(p, message.lower())
            for p in _CONTINUATION_PATTERNS
        )

        # Jika continuation intent + ada history → paksa ke orchestrator
        if is_continuation and history:
            # Ambil context dari pesan sebelumnya
            last_assistant = next(
                (h["content"] for h in reversed(history)
                 if h["role"] == "assistant"),
                ""
            )
            
            # Inject context ke message agar model tahu harus lakukan apa
            if last_assistant and len(last_assistant) > 50:
                message = (
                    f"{message}\n\n"
                    f"[CONTEXT: Lanjutkan dari response sebelumnya. "
                    f"Task yang belum selesai: "
                    f"{last_assistant[:300]}...]"
                )
                # Paksa sebagai task kompleks agar masuk agent executor
                spec.is_simple = False
                spec.primary_intent = _detect_intent_from_history(last_assistant)
                spec.complexity_score = 0.8
                
                yield OrchestratorEvent("status", "🔄 Melanjutkan task sebelumnya...")

        # ─── PLAN GENERATION (Informational) ───────────────────
        # Untuk task kompleks (buat aplikasi, perbaiki, dsb), tampilkan
        # implementation plan sebelum eksekusi — seperti VS Code Copilot.
        # Eksekusi langsung berjalan tanpa menunggu konfirmasi.
        try:
            from core.plan_generator import should_generate_plan, generate_plan
            if (
                should_generate_plan(message, spec.primary_intent, spec.action_type)
                and spec.complexity_score >= 0.45
                and not spec.is_simple
            ):
                yield OrchestratorEvent("status", "📋 Menyusun rencana implementasi...")
                # Ambil context dari history terakhir
                recent_ctx = ""
                if history:
                    recent_ctx = " | ".join(
                        h["content"][:80]
                        for h in history[-3:]
                        if h["role"] == "user"
                    )
                plan_text = await generate_plan(
                    message=message,
                    intent=spec.primary_intent,
                    context=recent_ctx,
                    timeout=12.0,
                )
                if plan_text:
                    yield OrchestratorEvent("impl_plan", plan_text, {
                        "intent": spec.primary_intent,
                        "complexity": round(spec.complexity_score, 2),
                    })
        except Exception as _pe:
            log.debug("Plan generation skipped", error=str(_pe)[:80])

        # ─── FAST PATH: Simple messages ──────────────────────────
        if spec.is_simple:
            # Create a lightweight TaskExecution for monitoring
            task_exec_id = await self._create_task_execution(
                session_id, user_id, message, spec, [], None
            )
            
            # Collect actual response from chunks
            full_response = ""
            chunk_count = 0
            log.info("Starting _handle_simple", is_simple=spec.is_simple, message=message[:50])
            async for event in self._handle_simple(
                spec, system_prompt, history, temperature, max_tokens,
                user_model_choice, include_tool_logs, emit_thinking=emit_thinking,
                auto_execute=auto_execute, session_id=session_id
            ):
                if event.type == "chunk":
                    full_response += event.content
                    chunk_count += 1
                    log.debug("Received chunk in fast path", count=chunk_count, preview=event.content[:50])
                yield event
            
            log.info("Finished _handle_simple", total_chunks=chunk_count, response_length=len(full_response))
            
            # Update simple task as completed with actual response
            if task_exec_id:
                await self._update_task_execution(
                    task_exec_id, 
                    AggregatedResult(final_response=full_response or "No response generated", overall_confidence=1.0), 
                    int((time.time() - start_time) * 1000), 
                    []
                )
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

        subtask_summary = "\n".join([
            f"{i+1}. [{st.task_type}] {st.description[:70]}"
            for i, st in enumerate(subtasks)
        ])
        yield OrchestratorEvent.proc("Planned", f"{len(subtasks)} sub-tasks", extra={
            "result": f"Sub-tasks yang akan dikerjakan:\n{subtask_summary}"
        })

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

        # ─── PHASE 4.5: INTERACTIVE PLAN CONFIRMATION ────────────
        # In web mode, show the plan and wait for user approval.
        # In auto_execute mode (Telegram/API), skip confirmation.
        assignment_summary = "\n".join([
            f"• {st.description[:50]} → {st.assigned_agent or 'general'} ({st.assigned_model or 'default'})"
            for st in assigned_subtasks
        ])

        # Auto-execute always — never pause for user confirmation.
        # Plan is shown as an informational status only.
        plan_detail = "📋 **Rencana Eksekusi (Otomatis):**\n\n"
        for i, st in enumerate(assigned_subtasks):
            agent_info = agent_registry.get_agent(st.assigned_agent)
            agent_name = agent_info.display_name if agent_info else st.assigned_agent
            model_short = (st.assigned_model or "default").split("/")[-1]
            deps = f" (setelah: {', '.join(st.dependencies)})" if st.dependencies else ""
            plan_detail += f"{i+1}. **[{st.task_type}]** {st.description[:100]}\n"
            plan_detail += f"   🤖 Agent: {agent_name} | Model: `{model_short}`{deps}\n\n"

        parallel_groups = len(dag.execution_order)
        plan_detail += f"⏱️ Estimasi: {len(assigned_subtasks)} sub-task"
        if parallel_groups < len(assigned_subtasks):
            plan_detail += f" ({parallel_groups} batch, sebagian paralel)"
        plan_detail += "\n"

        yield OrchestratorEvent("status", plan_detail)
        yield OrchestratorEvent("status", "⚡ Memulai eksekusi otomatis...")

        # ─── PHASE 5: EXECUTE ─────────────────────────────────────
        from workflow.dag_manager import DAGManager
        dag_manager = DAGManager(dag.to_json(), task_id=task_exec_id)
        
        yield OrchestratorEvent.proc("Worked", f"{len(subtasks)} sub-tasks", count=len(subtasks), extra={
            "result": f"Agent assignments:\n{assignment_summary}"
        })
        yield OrchestratorEvent("status", "⚡ Mengeksekusi sub-tasks...")

        results: List[SubTaskResult] = []
        phase5_streamed = False
        total_subtasks = len(assigned_subtasks)
        completed_subtask_count = 0
        SINGLE_TASK_TIMEOUT = 600.0  # 10 menit watchdog per single-task

        for group_idx, group in enumerate(dag.execution_order):
            group_tasks = [dag.subtasks[tid] for tid in group.task_ids if tid in dag.subtasks]

            if len(group_tasks) == 1:
                # Single task — execute directly with watchdog timer
                agent_type = group_tasks[0].assigned_agent or "general"
                agent_registry.mark_busy(agent_type, group_tasks[0].id)
                
                event_queue = asyncio.Queue()
                phase5_streamed = True
                dag_context_str = "Total tasks: {}\\n".format(len(assigned_subtasks))
                for i, st in enumerate(assigned_subtasks):
                    marker = ">> (SAAT INI) <<" if st.id == group_tasks[0].id else ""
                    dag_context_str += f"{i+1}. [{st.task_type}] {st.description[:100]} {marker}\\n"
                    
                exec_task = asyncio.create_task(self._execute_subtask(
                    group_tasks[0], system_prompt, history, spec, event_queue, stream_chunks=True, project_path=project_path, dag_context=dag_context_str
                ))
                
                # Watchdog: track elapsed time
                elapsed = 0.0
                watchdog_triggered = False
                while not exec_task.done():
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                        yield event
                    except asyncio.TimeoutError:
                        elapsed += 0.2
                        if elapsed >= SINGLE_TASK_TIMEOUT:
                            exec_task.cancel()
                            try:
                                await exec_task
                            except asyncio.CancelledError:
                                pass
                            watchdog_triggered = True
                            break
                        continue
                
                if watchdog_triggered:
                    result = SubTaskResult(
                        task_id=group_tasks[0].id,
                        description=group_tasks[0].description[:100],
                        agent_type=agent_type,
                        model_used=group_tasks[0].assigned_model or "unknown",
                        response="",
                        success=False,
                        error=f"Watchdog timeout: task melebihi batas {int(SINGLE_TASK_TIMEOUT)} detik",
                    )
                else:
                    result = exec_task.result()
                
                agent_registry.mark_idle(agent_type, group_tasks[0].id)
                results.append(result)
                completed_subtask_count += 1

                # Stream progress with [X/Y] format
                if result.success:
                    yield OrchestratorEvent("status",
                        f"  ✅ [{completed_subtask_count}/{total_subtasks}] "
                        f"{result.task_id}: selesai (confidence: {result.confidence:.0%})")
                else:
                    yield OrchestratorEvent("status",
                        f"  ❌ [{completed_subtask_count}/{total_subtasks}] "
                        f"{result.task_id}: gagal — {result.error}")
            else:
                # Multiple tasks — execute in parallel via Command Center
                from core.command_center import command_center
                
                event_queue = asyncio.Queue()
                
                dag_context_str = "Total tasks: {}\\n".format(len(assigned_subtasks))
                for i, st in enumerate(assigned_subtasks):
                    marker = ">> (SEDANG PARALEL) <<" if st.id in [gt.id for gt in group_tasks] else ""
                    dag_context_str += f"{i+1}. [{st.task_type}] {st.description[:100]} {marker}\\n"
                    
                coord_task = asyncio.create_task(command_center.coordinate_team(
                    group_tasks=group_tasks,
                    execute_fn=self._execute_subtask,
                    system_prompt=system_prompt,
                    history=history,
                    spec=spec,
                    project_path=project_path,
                    ui_event_queue=event_queue,
                    dag_context=dag_context_str
                ))
                
                while not coord_task.done():
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                        yield event
                    except asyncio.TimeoutError:
                        continue
                
                while not event_queue.empty():
                    try:
                        yield event_queue.get_nowait()
                    except Exception:
                        pass
                        
                parallel_results = coord_task.result()
                
                for pr in parallel_results:
                    results.append(pr)
                    completed_subtask_count += 1

            # Inject successful results into context for next group
            for r in results:
                if r.success and r.response:
                    history = history + [
                        {"role": "assistant", "content": f"[Sub-task Result: {r.description}]\n{r.response[:500]}"}
                    ]
            
            # Update DAG Manager state and Save Checkpoint
            for r in results:
                if r.success:
                    dag_manager.mark_completed(r.task_id, r.response)
                else:
                    dag_manager.mark_failed(r.task_id, r.error)
            
            await dag_manager.save_checkpoint()

        # ─── PHASE 5.5: DLQ — Kirim ke Dead Letter Queue jika SEMUA gagal ────
        all_failed = all(not r.success for r in results) if results else False
        if all_failed and task_exec_id:
            try:
                from core.error_recovery import error_recovery
                dlq_reason = "; ".join(
                    f"{r.task_id}: {r.error[:80]}" for r in results if r.error
                )[:500]
                await error_recovery.send_to_dlq(task_exec_id, dlq_reason)
                yield OrchestratorEvent("status",
                    "📪 Semua sub-task gagal — task disimpan ke Dead Letter Queue untuk review manual.")
            except Exception as _dlq_err:
                log.debug("DLQ send failed", error=str(_dlq_err)[:80])

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

        event_queue = asyncio.Queue()
        agg_task = asyncio.create_task(result_aggregator.aggregate(
            results=results,
            original_request=message,
            event_queue=event_queue
        ))

        streamed_chunks = False
        while not agg_task.done():
            try:
                chunk = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                yield OrchestratorEvent("chunk", chunk)
                streamed_chunks = True
            except asyncio.TimeoutError:
                continue
                
        # Flush any remaining chunks
        while not event_queue.empty():
            chunk = event_queue.get_nowait()
            yield OrchestratorEvent("chunk", chunk)
            streamed_chunks = True

        aggregated = agg_task.result()

        if not streamed_chunks and not phase5_streamed:
            # Yield the final response as chunks if it wasn't streamed in Phase 5 or Phase 7
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

        # ─── PHASE 8.5: PROCEDURAL MEMORY — SAVE RECIPE ──────────
        # Simpan pola sukses ke "Buku Resep" untuk referensi masa depan
        any_success = any(r.success for r in results)
        if any_success and aggregated.overall_confidence >= 0.6:
            try:
                from core.procedural_memory import procedural_memory
                tools_used = list(set(
                    r.agent_type for r in results if r.success
                ))
                models_used_list = list(set(
                    r.model_used for r in results if r.success and r.model_used
                ))
                avg_conf = sum(r.confidence for r in results if r.success) / max(1, sum(1 for r in results if r.success))
                await procedural_memory.reflect_on_task(
                    category=spec.primary_intent,
                    task_summary=message[:500],
                    tools_used=tools_used,
                    model_used=models_used_list[0] if models_used_list else "",
                    confidence=avg_conf,
                    steps_description=aggregated.final_response[:500] if aggregated.final_response else "",
                )
            except Exception as e:
                log.debug("Procedural memory save skipped", error=str(e)[:80])

        # ─── PHASE 8.6: CAPABILITY EVOLVER — record outcome ──────────
        # Beri feedback ke evolver tentang apakah assignment model berhasil
        try:
            from core.evolution_store import evolution_store

            for result in results:
                rules = await evolution_store.get_rules_for_context(
                    task_type=spec.primary_intent,
                    agent_type=result.agent_type,
                    model_id=result.model_used,
                    min_confidence=0.0,
                )
                for rule in rules:
                    await evolution_store.update_rule_outcome(
                        rule_id=rule.id,
                        success=result.success and result.confidence >= 0.6,
                    )
        except Exception as e:
            log.debug("Evolver outcome recording skipped", error=str(e)[:60])

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
            "cot": format_cot_for_ui(cot_result_obj) if cot_result_obj else None,
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
        emit_thinking: bool = True,
        auto_execute: bool = False,
        session_id: str = None,
        project_path: str = None,
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
            # Use agent registry for model selection based on primary intent
            model = agent_registry.resolve_model_for_agent(
                spec.primary_intent, user_model_choice
            )

        # Increase token limit for tasks that may need longer output
        if spec.primary_intent in ("coding", "web_development", "system", "file_operation"):
            max_tokens = max(max_tokens, 8192)

        # Determine if the intent is complex (requires orchestrator)
        is_complex_intent = (
            spec.primary_intent in ("system", "file_operation", "coding", "web_development", "research")
            or not spec.is_simple
        )

                # Paksa kompleks jika ada command-like keyword di pesan user
        msg_lower = spec.original_message.lower()
        # Perluasan keyword untuk mencakup perintah eksekusi langsung
        TECH_COMMANDS = [
            "curl", "ping", "ls", "df", "free", "systemctl", "ps", "cat", "grep", 
            "npm", "node", "python", "pip", "install", "run", "start", "cek", 
            "status", "periksa", "jalankan", "execute", "buka", "open", "buat", 
            "create", "perbaiki", "fix", "hapus", "delete", "remove", "tambah", 
            "add", "ubah", "ganti", "edit", "modify", "update", "setup", 
            "konfigurasi", "configure", "simpan", "save"
        ]
        
        has_command_keyword = any(w in msg_lower for w in TECH_COMMANDS)
        if has_command_keyword:
            is_complex_intent = True
            log.info("Forced complex intent due to command keyword in message", keywords=has_command_keyword)

        # Paksa kompleks jika history panjang (ada task yang sedang berlangsung)
        if spec.action_type != "explain" and len(history) >= 4 and not is_complex_intent:
            # Cek apakah history mengandung task teknis
            history_text = " ".join(
                h.get("content", "")[:100]
                for h in history[-6:]
            ).lower()
            has_technical_context = any(w in history_text for w in [
                "project", "file", "folder", "code", "buat", "create",
                "aplikasi", "server", "database", "install", "direktori"
            ])
            if has_technical_context:
                is_complex_intent = True
                log.info("Forced complex intent due to technical history context")
        
        # Determine if we should use orchestrator (agent executor) or direct chat
        if auto_execute:
            # Di Telegram/Auto mode, paksa eksekusi untuk semua intent kompleks agar tool benar-benar jalan
            is_orchestrator = is_complex_intent
        else:
            # Di Web, selalu gunakan orchestrator untuk task kompleks agar fitur tool dan thinking tetap jalan
            # meskipun user memilih model secara manual dari dropdown.
            is_orchestrator = is_complex_intent
        
        log.debug("_handle_simple routing", is_orchestrator=is_orchestrator, 
                  primary_intent=spec.primary_intent, action_type=spec.action_type,
                  auto_execute=auto_execute)

        # Check if VPS safety protocol needed for complex operations
        if spec.primary_intent in ("system", "file_operation") and spec.action_type == "execute":
            # Always auto-execute system commands via agent executor (with tool access)
            # The old pending_confirmation flow caused messages to stop silently
            yield OrchestratorEvent("status", "⚙️ Mengeksekusi perintah sistem via Agent...")
            is_orchestrator = True  # Force agent executor path so tools are available

        if not is_orchestrator:
            # STRICT: For ALL non-tool paths (simple or analysis), use a minimal
            # conversation-only prompt. NEVER pass the full system_prompt (ai_core_prompt.md)
            # which contains routing/model registry info that leaks into responses.
            from datetime import datetime
            now = datetime.now()
            hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            current_time_id = f"{hari[now.weekday()]}, {now.day} {bulan[now.month - 1]} {now.year}, {now.strftime('%H:%M:%S')}"
            
            simple_prompt = (
                f"WAKTU SAAT INI (REALTIME): {current_time_id}\n"
                "[PENTING: Gunakan WAKTU SAAT INI sebagai acuan mutlak jika pengguna bertanya tentang hari, tanggal, atau waktu. Dilarang halusinasi.]\n\n"
                "Anda adalah AI ORCHESTRATOR, AI Orchestrator tingkat tinggi yang merupakan inti dari sistem ini. "
                "Jawab pertanyaan atau sapaan user secara langsung, natural, dan profesional dalam Bahasa Indonesia. "
                "JANGAN PERNAH menyebutkan atau menjelaskan klasifikasi tugas, model yang digunakan, routing, atau arsitektur internal."
            )
            messages = [{"role": "system", "content": simple_prompt}]
        else:
            messages = [{"role": "system", "content": system_prompt}]

        messages += history[-10:]  # Limit history to prevent context overflow
        messages.append({"role": "user", "content": spec.original_message})

        # ── QMD: The Token Killer — distill messages ─────────────
        try:
            from core.qmd import qmd
            messages, qmd_result = qmd.distill(
                messages=messages,
                query=spec.original_message,
                max_token_budget=6000,
                keep_system=True,
                keep_last_n=4,
            )
            if qmd_result.savings_pct > 5:
                yield OrchestratorEvent("status",
                    f"⚡ QMD: hemat {qmd_result.savings_pct:.0f}% token "
                    f"({qmd_result.original_tokens_est}→{qmd_result.distilled_tokens_est})")
        except Exception as e:
            log.debug("QMD skip", error=str(e)[:60])

        # ── Humanizer: Anti AI Slop ──────────────────────────────
        try:
            from core.humanizer import humanizer
            messages, injected = humanizer.inject_anti_slop(messages, intent=spec.primary_intent)
            if injected:
                yield OrchestratorEvent("status", "✍️ Humanizer: Memoles gaya bahasa...")
        except Exception as e:
            log.debug("Humanizer skip", error=str(e)[:60])

        yield OrchestratorEvent("status", "Merespons...")

        active_agent = force_agent or spec.primary_intent
        import uuid
        task_id = str(uuid.uuid4())
        agent_registry.mark_busy(active_agent, task_id)

        try:
            if is_orchestrator:
                from agents.executor import agent_executor
                # Watchdog pattern: jika tidak ada chunk selama IDLE_TIMEOUT detik, hentikan
                IDLE_TIMEOUT = 3600.0  # 60 menit idle = timeout untuk task kompleks
                timed_out = False

                async def _producer(q: asyncio.Queue):
                    """Push chunks ke queue, None = selesai."""
                    try:
                        async for chunk in agent_executor.stream_chat(
                            base_model=model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            include_tool_logs=include_tool_logs,
                            emit_thinking=emit_thinking,
                            session_id=session_id,
                            project_path=project_path,
                        ):
                            await q.put(chunk)
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        import traceback
                        tb = traceback.format_exc()
                        log.error("Agent executor stream error", 
                                  error=str(e), 
                                  session_id=session_id,
                                  intent=spec.primary_intent,
                                  traceback=tb[:1000])
                        await q.put(f"\n\n❌ **Error Executor:** {str(e)}\n\n*Informasi debug telah dicatat di log sistem.*")
                    finally:
                        await q.put(None)  # sentinel

                q = asyncio.Queue()
                producer_task = asyncio.create_task(_producer(q))

                try:
                    while True:
                        try:
                            chunk = await asyncio.wait_for(q.get(), timeout=IDLE_TIMEOUT)
                        except asyncio.TimeoutError:
                            timed_out = True
                            producer_task.cancel()
                            break
                        if chunk is None:
                            break
                        # Detect process-event sentinels from executor
                        if isinstance(chunk, str) and chunk.startswith(PROCESS_EVENT_PREFIX):
                            try:
                                payload = json.loads(chunk[len(PROCESS_EVENT_PREFIX):])
                                # Forward ALL payload fields (including code/language for artifacts)
                                yield OrchestratorEvent.proc(
                                    action=payload.get("action", "Worked"),
                                    detail=payload.get("detail", ""),
                                    count=payload.get("count"),
                                    **{k: v for k, v in payload.items()
                                       if k not in ("action", "detail", "count", "ts")}
                                )
                            except Exception:
                                pass  # malformed sentinel — skip silently
                        else:
                            yield OrchestratorEvent("chunk", chunk)
                finally:
                    if not producer_task.done():
                        producer_task.cancel()
                    try:
                        await asyncio.shield(producer_task)
                    except:
                        pass

                if timed_out:
                    yield OrchestratorEvent("chunk",
                        "\n\n⏱️ **Waktu habis.** Model berhenti merespons."
                    )
            else:
                # Direct model call — no tools
                # For simple/direct path, NEVER emit thinking to avoid leakage of
                # internal classification/routing text that model may output without tags.
                import re
                buffer = ""
                response_started = False
                _thinking_stall_chars = 0  # Track chars accumulated during thinking
                _THINKING_MAX_BUFFER = 5000  # Emergency flush if thinking > 5000 chars
                _RESPONSE_FLUSH_INTERVAL = 2000  # Flush every N chars in response mode
                _response_unflushed = 0  # Track unflushed chars in response mode
                
                # Patterns that indicate leaked internal reasoning — must be stripped
                _LEAK_PATTERNS = [
                    r'\[THE RUNNER\][^\n]*\n?',
                    r'\[BRAIN\][^\n]*\n?',
                    r'\[ARCHITECT\][^\n]*\n?',
                    r'\[VISION_GATE\][^\n]*\n?',
                    r'\[THE EAR\][^\n]*\n?',
                    r'\[THE POLISHER\][^\n]*\n?',
                    r'(?i)This\s+(is\s+a\s+)?(simple\s+)?(greeting|general|coding|system|analysis)[^\n]*\n?',
                    r'(?i)The\s+(primary|category|main)\s+model\s+(for|applies|is)[^\n]*\n?',
                    r'(?i)The\s+user\s+(said|sent)[^\n]*(?:greeting|category|GREETING|GENERAL)[^\n]*\n?',
                    r'(?i)No\s+special\s+considerations[^\n]*\n?',
                    r'(?i)The\s+response\s+should\s+be\s+a[^\n]*\n?',
                    r'</?(?:thinking|think|response|tool|observation)>',
                ]
                
                def _strip_leaked_text(text: str) -> str:
                    # Remove full <thinking>...</thinking> blocks first
                    text = re.sub(r'<(?:thinking|think)>.*?</(?:thinking|think)>', '', text, flags=re.DOTALL)
                    for pattern in _LEAK_PATTERNS:
                        text = re.sub(pattern, '', text)
                    return text

                async for chunk in model_manager.chat_stream(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    buffer += chunk
                    
                    # Detect and skip <thinking> blocks
                    if not response_started:
                        # Skip if we're inside a thinking block
                        if '<thinking>' in buffer or '<think>' in buffer:
                            # Find the end of thinking block
                            end_tag = '</thinking>' if '</thinking>' in buffer else '</think>' if '</think>' in buffer else None
                            if end_tag:
                                # Found end of thinking block, strip it and continue
                                after_think = re.sub(r'<(?:thinking|think)>.*?</(?:thinking|think)>', '', buffer, flags=re.DOTALL)
                                buffer = after_think
                                _thinking_stall_chars = 0
                            else:
                                _thinking_stall_chars += len(chunk)
                                # EMERGENCY: Jika thinking block sudah > 5000 chars tanpa
                                # closing tag, model kemungkinan tidak akan menutupnya.
                                # Strip thinking dan emit sisa buffer sebagai response.
                                if _thinking_stall_chars > _THINKING_MAX_BUFFER:
                                    log.warning("Thinking block unclosed after %d chars, emergency flush",
                                                _thinking_stall_chars)
                                    # Remove the opening thinking tag and everything before it
                                    stripped = re.sub(r'<(?:thinking|think)>', '', buffer)
                                    clean = _strip_leaked_text(stripped)
                                    if clean.strip():
                                        response_started = True
                                        yield OrchestratorEvent("chunk", clean)
                                    buffer = ""
                                    _thinking_stall_chars = 0
                                continue
                        
                        # Check for response tag
                        if '<response>' in buffer:
                            response_started = True
                            resp_idx = buffer.find('<response>')
                            buffer = buffer[resp_idx + len('<response>'):]
                            # Emit anything already in buffer after <response>
                            if '</response>' in buffer:
                                clean = _strip_leaked_text(buffer.split('</response>')[0])
                                if clean:
                                    yield OrchestratorEvent("chunk", clean)
                                buffer = ""
                            continue
                        
                        # If buffer > 100 chars and no thinking tags, assume direct response
                        if len(buffer) > 100:
                            clean = _strip_leaked_text(buffer)
                            if clean:
                                response_started = True
                                yield OrchestratorEvent("chunk", clean)
                                buffer = ""
                    else:
                        # Already streaming — handle </response> termination
                        if '</response>' in buffer:
                            clean_part = _strip_leaked_text(buffer.split('</response>')[0])
                            if clean_part:
                                yield OrchestratorEvent("chunk", clean_part)
                            # Ambil sisa setelah </response> — mungkin masih ada konten
                            after_resp = buffer.split('</response>', 1)[1] if '</response>' in buffer else ""
                            buffer = after_resp.strip()
                            # Jika tidak ada sisa konten, selesai
                            if not buffer:
                                break
                            # Jika masih ada sisa, lanjutkan streaming
                        else:
                            # Stream chunk immediately
                            yield OrchestratorEvent("chunk", chunk)
                            _response_unflushed += len(chunk)
                            buffer = ""
                            # Periodic flush — reset accumulation counter
                            if _response_unflushed > _RESPONSE_FLUSH_INTERVAL:
                                _response_unflushed = 0

                # Flush remaining buffer
                if buffer:
                    clean = _strip_leaked_text(buffer)
                    if clean:
                        yield OrchestratorEvent("chunk", clean)
        finally:
            agent_registry.mark_idle(active_agent, task_id)

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

        import uuid
        task_id = str(uuid.uuid4())
        agent_registry.mark_busy("image_gen", task_id)

        try:
            # Try image generation via OpenAI-compatible /images/generations endpoint
            generated_url = None
            try:
                # Wrap dengan timeout 60 detik
                generated_url = await asyncio.wait_for(
                    model_manager.generate_image(
                        model=image_model,
                        prompt=spec.original_message,
                    ),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                log.warning("Image generation timeout")
                yield OrchestratorEvent("status",
                    f"⏱️ Model {image_model} timeout. Mencoba alternatif...")
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
                try:
                    # Wrap dengan timeout 90 detik
                    async for chunk in asyncio.wait_for(
                        model_manager.chat_stream(
                            model=image_model,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=1000,
                        ),
                        timeout=90.0
                    ):
                        full_response += chunk
                        yield OrchestratorEvent("chunk", chunk)
                except asyncio.TimeoutError:
                    log.warning("Chat stream timeout during image description")
                    yield OrchestratorEvent("chunk", "\n\n[Deskripsi terpotong karena timeout]")
                except Exception as e:
                    log.warning("Chat stream error", error=str(e)[:100])
                    yield OrchestratorEvent("chunk", f"\n\n[Error: {str(e)[:100]}]")

                yield OrchestratorEvent("done", "", {
                    "model_used": image_model,
                    "note": "image_gen_api_not_available",
                })
        finally:
            agent_registry.mark_idle("image_gen", task_id)

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

        import uuid
        task_id = str(uuid.uuid4())
        agent_registry.mark_busy("vision", task_id)

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
            import re
            def wrap_thinking(match):
                content = match.group(1).strip()
                formatted = "\n".join(f"> {line}" for line in content.split("\n"))
                return f'\n\n<details class="thinking-process">\n<summary>💭 Proses Pemikiran</summary>\n\n{formatted}\n</details>\n\n'
                
            formatted_response = re.sub(r'<(?:thinking|think)>(.*?)</(?:thinking|think)>', wrap_thinking, response, flags=re.DOTALL)
            
            for chunk in [formatted_response]:  # Simple line-by-line for now
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
        event_queue: Optional[asyncio.Queue] = None,
        stream_chunks: bool = False,
        project_path: str = None,
        dag_context: str = "",
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
        messages += history[-6:]
        # Task-specific instruction
        messages.append({"role": "user", "content": (
            f"You are working on a specific sub-task as part of a larger request.\n\n"
            f"Original Request: {spec.original_message}\n\n"
            f"Your Sub-task: {subtask.description}\n\n"
            f"Focus ONLY on this sub-task. Provide a clear, complete answer.\n"
            f"MANDATE: DO NOT give instructions for the user to follow. EXECUTE the sub-task directly using your tools."
        )})

        # ── QMD: distill subtask messages ─────────────────────────
        try:
            from core.qmd import qmd
            messages, _ = qmd.distill(
                messages=messages,
                query=subtask.description,
                max_token_budget=5000,
                keep_system=True,
                keep_last_n=2,
            )
        except Exception:
            pass

        # ── Humanizer: Anti AI Slop ──────────────────────────────
        try:
            from core.humanizer import humanizer
            messages, injected = humanizer.inject_anti_slop(messages, intent=subtask.task_type)
            if injected and event_queue is not None:
                event_queue.put_nowait(OrchestratorEvent("status", f"  ✍️ Humanizer memoles output {agent_type}..."))
        except Exception:
            pass

        try:
            from agents.executor import agent_executor
            
            # Execute with error recovery
            async def _exec(model, **kwargs):
                full_response = ""
                async for chunk in agent_executor.stream_chat(
                    base_model=model,
                    messages=messages,
                    temperature=kwargs.get("temperature", 0.5),
                    max_tokens=kwargs.get("max_tokens", 8192),
                    include_tool_logs=False,
                    emit_thinking=stream_chunks,
                    execution_mode="execution",
                    project_path=project_path,
                ):
                    # Filter out process-event sentinels from subtask responses
                    if isinstance(chunk, str) and chunk.startswith(PROCESS_EVENT_PREFIX):
                        if event_queue is not None:
                            try:
                                payload = json.loads(chunk[len(PROCESS_EVENT_PREFIX):])
                                action = payload.get("action", "Worked")
                                detail = payload.get("detail", "")
                                if detail:
                                    detail = f"[{subtask.description[:20]}...] {detail}"
                                else:
                                    detail = f"[{subtask.description[:20]}...]"
                                # Forward code/language for artifact display
                                event_queue.put_nowait(OrchestratorEvent.proc(
                                    action, detail, payload.get("count"),
                                    **{k: v for k, v in payload.items()
                                       if k not in ("action", "detail", "count", "ts")}
                                ))
                            except Exception:
                                pass
                        continue
                    
                    if stream_chunks and event_queue is not None:
                        event_queue.put_nowait(OrchestratorEvent("chunk", chunk))
                        
                    full_response += chunk
                return full_response

            response, attempts = await error_recovery.execute_with_recovery(
                execute_fn=_exec,
                model_id=model,
                task_type=subtask.task_type,
                max_retries=subtask.max_retries,
                temperature=0.5,
                max_tokens=8192,
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
        """Attempt to refine a low-quality result using a different (better) model."""
        try:
            # Pilih model yang berbeda dari yang sudah dipakai, preferensi model yang lebih kuat
            # Sesuai AI Core v2: [BRAIN] deepseek-v4-pro → [THINKER] qwen3.6-plus → [RUNNER] gemini-2.5-flash
            quality_keywords = ["deepseek-v4-pro", "qwen3.6-plus", "gemini/gemini-2.5-flash"]
            refine_model = None
            for keyword in quality_keywords:
                for k in model_manager.available_models:
                    if keyword in k and k != result.model_used:
                        refine_model = k
                        break
                if refine_model:
                    break

            # Fallback: gunakan model manapun yang berbeda
            if not refine_model:
                for k in model_manager.available_models:
                    if k != result.model_used:
                        refine_model = k
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
                    subtasks_json=json.dumps([s.to_dict() for s in subtasks], ensure_ascii=False) if subtasks else "[]",
                    dag_json=dag.to_json() if dag else "{}" ,
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


def _detect_intent_from_history(text: str) -> str:
    """Deteksi intent dari history untuk continuation."""
    text_lower = text.lower()
    if any(w in text_lower for w in
           ["def ", "function", "class ", "import ", "npm", "pip",
            "html", "css", "javascript", "python", "react"]):
        return "coding"
    if any(w in text_lower for w in
           ["server", "port", "bash", "terminal", "systemctl",
            "chmod", "sudo", "apt", "install"]):
        return "system"
    if any(w in text_lower for w in
           ["analisis", "laporan", "data", "tabel", "grafik"]):
        return "analysis"
    return "coding"  # default ke coding untuk task kompleks

orchestrator = Orchestrator()

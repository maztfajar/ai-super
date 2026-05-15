"""
Command Center (v2.0 — True Parallel + Watchdog)
=================================================
Pusat koordinasi untuk mengeksekusi banyak agent secara paralel (simultan).
Mengelola resource sharing, watchdog timer per task, status emisi untuk UI,
dan pengumpulan hasil dari tim digital yang dikerahkan.

v2.0 Enhancements:
  1. Watchdog Timer — setiap sub-task memiliki batas waktu individual.
     Jika melampaui batas, task dibatalkan dengan pesan yang jelas.
  2. True Parallel — agent benar-benar berjalan di coroutine terpisah
     via asyncio.gather, bukan sequential.
  3. Progress streaming — emit [X/Y] progress ke UI per task selesai.
  4. Error isolation — kegagalan satu task tidak meng-crash task lain.
"""

import asyncio
from typing import List, Callable, Any, Optional
import structlog

from core.dag_builder import SubTask
from core.result_aggregator import SubTaskResult
from core.process_emitter import OrchestratorEvent
from agents.agent_registry import agent_registry

log = structlog.get_logger()

# Default watchdog timeout per sub-task (5 menit)
DEFAULT_SUBTASK_TIMEOUT = 300.0

# Timeout override per agent type (detik)
_AGENT_TIMEOUT_MAP = {
    "coding":        600.0,    # 10 menit — coding task bisa panjang
    "web_development": 600.0,
    "system":        300.0,    # 5 menit
    "research":      180.0,    # 3 menit
    "writing":       180.0,
    "creative":      180.0,
    "validation":    120.0,    # 2 menit
    "general":       180.0,
}


class CommandCenter:
    """Koordinator eksekusi paralel multi-agent dengan watchdog timer."""

    async def coordinate_team(
        self,
        group_tasks: List[SubTask],
        execute_fn: Callable,  # The _execute_subtask function from Orchestrator
        system_prompt: str,
        history: list,
        spec: Any,  # TaskSpecification
        project_path: Optional[str],
        ui_event_queue: asyncio.Queue
    ) -> List[SubTaskResult]:
        """
        Deploy tim agent untuk mengeksekusi sub-task secara paralel.
        Setiap task memiliki watchdog timer individual.
        Mengembalikan daftar hasil eksekusi (SubTaskResult).
        """
        if not group_tasks:
            return []

        team = [st.assigned_agent or "general" for st in group_tasks]
        team_str = ", ".join(set(team))
        total = len(group_tasks)

        # Emit Command Center status
        ui_event_queue.put_nowait(OrchestratorEvent("status",
            f"🏛️ **Command Center**: Mengoordinasikan tim digital "
            f"({team_str}) untuk mengeksekusi {total} tugas secara paralel..."
        ))

        # Mark all agents as busy
        for st in group_tasks:
            agent_registry.mark_busy(st.assigned_agent or "general", st.id)

        # Track completion count for progress
        completed_count = 0

        # Buat task wrapper dengan watchdog timer individual dan limit konkurensi
        async def _run_task_with_watchdog(st: SubTask, task_index: int) -> SubTaskResult:
            async with self._semaphore:
                nonlocal completed_count
                agent_type = st.assigned_agent or "general"
            timeout = _AGENT_TIMEOUT_MAP.get(agent_type, DEFAULT_SUBTASK_TIMEOUT)

            agent_queue = asyncio.Queue()

            # Create the execution coroutine
            async def _execute():
                return await execute_fn(
                    st, system_prompt, history, spec, agent_queue,
                    project_path=project_path
                )

            try:
                # ── Watchdog: wrap execution with timeout ────────────────────
                exec_task = asyncio.create_task(_execute())

                # Forward events while executing, with periodic watchdog checks
                elapsed = 0.0
                check_interval = 0.2

                while not exec_task.done():
                    try:
                        event = await asyncio.wait_for(
                            agent_queue.get(), timeout=check_interval
                        )
                        ui_event_queue.put_nowait(event)
                    except asyncio.TimeoutError:
                        elapsed += check_interval
                        # Watchdog check
                        if elapsed >= timeout:
                            exec_task.cancel()
                            try:
                                await exec_task
                            except asyncio.CancelledError:
                                pass

                            completed_count += 1
                            ui_event_queue.put_nowait(OrchestratorEvent("status",
                                f"  ⏱️ [{completed_count}/{total}] "
                                f"{st.id}: TIMEOUT setelah {int(timeout)}s — dibatalkan"
                            ))

                            return SubTaskResult(
                                task_id=st.id,
                                description=st.description[:100],
                                agent_type=agent_type,
                                model_used=st.assigned_model or "unknown",
                                response="",
                                success=False,
                                error=f"Watchdog timeout: task melebihi batas {int(timeout)} detik",
                            )
                        continue

                # Forward any remaining events
                while not agent_queue.empty():
                    try:
                        ui_event_queue.put_nowait(agent_queue.get_nowait())
                    except Exception:
                        pass

                result = exec_task.result()
                completed_count += 1

                # Emit progress with [X/Y] format
                status_icon = "✅" if result.success else "❌"
                ui_event_queue.put_nowait(OrchestratorEvent("status",
                    f"  {status_icon} [{completed_count}/{total}] "
                    f"{result.task_id}: "
                    f"{'selesai' if result.success else 'gagal'}"
                    f"{f' — {result.error[:80]}' if not result.success and result.error else ''}"
                ))

                return result

            except asyncio.CancelledError:
                completed_count += 1
                return SubTaskResult(
                    task_id=st.id,
                    description=st.description[:100],
                    agent_type=agent_type,
                    model_used=st.assigned_model or "unknown",
                    response="",
                    success=False,
                    error="Task cancelled",
                )
            except Exception as e:
                completed_count += 1
                log.error("Command Center task exception",
                          task_id=st.id, error=str(e)[:200])
                return SubTaskResult(
                    task_id=st.id,
                    description=st.description[:100],
                    agent_type=agent_type,
                    model_used=st.assigned_model or "unknown",
                    response="",
                    success=False,
                    error=str(e)[:200],
                )

        # ── True Parallel Execution via asyncio.gather ────────────────────
        parallel_results = await asyncio.gather(
            *[
                _run_task_with_watchdog(st, i)
                for i, st in enumerate(group_tasks)
            ],
            return_exceptions=True,
        )

        # Mark all agents as idle
        for st in group_tasks:
            agent_registry.mark_idle(st.assigned_agent or "general", st.id)

        # Process results (handle any exceptions from gather)
        final_results = []
        for i, pr in enumerate(parallel_results):
            if isinstance(pr, Exception):
                log.error("Command Center task failed with exception",
                          error=str(pr)[:200])
                st = group_tasks[i]
                final_results.append(SubTaskResult(
                    task_id=st.id,
                    description=st.description[:100] if hasattr(st, 'description') else "unknown",
                    agent_type=st.assigned_agent or "unknown",
                    model_used=st.assigned_model or "unknown",
                    response="",
                    success=False,
                    error=str(pr)[:200],
                ))
            else:
                final_results.append(pr)

        # Summary
        success_count = sum(1 for r in final_results if r.success)
        fail_count = total - success_count
        ui_event_queue.put_nowait(OrchestratorEvent("status",
            f"🏛️ **Command Center**: Selesai — "
            f"{success_count} berhasil, {fail_count} gagal dari {total} tugas"
        ))

        return final_results


command_center = CommandCenter()

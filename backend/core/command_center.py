"""
Command Center Skill
====================
Pusat koordinasi untuk mengeksekusi banyak agent secara paralel (simultan).
Mengelola resource sharing, status emisi untuk UI, dan pengumpulan hasil
dari tim digital yang dikerahkan.
"""

import asyncio
from typing import List, Callable, Any, Optional
import structlog

from core.dag_builder import SubTask
from core.result_aggregator import SubTaskResult
from core.process_emitter import OrchestratorEvent
from agents.agent_registry import agent_registry

log = structlog.get_logger()

class CommandCenter:
    """Koordinator eksekusi paralel multi-agent."""

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
        Mengembalikan daftar hasil eksekusi (SubTaskResult).
        """
        if not group_tasks:
            return []

        team = [st.assigned_agent or "general" for st in group_tasks]
        team_str = ", ".join(set(team))

        # Emit Command Center status
        ui_event_queue.put_nowait(OrchestratorEvent("status",
            f"🏛️ **Command Center**: Mengoordinasikan tim digital ({team_str}) untuk mengeksekusi {len(group_tasks)} tugas secara paralel..."
        ))

        # Mark all agents as busy
        for st in group_tasks:
            agent_registry.mark_busy(st.assigned_agent or "general", st.id)

        # Buat task wrapper untuk menangkap event dari masing-masing agent
        async def _run_task(st: SubTask) -> SubTaskResult:
            agent_queue = asyncio.Queue()
            
            # Start execution task
            exec_task = asyncio.create_task(
                execute_fn(st, system_prompt, history, spec, agent_queue, project_path=project_path)
            )

            # Forward events while executing
            while not exec_task.done():
                try:
                    event = await asyncio.wait_for(agent_queue.get(), timeout=0.2)
                    ui_event_queue.put_nowait(event)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    log.warning("Queue error in command center", error=str(e))

            # Forward any remaining events
            while not agent_queue.empty():
                try:
                    ui_event_queue.put_nowait(agent_queue.get_nowait())
                except Exception:
                    pass

            return exec_task.result()

        # Run all agents concurrently
        gather_task = asyncio.create_task(
            asyncio.gather(*[_run_task(st) for st in group_tasks], return_exceptions=True)
        )

        await gather_task
        parallel_results = gather_task.result()

        # Mark all agents as idle
        for st in group_tasks:
            agent_registry.mark_idle(st.assigned_agent or "general", st.id)

        # Process results
        final_results = []
        for pr in parallel_results:
            if isinstance(pr, Exception):
                log.error("Command Center task failed with exception", error=str(pr)[:200])
                final_results.append(SubTaskResult(
                    task_id="error",
                    description="Execution error",
                    agent_type="unknown",
                    model_used="unknown",
                    response="",
                    success=False,
                    error=str(pr)[:200],
                ))
            else:
                final_results.append(pr)

        return final_results

command_center = CommandCenter()

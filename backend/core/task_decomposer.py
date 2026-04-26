"""
Super Agent Orchestrator — Task Decomposer
Uses LLM to break complex tasks into atomic subtasks with dependencies.
Implements HTN (Hierarchical Task Network) style decomposition.
"""
import json
import time
from typing import List, Optional, Dict
import structlog

from core.model_manager import model_manager
from core.dag_builder import SubTask
from core.request_preprocessor import TaskSpecification

log = structlog.get_logger()


DECOMPOSITION_PROMPT = """You are the AI Orchestrator Task Decomposition Engine.
Your job is to break complex user requests into atomic, executable subtasks.

RULES:
1. Each subtask must be small enough for a SINGLE AI agent to handle
2. Identify dependencies between subtasks (what must complete before what)
3. Maximize parallelism — make tasks independent where possible
4. Each subtask must have a clear, specific deliverable

Available task_type values:
- reasoning: complex logic, analysis, planning, strategy
- coding: writing/debugging/refactoring code
- research: gathering information, searching, comparing
- writing: creating content, documentation, translation
- system: VPS/server management, terminal commands
- file_operation: reading/writing/editing files
- creative: brainstorming, design, ideation
- validation: checking, testing, verifying other outputs

Output ONLY valid JSON in this exact format:
{
    "subtasks": [
        {
            "id": "task_0",
            "description": "Detailed description of what this subtask should accomplish",
            "task_type": "coding",
            "required_skills": ["python", "api"],
            "dependencies": [],
            "estimated_complexity": 0.5,
            "priority": 1
        },
        {
            "id": "task_1",
            "description": "Another subtask that depends on task_0",
            "task_type": "validation",
            "required_skills": ["testing"],
            "dependencies": ["task_0"],
            "estimated_complexity": 0.3,
            "priority": 2
        }
    ],
    "reasoning": "I decomposed this into X subtasks because..."
}

IMPORTANT:
- Use "task_0", "task_1", "task_2" etc as IDs
- dependencies is a LIST of task IDs that must complete BEFORE this task
- If a task has NO dependencies, set dependencies to []
- Tasks with same priority and no mutual dependencies can run in PARALLEL
- For simple requests, create just 1 subtask
- Maximum 6 subtasks per request (to avoid over-decomposition)
"""


class TaskDecomposer:
    """
    Decomposes complex tasks into atomic subtasks using LLM.
    """

    async def decompose(self, spec: TaskSpecification) -> List[SubTask]:
        """
        Decompose a TaskSpecification into a list of SubTasks.
        For simple tasks, returns a single subtask (no overhead).
        """
        start = time.time()

        # Simple tasks don't need decomposition
        if spec.is_simple or not spec.requires_multi_agent:
            return self._create_single_subtask(spec)

        try:
            subtasks = await self._decompose_with_llm(spec)
            elapsed = int((time.time() - start) * 1000)
            log.info("Task decomposed",
                     subtasks=len(subtasks), time_ms=elapsed,
                     intent=spec.primary_intent)
            return subtasks

        except Exception as e:
            log.warning("Decomposition failed, using single task", error=str(e)[:100])
            return self._create_single_subtask(spec)

    async def _decompose_with_llm(self, spec: TaskSpecification) -> List[SubTask]:
        """Use LLM to decompose the task."""
        fast_model = self._get_decomposition_model()

        # Build context-rich prompt
        context = f"""User Request:
{spec.original_message}

Analysis:
- Primary Intent: {spec.primary_intent}
- All Intents: {', '.join(spec.intents)}
- Complexity: {spec.complexity_score}
- Quality Priority: {spec.quality_priority}
- Success Criteria: {', '.join(spec.success_criteria) if spec.success_criteria else 'Not specified'}
"""

        messages = [
            {"role": "system", "content": DECOMPOSITION_PROMPT},
            {"role": "user", "content": context},
        ]

        result_str = await model_manager.chat_completion(
            model=fast_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1500,
        )

        # Parse JSON
        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()

        data = json.loads(result_str)
        raw_tasks = data.get("subtasks", [])

        # Convert to SubTask objects
        subtasks = []
        for raw in raw_tasks[:6]:  # cap at 6
            st = SubTask(
                id=raw.get("id", f"task_{len(subtasks)}"),
                description=raw.get("description", ""),
                task_type=raw.get("task_type", spec.primary_intent),
                required_skills=raw.get("required_skills", []),
                dependencies=raw.get("dependencies", []),
                estimated_complexity=min(1.0, max(0.0, raw.get("estimated_complexity", 0.5))),
                priority=raw.get("priority", 1),
            )
            subtasks.append(st)

        if not subtasks:
            return self._create_single_subtask(spec)

        return subtasks

    def _create_single_subtask(self, spec: TaskSpecification) -> List[SubTask]:
        """Create a single subtask for simple/non-decomposable requests."""
        return [SubTask(
            id="task_0",
            description=spec.original_message,
            task_type=spec.primary_intent,
            required_skills=spec.intents,
            dependencies=[],
            estimated_complexity=spec.complexity_score,
            priority=1,
        )]

    def _get_decomposition_model(self) -> str:
        """Pick a good model for decomposition (needs to be smart but reasonably fast)."""
        priorities = ["gpt-4o-mini", "deepseek-v3-2", "qwen3.6-flash",
                       "gemini-2.5-flash-lite"]
        for p in priorities:
            for k in model_manager.available_models.keys():
                if p in k:
                    return k
        return model_manager.get_default_model()


task_decomposer = TaskDecomposer()

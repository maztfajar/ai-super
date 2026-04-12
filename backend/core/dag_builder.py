"""
Super Agent Orchestrator — DAG Builder
Constructs and validates Directed Acyclic Graphs for task execution planning.
Supports topological sorting, parallel group identification, and critical path analysis.
"""
import json
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import structlog

log = structlog.get_logger()


@dataclass
class SubTask:
    """Represents a single atomic subtask in the execution plan."""
    id: str
    description: str
    task_type: str                        # coding, research, analysis, writing, etc
    required_skills: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # IDs of subtasks that must complete first
    estimated_complexity: float = 0.5     # 0.0-1.0
    estimated_tokens: int = 1000
    priority: int = 1                     # 1=highest
    max_retries: int = 2
    timeout_seconds: int = 120
    # Filled during execution
    assigned_model: Optional[str] = None
    assigned_agent: Optional[str] = None
    status: str = "pending"               # pending | running | completed | failed
    result: Optional[str] = None
    confidence: float = 0.0
    execution_time_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionGroup:
    """A group of subtasks that can execute in parallel."""
    level: int                             # execution order (0 = first)
    task_ids: List[str]                    # subtask IDs in this group
    depends_on_levels: List[int] = field(default_factory=list)


@dataclass
class ExecutionDAG:
    """Complete execution plan as a DAG."""
    subtasks: Dict[str, SubTask]           # id -> SubTask
    execution_order: List[ExecutionGroup]   # ordered groups for execution
    critical_path: List[str] = field(default_factory=list)  # IDs on the critical path
    total_estimated_time_ms: int = 0
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "subtasks": {k: v.to_dict() for k, v in self.subtasks.items()},
            "execution_order": [
                {"level": g.level, "task_ids": g.task_ids, "depends_on": g.depends_on_levels}
                for g in self.execution_order
            ],
            "critical_path": self.critical_path,
            "total_estimated_time_ms": self.total_estimated_time_ms,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class DAGBuilder:
    """
    Builds and validates execution DAGs from subtask lists.
    """

    def build(self, subtasks: List[SubTask]) -> ExecutionDAG:
        """Build a complete execution DAG from a list of subtasks."""
        task_map = {st.id: st for st in subtasks}
        dag = ExecutionDAG(subtasks=task_map, execution_order=[])

        # Validate
        errors = self._validate(task_map)
        if errors:
            dag.is_valid = False
            dag.validation_errors = errors
            log.warning("DAG validation failed", errors=errors)
            # Still try to build a best-effort plan
            # Remove invalid dependencies
            valid_ids = set(task_map.keys())
            for st in task_map.values():
                st.dependencies = [d for d in st.dependencies if d in valid_ids]

        # Topological sort into execution groups
        dag.execution_order = self._topological_group_sort(task_map)

        # Find critical path
        dag.critical_path = self._find_critical_path(task_map)

        # Estimate total time (critical path time)
        dag.total_estimated_time_ms = sum(
            task_map[tid].timeout_seconds * 1000
            for tid in dag.critical_path
        )

        log.info("DAG built",
                 tasks=len(task_map),
                 groups=len(dag.execution_order),
                 critical_path_len=len(dag.critical_path),
                 valid=dag.is_valid)

        return dag

    def _validate(self, task_map: Dict[str, SubTask]) -> List[str]:
        """Validate the task graph for errors."""
        errors = []

        # Check for missing dependencies
        for tid, task in task_map.items():
            for dep in task.dependencies:
                if dep not in task_map:
                    errors.append(f"Task '{tid}' depends on non-existent task '{dep}'")

        # Check for circular dependencies
        if self._has_cycle(task_map):
            errors.append("Circular dependency detected in task graph")

        # Check for self-dependencies
        for tid, task in task_map.items():
            if tid in task.dependencies:
                errors.append(f"Task '{tid}' depends on itself")

        return errors

    def _has_cycle(self, task_map: Dict[str, SubTask]) -> bool:
        """Detect cycles using DFS with coloring."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in task_map}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for dep in task_map[node].dependencies:
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    return True  # back edge = cycle
                if color[dep] == WHITE and dfs(dep):
                    return True
            color[node] = BLACK
            return False

        for tid in task_map:
            if color[tid] == WHITE:
                if dfs(tid):
                    return True
        return False

    def _topological_group_sort(self, task_map: Dict[str, SubTask]) -> List[ExecutionGroup]:
        """
        Topological sort that groups independent tasks together.
        Tasks in the same group can execute in parallel.
        """
        if not task_map:
            return []

        # Build in-degree map
        in_degree = {tid: 0 for tid in task_map}
        for tid, task in task_map.items():
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[tid] += 1

        # BFS level-by-level (Kahn's algorithm variant)
        groups = []
        level = 0
        remaining = set(task_map.keys())

        while remaining:
            # Find all tasks with no pending dependencies
            ready = [
                tid for tid in remaining
                if in_degree.get(tid, 0) == 0
            ]

            if not ready:
                # Should not happen if no cycles, but safeguard
                log.warning("DAG sort stuck — forcing remaining tasks", remaining=list(remaining))
                ready = list(remaining)

            group = ExecutionGroup(
                level=level,
                task_ids=sorted(ready, key=lambda t: task_map[t].priority),
                depends_on_levels=list(range(level)) if level > 0 else [],
            )
            groups.append(group)

            # Remove completed tasks and update in-degrees
            for tid in ready:
                remaining.discard(tid)
                # Reduce in-degree for tasks that depend on this one
                for other_id, other_task in task_map.items():
                    if tid in other_task.dependencies:
                        in_degree[other_id] = max(0, in_degree.get(other_id, 1) - 1)

            level += 1

        return groups

    def _find_critical_path(self, task_map: Dict[str, SubTask]) -> List[str]:
        """
        Find the critical path (longest path through the DAG).
        Uses the estimated timeout as the "weight" for each task.
        """
        if not task_map:
            return []

        # Compute longest path to each node
        dist: Dict[str, int] = {}
        parent: Dict[str, Optional[str]] = {}

        # Topological order
        topo = self._topological_sort_flat(task_map)

        for tid in topo:
            dist[tid] = task_map[tid].timeout_seconds
            parent[tid] = None

        for tid in topo:
            for other_id, other_task in task_map.items():
                if tid in other_task.dependencies:
                    new_dist = dist[tid] + other_task.timeout_seconds
                    if new_dist > dist.get(other_id, 0):
                        dist[other_id] = new_dist
                        parent[other_id] = tid

        if not dist:
            return []

        # Trace back from the node with the longest distance
        end_node = max(dist, key=lambda k: dist[k])
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = parent.get(current)
        path.reverse()

        return path

    def _topological_sort_flat(self, task_map: Dict[str, SubTask]) -> List[str]:
        """Flat topological sort (single list, not grouped)."""
        in_degree = {tid: 0 for tid in task_map}
        for tid, task in task_map.items():
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[tid] += 1

        queue = deque(tid for tid, d in in_degree.items() if d == 0)
        result = []

        while queue:
            tid = queue.popleft()
            result.append(tid)
            for other_id, other_task in task_map.items():
                if tid in other_task.dependencies:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        return result

    def build_single_task(self, task_type: str, description: str) -> ExecutionDAG:
        """Convenience: build a DAG with a single task (no decomposition needed)."""
        subtask = SubTask(
            id="task_0",
            description=description,
            task_type=task_type,
            required_skills=[task_type],
            dependencies=[],
            estimated_complexity=0.3,
        )
        return self.build([subtask])


dag_builder = DAGBuilder()

"""
DAG Manager (v2.0 — Checkpoint & Resume)
=========================================
Manages a Directed Acyclic Graph (DAG) of sub-tasks for the orchestrator.
Ensures tasks are executed only when their dependencies are met.

v2.0 Enhancements:
  1. Checkpoint persistence — save/load DAG state to SQLite
  2. Cascade skip — if a dependency fails, downstream nodes are auto-skipped
  3. Progress indicator — [X/Y] formatted string for UI streaming
  4. Timestamps — track when each node starts and finishes
"""

import asyncio
import json
import structlog
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone

log = structlog.get_logger()


class DAGNode(BaseModel):
    id: str
    agent_type: str
    task: str
    dependencies: List[str] = []
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[Any] = None
    files_affected: List[str] = []
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class DAGManager:
    """
    Manages a Directed Acyclic Graph (DAG) of sub-tasks for the orchestrator.
    Supports checkpointing to persistent storage and resume after interruption.
    """

    def __init__(self, dag_json: str, task_id: Optional[str] = None):
        self.task_id = task_id
        try:
            data = json.loads(dag_json)
            # Support both {nodes: [...]} and list [...] formats
            nodes_data = data.get("nodes", []) if isinstance(data, dict) else data
            self.nodes: Dict[str, DAGNode] = {
                node["id"]: DAGNode(**node) for node in nodes_data
            }
        except Exception as e:
            log.error("DAGManager: Failed to parse DAG JSON", error=str(e))
            self.nodes = {}

    # ── Node state transitions ───────────────────────────────────────────────

    def get_ready_nodes(self) -> List[DAGNode]:
        """Returns nodes that have all dependencies completed and are still pending."""
        ready = []
        for node in self.nodes.values():
            if node.status != "pending":
                continue

            # Check for failed dependencies → cascade skip
            deps_failed = any(
                dep_id in self.nodes
                and self.nodes[dep_id].status in ("failed", "skipped")
                for dep_id in node.dependencies
            )
            if deps_failed:
                self.mark_skipped(node.id, "Dependency failed — skipped automatically")
                continue

            # Check all deps completed
            deps_met = all(
                dep_id in self.nodes and self.nodes[dep_id].status == "completed"
                for dep_id in node.dependencies
            )
            if deps_met:
                ready.append(node)
        return ready

    def mark_running(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "running"
            self.nodes[node_id].started_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self, node_id: str, result: Any = None):
        if node_id in self.nodes:
            self.nodes[node_id].status = "completed"
            self.nodes[node_id].result = result
            self.nodes[node_id].completed_at = datetime.now(timezone.utc).isoformat()
            log.info("DAGManager: Task completed", task_id=node_id)

    def mark_failed(self, node_id: str, error: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "failed"
            self.nodes[node_id].result = error
            self.nodes[node_id].error_message = error
            self.nodes[node_id].completed_at = datetime.now(timezone.utc).isoformat()
            log.error("DAGManager: Task failed", task_id=node_id, error=error)

    def mark_skipped(self, node_id: str, reason: str = ""):
        """Mark a node as skipped (e.g. dependency failure cascade)."""
        if node_id in self.nodes:
            self.nodes[node_id].status = "skipped"
            self.nodes[node_id].error_message = reason or "Skipped due to dependency failure"
            self.nodes[node_id].completed_at = datetime.now(timezone.utc).isoformat()
            log.warning("DAGManager: Task skipped", task_id=node_id, reason=reason)

    # ── Status queries ───────────────────────────────────────────────────────

    def is_finished(self) -> bool:
        """Returns True if all nodes are in a terminal state."""
        if not self.nodes:
            return True
        return all(
            node.status in ("completed", "failed", "skipped")
            for node in self.nodes.values()
        )

    def has_errors(self) -> bool:
        """Returns True if any node has failed."""
        return any(node.status == "failed" for node in self.nodes.values())

    def get_progress(self) -> Dict[str, int]:
        total = len(self.nodes)
        completed = sum(1 for n in self.nodes.values() if n.status == "completed")
        failed = sum(1 for n in self.nodes.values() if n.status == "failed")
        skipped = sum(1 for n in self.nodes.values() if n.status == "skipped")
        running = sum(1 for n in self.nodes.values() if n.status == "running")
        pending = sum(1 for n in self.nodes.values() if n.status == "pending")
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "pending": pending,
        }

    def get_progress_str(self) -> str:
        """Returns a human-readable progress string like [3/5]."""
        p = self.get_progress()
        done = p["completed"] + p["failed"] + p["skipped"]
        return f"[{done}/{p['total']}]"

    def get_completed_results(self) -> Dict[str, Any]:
        """Returns results of all completed nodes."""
        return {
            nid: node.result
            for nid, node in self.nodes.items()
            if node.status == "completed" and node.result is not None
        }

    def to_json(self) -> str:
        return json.dumps({
            "nodes": [node.dict() for node in self.nodes.values()]
        })

    # ── Checkpoint Persistence (SQLite) ──────────────────────────────────────

    async def save_checkpoint(self):
        """Persist current DAG state to SQLite for resume capability."""
        if not self.task_id:
            return
        try:
            from db.database import AsyncSessionLocal
            from db.models import ExecutionCheckpoint
            from sqlmodel import select

            checkpoint_data = {
                "dag_json": self.to_json(),
                "progress": self.get_progress(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ExecutionCheckpoint).where(
                        ExecutionCheckpoint.task_id == self.task_id
                    )
                )
                cp = result.scalars().first()
                if cp:
                    cp.checkpoint_data_json = json.dumps(checkpoint_data)
                else:
                    cp = ExecutionCheckpoint(
                        task_id=self.task_id,
                        checkpoint_data_json=json.dumps(checkpoint_data),
                    )
                db.add(cp)
                # ── Fix Point #1: Shield DB commit from cancellation ────────────
                await asyncio.shield(db.commit())
            log.debug("DAG checkpoint saved", task_id=self.task_id,
                      progress=self.get_progress())
        except Exception as e:
            log.debug("DAG checkpoint save failed", error=str(e)[:80])

    @classmethod
    async def load_from_checkpoint(cls, task_id: str) -> Optional["DAGManager"]:
        """Restore DAG state from last saved checkpoint."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ExecutionCheckpoint
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ExecutionCheckpoint).where(
                        ExecutionCheckpoint.task_id == task_id
                    )
                )
                cp = result.scalars().first()
                if not cp:
                    return None

                data = json.loads(cp.checkpoint_data_json)
                dag_json = data.get("dag_json")
                if not dag_json:
                    return None

                manager = cls(dag_json, task_id=task_id)
                log.info("DAG restored from checkpoint",
                         task_id=task_id, progress=manager.get_progress())
                return manager
        except Exception as e:
            log.debug("DAG checkpoint load failed", error=str(e)[:80])
            return None

import json
import structlog
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

log = structlog.get_logger()

class DAGNode(BaseModel):
    id: str
    agent_type: str
    task: str
    dependencies: List[str] = []
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    files_affected: List[str] = []

class DAGManager:
    """
    Manages a Directed Acyclic Graph (DAG) of sub-tasks for the orchestrator.
    Ensures tasks are executed only when their dependencies are met.
    """
    def __init__(self, dag_json: str):
        try:
            data = json.loads(dag_json)
            # Support both {nodes: [...]} and list [...] formats
            nodes_data = data.get("nodes", []) if isinstance(data, dict) else data
            self.nodes: Dict[str, DAGNode] = {node["id"]: DAGNode(**node) for node in nodes_data}
        except Exception as e:
            log.error("DAGManager: Failed to parse DAG JSON", error=str(e))
            self.nodes = {}

    def get_ready_nodes(self) -> List[DAGNode]:
        """Returns nodes that have all dependencies completed and are still pending."""
        ready = []
        for node in self.nodes.values():
            if node.status == "pending":
                # Check if all dependencies exist and are completed
                deps_met = True
                for dep_id in node.dependencies:
                    if dep_id not in self.nodes or self.nodes[dep_id].status != "completed":
                        deps_met = False
                        break
                if deps_met:
                    ready.append(node)
        return ready

    def mark_running(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "running"

    def mark_completed(self, node_id: str, result: Any = None):
        if node_id in self.nodes:
            self.nodes[node_id].status = "completed"
            self.nodes[node_id].result = result
            log.info("DAGManager: Task completed", task_id=node_id)

    def mark_failed(self, node_id: str, error: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "failed"
            self.nodes[node_id].result = error
            log.error("DAGManager: Task failed", task_id=node_id, error=error)

    def is_finished(self) -> bool:
        """Returns True if all nodes are in a terminal state (completed or failed)."""
        if not self.nodes:
            return True
        return all(node.status in ["completed", "failed"] for node in self.nodes.values())

    def has_errors(self) -> bool:
        """Returns True if any node has failed."""
        return any(node.status == "failed" for node in self.nodes.values())

    def get_progress(self) -> Dict[str, int]:
        total = len(self.nodes)
        completed = sum(1 for node in self.nodes.values() if node.status == "completed")
        failed = sum(1 for node in self.nodes.values() if node.status == "failed")
        return {"total": total, "completed": completed, "failed": failed}

    def to_json(self) -> str:
        return json.dumps({
            "nodes": [node.dict() for node in self.nodes.values()]
        })

"""
Super Agent Orchestrator — Metrics & Performance Tracking Engine
Tracks agent performance per task type to enable continuous learning.
"""
import time
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import structlog

log = structlog.get_logger()


@dataclass
class AgentMetric:
    """Single execution metric record."""
    agent_type: str
    model_used: str
    task_type: str
    success: bool
    confidence: float
    execution_time_ms: int
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentPerformanceSummary:
    """Aggregated performance summary for an agent/model combo."""
    agent_type: str
    model_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_confidence: float = 0.0
    avg_execution_time_ms: float = 0.0
    total_cost_usd: float = 0.0
    success_rate: float = 0.0
    # Per-task-type breakdown
    task_type_stats: Dict[str, dict] = field(default_factory=dict)


class MetricsEngine:
    """
    Collects, stores, and queries agent performance metrics.
    Uses both in-memory cache (hot) and database (persistent).
    """

    def __init__(self):
        # In-memory rolling window for hot metrics (last 24h)
        self._hot_metrics: List[AgentMetric] = []
        self._max_hot_size = 5000
        # Cached performance summaries (recomputed periodically)
        self._summaries: Dict[str, AgentPerformanceSummary] = {}
        self._last_summary_compute = 0.0

    async def record(self, metric: AgentMetric, task_id: Optional[str] = None):
        """Record a single agent execution metric."""
        # Add to hot cache
        self._hot_metrics.append(metric)
        if len(self._hot_metrics) > self._max_hot_size:
            self._hot_metrics = self._hot_metrics[-self._max_hot_size:]

        # Persist to database
        try:
            from db.database import AsyncSessionLocal
            from db.models import AgentPerformance
            async with AsyncSessionLocal() as db:
                entry = AgentPerformance(
                    agent_type=metric.agent_type,
                    model_used=metric.model_used,
                    task_type=metric.task_type,
                    task_id=task_id,
                    success=metric.success,
                    confidence=metric.confidence,
                    execution_time_ms=metric.execution_time_ms,
                    tokens_input=metric.tokens_input,
                    tokens_output=metric.tokens_output,
                    cost_usd=metric.cost_usd,
                    error_message=metric.error_message,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            log.warning("Failed to persist metric", error=str(e)[:100])

        # Invalidate summary cache
        self._last_summary_compute = 0.0
        log.debug("Metric recorded", agent=metric.agent_type, model=metric.model_used,
                   success=metric.success, time_ms=metric.execution_time_ms)

    def get_hot_summary(self, model_id: Optional[str] = None,
                         task_type: Optional[str] = None) -> Dict:
        """Get performance summary from hot cache (fast, in-memory)."""
        now = time.time()
        cutoff = now - 86400  # last 24 hours

        filtered = [
            m for m in self._hot_metrics
            if m.timestamp > cutoff
            and (model_id is None or m.model_used == model_id)
            and (task_type is None or m.task_type == task_type)
        ]

        if not filtered:
            return {
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_time_ms": 0.0,
                "total_cost": 0.0,
            }

        successful = sum(1 for m in filtered if m.success)
        return {
            "total_tasks": len(filtered),
            "success_rate": successful / len(filtered),
            "avg_confidence": sum(m.confidence for m in filtered) / len(filtered),
            "avg_time_ms": sum(m.execution_time_ms for m in filtered) / len(filtered),
            "total_cost": sum(m.cost_usd for m in filtered),
        }

    def get_model_score(self, model_id: str, task_type: str) -> float:
        """
        Get historical performance score for a model on a specific task type.
        Returns 0.0-1.0 (higher is better). Used by AgentScorer.
        """
        relevant = [
            m for m in self._hot_metrics
            if m.model_used == model_id and m.task_type == task_type
            and m.timestamp > time.time() - 604800  # last 7 days
        ]

        if not relevant:
            return 0.5  # neutral score if no history

        # Weighted recent performance
        scores = []
        now = time.time()
        for m in relevant:
            age_hours = (now - m.timestamp) / 3600
            recency_weight = max(0.1, 1.0 - (age_hours / 168))  # decay over 7 days
            score = (
                (1.0 if m.success else 0.0) * 0.5 +
                m.confidence * 0.3 +
                max(0, 1.0 - m.execution_time_ms / 30000) * 0.2  # faster = better, cap at 30s
            )
            scores.append(score * recency_weight)

        weights = [max(0.1, 1.0 - ((now - m.timestamp) / 3600) / 168) for m in relevant]
        return sum(scores) / sum(weights) if weights else 0.5

    async def get_all_summaries(self) -> List[Dict]:
        """Get aggregated summaries for all agent/model combos (from DB)."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import AgentPerformance
            from sqlmodel import select, func
            from sqlalchemy import desc

            async with AsyncSessionLocal() as db:
                # Get unique model/agent combos with stats
                result = await db.execute(
                    select(
                        AgentPerformance.model_used,
                        AgentPerformance.agent_type,
                        func.count(AgentPerformance.id).label("total"),
                        func.sum(AgentPerformance.success.cast(int)).label("successes"),
                        func.avg(AgentPerformance.confidence).label("avg_conf"),
                        func.avg(AgentPerformance.execution_time_ms).label("avg_time"),
                        func.sum(AgentPerformance.cost_usd).label("total_cost"),
                    )
                    .group_by(AgentPerformance.model_used, AgentPerformance.agent_type)
                    .order_by(desc("total"))
                )
                rows = result.all()

            return [
                {
                    "model": r[0],
                    "agent_type": r[1],
                    "total_tasks": r[2],
                    "successful_tasks": r[3] or 0,
                    "success_rate": (r[3] or 0) / r[2] if r[2] else 0,
                    "avg_confidence": round(r[4] or 0, 3),
                    "avg_time_ms": round(r[5] or 0, 0),
                    "total_cost": round(r[6] or 0, 4),
                }
                for r in rows
            ]
        except Exception as e:
            log.warning("Failed to get summaries", error=str(e)[:100])
            return []

    async def get_recent_executions(self, limit: int = 50) -> List[Dict]:
        """Get recent task executions for monitoring dashboard."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import TaskExecution
            from sqlmodel import select
            from sqlalchemy import desc

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(TaskExecution)
                    .order_by(desc(TaskExecution.created_at))
                    .limit(limit)
                )
                rows = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "status": r.status,
                    "request": (r.original_request or "")[:100],
                    "agents_used": json.loads(r.agents_used) if r.agents_used else [],
                    "time_ms": r.total_time_ms,
                    "tokens": r.total_tokens,
                    "cost": r.total_cost_usd,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        except Exception as e:
            log.warning("Failed to get recent executions", error=str(e)[:100])
            return []

    async def get_dashboard_stats(self) -> Dict:
        """Aggregate stats for the monitoring dashboard."""
        hot = self.get_hot_summary()
        summaries = await self.get_all_summaries()
        recent = await self.get_recent_executions(limit=10)

        return {
            "last_24h": hot,
            "all_time_summaries": summaries,
            "recent_executions": recent,
        }


metrics_engine = MetricsEngine()

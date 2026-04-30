"""
Super Agent Orchestrator — Monitoring API
Exposes orchestrator performance metrics, agent health,
and task execution history for the monitoring dashboard.
"""
from fastapi import APIRouter
from core.metrics import metrics_engine
from core.error_recovery import error_recovery
from agents.agent_registry import agent_registry
from fastapi import Depends
from db.models import User
from core.auth import get_current_user, get_admin_user

router = APIRouter()


@router.get("/dashboard")
async def monitoring_dashboard():
    """Get monitoring dashboard data — aggregated stats, recent executions, agent health."""
    stats = await metrics_engine.get_dashboard_stats()
    health = error_recovery.get_health_status()
    recovery = error_recovery.get_recovery_stats()
    agents = agent_registry.list_for_api()
    active_agents = agent_registry.get_active_agents()

    return {
        "stats": stats,
        "agent_health": health,
        "recovery_stats": recovery,
        "registered_agents": agents,
        "active_agents": active_agents,
    }


@router.get("/agents")
async def list_agents():
    """List all registered agent types and their capabilities."""
    return {
        "agents": agent_registry.list_for_api(),
        "active_agents": agent_registry.get_active_agents()
    }


@router.get("/agent-performance")
async def agent_performance():
    """Get per-agent performance summaries from database."""
    summaries = await metrics_engine.get_all_summaries()
    return {"summaries": summaries}


@router.get("/recent-tasks")
async def recent_tasks(
    limit: int = 50,
):
    """Get recent task executions."""
    executions = await metrics_engine.get_recent_executions(limit=limit)
    return {"executions": executions}


@router.get("/health")
async def system_health():
    """Get health status of all models (circuit breaker state)."""
    return {
        "model_health": error_recovery.get_health_status(),
        "recovery_stats": error_recovery.get_recovery_stats(),
    }


@router.get("/active-sessions")
async def active_sessions():
    """
    Kembalikan daftar sesi chat aktif dengan model AI yang sedang dipakai.
    'Aktif' = sesi yang ada aktivitas dalam 30 menit terakhir.
    Returns summary of system-wide active sessions for monitoring.
    """
    from datetime import datetime, timedelta
    from sqlmodel import select, desc, func
    from db.database import AsyncSessionLocal
    from db.models import ChatSession, Message

    cutoff = datetime.utcnow() - timedelta(minutes=60)

    try:
        async with AsyncSessionLocal() as db:
            # Optimasi N+1 Query: Hitung total pesan per sesi menggunakan subquery/group by
            count_stmt = (
                select(Message.session_id, func.count(Message.id).label("cnt"))
                .group_by(Message.session_id)
            )
            count_res = await db.execute(count_stmt)
            msg_counts = {row.session_id: row.cnt for row in count_res.all()}

            # Ambil semua sesi yang updated dalam 60 menit terakhir (system-wide for monitoring)
            stmt = (
                select(ChatSession)
                .where(ChatSession.updated_at >= cutoff)
                .order_by(desc(ChatSession.updated_at))
                .limit(50)
            )
            res = await db.execute(stmt)
            sessions = res.scalars().all()

            result_sessions = []
            for session in sessions:
                # Ambil pesan terakhir untuk tahu model apa yang dipakai
                msg_stmt = (
                    select(Message)
                    .where(Message.session_id == session.id)
                    .order_by(desc(Message.created_at))
                    .limit(1)
                )
                msg_res = await db.execute(msg_stmt)
                last_msg = msg_res.scalars().first()

                msg_count = msg_counts.get(session.id, 0)
                model_used = session.model_used or "Unknown"
                last_role = None

                if last_msg:
                    model_used = last_msg.model or model_used
                    last_role = last_msg.role

                # Jika pesan terakhir dari user = AI belum membalas = sedang diproses
                is_streaming = (last_role == "user")

                result_sessions.append({
                    "session_id":    session.id,
                    "title":         session.title or "New Chat",
                    "model_used":    model_used,
                    "is_streaming":  is_streaming,
                    "msg_count":     msg_count,
                    "last_activity": session.updated_at.isoformat() if session.updated_at else None,
                    "created_at":    session.created_at.isoformat() if session.created_at else None,
                })

        return {"active_sessions": result_sessions, "cutoff_minutes": 60}
    except Exception as e:
        # Return empty list if database error (monitoring page should still work)
        return {"active_sessions": [], "cutoff_minutes": 60, "error": str(e)}


@router.get("/self-healing/events")
async def get_healing_events(
    limit: int = 20,
    user: User = Depends(get_current_user),
):
    """Ambil riwayat self-healing events."""
    from core.self_healing import self_healing_engine
    return {
        "events": self_healing_engine.get_recent_events(limit),
        "total":  len(self_healing_engine._events),
    }


@router.post("/self-healing/trigger")
async def trigger_healing_check(
    user: User = Depends(get_admin_user),
):
    """Trigger manual health check — hanya admin."""
    from core.self_healing import self_healing_engine
    await self_healing_engine._run_all_checks()
    events = self_healing_engine.get_recent_events(10)
    return {
        "status": "checked",
        "events_found": len(events),
        "events": events,
    }

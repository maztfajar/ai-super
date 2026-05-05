"""
AI ORCHESTRATOR — Capability Evolver API
Endpoints untuk mengontrol dan memonitor Capability Evolver.
"""

import asyncio
from fastapi import APIRouter, Depends
from core.auth import get_current_user
from db.models import User

router = APIRouter()


@router.post("/evolve")
async def trigger_evolution(user: User = Depends(get_current_user)):
    """Trigger siklus evolusi manual."""
    from core.capability_evolver import capability_evolver
    result = await capability_evolver.evolve_now(force=True)
    return result


@router.get("/rules")
async def list_rules(
    status: str = "active",
    min_confidence: float = 0.0,
    user: User = Depends(get_current_user),
):
    """Lihat semua rules yang dipelajari."""
    from core.evolution_store import evolution_store
    all_rules = evolution_store.list_rules_sync()
    if status != "all":
        all_rules = [r for r in all_rules if r["status"] == status]
    if min_confidence > 0:
        all_rules = [r for r in all_rules if r["confidence"] >= min_confidence]
    return {"rules": all_rules, "total": len(all_rules)}


@router.get("/stats")
async def evolver_stats(user: User = Depends(get_current_user)):
    """Statistik Capability Evolver."""
    from core.capability_evolver import capability_evolver
    from core.evolution_store import evolution_store
    return {
        "evolver": capability_evolver.get_status(),
        "store":   await evolution_store.get_all_stats(),
    }


@router.delete("/rules/{rule_id}")
async def deprecate_rule(
    rule_id: str,
    reason: str = "manual",
    user: User = Depends(get_current_user),
):
    """Deprecated rule tertentu secara manual."""
    from core.evolution_store import evolution_store
    success = await evolution_store.deprecate_rule(rule_id, reason)
    if not success:
        return {"status": "not_found", "rule_id": rule_id}
    return {"status": "deprecated", "rule_id": rule_id}

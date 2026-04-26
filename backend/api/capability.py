"""
AI ORCHESTRATOR — Capability API
Endpoints to view and manage the AI model capability map.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from core.auth import get_current_user
from core.capability_map import capability_map
from db.models import User
import structlog

log = structlog.get_logger()
router = APIRouter()


@router.get("/map")
async def get_capability_map(user: User = Depends(get_current_user)):
    """Return the full capability map for all detected models."""
    return {
        "status": "ok",
        "capability_map": capability_map.get_all(),
        "total_models": len(capability_map._map),
    }


@router.post("/sync")
async def trigger_sync(user: User = Depends(get_current_user)):
    """Manually trigger a capability sync (interview all models)."""
    import asyncio
    asyncio.create_task(capability_map.sync())
    return {"status": "sync_triggered", "message": "Capability sync dimulai di background."}


@router.get("/best")
async def get_best_model(
    intent: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """
    Return the best model for a given intent/capability requirement.
    Example: GET /api/capability/best?intent=image_gen
    """
    INTENT_TO_CAPS = {
        "image_gen":        {"image_gen"},
        "image_generation": {"image_gen"},
        "vision":           {"vision"},
        "audio":            {"audio", "tts"},
        "tts":              {"tts"},
        "coding":           {"coding"},
        "reasoning":        {"reasoning"},
        "analysis":         {"analysis", "reasoning"},
        "writing":          {"writing", "text"},
        "research":         {"search", "text"},
        "speed":            {"speed", "text"},
        "general":          {"text"},
    }

    required_caps = INTENT_TO_CAPS.get(intent or "general", {"text"})
    best = capability_map.find_best_model(required_caps)

    from core.model_manager import model_manager
    available = list(model_manager.available_models.keys())

    # List all models with this capability
    matching_models = [
        {"model_id": mid, "capabilities": sorted(capability_map.get_capabilities(mid))}
        for mid in available
        if required_caps & capability_map.get_capabilities(mid)
    ]

    return {
        "intent": intent,
        "required_capabilities": sorted(required_caps),
        "best_model": best,
        "matching_models": matching_models,
    }


@router.get("/model/{model_id:path}")
async def get_model_capabilities(
    model_id: str,
    user: User = Depends(get_current_user),
):
    """Get capabilities for a specific model."""
    caps = capability_map.get_capabilities(model_id)
    return {
        "model_id": model_id,
        "capabilities": sorted(caps),
        "has_vision": "vision" in caps,
        "has_audio": "audio" in caps,
        "has_image_gen": "image_gen" in caps,
        "has_tts": "tts" in caps,
    }

"""Remaining API routers bundled together"""

# ── models.py ──────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends
from db.models import User
from core.auth import get_current_user
from core.model_manager import model_manager
from core.config import settings
import json
from pathlib import Path

router = APIRouter()

# Helper: Get list of saved/installed models
CUSTOM_MODELS_FILE = Path(__file__).parent.parent.parent / ".custom_models.json"

def _get_saved_model_providers() -> dict:
    """Return dict of providers that are configured and saved.
    This checks .env and .custom_models.json to identify which providers are actually configured.
    """
    saved = {}
    
    # Check .env configured models
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."):
        saved["openai"] = True
    if settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("sk-ant-..."):
        saved["anthropic"] = True
    if settings.GOOGLE_API_KEY and not settings.GOOGLE_API_KEY.startswith("AIza..."):
        saved["google"] = True
    if settings.SUMOPOD_API_KEY and not settings.SUMOPOD_API_KEY.startswith("sk-..."):
        saved["sumopod"] = True
    # Ollama is always considered available (local)
    saved["ollama"] = True
    # Custom providers
    if CUSTOM_MODELS_FILE.exists():
        try:
            providers = json.loads(CUSTOM_MODELS_FILE.read_text(encoding="utf-8"))
            for p in providers:
                if p.get("status") in ("connected", "untested"):
                    saved[f"custom_{p.get('id')}"] = True
        except Exception:
            pass
    
    return saved

@router.get("")
async def list_models(user: User = Depends(get_current_user)):
    """Return all models (both saved and detected)"""
    all_models = await model_manager.get_status()
    return {"models": all_models}

@router.get("/saved")
async def list_saved_models(user: User = Depends(get_current_user)):
    """Return ONLY saved/installed models (configured via .env or .custom_models.json)"""
    all_models = await model_manager.get_status()
    saved_providers = _get_saved_model_providers()
    
    # Filter models: keep only those from saved providers
    filtered = []
    for model in all_models:
        provider = model.get("provider", "")
        model_id = model.get("id", "")
        
        # Check if provider is in saved list
        if provider in saved_providers:
            filtered.append(model)
        elif provider == "custom":
            # For custom models, check if specific custom provider is saved
            if "custom" in saved_providers or any(k.startswith("custom_") for k in saved_providers):
                filtered.append(model)
    
    return {"models": filtered, "total": len(filtered), "from_integrations": True}

@router.get("/default")
async def get_default(user: User = Depends(get_current_user)):
    return {"model": model_manager.get_default_model()}

@router.post("/reload-saved")
async def reload_saved_models(user: User = Depends(get_current_user)):
    """Reload model manager to pick up changes in .env or .custom_models.json"""
    await model_manager._detect_models()
    saved_resp = await list_saved_models(user)
    return {"status": "reloaded", "models": saved_resp["models"], "count": len(saved_resp["models"])}

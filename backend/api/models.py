"""Remaining API routers bundled together"""

# ── models.py ──────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends
from db.models import User
from core.auth import get_current_user
from core.model_manager import model_manager
from core.config import settings

router = APIRouter()

@router.get("/")
async def list_models(user: User = Depends(get_current_user)):
    return {"models": await model_manager.get_status()}

@router.get("/default")
async def get_default(user: User = Depends(get_current_user)):
    return {"model": model_manager.get_default_model()}

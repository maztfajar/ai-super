"""
AI ORCHESTRATOR — QMD API (The Token Killer)
Endpoint untuk test dan monitor QMD token savings.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from core.auth import get_current_user
from db.models import User

router = APIRouter()


class QMDTestRequest(BaseModel):
    messages: List[dict]       # [{"role": "user", "content": "..."}]
    query: str
    max_token_budget: int = 6000


@router.post("/test")
async def test_distill(
    req: QMDTestRequest,
    user: User = Depends(get_current_user),
):
    """Test QMD distillation pada messages yang diberikan."""
    from core.qmd import qmd
    distilled, result = qmd.distill(
        messages=req.messages,
        query=req.query,
        max_token_budget=req.max_token_budget,
    )
    return {
        "distilled_messages": distilled,
        "stats": {
            "original_messages": result.original_messages,
            "distilled_messages": result.distilled_messages,
            "original_tokens_est": result.original_tokens_est,
            "distilled_tokens_est": result.distilled_tokens_est,
            "savings_pct": result.savings_pct,
            "dropped_messages": result.dropped_messages,
            "trimmed_messages": result.trimmed_messages,
            "duration_ms": result.duration_ms,
        },
    }


@router.get("/info")
async def qmd_info(user: User = Depends(get_current_user)):
    """Informasi tentang QMD."""
    from core.qmd import DEFAULT_MAX_TOKENS, CHARS_PER_TOKEN, MIN_KEEP_MESSAGES
    return {
        "name": "QMD — The Token Killer",
        "version": "1.0",
        "description": "Query-aware Message Distiller untuk menghemat biaya API",
        "config": {
            "default_max_tokens": DEFAULT_MAX_TOKENS,
            "chars_per_token": CHARS_PER_TOKEN,
            "min_keep_messages": MIN_KEEP_MESSAGES,
        },
        "integration_points": [
            "orchestrator._handle_simple — simple path",
            "orchestrator._execute_subtask — complex/multi-agent path",
        ],
    }

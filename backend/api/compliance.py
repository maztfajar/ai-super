"""
Compliance & Security API Endpoints
- Approval system endpoints
- Cost tracking endpoints
- Audit logging endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import structlog

from db.database import get_db
from core.auth import get_current_user
from db.models import User
from core.approval_system import approval_system
from core.cost_tracking import cost_engine
from core.audit_logging import audit_logger

log = structlog.get_logger()
router = APIRouter()


# ═════════════════════════════════════════════════════════════════
#  APPROVAL SYSTEM ENDPOINTS
# ═════════════════════════════════════════════════════════════════

class ApprovalResponse(BaseModel):
    request_id: str
    status: str
    operation_type: str
    operation_detail: str
    risk_level: str


class ApprovalAction(BaseModel):
    action: str  # "approve" | "reject"
    reason: Optional[str] = ""  # For rejection


@router.get("/approvals/pending")
async def get_pending_approvals(
    user: User = Depends(get_current_user),
):
    """Get pending approval requests untuk user (atau admin melihat semua)."""
    requests = approval_system.get_pending_requests()
    
    # Admin bisa lihat semua, user hanya lihat milik mereka
    if user.role != "admin":
        # Filter untuk user ini saja
        requests = [r for r in requests if r.get("created_by") == user.id or True]
    
    return {
        "pending_count": len(requests),
        "requests": requests,
    }


@router.get("/approvals/{request_id}")
async def get_approval_request(
    request_id: str,
    user: User = Depends(get_current_user),
):
    """Get specific approval request."""
    request = approval_system.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    return request


@router.post("/approvals/{request_id}/approve")
async def approve_request(
    request_id: str,
    user: User = Depends(get_current_user),
):
    """Approve risky operation."""
    success = approval_system.approve_request(request_id, user.id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve this request")
    
    # Log approval
    from core.audit_logging import audit_logger, AuditEventType
    audit_logger.log_approval_granted(
        user_id=user.id,
        request_id=request_id,
        approved_by=user.id,
    )
    
    return {
        "status": "approved",
        "request_id": request_id,
        "approved_by": user.id,
    }


@router.post("/approvals/{request_id}/reject")
async def reject_request(
    request_id: str,
    action: ApprovalAction,
    user: User = Depends(get_current_user),
):
    """Reject risky operation."""
    success = approval_system.reject_request(
        request_id,
        user.id,
        action.reason or "No reason provided"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot reject this request")
    
    return {
        "status": "rejected",
        "request_id": request_id,
        "rejected_by": user.id,
    }


@router.get("/approvals/history")
async def get_approval_history(
    limit: int = 100,
    user: User = Depends(get_current_user),
):
    """Get approval history."""
    history = approval_system.get_history(limit)
    return {
        "total": len(history),
        "history": history,
    }


# ═════════════════════════════════════════════════════════════════
#  COST TRACKING ENDPOINTS
# ═════════════════════════════════════════════════════════════════

class BudgetSetRequest(BaseModel):
    monthly_limit_usd: float


@router.get("/costs/budget")
async def get_user_budget(
    user: User = Depends(get_current_user),
):
    """Get user cost budget."""
    budget = cost_engine.get_user_budget(user.id)
    return budget.to_dict()


@router.post("/costs/budget")
async def set_user_budget(
    request: BudgetSetRequest,
    user: User = Depends(get_current_user),
):
    """Set user monthly budget."""
    if request.monthly_limit_usd < 0:
        raise HTTPException(status_code=400, detail="Budget must be positive")
    
    cost_engine.set_user_budget(user.id, request.monthly_limit_usd)
    
    budget = cost_engine.get_user_budget(user.id)
    return budget.to_dict()


@router.get("/costs/stats")
async def get_cost_stats(
    days: int = 30,
    user: User = Depends(get_current_user),
):
    """Get user cost statistics."""
    stats = cost_engine.get_user_stats(user.id, days)
    return stats


@router.get("/costs/estimate")
async def estimate_request_cost(
    model_id: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    user: User = Depends(get_current_user),
):
    """Estimate cost sebelum execute request."""
    estimated_cost = cost_engine.estimate_cost(
        model_id,
        estimated_input_tokens,
        estimated_output_tokens,
    )
    
    budget = cost_engine.get_user_budget(user.id)
    
    return {
        "model_id": model_id,
        "estimated_cost_usd": round(estimated_cost, 6),
        "within_budget": estimated_cost <= budget.remaining_usd(),
        "remaining_budget_usd": round(budget.remaining_usd(), 2),
    }


@router.get("/costs/history")
async def get_cost_history(
    limit: int = 100,
    user: User = Depends(get_current_user),
):
    """Get cost history."""
    history = cost_engine.get_history(user.id, limit)
    return {
        "total": len(history),
        "history": history,
    }


# ═════════════════════════════════════════════════════════════════
#  AUDIT LOGGING ENDPOINTS
# ═════════════════════════════════════════════════════════════════

class AuditEventQuery(BaseModel):
    event_type: Optional[str] = None
    severity: Optional[str] = None
    limit: int = 100


@router.get("/audit/events")
async def get_audit_events(
    session_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
):
    """Query audit events (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    events = audit_logger.query_events(
        user_id=user.id,
        session_id=session_id,
        severity=severity,
        limit=limit,
    )
    
    return {
        "total": len(events),
        "events": events,
    }


@router.get("/audit/activity")
async def get_activity_summary(
    days: int = 7,
    user: User = Depends(get_current_user),
):
    """Get user activity summary."""
    summary = audit_logger.get_user_activity_summary(user.id, days)
    return summary


@router.get("/audit/export")
async def export_audit_logs(
    format: str = "json",  # json | csv | jsonl
    days: int = 30,
    user: User = Depends(get_current_user),
):
    """Export audit logs (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    events = audit_logger.query_events(
        user_id=None,  # Get all
        limit=10000,
    )
    
    if format == "json":
        return {
            "total": len(events),
            "events": events,
        }
    elif format == "csv":
        # Simple CSV export
        import csv
        import io
        
        output = io.StringIO()
        if events:
            writer = csv.DictWriter(output, fieldnames=events[0].keys())
            writer.writeheader()
            writer.writerows(events)
        
        return {
            "format": "csv",
            "content": output.getvalue(),
        }
    elif format == "jsonl":
        # JSON lines format
        import json
        lines = [json.dumps(e) for e in events]
        return {
            "format": "jsonl",
            "content": "\n".join(lines),
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


# ═════════════════════════════════════════════════════════════════
#  DASHBOARD ENDPOINTS
# ═════════════════════════════════════════════════════════════════

@router.get("/dashboard/compliance-overview")
async def get_compliance_overview(
    user: User = Depends(get_current_user),
):
    """Get compliance overview untuk user."""
    
    # Get all relevant data
    pending_approvals = approval_system.get_pending_requests()
    cost_stats = cost_engine.get_user_stats(user.id, days=7)
    activity = audit_logger.get_user_activity_summary(user.id, days=7)
    
    return {
        "pending_approvals": len(pending_approvals),
        "approval_requests": pending_approvals,
        "cost_stats": cost_stats,
        "activity_summary": activity,
        "timestamp": __import__("time").time(),
    }

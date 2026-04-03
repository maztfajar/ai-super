import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, WorkflowDef, WorkflowRun
from core.auth import get_current_user

router = APIRouter()

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nodes_json: str = "[]"
    edges_json: str = "[]"
    trigger_type: str = "manual"
    trigger_config: str = "{}"

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes_json: Optional[str] = None
    edges_json: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/")
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowDef)
        .where(WorkflowDef.user_id == user.id)
        .order_by(desc(WorkflowDef.created_at))
    )
    return result.scalars().all()

@router.post("/")
async def create_workflow(
    req: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wf = WorkflowDef(user_id=user.id, **req.dict())
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf

@router.put("/{wf_id}")
async def update_workflow(
    wf_id: str,
    req: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wf = await db.get(WorkflowDef, wf_id)
    if not wf or wf.user_id != user.id:
        raise HTTPException(404, "Workflow not found")
    for k, v in req.dict(exclude_none=True).items():
        setattr(wf, k, v)
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf

@router.delete("/{wf_id}")
async def delete_workflow(
    wf_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wf = await db.get(WorkflowDef, wf_id)
    if not wf or wf.user_id != user.id:
        raise HTTPException(404, "Workflow not found")
    await db.delete(wf)
    await db.commit()
    return {"status": "deleted"}

@router.post("/{wf_id}/run")
async def trigger_workflow(
    wf_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wf = await db.get(WorkflowDef, wf_id)
    if not wf or wf.user_id != user.id:
        raise HTTPException(404, "Workflow not found")
    run = WorkflowRun(workflow_id=wf_id, status="running")
    db.add(run)
    wf.run_count += 1
    wf.last_run_at = datetime.utcnow()
    db.add(wf)
    await db.commit()
    await db.refresh(run)
    # Simple mock execution
    import asyncio
    asyncio.create_task(_execute_workflow(run.id, wf))
    return {"run_id": run.id, "status": "started"}

async def _execute_workflow(run_id: str, wf: WorkflowDef):
    import asyncio
    from db.database import AsyncSessionLocal
    await asyncio.sleep(1)
    async with AsyncSessionLocal() as db:
        run = await db.get(WorkflowRun, run_id)
        if run:
            run.status = "success"
            run.output = json.dumps({"message": f"Workflow '{wf.name}' executed successfully"})
            run.finished_at = datetime.utcnow()
            run.duration_ms = 1000
            db.add(run)
            await db.commit()

@router.get("/{wf_id}/runs")
async def get_runs(
    wf_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == wf_id)
        .order_by(desc(WorkflowRun.started_at))
        .limit(20)
    )
    return result.scalars().all()

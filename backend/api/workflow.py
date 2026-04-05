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
    from db.database import AsyncSessionLocal
    import traceback
    
    try:
        # Run workflow logic via AI Agent
        from core.model_manager import model_manager
        from agents.executor import agent_executor
        
        prompt = f"Eksekusi tugas workflow berikut secara autonomous:\nNama: {wf.name}\nDeskripsi: {wf.description or 'Tidak ada deskripsi'}\n\nLakukan analisis atau jalankan perintah yang diperlukan untuk menyelesaikan tugas ini."
        
        output_buffer = ""
        # Use orchestrator seed-2-0-pro or default
        model = "sumopod/seed-2-0-pro" if "sumopod/seed-2-0-pro" in model_manager.available_models else model_manager.get_default_model()
        
        async for chunk in agent_executor.stream_chat(model, [{"role": "user", "content": prompt}], include_tool_logs=True):
            output_buffer += chunk
            
        async with AsyncSessionLocal() as db:
            run = await db.get(WorkflowRun, run_id)
            if run:
                run.status = "success"
                run.output = output_buffer
                run.finished_at = datetime.utcnow()
                run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000) if run.started_at else 1000
                db.add(run)
                await db.commit()
    except Exception as e:
        async with AsyncSessionLocal() as db:
            run = await db.get(WorkflowRun, run_id)
            if run:
                run.status = "failed"
                run.output = f"Error: {str(e)}\n{traceback.format_exc()}"
                run.finished_at = datetime.utcnow()
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

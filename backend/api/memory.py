from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, UserMemoryEntry
from core.auth import get_current_user
from memory.manager import memory_manager

router = APIRouter()

class MemoryRequest(BaseModel):
    content: str
    memory_type: str = "behavioral"

@router.get("/")
async def get_memories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserMemoryEntry)
        .where(UserMemoryEntry.user_id == user.id)
        .order_by(desc(UserMemoryEntry.created_at))
        .limit(50)
    )
    return result.scalars().all()

@router.post("/")
async def add_memory(
    req: MemoryRequest,
    user: User = Depends(get_current_user),
):
    await memory_manager.save_preference(user.id, req.content, req.memory_type)
    return {"status": "saved"}

@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = await db.get(UserMemoryEntry, memory_id)
    if entry and entry.user_id == user.id:
        await db.delete(entry)
        await db.commit()
    return {"status": "deleted"}

@router.get("/session/{session_id}")
async def get_session_context(
    session_id: str,
    user: User = Depends(get_current_user),
):
    messages = await memory_manager.get_short_term(session_id)
    return {"messages": messages, "count": len(messages)}


@router.get("/session-info/{session_id}")
async def session_memory_info(
    session_id: str,
    user: User = Depends(get_current_user),
):
    """Info memory untuk satu sesi — dipanggil dari halaman Memory."""
    from memory.manager import memory_manager
    return await memory_manager.get_memory_info(session_id, user.id)

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import ChatSession, Message, User
from core.auth import get_current_user
from core.model_manager import model_manager
from core.smart_router import smart_router
from rag.engine import rag_engine
from memory.manager import memory_manager

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    use_rag: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096


class NewSessionRequest(BaseModel):
    title: Optional[str] = None


@router.post("/sessions")
async def create_session(
    req: NewSessionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = ChatSession(
        user_id=user.id,
        title=req.title or "New Chat",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(desc(ChatSession.updated_at))
        .limit(50)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.user_id == user.id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    await db.delete(session)
    await db.commit()
    return {"status": "deleted"}


@router.post("/send")
async def chat_send(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Chat endpoint — returns streaming response"""

    # Get or create session
    if req.session_id:
        session = await db.get(ChatSession, req.session_id)
        if not session:
            raise HTTPException(404, "Session not found")
    else:
        session = ChatSession(user_id=user.id, title=req.message[:50])
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Route to best model
    route = smart_router.route(req.message, req.model)
    model = route["model"]

    # Build messages list
    system_prompt = await memory_manager.build_system_prompt(user.id, session.id)

    # RAG injection
    rag_context = ""
    rag_sources = []
    if req.use_rag:
        rag_results = await rag_engine.query(req.message, user_id=user.id)
        if rag_results:
            rag_context = rag_engine.build_context(rag_results)
            rag_sources = [r["source"] for r in rag_results]

    if rag_context:
        system_prompt += f"\n\n{rag_context}"

    # Get previous messages from memory
    # get_context: load dari Redis, fallback ke DB jika kosong
    history = await memory_manager.get_context(session.id, user.id)

    messages = [{"role": "system", "content": system_prompt}]
    messages += history  # sudah dibatasi CONTEXT_WINDOW di get_context()
    messages.append({"role": "user", "content": req.message})

    # Save user message
    user_msg = Message(
        session_id=session.id,
        user_id=user.id,
        role="user",
        content=req.message,
        model=model,
    )
    db.add(user_msg)

    async def generate():
        full_response = ""
        # Send session info first
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.id, 'model': model})}\n\n"

        try:
            from agents.executor import agent_executor
            async for chunk in agent_executor.stream_chat(
                base_model=model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            full_response = f"Error: {e}"

        # Save assistant response
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as save_db:
            ai_msg = Message(
                session_id=session.id,
                user_id=user.id,
                role="assistant",
                content=full_response,
                model=model,
                rag_sources=json.dumps(rag_sources) if rag_sources else None,
            )
            save_db.add(ai_msg)

            # Update session title if first message
            sess = await save_db.get(ChatSession, session.id)
            if sess:
                if sess.title == "New Chat":
                    sess.title = req.message[:60]
                sess.model_used = model
                sess.updated_at = datetime.utcnow()
                save_db.add(sess)
            await save_db.commit()

        # Update memory
        await memory_manager.save_chat_to_redis(session.id, "user", req.message)
        await memory_manager.save_chat_to_redis(session.id, "assistant", full_response)

        yield f"data: {json.dumps({'type': 'done', 'sources': rag_sources})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

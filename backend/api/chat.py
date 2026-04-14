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
from core.orchestrator import orchestrator
from agents.executor import agent_executor
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
    image_b64: Optional[str] = None  # Base64 encoded image
    image_mime: Optional[str] = None  # MIME type (image/png, image/jpeg, etc)


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


@router.get("/sessions/{session_id}/messages/new")
async def get_new_messages(
    session_id: str,
    after_ts: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch messages created after a given ISO timestamp.
    Used by frontend polling to sync cross-channel messages (Telegram → Web)."""
    query = (
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.user_id == user.id)
        .order_by(Message.created_at)
    )
    if after_ts:
        try:
            from datetime import datetime as _dt
            cutoff = _dt.fromisoformat(after_ts.replace("Z", "+00:00"))
            query = query.where(Message.created_at > cutoff)
        except ValueError:
            pass  # ignore bad timestamp, return all
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await db.get(ChatSession, session_id)

    # Idempotent: jika sudah tidak ada, anggap berhasil (jangan error 404)
    if not session:
        return {"status": "deleted", "note": "session_not_found_treated_as_deleted"}

    # Pastikan hanya pemilik yang bisa hapus
    if session.user_id != user.id:
        raise HTTPException(403, "Tidak punya akses untuk menghapus sesi ini")

    # Hapus semua messages terkait session
    from sqlalchemy import delete
    await db.execute(delete(Message).where(Message.session_id == session_id))

    # Hapus session
    await db.delete(session)
    await db.commit()

    # Invalidate cache Redis — nonblocking, jangan gagalkan delete jika Redis error
    try:
        await memory_manager.clear_session(session_id)
    except Exception:
        pass  # Redis gagal tidak boleh batalkan penghapusan

    return {"status": "deleted"}



@router.post("/send")
async def chat_send(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Chat endpoint — returns streaming response via Orchestrator pipeline"""

    # Debug: Log image data
    if req.image_b64 or req.image_mime:
        import structlog
        log = structlog.get_logger()
        log.info("Chat API received image",
                image_mime=req.image_mime,
                image_b64_len=len(req.image_b64) if req.image_b64 else 0,
                message_preview=req.message[:100])

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

    # Build system prompt + RAG context
    system_prompt = await memory_manager.build_system_prompt(user.id, session.id)

    rag_context = ""
    rag_sources = []
    if req.use_rag:
        rag_results = await rag_engine.query(req.message, user_id=user.id)
        if rag_results:
            rag_context = rag_engine.build_context(rag_results)
            rag_sources = list(dict.fromkeys(r["source"] for r in rag_results if "source" in r))

    if rag_context:
        system_prompt += f"\n\n{rag_context}"

    # Get conversation history from memory
    history = await memory_manager.get_context(session.id, user.id)

    # Save user message to DB
    user_msg = Message(
        session_id=session.id,
        user_id=user.id,
        role="user",
        content=req.message,
        model=req.model or "orchestrator",
    )
    db.add(user_msg)

    async def generate():
        full_response = ""
        final_model = req.model or "orchestrator"

        # Send session info
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.id, 'model': final_model})}\n\n"

        try:
            # ═══════════════════════════════════════════════════════
            # DELEGATE TO ORCHESTRATOR — all intelligence lives there
            # ═══════════════════════════════════════════════════════
            async for event in orchestrator.process(
                message=req.message,
                user_id=user.id,
                session_id=session.id,
                user_model_choice=req.model,
                system_prompt=system_prompt,
                history=history,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                use_rag=req.use_rag,
                image_b64=req.image_b64,
                image_mime=req.image_mime,
            ):
                if event.type == "chunk":
                    full_response += event.content
                    yield event.to_sse()

                elif event.type == "status":
                    yield event.to_sse()

                elif event.type == "pending_confirmation":
                    # VPS safety protocol — send confirmation request
                    payload = {
                        "type": "pending_confirmation",
                        "command": req.message,
                        "purpose": event.data.get("purpose", "") if event.data else "",
                        "risk": event.data.get("risk", "MEDIUM") if event.data else "MEDIUM",
                        "session_id": session.id,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    return  # Stop generator

                elif event.type == "done":
                    # Pass through done event with orchestrator metadata
                    done_payload = {"type": "done", "sources": rag_sources}
                    if event.data:
                        done_payload.update(event.data)
                    yield f"data: {json.dumps(done_payload)}\n\n"

                elif event.type == "error":
                    yield event.to_sse()
                    full_response = f"Error: {event.content}"

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_str = str(e)

            if "overdue balance" in err_str.lower() or "insufficient_quota" in err_str.lower():
                user_friendly_err = "❌ API Key Anda kehabisan saldo. Silakan isi ulang di menu Integrations."
                yield f"data: {json.dumps({'type': 'chunk', 'content': user_friendly_err})}\n\n"
                full_response = user_friendly_err
            else:
                yield f"data: {json.dumps({'type': 'error', 'content': err_str})}\n\n"
                full_response = f"Error: {err_str}"

        # ─── Save response & update session ───────────────────
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as save_db:
            ai_msg = Message(
                session_id=session.id,
                user_id=user.id,
                role="assistant",
                content=full_response,
                model=final_model,
                rag_sources=json.dumps(rag_sources) if rag_sources else None,
            )
            save_db.add(ai_msg)

            sess = await save_db.get(ChatSession, session.id)
            if sess:
                if sess.title == "New Chat":
                    sess.title = req.message[:60]
                sess.model_used = final_model
                sess.updated_at = datetime.utcnow()
                save_db.add(sess)
            await save_db.commit()

        # ─── Update memory ────────────────────────────────────
        await memory_manager.save_chat_to_redis(session.id, "user", req.message)
        await memory_manager.save_chat_to_redis(session.id, "assistant", full_response)

        # Ensure done event if not already sent
        if not full_response.startswith("Error"):
            pass  # done already yielded by orchestrator

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class PendingExecutionRequest(BaseModel):
    session_id: str
    command: str
    model: Optional[str] = None

@router.post("/execute_pending")
async def execute_pending(
    req: PendingExecutionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await db.get(ChatSession, req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
        
    system_prompt = await memory_manager.build_system_prompt(user.id, session.id)
    history = await memory_manager.get_context(session.id, user.id)
    
    # Force the AI to stop conversational hallucination and use the exact tool syntax immediately
    enforced_command = f"{req.command}\n\n[SYSTEM DIRECTIVE]: You have explicit user authorization to execute this command. DO NOT generate conversational text like 'I will check it now'. Output ONLY the JSON <tool> format immediately to execute what is asked."
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": enforced_command}]
    
    # Resolve model using agent registry instead of deprecated smart_router
    from agents.agent_registry import agent_registry
    model = agent_registry.resolve_model_for_agent("system", req.model)
    
    # Force high-tier model for executor if using auto-orchestrator to prevent nano hallucination
    if not req.model or "auto-orchestrator" in req.model.lower():
        if "sumopod/seed-2-0-pro" in model_manager.available_models:
            model = "sumopod/seed-2-0-pro"

    async def generate():
        full_response = ""
        yield f"data: {json.dumps({'type': 'chunk', 'content': '*(Execution Approved)*\\n\\n'})}\n\n"
        try:
            async for chunk in agent_executor.stream_chat(
                base_model=model,
                messages=messages,
                temperature=0.4,
                max_tokens=4096,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        except Exception as e:
            full_response = f"Error: {e}"
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
        # Update memory
        await memory_manager.save_chat_to_redis(session.id, "user", f"[Approved Execution] {req.command}")
        await memory_manager.save_chat_to_redis(session.id, "assistant", full_response)
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

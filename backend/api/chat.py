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
from core.classifier import task_classifier
from agents.voting_engine import voting_engine
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
        # The communication layer follows the user's choice or the AI Core routed model
        communicator_model = model
        
        # Send session info mapping exactly what user sees
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.id, 'model': communicator_model})}\n\n"

        try:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Menganalisa tingkat kesulitan tugas...'})}\n\n"
            # 1. TASK CLASSIFICATION
            classification = await task_classifier.classify(req.message)
            task_type = classification["category"]
            is_complex = classification["is_complex"]
            
            # 2. VPS SAFETY PROTOCOL
            if task_type in ["SYSTEM", "FILE OPERATION"]:
                # Pause and ask for user confirmation!
                pending_payload = {
                    "type": "pending_confirmation",
                    "command": req.message,
                    "purpose": f"User requested {task_type} action. ({classification['reasoning']})",
                    "risk": "MEDIUM",
                    "session_id": session.id
                }
                yield f"data: {json.dumps(pending_payload)}\n\n"
                return # Stop generator immediately
                
            # 3. EXECUTION
            
            if is_complex:
                yield f"data: {json.dumps({'type': 'status', 'content': 'Mengaktifkan mode Analisa Mendalam (Multi-AI)...'})}\n\n"
                raw_result = await voting_engine.execute_complex_task(system_prompt, req.message, history)
                
                yield f"data: {json.dumps({'type': 'status', 'content': 'Menyusun kesimpulan jawaban akhir...'})}\n\n"
                
                # 4. STRICT COMMUNICATION LAYER (Only for complex/voted tasks)
                com_messages = [
                    {"role": "system", "content": "You are AL FATIH Communicator. Your strict rule: Rewrite the provided content into clear, professional Bahasa Indonesia. Do not change facts, just act as the formatter."},
                    {"role": "user", "content": f"FORMAT THIS CONTENT FOR THE USER:\n\n{raw_result}"}
                ]
                async for chunk in model_manager.chat_stream(communicator_model, com_messages, temperature=0.7, max_tokens=4096):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'content': 'Merespons kueri...'})}\n\n"
                # Directly stream through the communicator model to retain conversational flow and reduce latency
                async for chunk in agent_executor.stream_chat(
                    base_model=communicator_model,
                    messages=messages,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
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
                # Log communicator model
                sess.model_used = communicator_model
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
    
    # Resolve Model dynamically properly for execution
    route_info = smart_router.route(req.command, req.model)
    model = route_info["model"]
    
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

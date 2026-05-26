import json
import asyncio
import time as _time
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
from core.orchestrator import orchestrator, OrchestratorEvent
from agents.executor import agent_executor
from rag.engine import rag_engine
from memory.manager import memory_manager

router = APIRouter()

import structlog
log = structlog.get_logger()

# ── Chat Rate Limiter ─────────────────────────────────────────
# 500 requests per minute per user — tinggi karena orchestrator internal loop
# bisa menghasilkan banyak request saat tool execution (15 iterasi × multi-event)
_CHAT_RATE_LIMIT   = 500
_CHAT_RATE_WINDOW  = 60    # seconds
_chat_mem_counters: dict = {}  # fallback in-memory tracker

async def _check_chat_rate_limit(user_id: str) -> None:
    """Raise 429 if user exceeds chat rate limit. Redis-first, memory fallback."""
    key = f"chat:rl:{user_id}"
    try:
        redis = None
        if memory_manager._redis_available and memory_manager.redis:
            redis = memory_manager.redis
        if redis:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, _CHAT_RATE_WINDOW)
            if count > _CHAT_RATE_LIMIT:
                ttl = await redis.ttl(key)
                # Pastikan TTL minimal 1 agar tidak muncul -1 atau 0 di UI
                wait_time = max(1, ttl)
                raise HTTPException(
                    status_code=429,
                    detail=f"Terlalu banyak pesan. Batas {_CHAT_RATE_LIMIT} pesan/{_CHAT_RATE_WINDOW}s. Coba lagi dalam {wait_time} detik.",
                    headers={"Retry-After": str(wait_time)},
                )
            return
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — fall through to memory tracker

    # In-memory fallback (per-worker, resets on restart)
    now = _time.time()
    rec = _chat_mem_counters.get(user_id, {"count": 0, "reset_at": now + _CHAT_RATE_WINDOW})
    if now > rec["reset_at"]:
        rec = {"count": 0, "reset_at": now + _CHAT_RATE_WINDOW}
    rec["count"] += 1
    _chat_mem_counters[user_id] = rec
    if rec["count"] > _CHAT_RATE_LIMIT:
        wait = max(1, int(rec["reset_at"] - now))
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak pesan. Batas {_CHAT_RATE_LIMIT} pesan/{_CHAT_RATE_WINDOW}s. Coba lagi dalam {wait} detik.",
            headers={"Retry-After": str(wait)},
        )


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    use_rag: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    image_b64: Optional[str] = None  # Base64 encoded image
    image_mime: Optional[str] = None  # MIME type (image/png, image/jpeg, etc)
    channel: Optional[str] = None  # Channel source (e.g. 'web', 'telegram')
    agent_mode: Optional[bool] = None


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
    # Verifikasi apakah sesi ada dan milik user
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

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
            # FIX: Postgres is strict about aware vs naive. Match DB naive UTC.
            cutoff = _dt.fromisoformat(after_ts.replace("Z", "+00:00")).replace(tzinfo=None)
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
    user: User = Depends(get_current_user),
):
    """Chat endpoint — returns streaming response via Orchestrator pipeline"""

    # ── Rate limiting: 30 requests/minute per user ────────────
    await _check_chat_rate_limit(user.id)

    # Debug: Log image data
    if req.image_b64 or req.image_mime:
        log.info("Chat API received image",
                image_mime=req.image_mime,
                image_b64_len=len(req.image_b64) if req.image_b64 else 0,
                message_preview=req.message[:100])

    from db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # Get or create session
        if req.session_id and not req.session_id.startswith("new-"):
            session = await db.get(ChatSession, req.session_id)
            if not session:
                # Sesi tidak ditemukan di DB (mungkin URL custom atau sudah terhapus)
                # Buat sesi baru dengan ID tersebut agar UI tetap sinkron dengan URL
                platform = req.channel if req.channel in ["web", "telegram", "whatsapp"] else "web"
                session = ChatSession(id=req.session_id, user_id=user.id, title=req.message[:50], platform=platform)
                db.add(session)
                await db.commit()
                await db.refresh(session)
        else:
            # Jika session_id kosong atau dimulai dengan 'new-', buat sesi baru dengan UUID otomatis
            platform = req.channel if req.channel in ["web", "telegram", "whatsapp"] else "web"
            session = ChatSession(user_id=user.id, title=req.message[:50], platform=platform)
            db.add(session)
            await db.commit()
            await db.refresh(session)

        # ─── Forward Web User Message to Telegram (If applicable) ───
        is_telegram_sync = (session.platform == "telegram" or req.channel == "telegram")
        if is_telegram_sync and getattr(user, "telegram_chat_id", None):
            import os
            from integrations.telegram_bot import _send
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
            if telegram_token:
                try:
                    # Forward user's message to their Telegram App
                    asyncio.create_task(_send(
                        telegram_token, 
                        int(user.telegram_chat_id), 
                        f"💻 *Dari Web:* {req.message}"
                    ))
                except Exception as e:
                    log.warning("Gagal forward pesan ke Telegram", error=str(e))

        # Save user message to DB immediately so it's not lost on stream abort
        user_msg = Message(
            session_id=session.id,
            user_id=user.id,
            role="user",
            content=req.message,
            model=req.model or "orchestrator",
        )
        db.add(user_msg)
        await db.commit()

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

    # ── Byte Rover: Long-term Memory Recall ──
    try:
        from core.byte_rover import byte_rover
        memory_context = await byte_rover.recall(req.message)
        if memory_context:
            system_prompt += f"\n\n{memory_context}"
    except Exception as e:
        log.warning("Gagal me-recall Byte Rover memory", error=str(e))

    # Get conversation history from memory
    history = await memory_manager.get_context(session.id, user.id)

    import re as _re

    def _strip_internal_tags(text: str) -> str:
        """Bersihkan tag XML internal AI (<function_calls> dll) yang bocor ke response."""
        if not text:
            return text
        text = _re.sub(r'<function_calls>[\s\S]*?</function_calls>', '', text)
        text = _re.sub(r'<invoke[\s\S]*?</invoke>', '', text)
        text = _re.sub(r'<parameter[\s\S]*?</parameter>', '', text)
        text = _re.sub(r'<[a-z_]+\s+name="[^"]*"\s*/>', '', text)
        
        # Strip AI thinking process tags that leak into the final output
        text = _re.sub(r'<(?:thinking|think|thought|thought_process)>[\s\S]*?</(?:thinking|think|thought|thought_process)>', '', text)
        text = _re.sub(r'<(?:plan|task|action)>[\s\S]*?</(?:plan|task|action)>', '', text)
        
        text = _re.sub(r'\n{3,}', '\n\n', text)
        return text

    async def generate():
        final_model = req.model or "orchestrator"

        async def orchestrator_producer(q: asyncio.Queue):
            full_response = ""
            thinking_steps = []
            error_occurred = False
            _saved_to_db = False

            async def save_to_db_bg():
                nonlocal _saved_to_db, full_response
                if _saved_to_db or (not full_response.strip() and not thinking_steps):
                    return
                try:
                    # --- AUTO IMAGE POST-PROCESSOR ---
                    # Detect fake/hallucinated markdown images and replace them with actual generated images!
                    import re
                    fake_img_pattern = r'!\[(.*?)\]\((https?://[^\s)]+)\)'
                    matches = re.findall(fake_img_pattern, full_response)
                    if matches:
                        log.info("Checking detected image tags for hallucinations in background save", count=len(matches))
                        for alt_text, fake_url in matches:
                            hallucination_domains = ["imgur.com", "unsplash.com", "placeholder", "dummy", "example.com", "picsum.photos", "google.com/imgres"]
                            if any(dom in fake_url.lower() for dom in hallucination_domains):
                                log.info("Detected hallucinated image URL, replacing with real generated image", url=fake_url, prompt=alt_text)
                                try:
                                    prompt_clean = alt_text.replace("Ilustrasi", "").replace("ilustrasi", "").strip("1234567890:.- ")
                                    if not prompt_clean:
                                        prompt_clean = f"{req.message} - {alt_text}"
                                    
                                    # Add user's message context if prompt is very short to get relevant results
                                    if len(prompt_clean) < 10:
                                        prompt_clean = f"{req.message}: {prompt_clean}"
                                        
                                    real_url = await model_manager.generate_image(prompt_clean, model="pollinations/auto")
                                    if real_url:
                                        full_response = full_response.replace(fake_url, real_url)
                                except Exception as img_err:
                                    log.warning("Failed to auto-generate replacement image in background save", error=str(img_err))

                    from db.database import AsyncSessionLocal
                    from datetime import datetime, timezone
                    async with AsyncSessionLocal() as save_db:
                        # Implement retry logic for WAL locks
                        for attempt in range(3):
                            try:
                                # Safely encode thinking steps
                                thinking_json = None
                                if thinking_steps:
                                    try:
                                        thinking_json = json.dumps(thinking_steps, ensure_ascii=False)
                                    except Exception:
                                        thinking_json = str(thinking_steps)

                                ai_msg = Message(
                                    session_id=session.id,
                                    user_id=user.id,
                                    role="assistant",
                                    content=full_response.strip() or "*(Eksekusi Selesai)*",
                                    model=final_model,
                                    rag_sources=json.dumps(rag_sources) if rag_sources else None,
                                    thinking_process=thinking_json,
                                )
                                save_db.add(ai_msg)

                                sess = await save_db.get(ChatSession, session.id)
                                if sess:
                                    if sess.title == "New Chat" and req.message:
                                        sess.title = req.message[:50]
                                    sess.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                                    save_db.add(sess)
                                
                                await save_db.commit()
                                _saved_to_db = True
                                break
                            except Exception as dberr:
                                if attempt == 2:
                                    log.error("Background DB Save failed completely", error=str(dberr))
                                    raise dberr
                                await asyncio.sleep(0.5)
                except Exception as e:
                    log.error("Failed to save AI response in background task", error=str(e))

            try:
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
                    project_path=project_path,
                    force_simple=True if req.agent_mode is False else False,
                ):
                    # Accumulate state inside producer
                    if event.type == "chunk":
                        clean_content = _strip_internal_tags(event.content)
                        if clean_content:
                            full_response += clean_content
                            await q.put(event)
                    elif event.type == "process":
                        if event.data:
                            action = event.data.get("action", "")
                            if action != "thinking_delta":
                                thinking_steps.append(event.data)
                        await q.put(event)
                    elif event.type == "status":
                        thinking_steps.append(event.content)
                        await q.put(event)
                    elif event.type == "impl_plan":
                        await q.put(event)
                    elif event.type == "pending_plan":
                        await q.put(event)
                    elif event.type == "pending_confirmation":
                        await q.put(event)
                    elif event.type == "require_project_location":
                        await q.put(event)
                    elif event.type == "done":
                        # Save to DB inside the background task immediately on 'done'
                        await save_to_db_bg()
                        
                        # Update memory
                        try:
                            await memory_manager.save_chat_to_redis(session.id, "user", req.message)
                            await memory_manager.save_chat_to_redis(session.id, "assistant", full_response[:5000])
                        except Exception as mem_err:
                            log.warning("Failed to update memory in background", error=str(mem_err)[:100])
                            
                        # Forward AI Response to Telegram (If applicable)
                        if is_telegram_sync and getattr(user, "telegram_chat_id", None) and not error_occurred:
                            import os
                            from integrations.telegram_bot import _send
                            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
                            if telegram_token:
                                try:
                                    asyncio.create_task(_send(
                                        telegram_token, 
                                        int(user.telegram_chat_id), 
                                        f"🤖 *AI:* {full_response[:4000]}"  # Telegram limits to 4096
                                    ))
                                except Exception as tel_err:
                                    log.warning("Gagal forward balasan AI ke Telegram", error=str(tel_err))

                        # Enrich the 'done' event with accumulated metadata for the generator stream
                        event.data = event.data or {}
                        event.data["thinking_process"] = json.dumps(thinking_steps) if thinking_steps else ""
                        event.data["sources"] = rag_sources
                        await q.put(event)

                    elif event.type == "error":
                        full_response = f"Error: {event.content}"
                        error_occurred = True
                        await q.put(event)
            except asyncio.CancelledError:
                log.info("Background orchestrator producer was cancelled", session_id=session.id)
                error_occurred = True
                thinking_steps.append("⚠️ Latar belakang dibatalkan...")
                raise
            except Exception as e:
                log.error("orchestrator_producer failed", error=str(e))
                error_occurred = True
                try:
                    await q.put(OrchestratorEvent(type="error", content=str(e), data={}))
                except Exception:
                    pass
            finally:
                # In all cases (success, error, or cancellation), save to DB if not saved yet
                if not _saved_to_db:
                    await save_to_db_bg()
                    try:
                        await memory_manager.save_chat_to_redis(session.id, "user", req.message)
                        await memory_manager.save_chat_to_redis(session.id, "assistant", full_response[:5000])
                    except Exception as mem_err:
                        log.warning("Failed to update memory in background finally", error=str(mem_err)[:100])
                await q.put(None)

        # ─── ANTI-BUFFERING PADDING ────────────────────────────
        yield f": {' ' * 4096}\n\n"

        # Send session info
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.id, 'model': final_model})}\n\n"

        try:
            # Get project path if set (Robust handling for dict or JSON str)
            project_path = None
            if session.project_metadata:
                meta = session.project_metadata
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except: meta = {}
                project_path = meta.get("project_path") if isinstance(meta, dict) else None

            q = asyncio.Queue()
            prod_task = asyncio.create_task(orchestrator_producer(q))

            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield f": keepalive {' ' * 4096}\n\n"
                    continue
                
                if item is None:
                    break
                
                if isinstance(item, Exception):
                    raise item
                
                event = item

                if event.type == "chunk":
                    clean_content = _strip_internal_tags(event.content)
                    if clean_content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': clean_content})}\n\n"

                elif event.type == "process":
                    yield event.to_sse()

                elif event.type == "status":
                    yield event.to_sse()

                elif event.type == "impl_plan":
                    payload = {
                        "type": "impl_plan",
                        "content": event.content,
                        "intent": event.data.get("intent", ""),
                        "complexity": event.data.get("complexity", 0),
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                elif event.type == "pending_plan":
                    payload = {
                        "type": "pending_plan",
                        "plan": event.data.get("plan", "") if event.data else "",
                        "subtask_count": event.data.get("subtask_count", 0) if event.data else 0,
                        "session_id": session.id,
                        "assignment_summary": event.data.get("assignment_summary", "") if event.data else "",
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                elif event.type == "pending_confirmation":
                    payload = {
                        "type": "pending_confirmation",
                        "command": req.message,
                        "purpose": event.data.get("purpose", "") if event.data else "",
                        "risk": event.data.get("risk", "MEDIUM") if event.data else "MEDIUM",
                        "session_id": session.id,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    return

                elif event.type == "require_project_location":
                    payload = {
                        "type": "require_project_location",
                        "session_id": session.id,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    return

                elif event.type == "done":
                    done_payload = {"type": "done", "sources": event.data.get("sources", [])}
                    if event.data:
                        done_payload.update({k: v for k, v in event.data.items() if k not in ["sources", "thinking_process"]})
                    done_payload["thinking_process"] = event.data.get("thinking_process", "")
                    yield f"data: {json.dumps(done_payload)}\n\n"
                    return

                elif event.type == "error":
                    yield event.to_sse()
                    return

        except asyncio.CancelledError:
            log.info("Chat stream cancelled by client (navigated away or refreshed)", session_id=session.id)
            raise

        except Exception as e:
            import traceback
            import uuid as _uuid
            traceback.print_exc()
            err_str = str(e)
            err_id = _uuid.uuid4().hex[:8].upper()
            log.error("Generator loop error", error=err_str[:300], error_id=err_id)

            if "overdue balance" in err_str.lower() or "insufficient_quota" in err_str.lower():
                user_friendly_err = "❌ API Key Anda kehabisan saldo. Silakan isi ulang di menu Integrations."
            elif "timeout" in err_str.lower():
                user_friendly_err = "⏱️ Operasi timeout - silakan coba lagi dengan pesan yang lebih singkat"
            elif "rate limit" in err_str.lower():
                user_friendly_err = "🛑 Terlalu banyak request - silakan tunggu beberapa detik sebelum mencoba lagi"
            elif "content filter" in err_str.lower() or "request was blocked" in err_str.lower():
                user_friendly_err = "🔒 Permintaan diblokir oleh filter konten provider. Silakan coba ulangi pesan Anda."
            elif "connection" in err_str.lower() or "network" in err_str.lower():
                user_friendly_err = "🌐 Gagal terhubung ke layanan AI. Periksa koneksi dan coba lagi."
            else:
                user_friendly_err = f"⚠️ Terjadi kesalahan internal (ID: {err_id}). Silakan coba lagi atau hubungi admin."

            yield f"data: {json.dumps({'type': 'error', 'content': user_friendly_err})}\n\n"
            raise

        finally:
            pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class ConfirmPlanRequest(BaseModel):
    session_id: str


@router.post("/confirm_plan")
async def confirm_plan(
    req: ConfirmPlanRequest,
    user: User = Depends(get_current_user),
):
    """Confirm an interactive execution plan so the orchestrator proceeds."""
    from core.orchestrator import _pending_plans
    event = _pending_plans.get(req.session_id)
    if event:
        event.set()
        return {"status": "confirmed", "session_id": req.session_id}
    return {"status": "no_pending_plan", "session_id": req.session_id}


class PendingExecutionRequest(BaseModel):
    session_id: str
    command: str
    model: Optional[str] = None


class ProjectLocationRequest(BaseModel):
    session_id: str
    project_path: str

@router.post("/execute_pending")
async def execute_pending(
    req: PendingExecutionRequest,
    user: User = Depends(get_current_user),
):
    from db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
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
        async def executor_producer(q: asyncio.Queue):
            try:
                async for chunk in agent_executor.stream_chat(
                    base_model=model,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=4096,
                ):
                    await q.put(chunk)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                await q.put(e)
            finally:
                await q.put(None)

        q = asyncio.Queue()
        prod_task = asyncio.create_task(executor_producer(q))

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                    
                if chunk is None:
                    break
                    
                if isinstance(chunk, Exception):
                    raise chunk

                # Detect process-event sentinels from executor
                from core.process_emitter import PROCESS_EVENT_PREFIX
                if isinstance(chunk, str) and chunk.startswith(PROCESS_EVENT_PREFIX):
                    try:
                        payload = json.loads(chunk[len(PROCESS_EVENT_PREFIX):])
                        yield f"data: {json.dumps({'type': 'process', **payload})}\n\n"
                    except Exception:
                        pass # skip malformed
                else:
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        except Exception as e:
            full_response = f"Error: {e}"
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
        finally:
            if not prod_task.done():
                prod_task.cancel()
                try:
                    await prod_task
                except (asyncio.CancelledError, Exception):
                    pass
            
        # Update memory
        await memory_manager.save_chat_to_redis(session.id, "user", f"[Approved Execution] {req.command}")
        await memory_manager.save_chat_to_redis(session.id, "assistant", full_response)
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/set_project_location")
async def set_project_location(
    req: ProjectLocationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set project location for a session"""
    session = await db.get(ChatSession, req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if session.user_id != user.id:
        raise HTTPException(403, "No access to this session")
    
    # Validate path (basic security check)
    import os
    project_path = os.path.abspath(req.project_path)
    if not project_path.startswith(os.path.expanduser("~")) and not project_path.startswith("/home/"):
        raise HTTPException(400, "Project path must be in user home directory")
    
    # Store project location in session metadata
    # Robust dict conversion (handle case where DB returns JSON string)
    meta = session.project_metadata
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except: meta = {}
    
    metadata = dict(meta) if meta else {}
    metadata["project_path"] = project_path
    session.project_metadata = metadata
    
    await db.commit()
    return {"status": "success", "project_path": project_path}


@router.get("/get_project_location/{session_id}")
async def get_project_location(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get project location for a session"""
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if session.user_id != user.id:
        raise HTTPException(403, "No access to this session")
    
    project_path = None
    if session.project_metadata:
        meta = session.project_metadata
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except: meta = {}
        project_path = meta.get("project_path") if isinstance(meta, dict) else None
    
    return {"project_path": project_path}


class DirectoryListRequest(BaseModel):
    path: str


@router.post("/list_directories")
async def list_directories(
    req: DirectoryListRequest,
    user: User = Depends(get_current_user),
):
    """List subdirectories for a given path to enable server-side directory browsing"""
    import os
    
    try:
        target_path = os.path.abspath(req.path) if req.path else os.path.expanduser("~")
        
        # Security check: Ensure we can only browse within allowed boundaries
        # For a local AI app, we might allow browsing anywhere, but let's restrict to ~ or /home/
        if not target_path.startswith(os.path.expanduser("~")) and not target_path.startswith("/home/"):
            target_path = os.path.expanduser("~")
            
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            return {"path": target_path, "directories": [], "parent": os.path.dirname(target_path)}
            
        directories = []
        for item in sorted(os.listdir(target_path)):
            item_path = os.path.join(target_path, item)
            # Only include directories, ignore hidden folders
            if os.path.isdir(item_path) and not item.startswith("."):
                directories.append({
                    "name": item,
                    "path": item_path
                })
                
        parent_dir = os.path.dirname(target_path) if target_path != "/" else "/"
        
        return {
            "path": target_path,
            "directories": directories,
            "parent": parent_dir
        }
    except Exception as e:
        raise HTTPException(500, f"Error reading directory: {str(e)}")

class CreateDirectoryRequest(BaseModel):
    parent_path: str
    folder_name: str

@router.post("/create_directory")
async def create_directory(
    req: CreateDirectoryRequest,
    user: User = Depends(get_current_user),
):
    """Create a new subdirectory inside a given parent path."""
    import os
    
    try:
        parent_dir = os.path.abspath(req.parent_path)
        
        # Security check: Ensure we can only browse within allowed boundaries
        if not parent_dir.startswith(os.path.expanduser("~")) and not parent_dir.startswith("/home/"):
            raise HTTPException(403, "Akses ditolak: hanya boleh membuat folder di direktori home")
            
        safe_name = os.path.basename(req.folder_name)
        if not safe_name:
            raise HTTPException(400, "Nama folder tidak valid")
            
        new_dir_path = os.path.join(parent_dir, safe_name)
        
        if os.path.exists(new_dir_path):
            raise HTTPException(400, "Folder sudah ada")
            
        os.makedirs(new_dir_path)
        
        return {
            "ok": True,
            "path": new_dir_path,
            "message": f"Folder {safe_name} berhasil dibuat"
        }
    except PermissionError:
        raise HTTPException(403, f"Tidak memiliki izin membuat folder di {parent_dir}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Gagal membuat folder: {str(e)}")


class SaveFileRequest(BaseModel):
    directory: str
    filename: str
    content: str


@router.post("/save-file")
async def save_file_to_directory(
    req: SaveFileRequest,
    user: User = Depends(get_current_user),
):
    """Save AI-generated content to a user-chosen directory on the server."""
    import os

    # Sanitize filename — strip path separators to prevent directory traversal
    safe_name = os.path.basename(req.filename)
    if not safe_name:
        raise HTTPException(400, "Nama file tidak valid")

    # Resolve and validate directory
    target_dir = os.path.abspath(req.directory)

    # Security: only allow saving inside user home directory
    home = os.path.expanduser("~")
    allowed_prefixes = [home, "/home/", "/data/"]
    if not any(target_dir.startswith(p) for p in allowed_prefixes):
        raise HTTPException(403, f"Akses ditolak: hanya boleh menyimpan di dalam direktori home ({home})")

    full_path = os.path.join(target_dir, safe_name)

    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(req.content)

        file_size = os.path.getsize(full_path)
        log.info("File saved via API", path=full_path, size=file_size, user=user.username)

        return {
            "ok": True,
            "path": full_path,
            "size": file_size,
            "message": f"File berhasil disimpan ke {full_path}"
        }
    except PermissionError:
        raise HTTPException(403, f"Tidak memiliki izin menulis ke {target_dir}")
    except Exception as e:
        raise HTTPException(500, f"Gagal menyimpan file: {str(e)}")


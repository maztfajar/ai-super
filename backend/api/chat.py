import json
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
from core.orchestrator import orchestrator
from agents.executor import agent_executor
from rag.engine import rag_engine
from memory.manager import memory_manager

router = APIRouter()

# ── Chat Rate Limiter ─────────────────────────────────────────
# 30 requests per minute per user (prevents API quota abuse)
_CHAT_RATE_LIMIT   = 30    # max requests
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
                raise HTTPException(
                    status_code=429,
                    detail=f"Terlalu banyak pesan. Batas {_CHAT_RATE_LIMIT} pesan/{_CHAT_RATE_WINDOW}s. Coba lagi dalam {ttl} detik.",
                    headers={"Retry-After": str(ttl)},
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
        wait = int(rec["reset_at"] - now)
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

    # ── Rate limiting: 30 requests/minute per user ────────────
    await _check_chat_rate_limit(user.id)

    # Debug: Log image data
    if req.image_b64 or req.image_mime:
        import structlog
        log = structlog.get_logger()
        log.info("Chat API received image",
                image_mime=req.image_mime,
                image_b64_len=len(req.image_b64) if req.image_b64 else 0,
                message_preview=req.message[:100])


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

    async def generate():
        full_response = ""
        final_model = req.model or "orchestrator"
        thinking_steps = []  # Collect all status messages for thinking section
        error_occurred = False

        # ─── ANTI-BUFFERING PADDING ────────────────────────────
        # VPS reverse proxies (Nginx/Cloudflare) often buffer SSE chunks until 4KB.
        # This padding forces the proxy to flush the headers/buffer immediately
        # so the frontend doesn't hang at "0 karakter" for a long time.
        yield f": {' ' * 4096}\n\n"

        # Send session info
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.id, 'model': final_model})}\n\n"

        try:
            # Get project path if set
            project_path = None
            if session.project_metadata:
                project_path = session.project_metadata.get("project_path")

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
                project_path=project_path,
            ):
                if event.type == "chunk":
                    full_response += event.content
                    yield event.to_sse()

                elif event.type == "process":
                    # Structured process step — forward directly to frontend
                    yield event.to_sse()
                    # Also collect for storage
                    if event.data:
                        action = event.data.get("action", "")
                        detail = event.data.get("detail", "")
                        thinking_steps.append(f"{action}: {detail}" if detail else action)

                elif event.type == "status":
                    # Collect thinking steps
                    thinking_steps.append(event.content)
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
                    # Pass through done event with orchestrator metadata + thinking process
                    done_payload = {"type": "done", "sources": rag_sources}
                    if event.data:
                        done_payload.update(event.data)
                    # Include thinking process for expandable thinking section
                    done_payload["thinking_process"] = "\n".join(thinking_steps) if thinking_steps else ""
                    yield f"data: {json.dumps(done_payload)}\n\n"

                elif event.type == "error":
                    yield event.to_sse()
                    full_response = f"Error: {event.content}"
                    error_occurred = True

        except asyncio.TimeoutError:
            import traceback
            traceback.print_exc()
            err_str = "⏱️ Operasi timeout - permintaan Anda memerlukan waktu terlalu lama. Sistem akan melanjutkan dengan respons yang sudah ada."
            log.error("Chat timeout", message=req.message[:50])
            
            # Try to get partial response before timeout
            if full_response.strip():
                yield f"data: {json.dumps({'type': 'chunk', 'content': '\\n\\n⚠️ Partial response due to timeout:\\n\\n' + full_response[-1000:]})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'partial': True, 'sources': rag_sources})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'content': err_str})}\n\n"
                full_response = err_str
            error_occurred = True
            thinking_steps.append(f"❌ Timeout error: {err_str}")

        except asyncio.CancelledError:
            log.info("Chat stream cancelled by client", session_id=session.id)
            error_occurred = True
            if full_response.strip():
                thinking_steps.append("⚠️ Klien terputus, menyimpan sebagian respons...")

        except Exception as e:
            import traceback
            import uuid as _uuid
            traceback.print_exc()
            err_str = str(e)
            # Generate an error ID for debugging — full details stay server-side
            err_id = _uuid.uuid4().hex[:8].upper()
            log.error("Chat error", error=err_str[:300], error_id=err_id)

            # Provide user-friendly error messages — never expose raw internals to client
            if "overdue balance" in err_str.lower() or "insufficient_quota" in err_str.lower():
                user_friendly_err = "❌ API Key Anda kehabisan saldo. Silakan isi ulang di menu Integrations."
                yield f"data: {json.dumps({'type': 'chunk', 'content': user_friendly_err})}\n\n"
                full_response = user_friendly_err
            elif "timeout" in err_str.lower():
                user_friendly_err = "⏱️ Operasi timeout - silakan coba lagi dengan pesan yang lebih singkat"
                yield f"data: {json.dumps({'type': 'error', 'content': user_friendly_err})}\n\n"
                full_response = user_friendly_err
            elif "rate limit" in err_str.lower():
                user_friendly_err = "🛑 Terlalu banyak request - silakan tunggu beberapa detik sebelum mencoba lagi"
                yield f"data: {json.dumps({'type': 'error', 'content': user_friendly_err})}\n\n"
                full_response = user_friendly_err
            elif "connection" in err_str.lower() or "network" in err_str.lower():
                user_friendly_err = "🌐 Gagal terhubung ke layanan AI. Periksa koneksi dan coba lagi."
                yield f"data: {json.dumps({'type': 'error', 'content': user_friendly_err})}\n\n"
                full_response = user_friendly_err
            else:
                # Generic safe message — include error ID so admin can trace in logs
                user_friendly_err = f"⚠️ Terjadi kesalahan internal (ID: {err_id}). Silakan coba lagi atau hubungi admin."
                yield f"data: {json.dumps({'type': 'error', 'content': user_friendly_err})}\n\n"
                full_response = f"Error [{err_id}]: Internal error"

            error_occurred = True
            thinking_steps.append(f"❌ Error [{err_id}]: {err_str[:100]}")

        # ─── Save response & update session ───────────────────
        try:
            from db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as save_db:
                ai_msg = Message(
                    session_id=session.id,
                    user_id=user.id,
                    role="assistant",
                    content=full_response[:5000],  # Limit to 5000 chars to prevent DB issues
                    model=final_model,
                    rag_sources=json.dumps(rag_sources) if rag_sources else None,
                    thinking_process="\n".join(thinking_steps) if thinking_steps else None,
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
        except Exception as e:
            log.warning("Failed to save message", error=str(e)[:100])
            # Continue anyway - don't fail the chat if message save fails

        # ─── Update memory ────────────────────────────────────
        try:
            await memory_manager.save_chat_to_redis(session.id, "user", req.message)
            await memory_manager.save_chat_to_redis(session.id, "assistant", full_response[:5000])
        except Exception as e:
            log.warning("Failed to update memory", error=str(e)[:100])
            # Continue anyway - don't fail the chat if memory update fails

        # Ensure done event if not already sent and no error
        if not error_occurred and not full_response.startswith("Error"):
            pass  # done already yielded by orchestrator

        # ─── Forward AI Response to Telegram (If applicable) ───
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
                except Exception as e:
                    log.warning("Gagal forward balasan AI ke Telegram", error=str(e))

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


class ProjectLocationRequest(BaseModel):
    session_id: str
    project_path: str

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
    metadata = dict(session.project_metadata) if session.project_metadata else {}
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
        project_path = session.project_metadata.get("project_path")
    
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
    import structlog
    log = structlog.get_logger()

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


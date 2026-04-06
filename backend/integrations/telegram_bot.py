"""
AI SUPER ASSISTANT — Telegram Bot (Polling Mode)
Setiap pesan diproses sebagai asyncio.Task terpisah
agar polling loop tidak terblokir saat AI generate.
"""
import asyncio
import threading
from typing import Optional
import structlog

log = structlog.get_logger()

_bot_thread: Optional[threading.Thread] = None
_bot_running = False
_bot_loop:   Optional[asyncio.AbstractEventLoop] = None


# ── Helper kirim pesan ────────────────────────────────────────
async def _send(token: str, chat_id: int, text: str, include_drive_btn: bool = False):
    """Kirim pesan Markdown, auto-split > 4000 char."""
    import httpx
    chunks = [text[i:i+4000] for i in range(0, max(len(text), 1), 4000)]
    async with httpx.AsyncClient(timeout=15) as c:
        for idx, chunk in enumerate(chunks):
            try:
                payload = {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"}
                if include_drive_btn and idx == len(chunks) - 1:
                    payload["reply_markup"] = {
                        "inline_keyboard": [[{"text": "📁 Simpan ke Google Drive", "callback_data": "drive_options"}]]
                    }
                await c.post(
                    "https://api.telegram.org/bot" + token + "/sendMessage",
                    json=payload,
                )
            except Exception as ex:
                log.warning("Telegram send error", error=str(ex)[:80])


async def _send_typing(token: str, chat_id: int):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                "https://api.telegram.org/bot" + token + "/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
    except Exception:
        pass


# ── Handle satu pesan (asyncio.Task terpisah) ─────────────────
async def _handle_message(chat_id: int, user_id: str, text: str,
                           from_name: str, token: str):
    try:

        # /start
        if text == "/start":
            await _send(token, chat_id,
                "Halo " + from_name + "! Saya *AI SUPER ASSISTANT*, AI Super Assistant kamu.\n\n"
                "Ketik pertanyaan apa saja dan saya akan menjawab!\n\n"
                "Perintah:\n"
                "/start - Mulai\n"
                "/help - Bantuan\n"
                "/clear - Hapus konteks chat\n"
                "/model - Lihat model aktif"
            )
            return

        # /help
        if text == "/help":
            await _send(token, chat_id,
                "*AI SUPER ASSISTANT Bot*\n\n"
                "Kirim pesan teks biasa untuk chat dengan AI.\n\n"
                "Fitur:\n"
                "- Chat dengan AI (auto-pilih model terbaik)\n"
                "- Cari di knowledge base (RAG)\n"
                "- Ingat konteks percakapan\n\n"
                "Perintah:\n"
                "/start - Mulai bot\n"
                "/help - Tampilkan bantuan ini\n"
                "/clear - Reset konteks chat\n"
                "/model - Model yang digunakan"
            )
            return

        # /clear
        if text == "/clear":
            from memory.manager import memory_manager
            await memory_manager.save_short_term("tg_" + str(chat_id), [])
            await _send(token, chat_id, "Konteks chat direset!")
            return

        # /model
        if text == "/model":
            from core.smart_router import smart_router
            route = smart_router.route("test")
            model_name = route.get("model", "unknown")
            await _send(token, chat_id, "Model aktif: `" + model_name + "`")
            return

        # Pesan biasa → proses AI
        await _send_typing(token, chat_id)

        from core.model_manager import model_manager
        from core.smart_router import smart_router
        from memory.manager import memory_manager
        from rag.engine import rag_engine

        route  = smart_router.route(text)
        # Default telegram bot to orchestrator (seed-2-0-pro) as requested
        model  = "sumopod/seed-2-0-pro"
        system = await memory_manager.build_system_prompt(user_id, "tg_" + str(chat_id))

        # RAG context
        try:
            rag_results = await rag_engine.query(text, user_id=user_id)
            if rag_results:
                system += "\n\n" + rag_engine.build_context(rag_results)
        except Exception:
            pass

        # Riwayat chat (load dari Redis, fallback ke DB)
        history  = await memory_manager.get_context("tg_" + str(chat_id), user_id)
        messages = [{"role": "system", "content": system}]
        messages += history
        messages.append({"role": "user", "content": text})

        # Generate using AgentExecutor for Tool support (Agentic)
        full_response = ""
        from agents.executor import agent_executor
        
        # Periodic typing status task
        typing_active = True
        async def keep_typing():
            while typing_active:
                await _send_typing(token, chat_id)
                await asyncio.sleep(5)
        
        typing_task = asyncio.create_task(keep_typing())
        
        try:
            async for chunk in agent_executor.stream_chat(
                base_model=model, 
                messages=messages,
                include_tool_logs=False  # Sembunyikan logs di Telegram agar bersih
            ):
                full_response += chunk
        finally:
            typing_active = False
            typing_task.cancel()

        if not full_response.strip():
            full_response = "Maaf, saya tidak bisa memproses permintaan itu. Coba lagi ya!"

        await _send(token, chat_id, full_response, include_drive_btn=True)

        # Simpan ke memory
        await memory_manager.save_chat_to_redis("tg_" + str(chat_id), "user", text)
        await memory_manager.save_chat_to_redis("tg_" + str(chat_id), "assistant", full_response)
        log.info("Telegram reply sent", chat_id=chat_id, model=model, chars=len(full_response))

    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.error("Telegram handle_message error", error=str(e), chat_id=chat_id)
        err = str(e).lower()
        try:
            if "cancelled" in err:
                return
            if "timeout" in err or "timed out" in err:
                msg = "Maaf, request terlalu lama. Coba kirim lagi ya!"
            elif "api key" in err or "unauthorized" in err or "invalid" in err:
                msg = "Model AI tidak bisa diakses. Pastikan API key sudah diset di menu Integrasi."
            elif "redis" in err or "connection" in err:
                msg = "Sedang menginisialisasi. Coba kirim pesan lagi."
            else:
                msg = "Maaf ada gangguan sementara. Silakan kirim ulang pesan kamu."
            await _send(token, chat_id, msg)
        except Exception:
            pass

# ── Handle Callback Query ─────────────────────────────────────
async def _handle_callback_query(callback_query: dict, token: str):
    import httpx
    from integrations.google_drive import list_drive_folders, get_drive_service
    from memory.manager import memory_manager
    import json
    
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    msg_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")
    callback_id = callback_query.get("id")
    user_id = str(callback_query.get("from", {}).get("id", "unknown"))
    
    async def _answer(text=""):
        async with httpx.AsyncClient() as c:
            await c.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})
            
    async def _edit_markup(markup):
        async with httpx.AsyncClient() as c:
            await c.post(f"https://api.telegram.org/bot{token}/editMessageReplyMarkup", json={"chat_id": chat_id, "message_id": msg_id, "reply_markup": markup})
            
    async def _send_text(text):
        await _send(token, chat_id, text)

    try:
        if data == "drive_options":
            await _answer("Pilih Format")
            markup = {"inline_keyboard": [
                [{"text": "📄 PDF", "callback_data": "drive_format_pdf"}, {"text": "📝 Word", "callback_data": "drive_format_docx"}],
                [{"text": "📊 Excel", "callback_data": "drive_format_xlsx"}, {"text": "🗄 CSV", "callback_data": "drive_format_csv"}]
            ]}
            await _edit_markup(markup)
            
        elif data.startswith("drive_format_"):
            fmt = data.split("_")[-1]
            await memory_manager.save_short_term(f"tg_fmt_{chat_id}", fmt) # store format
            await _answer("Memuat daftar folder...")
            
            # Fetch root folders
            folders = await list_drive_folders()
            root_folders = [f for f in folders if not f.get('parents')]
            if not root_folders:
                root_folders = folders[:10]
                
            kb = []
            for f in root_folders[:10]:
                kb.append([{"text": f"📁 {f['name'][:30]}", "callback_data": f"drive_save_{f['id']}"}])
            kb.append([{"text": "✅ Simpan di Root", "callback_data": "drive_save_root"}])
            
            await _edit_markup({"inline_keyboard": kb})
            
        elif data.startswith("drive_save_"):
            folder_id = data.replace("drive_save_", "")
            if folder_id == "root": folder_id = None
            
            await _edit_markup({"inline_keyboard": []}) # clear buttons
            await _answer("Mengekspor file ke Google Drive...")
            await _send_text("⏳ Sedang memproses dan mengunggah ke Google Drive...")
            
            # Reconstruct content from memory
            history = await memory_manager.get_context("tg_" + str(chat_id), user_id)
            if not history:
                await _send_text("❌ Gagal menyimpan. Konten kadaluarsa.")
                return
            last_ai = history[-1]['content']
            
            fmt = await memory_manager.get_context(f"tg_fmt_{chat_id}", user_id)
            if not fmt: fmt = "pdf"
            if isinstance(fmt, list) and len(fmt) > 0: fmt = fmt[0].get('content', 'pdf')
            elif isinstance(fmt, list): fmt = "pdf"
            
            # Generate the file buffer (using same logic as api/drive.py)
            filename = f"AI_Generated_{chat_id}.{fmt}"
            import io
            file_bytes = b""
            
            if fmt in ["txt", "csv", "md"]:
                file_bytes = last_ai.encode("utf-8")
            elif fmt == "docx":
                from docx import Document
                doc = Document()
                for line in last_ai.split("\n"): doc.add_paragraph(line)
                buf = io.BytesIO()
                doc.save(buf)
                file_bytes = buf.getvalue()
            elif fmt == "xlsx":
                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                for row in last_ai.strip().split("\n"): ws.append(row.split(",")) 
                buf = io.BytesIO()
                wb.save(buf)
                file_bytes = buf.getvalue()
            elif fmt == "pdf":
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet
                buf = io.BytesIO()
                doc = SimpleDocTemplate(buf, pagesize=letter)
                styles = getSampleStyleSheet()
                flowables = []
                for line in last_ai.split("\n"):
                    if line.strip():
                        sanitized = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        flowables.append(Paragraph(sanitized, styles["Normal"]))
                doc.build(flowables)
                file_bytes = buf.getvalue()
            
            from integrations.google_drive import upload_to_drive
            res = await upload_to_drive(filename, file_bytes, folder_id)
            if res.get("status") == "success":
                await _send_text(f"✅ *File Berhasil Disimpan!*\n\n[Lihat di Google Drive]({res.get('link')})")
            else:
                await _send_text(f"❌ *Gagal menyimpan file:*\n{res.get('message')}")
                
    except Exception as e:
        log.error("Telegram callback error", error=str(e))
        await _answer()


# ── Callback task selesai ─────────────────────────────────────
def _task_done(task: asyncio.Task, active_tasks: set):
    active_tasks.discard(task)
    if task.cancelled():
        return
    try:
        exc = task.exception()
        if exc:
            log.error("Telegram task error", error=str(exc))
    except Exception:
        pass


# ── Polling loop utama ────────────────────────────────────────
async def _polling_loop(token: str):
    global _bot_running
    import httpx

    offset       = 0
    active_tasks: set = set()

    # Tunggu service siap
    await asyncio.sleep(2)
    log.info("Telegram polling started")

    # Flush pending updates
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://api.telegram.org/bot" + token + "/getUpdates",
                params={"offset": -1, "limit": 1},
            )
            data = r.json()
            if data.get("ok") and data.get("result"):
                offset = data["result"][-1]["update_id"] + 1
                log.info("Flushed pending updates", next_offset=offset)
    except Exception as e:
        log.warning("Flush updates failed", error=str(e))

    while _bot_running:
        try:
            async with httpx.AsyncClient(timeout=40) as c:
                resp = await c.get(
                    "https://api.telegram.org/bot" + token + "/getUpdates",
                    params={
                        "offset":          offset,
                        "timeout":         30,
                        "allowed_updates": ["message", "callback_query"],
                    },
                )

            if resp.status_code == 409:
                log.warning("Telegram 409 Conflict, retry 10s")
                await asyncio.sleep(10)
                continue

            if resp.status_code != 200:
                log.warning("Telegram non-200", status=resp.status_code)
                await asyncio.sleep(3)
                continue

            data = resp.json()
            if not data.get("ok"):
                log.warning("Telegram not ok", desc=data.get("description"))
                await asyncio.sleep(3)
                continue

            for update in data.get("result", []):
                offset    = update["update_id"] + 1
                # Process Callbacks
                if "callback_query" in update:
                    task = asyncio.create_task(
                        _handle_callback_query(update["callback_query"], token),
                        name="tg-cb-" + str(update["callback_query"]["id"]),
                    )
                    active_tasks.add(task)
                    task.add_done_callback(lambda t: _task_done(t, active_tasks))
                    continue

                message   = update.get("message", {})
                chat_id   = message.get("chat", {}).get("id")
                text      = (message.get("text") or "").strip()
                user_id   = str(message.get("from", {}).get("id", "unknown"))
                from_name = message.get("from", {}).get("first_name", "User")

                if not chat_id or not text:
                    continue

                log.info("Message", from_name=from_name, text=text[:50])

                task = asyncio.create_task(
                    _handle_message(chat_id, user_id, text, from_name, token),
                    name="tg-" + str(chat_id),
                )
                active_tasks.add(task)
                task.add_done_callback(lambda t: _task_done(t, active_tasks))

        except asyncio.CancelledError:
            break
        except httpx.ReadTimeout:
            continue
        except Exception as e:
            if _bot_running:
                log.error("Polling error", error=str(e))
                await asyncio.sleep(5)

    if active_tasks:
        await asyncio.gather(*active_tasks, return_exceptions=True)

    log.info("Telegram polling stopped")


# ── Thread runner ─────────────────────────────────────────────
def _run_in_thread(token: str):
    global _bot_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bot_loop = loop
    try:
        loop.run_until_complete(_polling_loop(token))
    except Exception as e:
        log.error("Polling thread fatal", error=str(e))
    finally:
        loop.close()
        _bot_loop = None


# ── Public API ────────────────────────────────────────────────
def start_polling(token: str) -> bool:
    global _bot_thread, _bot_running
    if _bot_running:
        return False
    _bot_running = True
    _bot_thread  = threading.Thread(
        target=_run_in_thread,
        args=(token,),
        daemon=True,
        name="telegram-polling",
    )
    _bot_thread.start()
    log.info("Telegram polling thread started")
    return True


def stop_polling():
    global _bot_running, _bot_thread, _bot_loop
    _bot_running = False
    if _bot_loop and _bot_loop.is_running():
        _bot_loop.call_soon_threadsafe(_bot_loop.stop)
    if _bot_thread and _bot_thread.is_alive():
        _bot_thread.join(timeout=8)
    _bot_thread = None
    log.info("Telegram polling stopped")


def is_running() -> bool:
    return (
        _bot_running
        and _bot_thread is not None
        and _bot_thread.is_alive()
    )

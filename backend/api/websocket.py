import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.model_manager import model_manager
from core.smart_router import smart_router
from memory.manager import memory_manager
from rag.engine import rag_engine
import structlog

router = APIRouter()
log = structlog.get_logger()

active_connections: dict = {}


@router.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    log.info("WebSocket connected", session_id=session_id)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            msg_type = payload.get("type", "chat")

            if msg_type == "chat":
                message = payload.get("message", "")
                model = payload.get("model")
                user_id = payload.get("user_id", "anonymous")
                use_rag = payload.get("use_rag", True)

                # Route model
                route = smart_router.route(message, model)
                chosen_model = route["model"]

                # Build context
                system = await memory_manager.build_system_prompt(user_id, session_id)
                rag_sources = []

                if use_rag:
                    rag_results = await rag_engine.query(message, user_id=user_id)
                    if rag_results:
                        system += "\n\n" + rag_engine.build_context(rag_results)
                        rag_sources = [r["source"] for r in rag_results]

                history = await memory_manager.get_short_term(session_id)
                messages = [{"role": "system", "content": system}]
                messages += history[-10:]
                messages.append({"role": "user", "content": message})

                # Send start event
                await websocket.send_text(json.dumps({
                    "type": "start",
                    "model": chosen_model,
                    "session_id": session_id,
                }))

                # Stream response
                full_response = ""
                async for chunk in model_manager.chat_stream(
                    model=chosen_model,
                    messages=messages,
                    temperature=payload.get("temperature", 0.7),
                    max_tokens=payload.get("max_tokens", 4096),
                ):
                    full_response += chunk
                    await websocket.send_text(json.dumps({
                        "type": "chunk",
                        "content": chunk,
                    }))

                # Save to memory
                await memory_manager.save_chat_to_redis(session_id, "user", message)
                await memory_manager.save_chat_to_redis(session_id, "assistant", full_response)

                await websocket.send_text(json.dumps({
                    "type": "done",
                    "sources": rag_sources,
                    "model": chosen_model,
                }))

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        active_connections.pop(session_id, None)
        log.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        log.error("WebSocket error", error=str(e))
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass
        active_connections.pop(session_id, None)

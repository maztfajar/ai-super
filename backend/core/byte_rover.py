"""
Byte Rover Skill (Long-term Memory)
===================================
Menyimpan dan me-recall memori percakapan lama ke dalam Vector Database (ChromaDB)
menggunakan RAG engine, sehingga agent tidak melupakan detail proyek dari sesi yang terputus.
"""

import asyncio
import structlog
from datetime import datetime
from db.database import AsyncSessionLocal
from db.models import ChatSession, Message
from sqlmodel import select, desc
from rag.engine import rag_engine
from core.model_manager import model_manager

log = structlog.get_logger()


class ByteRover:
    """Long-term Memory Engine."""
    
    async def background_loop(self):
        """Berjalan di background untuk merangkum sesi-sesi yang sudah idle (selesai)."""
        while True:
            try:
                await asyncio.sleep(3600)  # Cek setiap 1 jam
                await self._process_idle_sessions()
            except Exception as e:
                log.error("Byte Rover background loop error", error=str(e))
                await asyncio.sleep(300)

    async def _process_idle_sessions(self):
        try:
            from datetime import timedelta
            async with AsyncSessionLocal() as db:
                # Cari sesi yang belum dirangkum dan tidak diupdate selama > 1 jam
                idle_time = datetime.utcnow() - timedelta(hours=1)
                stmt = select(ChatSession).where(ChatSession.updated_at < idle_time)
                res = await db.execute(stmt)
                sessions = res.scalars().all()
                
                for session in sessions:
                    meta = session.project_metadata or {}
                    if not isinstance(meta, dict):
                        meta = {}
                        
                    if not meta.get("byte_rover_summarized"):
                        log.info("Byte Rover: Merangkum sesi idle", session_id=session.id)
                        await self.memorize(session.id)
                        # Tandai sudah dirangkum
                        meta["byte_rover_summarized"] = True
                        session.project_metadata = meta
                        db.add(session)
                        await db.commit()
                        await asyncio.sleep(5)  # Beri jeda agar LLM tidak rate-limit
        except Exception as e:
            log.error("Gagal memproses sesi idle", error=str(e))

    async def memorize(self, session_id: str):
        """
        Baca seluruh pesan dari sebuah sesi, buat ringkasannya (jika cukup panjang),
        dan simpan sebagai memori permanen ke VectorDB.
        """
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
                res = await db.execute(stmt)
                messages = res.scalars().all()

            if len(messages) < 4:
                return  # Terlalu pendek untuk dijadikan memori bermakna

            # Kumpulkan teks percakapan
            conversation = []
            for msg in messages:
                if msg.role in ["user", "assistant"]:
                    conversation.append(f"{msg.role.upper()}: {msg.content}")

            full_text = "\n\n".join(conversation)
            
            # Buat ringkasan menggunakan model ringan (gpt-5-mini atau qwen3.6-plus)
            prompt = (
                "Buatlah ringkasan eksekutif dan terstruktur dari percakapan berikut. "
                "Fokus pada fakta penting, keputusan yang diambil, teknologi yang digunakan, "
                "dan status terakhir proyek. Ringkasan ini akan disimpan sebagai memori jangka panjang AI. "
                "Hanya berikan teks ringkasan, tanpa basa-basi.\n\n"
                f"Percakapan:\n{full_text[:15000]}" # Batasi konteks agar tidak OOM
            )

            # Cari model yang cepat/ringan untuk summarization (capability "speed" atau "text")
            model = model_manager.get_default_model()
            try:
                from agents.agent_registry import agent_registry as _ar
                model = _ar.resolve_model_for_agent("general")
            except Exception:
                pass

            summary = ""
            async for chunk in model_manager.chat_stream(
                model_id=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            ):
                summary += chunk

            if not summary.strip():
                return

            # Format final memori
            now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            memory_text = (
                f"### MEMORY CHECKPOINT (Session: {session_id})\n"
                f"Date: {now_str}\n\n"
                f"{summary.strip()}"
            )

            metadata = {
                "type": "byte_rover_memory",
                "session_id": session_id,
                "source": "memory",
                "timestamp": now_str
            }

            # Simpan ke RAG
            result = await rag_engine.index_text(memory_text, metadata)
            log.info("Byte Rover: Memori tersimpan", session_id=session_id, chunks=result.get("chunks", 0))

        except Exception as e:
            log.error("Byte Rover memorize gagal", session_id=session_id, error=str(e))

    async def recall(self, query: str) -> str:
        """
        Tarik memori masa lalu yang paling relevan dengan query user.
        """
        try:
            # Query ke RAG
            rag_results = await rag_engine.query(query, top_k=3)
            
            memory_context = ""
            count = 1
            for r in rag_results:
                meta = r.get("metadata", {})
                if meta.get("type") == "byte_rover_memory":
                    memory_context += f"[Memory {count} | {meta.get('timestamp', '')}]\n{r['content']}\n\n"
                    count += 1
                    
            if memory_context:
                return f"### LONG-TERM MEMORY RECALLED (Byte Rover) ###\n\n{memory_context.strip()}"
                
            return ""
        except Exception as e:
            log.error("Byte Rover recall gagal", error=str(e))
            return ""

byte_rover = ByteRover()

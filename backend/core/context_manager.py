"""
ContextManager — Rolling context summarizer dengan pinned context.
Auto-summarize setiap 20 pesan. Pinned context untuk task aktif.
"""
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import structlog

log = structlog.get_logger()

MAX_RECENT = 10       # pesan terakhir yang selalu disertakan
SUMMARY_THRESHOLD = 20  # trigger auto-summary setiap N pesan


class ContextManager:
    """
    Kelola context window agar tidak membengkak.
    Struktur: summary (ringkasan lama) + pinned (task aktif) + recent (10 terakhir)
    """

    async def get_context(
        self,
        session_id: str,
        history: List[Dict],
        active_task: Optional[str] = None,
        active_step: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Kembalikan context yang sudah dikompresi.

        Returns:
            {
                "summary": str,       # ringkasan pesan lama
                "pinned": str,        # task aktif + progress
                "recent": list,       # 10 pesan terakhir
                "total_original": int # jumlah pesan asli
            }
        """
        total = len(history)
        recent = history[-MAX_RECENT:] if len(history) > MAX_RECENT else history
        older = history[:-MAX_RECENT] if len(history) > MAX_RECENT else []

        # Load summary dari DB (jika ada)
        summary = await self._load_summary(session_id)

        # Auto-summarize jika pesan lama cukup banyak dan belum ada summary
        if older and not summary:
            summary = await self._summarize(older, session_id)

        # Build pinned context
        pinned = self._build_pinned(active_task, active_step)

        return {
            "summary": summary or "",
            "pinned": pinned,
            "recent": recent,
            "total_original": total,
        }

    def build_system_injection(self, context: Dict[str, Any]) -> str:
        """
        Format context dict menjadi string untuk di-inject ke system prompt.
        """
        parts = []

        if context.get("summary"):
            parts.append(f"[RINGKASAN PERCAKAPAN SEBELUMNYA]\n{context['summary']}")

        if context.get("pinned"):
            parts.append(f"[TASK AKTIF]\n{context['pinned']}")

        if context.get("total_original", 0) > MAX_RECENT:
            skipped = context["total_original"] - MAX_RECENT
            parts.append(f"[Catatan: {skipped} pesan lama sudah diringkas di atas]")

        return "\n\n".join(parts)

    def _build_pinned(
        self,
        active_task: Optional[str],
        active_step: Optional[str],
    ) -> str:
        """Build pinned context string untuk task yang sedang aktif."""
        if not active_task:
            return ""
        lines = [f"Sedang mengerjakan: {active_task}"]
        if active_step:
            lines.append(f"Progress: {active_step}")
        return "\n".join(lines)

    async def _summarize(
        self,
        messages: List[Dict],
        session_id: str,
    ) -> str:
        """
        Buat ringkasan dari pesan-pesan lama menggunakan LLM.
        Simpan ke DB untuk dipakai lagi.
        """
        if not messages:
            return ""

        try:
            from core.model_manager import model_manager

            # Format pesan untuk summarization
            text_parts = []
            for m in messages[-40:]:  # max 40 pesan untuk summarize
                role = m.get("role", "user")
                content = str(m.get("content", ""))[:500]
                text_parts.append(f"{role}: {content}")

            conversation_text = "\n".join(text_parts)

            summary_prompt = (
                "Buat ringkasan singkat (max 200 kata) dari percakapan berikut. "
                "Fokus pada: task yang dikerjakan, keputusan penting, dan hasil yang sudah dicapai.\n\n"
                f"{conversation_text}"
            )

            model = model_manager.get_default_model()
            if not model:
                return self._simple_summary(messages)

            response = await model_manager.chat_completion(
                model=model,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=300,
                temperature=0.3,
            )

            summary = ""
            if hasattr(response, "choices") and response.choices:
                summary = response.choices[0].message.content or ""
            elif isinstance(response, dict):
                summary = response.get("content", "")

            if summary:
                await self._save_summary(session_id, summary)
                return summary

        except Exception as e:
            log.debug("LLM summarization failed, using simple summary", error=str(e)[:80])

        return self._simple_summary(messages)

    def _simple_summary(self, messages: List[Dict]) -> str:
        """Fallback: ringkasan sederhana tanpa LLM."""
        user_msgs = [m.get("content", "")[:100] for m in messages if m.get("role") == "user"]
        if not user_msgs:
            return ""
        count = len(messages)
        preview = user_msgs[0] if user_msgs else ""
        return f"[{count} pesan sebelumnya. Topik awal: {preview}...]"

    async def _load_summary(self, session_id: str) -> Optional[str]:
        """Load summary dari DB."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ChatSession
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = select(ChatSession).where(ChatSession.id == session_id)
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session and session.project_metadata:
                    meta = session.project_metadata
                    if isinstance(meta, dict):
                        return meta.get("context_summary")
        except Exception as e:
            log.debug("Failed to load summary", error=str(e)[:80])
        return None

    async def _save_summary(self, session_id: str, summary: str) -> None:
        """Simpan summary ke ChatSession.project_metadata."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ChatSession
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = select(ChatSession).where(ChatSession.id == session_id)
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session:
                    meta = session.project_metadata or {}
                    meta["context_summary"] = summary
                    meta["summary_updated_at"] = datetime.utcnow().isoformat()
                    session.project_metadata = meta
                    db.add(session)
                    await db.commit()
        except Exception as e:
            log.debug("Failed to save summary", error=str(e)[:80])

    def should_summarize(self, history: List[Dict]) -> bool:
        """Cek apakah sudah waktunya auto-summarize."""
        return len(history) > 0 and len(history) % SUMMARY_THRESHOLD == 0


context_manager = ContextManager()

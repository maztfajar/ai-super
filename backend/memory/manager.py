"""
AI ORCHESTRATOR — Memory Manager (Enhanced)
3-Layer Memory System:
  Layer 1: Short-term  → Redis (active context, TTL 7 hari)
  Layer 2: Long-term   → Database (riwayat chat permanen, fallback Redis)
  Layer 3: Behavioral  → Database (preferensi & kebiasaan user)
"""
import json
import asyncio
from typing import Optional, List
import structlog
from core.config import settings

log = structlog.get_logger()

CONTEXT_WINDOW   = 30
DB_HISTORY_LIMIT = 60
REDIS_TTL        = 86400 * 7  # 7 hari

_SESSION_LOCKS: dict = {}

DEFAULT_AI_CORE_PROMPT = """# SYSTEM PROMPT: AI ORCHESTRATOR CORE ENGINE (AI ORCHESTRATOR)

Anda adalah **Global AI Orchestrator**, otak pusat dari sistem manajemen AI tingkat tinggi. Anda bukan satu AI tunggal, melainkan pengendali orkestrasi yang mengoordinasikan berbagai model AI untuk menyelesaikan tugas kompleks.

## PRINSIP UTAMA
1. **Peran sebagai Orchestrator**: Tugas Anda adalah memahami permintaan pengguna, menentukan strategi penyelesaian (routing), membagi tugas ke sub-model (multi-AI), mengumpulkan hasil, dan melakukan voting/validasi sebelum memberikan respon akhir.
2. **Interface vs Logic**: `seed-2-0-pro` hanya berfungsi sebagai jembatan komunikasi (antarmuka). Logika pengambilan keputusan dan eksekusi tetap berada di tangan Core Engine (Anda).
3. **Keamanan VPS**: Anda memiliki kendali atas eksekusi sistem (VPS). Setiap perintah terminal yang berisiko tinggi atau merubah status sistem **WAJIB** meminta konfirmasi eksplisit dari pengguna.
4. **Manajemen File**: Anda dapat membaca, membuat, mengedit, dan menghapus file. Setiap perubahan file **WAJIB** menampilkan preview perubahan (diff) dan meminta konfirmasi.
5. **Monitoring & Automation**: Anda bertanggung jawab memantau kesehatan sistem dan mengirimkan laporan harian otomatis melalui Telegram.

## ALUR KERJA (PIPELINE)
Setiap permintaan diproses melalui tahapan:
`Request` ➔ `Routing (Analisis Tugas)` ➔ `Multi-AI Execution (Sub-tasks)` ➔ `Voting (Konsensus Hasil)` ➔ `Validasi (Keamanan/Logika)` ➔ `Final Response`

## ATURAN EKSEKUSI
- **Routing**: Identifikasi apakah tugas memerlukan akses internet (perlu browsing), pemrosesan kode (coding), analisis data (analytics), atau komunikasi kreatif.
- **AI Voting**: Jika terdapat keraguan dalam hasil sub-model, lakukan perbandingan (voting) dan pilih hasil paling akurat/aman.
- **Konfirmasi**: Gunakan format `[MEMERLUKAN KONFIRMASI]` sebelum menjalankan perintah `sudo`, menghapus file, atau merestart layanan.
- **Preview**: Tampilkan snippet kode atau ringkasan isi file sebelum melakukan `write` atau `edit`.

## ATURAN PENULISAN & TABEL (EXCEL OPTIMIZATION)
1. Setiap kali menyajikan data tabular, Anda **WAJIB** menggunakan format Markdown Table yang standar dan bersih.
2. **JANGAN** memasukkan baris baru (line breaks) atau karakter khusus yang berlebihan di dalam satu sel tabel.
3. Pastikan setiap kolom dipisahkan secara konsisten dengan karakter pipe (`|`).
4. Jika data sangat kompleks atau besar, berikan data dalam blok kode terpisah dengan label "DATA_TABULAR".

## LOGIKA INTERAKSI (SINGLE MESSAGE EXPORT)
1. Fokuskan setiap respons sebagai satu kesatuan informasi yang mandiri.
2. Pastikan inti jawaban berada dalam **satu blok pesan yang padat dan jelas**.
3. Hindari pengulangan informasi dari pesan sebelumnya secara berlebihan.

## IDENTITAS
Nama Sistem: **AI ORCHESTRATOR Core Engine**
Bahasa: **Bahasa Indonesia (Utama)**, teknis tetap presisi.
Sikap: **Profesional, Waspada (Security-first), Efisien.**"""


# ── Helper: baca project_path dari session DB ─────────────────────────────────
async def _get_session_project_path(session_id: str) -> Optional[str]:
    """
    Ambil project_path dari session.project_metadata di database.
    FIX: Handle kasus metadata tersimpan sebagai JSON string maupun dict.
    """
    if not session_id:
        return None
    try:
        from db.database import AsyncSessionLocal
        from db.models import ChatSession
        async with AsyncSessionLocal() as db:
            session = await db.get(ChatSession, session_id)
            if not session or not session.project_metadata:
                return None
            meta = session.project_metadata
            # FIX: parse JSON string jika perlu
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    return None
            if isinstance(meta, dict):
                return meta.get("project_path")
    except Exception as e:
        log.debug("Could not read project_path from session", error=str(e)[:80])
    return None


class MemoryManager:
    def __init__(self):
        self.redis = None
        self._redis_available = False

    async def startup(self):
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.redis.ping()
            self._redis_available = True
            log.info("Memory system (Redis) connected — TTL 7 hari")
        except Exception:
            self._redis_available = False
            log.warning("Redis tidak tersedia — pakai DB fallback untuk memory")

    # ── Layer 1: Short-term Redis ─────────────────────────────────────────────
    async def save_short_term(self, session_id: str, messages: list, ttl: int = REDIS_TTL):
        if self._redis_available and self.redis:
            try:
                key = "chat:ctx:" + session_id
                trimmed = messages[-(CONTEXT_WINDOW * 2):]
                await self.redis.setex(key, ttl, json.dumps(trimmed))
            except Exception as e:
                log.warning("Redis save error", error=str(e)[:80])

    async def get_short_term(self, session_id: str) -> list:
        if self._redis_available and self.redis:
            try:
                key  = "chat:ctx:" + session_id
                data = await self.redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                log.warning("Redis get error", error=str(e)[:80])
        return []

    # ── Load history dari DB ke Redis ─────────────────────────────────────────
    async def seed_from_db(self, session_id: str, user_id: str):
        """
        Ambil riwayat chat dari database dan masukkan ke Redis.
        Dipanggil saat session dibuka / Redis kosong.
        """
        try:
            from db.database import AsyncSessionLocal
            from db.models import Message
            from sqlmodel import select
            from sqlalchemy import desc

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Message)
                    .where(Message.session_id == session_id)
                    .where(Message.user_id    == user_id)
                    .where(Message.role.in_(["user", "assistant"]))
                    .order_by(desc(Message.created_at))
                    .limit(DB_HISTORY_LIMIT)
                )
                msgs = result.scalars().all()

            if not msgs:
                return []

            msgs = list(reversed(msgs))
            history = [
                {"role": m.role, "content": m.content}
                for m in msgs
                if m.content and m.content.strip()
            ]
            await self.save_short_term(session_id, history)
            log.info("Memory seeded from DB", session_id=session_id[:8], count=len(history))
            return history
        except Exception as e:
            log.warning("Seed from DB error", error=str(e)[:100])
            return []

    async def get_context(self, session_id: str, user_id: str) -> list:
        """
        Ambil konteks chat untuk dikirim ke AI.
        Prioritas: Redis → DB → kosong
        """
        history = await self.get_short_term(session_id)
        if not history:
            history = await self.seed_from_db(session_id, user_id)
        return history[-CONTEXT_WINDOW:]

    # ── Layer 3: Behavioral (DB) ──────────────────────────────────────────────
    async def save_preference(self, user_id: str, content: str,
                              memory_type: str = "behavioral"):
        try:
            from db.database import AsyncSessionLocal
            from db.models import UserMemoryEntry
            async with AsyncSessionLocal() as db:
                entry = UserMemoryEntry(
                    user_id=user_id,
                    memory_type=memory_type,
                    content=content,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            log.warning("Save preference error", error=str(e)[:100])

    async def get_user_preferences(self, user_id: str) -> list:
        try:
            from db.database import AsyncSessionLocal
            from db.models import UserMemoryEntry
            from sqlmodel import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(UserMemoryEntry)
                    .where(UserMemoryEntry.user_id == user_id)
                    .order_by(UserMemoryEntry.created_at.desc())
                    .limit(10)
                )
                return result.scalars().all()
        except Exception:
            return []

    # ── Build system prompt ───────────────────────────────────────────────────
    async def build_system_prompt(self, user_id: str, session_id: str) -> str:
        """
        Bangun system prompt lengkap termasuk:
        - Base prompt dari file/env/default
        - User preferences
        - FIX: Project path dari session (agar AI selalu ingat lokasi project)
        """
        prefs = await self.get_user_preferences(user_id)

        # Ambil base prompt dari file external
        import os
        from pathlib import Path
        prompt_file = Path(__file__).resolve().parent.parent.parent / "data" / "ai_core_prompt.md"
        if prompt_file.exists():
            try:
                base = prompt_file.read_text(encoding="utf-8")
            except Exception:
                base = os.environ.get("AI_CORE_SYSTEM_PROMPT") or DEFAULT_AI_CORE_PROMPT
        else:
            base = os.environ.get("AI_CORE_SYSTEM_PROMPT") or DEFAULT_AI_CORE_PROMPT

        # Tambahkan user preferences
        if prefs:
            pref_texts = [p.content for p in prefs[:5] if p.content]
            if pref_texts:
                base += "\n\nUser preferences & context: " + "; ".join(pref_texts) + ". "

        # ── FIX: Inject project_path ke system prompt ─────────────────────
        # Ini yang membuat AI selalu ingat lokasi project meskipun:
        # 1. Redis TTL habis
        # 2. Chat ditinggal lama
        # 3. Session di-reload
        project_path = await _get_session_project_path(session_id)
        if project_path:
            base += (
                f"\n\n## KONTEKS PROJECT AKTIF (KRITIS — JANGAN DIABAIKAN)\n"
                f"Session ini memiliki project yang sedang dikerjakan:\n"
                f"- **Lokasi Project:** `{project_path}`\n"
                f"- **WAJIB:** Semua operasi file, bash command, dan instalasi paket "
                f"HARUS dilakukan di dalam direktori ini.\n"
                f"- **Format command yang benar:** `cd {project_path} && <perintah>`\n"
                f"- **Format write_file yang benar:** path relatif terhadap `{project_path}`\n"
                f"- **JANGAN** membuat folder project baru atau bekerja di luar direktori ini "
                f"kecuali user secara eksplisit meminta.\n"
                f"- Jika diminta melanjutkan pekerjaan, langsung lanjutkan di `{project_path}` "
                f"tanpa tanya ulang lokasi."
            )
            log.debug("Project path injected into system prompt",
                     session_id=session_id[:8] if session_id else "none",
                     project_path=project_path)
        else:
            # FIX: Beri hint ke model agar tanya lokasi project jika belum di-set
            base += (
                "\n\n## CATATAN PROJECT\n"
                "Belum ada lokasi project yang ditetapkan untuk session ini. "
                "Jika user meminta membuat aplikasi atau project baru, "
                "WAJIB minta user memilih lokasi penyimpanan terlebih dahulu "
                "sebelum membuat file apapun."
            )

        return base

    # ── Save ke Redis + perpanjang TTL ────────────────────────────────────────
    async def save_chat_to_redis(self, session_id: str, role: str, content: str):
        """Thread-safe save menggunakan per-session asyncio.Lock."""
        if session_id not in _SESSION_LOCKS:
            _SESSION_LOCKS[session_id] = asyncio.Lock()
        lock = _SESSION_LOCKS[session_id]

        async with lock:
            existing = await self.get_short_term(session_id)
            existing.append({"role": role, "content": content})
            await self.save_short_term(session_id, existing)

    # ── Info memory untuk UI ──────────────────────────────────────────────────
    async def get_memory_info(self, session_id: str, user_id: str) -> dict:
        redis_count = 0
        db_count    = 0
        try:
            history     = await self.get_short_term(session_id)
            redis_count = len(history)
        except Exception:
            pass
        try:
            from db.database import AsyncSessionLocal
            from db.models import Message
            from sqlmodel import select, func
            async with AsyncSessionLocal() as db:
                r = await db.execute(
                    select(func.count(Message.id))
                    .where(Message.session_id == session_id)
                )
                db_count = r.scalar() or 0
        except Exception:
            pass
        return {
            "redis_messages":    redis_count,
            "db_messages":       db_count,
            "redis_available":   self._redis_available,
            "context_window":    CONTEXT_WINDOW,
            "redis_ttl_days":    REDIS_TTL // 86400,
        }

    async def clear_session(self, session_id: str):
        """Reset konteks satu sesi (tanpa hapus dari DB)."""
        if self._redis_available and self.redis:
            try:
                await self.redis.delete("chat:ctx:" + session_id)
            except Exception:
                pass


memory_manager = MemoryManager()

"""
AI ORCHESTRATOR — Memory Manager (Enhanced)
3-Layer Memory System:
  Layer 1: Short-term  → Redis (active context, TTL 24 jam)
  Layer 2: Long-term   → Database (riwayat chat permanen, fallback Redis)
  Layer 3: Behavioral  → Database (preferensi & kebiasaan user)
"""
import json
import asyncio
from typing import Optional, List
import structlog
from core.config import settings

log = structlog.get_logger()

# Batas riwayat yang dibawa ke konteks AI
CONTEXT_WINDOW   = 30   # naik dari 20 → 30 agar AI lebih ingat konteks panjang
DB_HISTORY_LIMIT = 60   # maks pesan diambil dari DB untuk seed Redis
REDIS_TTL        = 86400 * 7  # 7 hari

# Per-session asyncio locks untuk mencegah race condition di save_chat_to_redis
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
2. **JANGAN** memasukkan baris baru (line breaks) atau karakter khusus yang berlebihan di dalam satu sel tabel, karena akan merusak format saat dikonversi ke Excel.
3. Pastikan setiap kolom dipisahkan secara konsisten dengan karakter pipe (`|`) dan header tabel didefinisikan dengan jelas menggunakan garis putus-putus (`---`).
4. Jika data sangat kompleks atau besar, berikan data dalam blok kode terpisah dengan label "DATA_TABULAR" agar sistem dapat memproses konversi kolom Excel secara otomatis.

## LOGIKA INTERAKSI (SINGLE MESSAGE EXPORT)
1. Fokuskan setiap respons sebagai satu kesatuan informasi yang mandiri. Hal ini karena setiap pesan Anda akan memiliki tombol unduhan (PDF, DOCX, XLSX, TXT) tepat di bawahnya.
2. Karena sistem menggunakan *single-message export*, pastikan inti jawaban Anda berada dalam **satu blok pesan yang padat dan jelas** agar pengguna tidak perlu menggabungkan beberapa pesan saat mengunduh.
3. Hindari pengulangan informasi dari pesan sebelumnya secara berlebihan agar file yang diunduh per-pesan tetap ringkas dan relevan. Tujuan akhirnya adalah menghasilkan output yang jika dikonversi menjadi file Excel, setiap baris Markdown akan menjadi baris Excel yang rapi, dan setiap kolom Markdown akan terpisah menjadi kolom Excel (A, B, C, dst) secara akurat.

## IDENTITAS
Nama Sistem: **AI ORCHESTRATOR Core Engine**
Bahasa: **Bahasa Indonesia (Utama)**, teknis tetap presisi.
Sikap: **Profesional, Waspada (Security-first), Efisien.**"""



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

    # ── Layer 1: Short-term Redis ─────────────────────────────
    async def save_short_term(self, session_id: str, messages: list, ttl: int = REDIS_TTL):
        if self._redis_available and self.redis:
            try:
                key = "chat:ctx:" + session_id
                # Simpan maks CONTEXT_WINDOW * 2 pesan (user+assistant pairs)
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

    # ── Load history dari DB ke Redis (saat session dibuka) ───
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

            # Balik urutan (terbaru di akhir)
            msgs = list(reversed(msgs))
            history = [
                {"role": m.role, "content": m.content}
                for m in msgs
                if m.content and m.content.strip()
            ]
            # Simpan ke Redis
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
        # Coba Redis dulu
        history = await self.get_short_term(session_id)

        # Jika Redis kosong, ambil dari DB dan seed ke Redis
        if not history:
            history = await self.seed_from_db(session_id, user_id)

        return history[-CONTEXT_WINDOW:]  # batas window ke AI

    # ── Layer 3: Behavioral (DB) ──────────────────────────────
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

    # ── Build system prompt ────────────────────────────────────
    async def build_system_prompt(self, user_id: str, session_id: str) -> str:
        prefs = await self.get_user_preferences(user_id)
        
        # Coba ambil dari file external
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
        
        if prefs:
            pref_texts = [p.content for p in prefs[:5] if p.content]
            if pref_texts:
                base += "\n\nUser preferences & context: " + "; ".join(pref_texts) + ". "
        return base

    # ── Save ke Redis + perpanjang TTL ────────────────────────
    async def save_chat_to_redis(self, session_id: str, role: str, content: str):
        """Thread-safe save menggunakan per-session asyncio.Lock."""
        # Dapatkan atau buat lock untuk session ini
        if session_id not in _SESSION_LOCKS:
            _SESSION_LOCKS[session_id] = asyncio.Lock()
        lock = _SESSION_LOCKS[session_id]

        async with lock:
            existing = await self.get_short_term(session_id)
            existing.append({"role": role, "content": content})
            await self.save_short_term(session_id, existing)

    # ── Info memory untuk UI ──────────────────────────────────
    async def get_memory_info(self, session_id: str, user_id: str) -> dict:
        """Info singkat tentang state memory — untuk ditampilkan di UI."""
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

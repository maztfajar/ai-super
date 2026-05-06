"""
AI ORCHESTRATOR — Skill Evolution Engine
Mengkristalisasi ProceduralMemory menjadi Skill permanen.

Alur:
  ProceduralMemory (success_count >= THRESHOLD)
    → AI generates Skill definition
    → Simpan ke LearnedSkill
    → Skill dipakai otomatis saat ada task serupa
    → Token lebih hemat karena tidak perlu reasoning ulang
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional
import structlog

log = structlog.get_logger()

# Threshold sebelum resep dikristalisasi jadi Skill
CRYSTALLIZE_THRESHOLD = 5   # berhasil 5x → jadi Skill
IMPROVE_THRESHOLD     = 10  # berhasil 10x → AI improve Skill
TOKEN_SAVING_ESTIMATE = 800 # estimasi token hemat per penggunaan skill


class SkillEvolutionEngine:
    """
    Engine yang mengubah pengalaman berulang menjadi Skill permanen.
    Semakin sering dipakai → semakin pintar → semakin hemat token.
    """

    def __init__(self):
        # Cache skill di memory untuk akses cepat
        self._skill_cache: dict[str, list] = {}
        self._cache_updated = 0.0

    # ══════════════════════════════════════════════════════
    # KRISTALISASI: ProceduralMemory → Skill
    # ══════════════════════════════════════════════════════

    async def check_and_crystallize(self, memory_id: str):
        """
        Dipanggil setiap kali ProceduralMemory diupdate.
        Jika sudah memenuhi threshold → kristalisasi jadi Skill.
        """
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProceduralMemory, LearnedSkill
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                # Ambil memory yang baru diupdate
                mem = await db.get(ProceduralMemory, memory_id)
                if not mem:
                    return

                # Cek apakah sudah ada skill dari memory ini
                existing_skill = await db.execute(
                    select(LearnedSkill).where(
                        LearnedSkill.source_memory_id == memory_id,
                        LearnedSkill.is_active == True,
                    )
                )
                skill = existing_skill.scalar_one_or_none()

                if skill:
                    # Skill sudah ada — cek apakah perlu improvement
                    if mem.success_count >= IMPROVE_THRESHOLD and \
                       mem.success_count % IMPROVE_THRESHOLD == 0:
                        await self._improve_skill(db, skill, mem)
                    else:
                        # Update stats saja
                        skill.usage_count    = mem.success_count
                        skill.avg_confidence = mem.avg_confidence
                        skill.updated_at = datetime.now(
                            timezone.utc).replace(tzinfo=None)
                        db.add(skill)
                        await db.commit()

                elif mem.success_count >= CRYSTALLIZE_THRESHOLD:
                    # Belum ada skill — kristalisasi sekarang
                    log.info("Crystallizing memory into skill",
                             category=mem.category,
                             memory_id=memory_id[:8],
                             success_count=mem.success_count)
                    await self._crystallize(db, mem)

        except Exception as e:
            log.warning("Crystallization check failed",
                        error=str(e)[:100])

    async def _crystallize(self, db, mem) -> Optional[str]:
        """
        Ubah ProceduralMemory menjadi Skill permanen.
        AI akan generate nama, deskripsi, dan template skill.
        """
        from db.models import LearnedSkill

        # Generate skill definition menggunakan AI
        skill_def = await self._ai_generate_skill(mem)

        skill = LearnedSkill(
            name=              skill_def.get("name", f"skill_{mem.category}"),
            category=          mem.category,
            description=       skill_def.get("description", mem.task_summary[:200]),
            trigger_keywords=  skill_def.get("trigger_keywords", mem.keywords),
            steps_json=        mem.steps_json,
            tools_json=        mem.tools_used or "[]",
            template=          skill_def.get("template", ""),
            version=           1,
            usage_count=       mem.success_count,
            success_count=     mem.success_count,
            avg_confidence=    mem.avg_confidence,
            avg_tokens_saved=  TOKEN_SAVING_ESTIMATE,
            source_memory_id=  mem.id,
            is_active=         True,
            created_at=        datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=        datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(skill)
        await db.commit()
        await db.refresh(skill)

        # Invalidate cache
        self._skill_cache = {}

        log.info("New skill crystallized",
                 name=skill.name,
                 category=skill.category,
                 skill_id=skill.id[:8])

        # Kirim notifikasi ke Telegram
        await self._notify_new_skill(skill)

        return skill.id

    async def _improve_skill(self, db, skill, mem):
        """
        AI memperbaiki skill yang sudah ada berdasarkan
        pengalaman tambahan yang terkumpul.
        """
        log.info("Improving existing skill",
                 name=skill.name,
                 current_version=skill.version,
                 usage_count=mem.success_count)

        improved = await self._ai_improve_skill(skill, mem)
        if not improved:
            return

        skill.template       = improved.get("template", skill.template)
        skill.description    = improved.get("description", skill.description)
        skill.steps_json     = mem.steps_json  # update dengan langkah terbaru
        skill.version       += 1
        skill.avg_confidence = mem.avg_confidence
        skill.avg_tokens_saved = int(
            skill.avg_tokens_saved * 1.1  # setiap improvement hemat 10% lebih banyak
        )
        skill.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        db.add(skill)
        await db.commit()

        # Invalidate cache
        self._skill_cache = {}

        log.info("Skill improved",
                 name=skill.name,
                 new_version=skill.version)

    # ══════════════════════════════════════════════════════
    # SKILL LOOKUP: gunakan skill untuk hemat token
    # ══════════════════════════════════════════════════════

    async def find_matching_skill(
        self, category: str, query: str
    ) -> Optional[dict]:
        """
        Cari skill yang cocok dengan query.
        Jika ditemukan → kembalikan template skill untuk dipakai langsung.
        Token hemat karena tidak perlu thinking dari nol.
        """
        try:
            skills = await self._get_skills_for_category(category)
            if not skills:
                return None

            query_words = set(query.lower().split())
            best_match  = None
            best_score  = 0.0

            for skill in skills:
                trigger_words = set(
                    skill["trigger_keywords"].lower().split()
                )
                overlap = len(query_words & trigger_words)
                if overlap == 0:
                    continue

                # Score: overlap × confidence × usage (semakin sering dipakai, lebih dipercaya)
                score = (
                    overlap *
                    skill["avg_confidence"] *
                    min(skill["usage_count"] / 10, 2.0)  # cap bonus di 2x
                )

                if score > best_score:
                    best_score  = score
                    best_match  = skill

            if best_match and best_score >= 1.5:  # threshold minimum
                log.info("Skill match found",
                         name=best_match["name"],
                         score=round(best_score, 2),
                         tokens_saved=best_match["avg_tokens_saved"])
                return best_match

            return None

        except Exception as e:
            log.warning("Skill lookup failed", error=str(e)[:80])
            return None

    async def record_skill_usage(
        self, skill_id: str, success: bool, tokens_used: int = 0
    ):
        """Catat penggunaan skill untuk tracking dan improvement."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import LearnedSkill

            async with AsyncSessionLocal() as db:
                skill = await db.get(LearnedSkill, skill_id)
                if not skill:
                    return

                skill.usage_count += 1
                if success:
                    skill.success_count += 1

                # Update estimasi token saving
                if tokens_used > 0:
                    skill.avg_tokens_saved = int(
                        (skill.avg_tokens_saved * (skill.usage_count - 1) +
                         tokens_used) / skill.usage_count
                    )

                skill.updated_at = datetime.now(
                    timezone.utc).replace(tzinfo=None)
                db.add(skill)
                await db.commit()

        except Exception as e:
            log.debug("Skill usage record failed", error=str(e)[:60])

    def build_skill_context(self, skill: dict) -> str:
        """
        Bangun context string dari skill untuk diinjeksi ke prompt.
        Ini yang menghemat token — AI langsung tahu langkah-langkahnya.
        """
        steps = json.loads(skill.get("steps_json", "[]"))
        tools = json.loads(skill.get("tools_json", "[]"))

        steps_text = "\n".join(
            f"  {i+1}. {s}" for i, s in enumerate(steps)
        )
        tools_text = ", ".join(tools) if tools else "standard tools"

        return (
            f"\n\n[LEARNED SKILL — v{skill.get('version', 1)}]\n"
            f"📚 Skill: **{skill['name']}**\n"
            f"📝 {skill['description']}\n"
            f"⚡ Telah dipakai {skill['usage_count']}x "
            f"(confidence: {skill['avg_confidence']:.0%})\n\n"
            f"Langkah yang terbukti efektif:\n{steps_text}\n\n"
            f"Tools yang dipakai: {tools_text}\n"
            f"[/LEARNED SKILL]\n\n"
            f"INSTRUKSI: Gunakan skill di atas sebagai panduan utama. "
            f"Kecuali ada kondisi berbeda, ikuti langkah tersebut "
            f"tanpa perlu analisis ulang dari nol."
        )

    # ══════════════════════════════════════════════════════
    # AI GENERATION
    # ══════════════════════════════════════════════════════

    async def _ai_generate_skill(self, mem) -> dict:
        """AI generate nama, deskripsi, dan template untuk skill baru."""
        try:
            from core.model_manager import model_manager
            model = model_manager.get_default_model()
            if not model:
                return self._fallback_skill_def(mem)

            steps = json.loads(mem.steps_json)
            steps_text = "\n".join(
                f"{i+1}. {s}" for i, s in enumerate(steps)
            )

            prompt = f"""Berdasarkan pola tugas yang telah berhasil dilakukan {mem.success_count} kali:

Kategori: {mem.category}
Contoh tugas: {mem.task_summary[:300]}
Langkah yang berhasil:
{steps_text}

Buatkan definisi Skill dalam format JSON:
{{
  "name": "nama skill singkat dalam snake_case (maks 5 kata)",
  "description": "deskripsi singkat apa yang dilakukan skill ini (maks 100 karakter)",
  "trigger_keywords": "kata kunci yang memicu skill ini, pisahkan spasi (maks 15 kata)",
  "template": "instruksi singkat untuk AI agar langsung eksekusi skill tanpa berpikir ulang (maks 200 karakter)"
}}

Jawab HANYA dengan JSON valid, tanpa teks lain."""

            response = await model_manager.chat_completion(
                model=model,
                messages=[
                    {"role": "system",
                     "content": "Anda adalah sistem manajemen skill AI. "
                                "Jawab hanya dengan JSON valid."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
            )

            if response:
                # Bersihkan response
                clean = response.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                return json.loads(clean.strip())

        except Exception as e:
            log.debug("AI skill generation failed", error=str(e)[:80])

        return self._fallback_skill_def(mem)

    async def _ai_improve_skill(self, skill, mem) -> Optional[dict]:
        """AI perbaiki skill berdasarkan pengalaman tambahan."""
        try:
            from core.model_manager import model_manager
            model = model_manager.get_default_model()
            if not model:
                return None

            current_steps = json.loads(skill.steps_json)
            new_steps     = json.loads(mem.steps_json)

            prompt = f"""Skill ini sudah dipakai {skill.usage_count} kali.
Perbaiki berdasarkan pengalaman terbaru.

Skill saat ini (v{skill.version}):
Nama: {skill.name}
Deskripsi: {skill.description}
Langkah: {json.dumps(current_steps, ensure_ascii=False)}

Pengalaman terbaru yang lebih baik:
Langkah baru: {json.dumps(new_steps, ensure_ascii=False)}
Confidence baru: {mem.avg_confidence:.2f}

Berikan versi yang diperbaiki dalam JSON:
{{
  "description": "deskripsi yang lebih akurat",
  "template": "instruksi yang lebih efisien"
}}

Jawab HANYA dengan JSON valid."""

            response = await model_manager.chat_completion(
                model=model,
                messages=[
                    {"role": "system",
                     "content": "Jawab hanya dengan JSON valid."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200,
            )

            if response:
                clean = response.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                return json.loads(clean.strip())

        except Exception as e:
            log.debug("AI skill improvement failed", error=str(e)[:80])

        return None

    def _fallback_skill_def(self, mem) -> dict:
        """Fallback jika AI tidak tersedia."""
        name = "_".join(mem.keywords.split()[:3]) or f"skill_{mem.category}"
        return {
            "name":             name,
            "description":      mem.task_summary[:100],
            "trigger_keywords": mem.keywords,
            "template":         f"Gunakan pola {mem.category} yang sudah terbukti.",
        }

    # ══════════════════════════════════════════════════════
    # CACHE & DB HELPERS
    # ══════════════════════════════════════════════════════

    async def _get_skills_for_category(self, category: str) -> list:
        """Ambil skills dari cache atau DB."""
        now = time.time()

        # Refresh cache setiap 5 menit
        if (category not in self._skill_cache or
                now - self._cache_updated > 300):
            await self._refresh_cache(category)

        return self._skill_cache.get(category, [])

    async def _refresh_cache(self, category: str):
        """Refresh skill cache dari DB."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import LearnedSkill
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(LearnedSkill).where(
                        LearnedSkill.category == category,
                        LearnedSkill.is_active == True,
                    ).order_by(LearnedSkill.usage_count.desc())
                )
                skills = result.scalars().all()

                self._skill_cache[category] = [
                    {
                        "id":               s.id,
                        "name":             s.name,
                        "category":         s.category,
                        "description":      s.description,
                        "trigger_keywords": s.trigger_keywords,
                        "steps_json":       s.steps_json,
                        "tools_json":       s.tools_json,
                        "template":         s.template,
                        "version":          s.version,
                        "usage_count":      s.usage_count,
                        "success_count":    s.success_count,
                        "avg_confidence":   s.avg_confidence,
                        "avg_tokens_saved": s.avg_tokens_saved,
                    }
                    for s in skills
                ]

            self._cache_updated = time.time()

        except Exception as e:
            log.warning("Skill cache refresh failed", error=str(e)[:80])

    async def list_all_skills(self, active_only: bool = True) -> list[dict]:
        """Ambil semua skill untuk ditampilkan di dashboard."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import LearnedSkill
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = select(LearnedSkill)
                if active_only:
                    stmt = stmt.where(LearnedSkill.is_active == True)
                stmt = stmt.order_by(LearnedSkill.usage_count.desc())

                result = await db.execute(stmt)
                skills = result.scalars().all()

                return [
                    {
                        "id":               s.id,
                        "name":             s.name,
                        "category":         s.category,
                        "description":      s.description,
                        "version":          s.version,
                        "usage_count":      s.usage_count,
                        "success_count":    s.success_count,
                        "avg_confidence":   round(s.avg_confidence, 2),
                        "avg_tokens_saved": s.avg_tokens_saved,
                        "total_tokens_saved": s.avg_tokens_saved * s.usage_count,
                        "is_active":        s.is_active,
                        "created_at":       s.created_at.isoformat(),
                        "updated_at":       s.updated_at.isoformat(),
                    }
                    for s in skills
                ]
        except Exception as e:
            log.warning("List skills failed", error=str(e)[:80])
            return []

    async def _notify_new_skill(self, skill):
        """Kirim notifikasi ke Telegram ketika skill baru terbentuk."""
        try:
            import httpx
            from core.config import settings

            token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
            chat_id = ""

            if not token:
                return

            # Ambil chat_id admin dari DB
            from db.database import AsyncSessionLocal
            from db.models import User
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(
                        User.is_admin == True,
                        User.telegram_chat_id != None,
                        User.is_active == True,
                    )
                )
                admin = result.scalars().first()
                if admin:
                    chat_id = admin.telegram_chat_id or ""

            if not chat_id:
                return

            msg = (
                f"🧠 *AI ORCHESTRATOR — Skill Baru Terbentuk\\!*\n\n"
                f"📚 Nama: `{skill.name}`\n"
                f"📂 Kategori: {skill.category}\n"
                f"📝 {skill.description}\n\n"
                f"✅ Terbentuk setelah {skill.usage_count}x penggunaan\n"
                f"⚡ Estimasi hemat: ~{skill.avg_tokens_saved} token/request\n\n"
                f"_Orchestra Anda semakin pintar\\!_"
            )

            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id":    chat_id,
                        "text":       msg,
                        "parse_mode": "MarkdownV2",
                    }
                )

        except Exception as e:
            log.debug("Skill notification failed", error=str(e)[:60])


# ── Singleton ─────────────────────────────────────────────────
skill_evolution = SkillEvolutionEngine()

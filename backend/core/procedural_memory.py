"""
AI ORCHESTRATOR — Procedural Memory Engine
Memori Prosedural: "Buku Resep" yang menyimpan pola tugas sukses ke database.
"""
import json
import re
import asyncio
from typing import Optional
from datetime import datetime, timezone
import structlog

log = structlog.get_logger()


class ProceduralMemoryEngine:
    async def reflect_on_task(self, category: str, task_summary: str,
                               tools_used: list, model_used: str,
                               confidence: float, steps_description: str = "") -> Optional[str]:
        if confidence < 0.5:
            return None
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProceduralMemory
            from sqlmodel import select
            keywords = self._extract_keywords(task_summary)
            async with AsyncSessionLocal() as db:
                existing = await self._find_similar(db, category, keywords)
                if existing:
                    existing.success_count += 1
                    existing.avg_confidence = (
                        (existing.avg_confidence * (existing.success_count - 1) + confidence)
                        / existing.success_count
                    )
                    existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    old_tools = json.loads(existing.tools_used or "[]")
                    existing.tools_used = json.dumps(list(set(old_tools + tools_used)))
                    if steps_description:
                        existing.steps_json = json.dumps([steps_description], ensure_ascii=False)
                    db.add(existing)
                    await db.commit()
                    log.info("Procedural memory updated", category=category, count=existing.success_count)
                    # ── Trigger kristalisasi jika memenuhi threshold ──────
                    if existing.success_count >= 5:  # CRYSTALLIZE_THRESHOLD
                        try:
                            from core.skill_evolution import skill_evolution
                            asyncio.create_task(
                                skill_evolution.check_and_crystallize(existing.id)
                            )
                        except Exception:
                            pass
                    return existing.id
                else:
                    steps = [steps_description] if steps_description else [task_summary]
                    memory = ProceduralMemory(
                        category=category, task_summary=task_summary[:500],
                        steps_json=json.dumps(steps, ensure_ascii=False),
                        tools_used=json.dumps(tools_used), model_used=model_used,
                        avg_confidence=confidence, keywords=keywords,
                        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    db.add(memory)
                    await db.commit()
                    await db.refresh(memory)
                    log.info("Procedural memory saved", category=category, id=memory.id[:8])
                    return memory.id
        except Exception as e:
            log.warning("Failed to save procedural memory", error=str(e)[:100])
            return None

    async def recall_recipes(self, category: str, query: str, limit: int = 3) -> list:
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProceduralMemory
            from sqlmodel import select
            query_keywords = set(self._extract_keywords(query).lower().split())
            if not query_keywords:
                return []
            async with AsyncSessionLocal() as db:
                stmt = (select(ProceduralMemory)
                        .where(ProceduralMemory.category == category)
                        .order_by(ProceduralMemory.success_count.desc()).limit(20))
                result = await db.execute(stmt)
                memories = result.scalars().all()
                if not memories:
                    return []
                scored = []
                for mem in memories:
                    mem_keywords = set(mem.keywords.lower().split())
                    overlap = len(query_keywords & mem_keywords)
                    if overlap > 0:
                        score = overlap * mem.success_count * mem.avg_confidence
                        scored.append((score, mem))
                scored.sort(key=lambda x: x[0], reverse=True)
                recipes = []
                for score, mem in scored[:limit]:
                    recipes.append({
                        "summary": mem.task_summary,
                        "steps": json.loads(mem.steps_json),
                        "tools": json.loads(mem.tools_used or "[]"),
                        "confidence": round(mem.avg_confidence, 2),
                        "used_count": mem.success_count,
                        "model": mem.model_used,
                    })
                if recipes:
                    log.info("Procedural memory recalled", category=category, count=len(recipes))
                return recipes
        except Exception as e:
            log.warning("Failed to recall procedural memory", error=str(e)[:100])
            return []

    async def build_recipe_context(self, category: str, query: str) -> str:
        recipes = await self.recall_recipes(category, query)
        if not recipes:
            return ""
        parts = ["\n\n[PROCEDURAL MEMORY — Pola Sukses Sebelumnya]"]
        for i, recipe in enumerate(recipes, 1):
            steps_text = "\n".join(f"  {j}. {s}" for j, s in enumerate(recipe["steps"], 1))
            tools_text = ", ".join(recipe["tools"]) if recipe["tools"] else "none"
            parts.append(
                f"\n📋 Resep #{i} (digunakan {recipe['used_count']}x, "
                f"confidence {recipe['confidence']:.0%}):\n"
                f"  Tugas: {recipe['summary'][:200]}\n  Langkah:\n{steps_text}\n  Tools: {tools_text}"
            )
        parts.append("\nGunakan pola di atas sebagai referensi.\n[/PROCEDURAL MEMORY]")
        return "\n".join(parts)

    async def _find_similar(self, db, category: str, keywords: str):
        from db.models import ProceduralMemory
        from sqlmodel import select
        stmt = (select(ProceduralMemory).where(ProceduralMemory.category == category)
                .order_by(ProceduralMemory.success_count.desc()).limit(10))
        result = await db.execute(stmt)
        memories = result.scalars().all()
        query_keywords = set(keywords.lower().split())
        best_match, best_overlap = None, 0
        for mem in memories:
            mem_keywords = set(mem.keywords.lower().split())
            overlap = len(query_keywords & mem_keywords)
            min_required = max(2, int(len(query_keywords) * 0.4))
            if overlap >= min_required and overlap > best_overlap:
                best_overlap = overlap
                best_match = mem
        return best_match

    def _extract_keywords(self, text: str) -> str:
        clean = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean.split()
        stopwords = {
            'dan', 'atau', 'yang', 'di', 'ke', 'dari', 'untuk', 'dengan',
            'adalah', 'ini', 'itu', 'pada', 'akan', 'sudah', 'bisa', 'juga',
            'saya', 'anda', 'kita', 'ada', 'tidak', 'bukan',
            'the', 'a', 'an', 'is', 'are', 'was', 'be', 'have', 'has', 'do',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'this', 'that', 'it', 'its', 'tolong', 'buat', 'buatkan', 'minta',
        }
        keywords = [w for w in words if len(w) >= 3 and w not in stopwords]
        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return " ".join(unique[:20])


procedural_memory = ProceduralMemoryEngine()

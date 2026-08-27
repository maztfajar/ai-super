"""
AI ORCHESTRATOR — Skill Registry (v1.0)
========================================
Menyimpan, mengelola, dan mencocokkan Skill yang dipelajari AI dari penyelesaian tugas.

Format penyimpanan: file Markdown dengan YAML frontmatter (skills/<id>.md)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import structlog

log = structlog.get_logger()

# ── Konstanta ─────────────────────────────────────────────────────────────────

SKILLS_DIR = Path(__file__).parent.parent / "data" / "skills"

# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Skill:
    """Satu unit kemampuan prosedural yang telah dipelajari AI."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    use_count: int = 0
    success_rate: float = 1.0
    content: str = ""  # Konten bebas dari frontmatter Markdown

    def to_dict(self) -> dict:
        return asdict(self)

    def similarity_hash(self) -> str:
        """Hash untuk deteksi duplikat berdasarkan nama + deskripsi."""
        raw = f"{self.name.lower().strip()}|{self.description.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def to_markdown(self) -> str:
        """Serialize ke format Markdown dengan YAML frontmatter."""
        tags_str = ", ".join(self.tags) if self.tags else ""
        keywords_str = ", ".join(self.trigger_keywords) if self.trigger_keywords else ""
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(self.steps)) if self.steps else ""
        examples_md = "\n".join(f"- {e}" for e in self.examples) if self.examples else ""

        md = f"""---
id: {self.id}
name: {self.name}
description: {self.description}
category: {self.category}
tags: [{tags_str}]
trigger_keywords: [{keywords_str}]
created_at: {self.created_at}
updated_at: {self.updated_at}
use_count: {self.use_count}
success_rate: {self.success_rate}
---

## Deskripsi
{self.description}

## Langkah-langkah
{steps_md}

## Contoh Penggunaan
{examples_md}

## Catatan Tambahan
{self.content}
"""
        return md.strip()

    @staticmethod
    def from_markdown(text: str, skill_id: str = "") -> "Skill":
        """Parse dari format Markdown dengan YAML frontmatter."""
        skill = Skill()
        if skill_id:
            skill.id = skill_id

        # Ekstrak YAML frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            body = text[fm_match.end():]

            def _get(key: str, default="") -> str:
                m = re.search(rf"^{key}:\s*(.+)$", fm_text, re.MULTILINE)
                return m.group(1).strip() if m else default

            def _get_list(key: str) -> list[str]:
                m = re.search(rf"^{key}:\s*\[(.*?)\]$", fm_text, re.MULTILINE)
                if m:
                    raw = m.group(1).strip()
                    return [x.strip() for x in raw.split(",") if x.strip()] if raw else []
                return []

            skill.id = _get("id") or skill.id
            skill.name = _get("name")
            skill.description = _get("description")
            skill.category = _get("category", "general")
            skill.tags = _get_list("tags")
            skill.trigger_keywords = _get_list("trigger_keywords")
            skill.created_at = _get("created_at")
            skill.updated_at = _get("updated_at")
            try:
                skill.use_count = int(_get("use_count", "0"))
            except ValueError:
                skill.use_count = 0
            try:
                skill.success_rate = float(_get("success_rate", "1.0"))
            except ValueError:
                skill.success_rate = 1.0

            # Ekstrak steps dari body
            steps_match = re.search(r"## Langkah-langkah\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
            if steps_match:
                raw_steps = steps_match.group(1).strip()
                skill.steps = [
                    re.sub(r"^\d+\.\s*", "", s).strip()
                    for s in raw_steps.split("\n")
                    if s.strip()
                ]

            # Ekstrak examples dari body
            examples_match = re.search(r"## Contoh Penggunaan\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
            if examples_match:
                raw_ex = examples_match.group(1).strip()
                skill.examples = [
                    re.sub(r"^-\s*", "", e).strip()
                    for e in raw_ex.split("\n")
                    if e.strip()
                ]

            # Sisanya jadi content
            notes_match = re.search(r"## Catatan Tambahan\n(.*?)$", body, re.DOTALL)
            if notes_match:
                skill.content = notes_match.group(1).strip()
        else:
            # Tidak ada frontmatter — anggap sebagai plain text
            skill.name = "Imported Skill"
            skill.content = text
            skill.created_at = _now_iso()
            skill.updated_at = _now_iso()

        return skill


# ══════════════════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ══════════════════════════════════════════════════════════════════════════════
# Skill Registry
# ══════════════════════════════════════════════════════════════════════════════

class SkillRegistry:
    """
    Singleton registry untuk seluruh skill.
    Menyimpan skill ke file .md di SKILLS_DIR, load saat startup.
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._loaded = False
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Startup load ─────────────────────────────────────────────────────────

    def load_all(self) -> int:
        """Load semua skill dari disk ke memory. Dipanggil saat startup."""
        self._skills.clear()
        count = 0
        for md_file in SKILLS_DIR.glob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
                skill = Skill.from_markdown(text, skill_id=md_file.stem)
                if skill.name:
                    self._skills[skill.id] = skill
                    count += 1
            except Exception as e:
                log.warning("SkillRegistry: gagal load skill", file=str(md_file), error=str(e))
        self._loaded = True
        log.info(f"SkillRegistry: loaded {count} skill(s)")
        return count

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def list_skills(self, category: str = "", search: str = "") -> list[Skill]:
        """Ambil semua skill, dengan filter opsional."""
        results = list(self._skills.values())
        if category:
            results = [s for s in results if s.category == category]
        if search:
            q = search.lower()
            results = [
                s for s in results
                if q in s.name.lower()
                or q in s.description.lower()
                or any(q in t for t in s.tags)
                or any(q in k for k in s.trigger_keywords)
            ]
        return sorted(results, key=lambda s: s.updated_at or "", reverse=True)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    # ── Safety Validation ───────────────────────────────────────────────────

    DANGEROUS_SKILL_PATTERNS = [
        r"\brm\s+-rf\s+[/~]",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r":\(\)\s*\{",
        r"\b(shutdown|reboot|halt|poweroff)\b",
        r"nc\s+.*-e\s+/bin",
        r"chmod\s+[0-7]*[67][0-7]\s+/(etc|bin|usr)",
    ]

    def validate_safety(self, skill: Skill) -> tuple[bool, str]:
        """
        Validasi apakah skill mengandung instruksi/command berbahaya.
        Returns: (is_safe, error_reason)
        """
        all_text = " ".join([
            skill.name,
            skill.description,
            " ".join(skill.steps),
            " ".join(skill.examples),
            skill.content,
        ])

        for pattern in self.DANGEROUS_SKILL_PATTERNS:
            if re.search(pattern, all_text, re.IGNORECASE):
                return False, f"Dangerous command pattern detected: {pattern}"

        return True, ""

    def create_skill(self, data: dict) -> Skill:
        """Buat skill baru. Tolak jika duplikat ditemukan atau tidak aman."""
        now = _now_iso()
        skill = Skill(
            id=str(uuid.uuid4())[:8],
            name=data.get("name", "Untitled Skill"),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            steps=data.get("steps", []),
            examples=data.get("examples", []),
            trigger_keywords=data.get("trigger_keywords", []),
            content=data.get("content", ""),
            created_at=now,
            updated_at=now,
            use_count=0,
            success_rate=1.0,
        )

        # Cek safety
        is_safe, reason = self.validate_safety(skill)
        if not is_safe:
            raise ValueError(f"Skill creation blocked by safety engine: {reason}")

        # Cek duplikat
        dup = self._find_duplicate(skill)
        if dup:
            raise ValueError(f"Skill serupa sudah ada: '{dup.name}' (id={dup.id})")

        self._skills[skill.id] = skill
        self._save_to_disk(skill)
        log.info("SkillRegistry: skill dibuat", id=skill.id, name=skill.name)
        return skill

    def update_skill(self, skill_id: str, data: dict) -> Skill:
        """Update skill yang sudah ada."""
        skill = self._skills.get(skill_id)
        if not skill:
            raise KeyError(f"Skill tidak ditemukan: {skill_id}")

        for field_name in ["name", "description", "category", "tags", "steps",
                            "examples", "trigger_keywords", "content"]:
            if field_name in data:
                setattr(skill, field_name, data[field_name])

        skill.updated_at = _now_iso()
        self._save_to_disk(skill)
        log.info("SkillRegistry: skill diupdate", id=skill_id)
        return skill

    def delete_skill(self, skill_id: str) -> bool:
        """Hapus skill dari registry dan disk."""
        if skill_id not in self._skills:
            return False
        del self._skills[skill_id]
        md_path = SKILLS_DIR / f"{skill_id}.md"
        if md_path.exists():
            md_path.unlink()
        log.info("SkillRegistry: skill dihapus", id=skill_id)
        return True

    # ── Import / Export ───────────────────────────────────────────────────────

    def import_from_markdown(self, text: str) -> list[Skill]:
        """Import dari teks Markdown (satu atau beberapa skill dipisah ---)."""
        # Coba split multi-skill dengan separator khusus
        blocks = re.split(r"\n---\n(?=---\n)", text)
        if len(blocks) == 1:
            blocks = [text]

        imported = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            try:
                skill_data = Skill.from_markdown(block)
                if not skill_data.name:
                    continue
                skill_data.id = str(uuid.uuid4())[:8]
                skill_data.created_at = _now_iso()
                skill_data.updated_at = _now_iso()
                dup = self._find_duplicate(skill_data)
                if dup:
                    log.info("SkillRegistry: import skip duplikat", name=skill_data.name)
                    continue
                self._skills[skill_data.id] = skill_data
                self._save_to_disk(skill_data)
                imported.append(skill_data)
            except Exception as e:
                log.warning("SkillRegistry: gagal import skill", error=str(e))

        return imported

    def import_from_json(self, data: list[dict]) -> list[Skill]:
        """Import dari list of dict (JSON format)."""
        imported = []
        for item in data:
            try:
                item["id"] = str(uuid.uuid4())[:8]
                item.setdefault("created_at", _now_iso())
                item["updated_at"] = _now_iso()
                skill = Skill(**{
                    k: v for k, v in item.items()
                    if k in Skill.__dataclass_fields__
                })
                dup = self._find_duplicate(skill)
                if dup:
                    continue
                self._skills[skill.id] = skill
                self._save_to_disk(skill)
                imported.append(skill)
            except Exception as e:
                log.warning("SkillRegistry: gagal import JSON skill", error=str(e))
        return imported

    def export_all_json(self) -> list[dict]:
        """Export semua skill ke list of dict."""
        return [s.to_dict() for s in self._skills.values()]

    def export_all_markdown(self) -> str:
        """Export semua skill ke satu string Markdown."""
        parts = [s.to_markdown() for s in self._skills.values()]
        return "\n\n---\n\n".join(parts)

    # ── Skill Matching ────────────────────────────────────────────────────────

    def find_matching_skill(self, message: str, top_k: int = 3) -> list[tuple[Skill, float]]:
        """
        Cari skill yang relevan berdasarkan keyword matching.
        Return: list of (skill, score) diurutkan dari paling relevan.
        """
        if not self._skills:
            return []

        msg_lower = message.lower()
        scored: list[tuple[Skill, float]] = []

        for skill in self._skills.values():
            score = 0.0

            # Keyword matching di trigger_keywords
            for kw in skill.trigger_keywords:
                if kw.lower() in msg_lower:
                    score += 2.0

            # Keyword matching di tags
            for tag in skill.tags:
                if tag.lower() in msg_lower:
                    score += 1.0

            # Nama dan deskripsi
            if skill.name.lower() in msg_lower:
                score += 3.0
            for word in skill.name.lower().split():
                if len(word) > 3 and word in msg_lower:
                    score += 0.5

            # Popularitas (bonus kecil untuk skill yang sering dipakai)
            if score > 0 and skill.use_count > 0:
                score += min(1.0, skill.use_count * 0.1)

            if score > 0:
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def record_usage(self, skill_id: str, success: bool = True):
        """Catat penggunaan skill untuk statistik."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        skill.use_count += 1
        # Rolling average success rate
        skill.success_rate = (
            (skill.success_rate * (skill.use_count - 1) + (1.0 if success else 0.0))
            / skill.use_count
        )
        skill.updated_at = _now_iso()
        self._save_to_disk(skill)

    # ── Auto-extraction dari task hasil ──────────────────────────────────────

    async def auto_extract_skill(
        self,
        task_description: str,
        task_result: str,
        model_manager=None,
    ) -> Optional[Skill]:
        """
        Gunakan LLM untuk mengekstrak skill dari task yang berhasil diselesaikan.
        Dipanggil secara async setelah orchestrator menyelesaikan tugas kompleks.
        """
        if not model_manager:
            return None

        prompt = f"""Kamu adalah AI yang bertugas mengekstrak pelajaran dari tugas yang berhasil diselesaikan.

Tugas yang diselesaikan:
{task_description[:500]}

Hasil/Solusi:
{task_result[:1000]}

Apakah ini merupakan tugas yang cukup kompleks atau unik sehingga layak dijadikan SKILL yang bisa dipakai ulang?
Jika YA, ekstrak skill-nya dalam format JSON berikut. Jika TIDAK (misalnya tugas terlalu sederhana, umum, atau percakapan biasa), jawab dengan JSON: {{"skip": true}}

Format JSON jika layak jadi skill:
{{
  "skip": false,
  "name": "Nama skill yang singkat dan deskriptif",
  "description": "Deskripsi satu kalimat tentang apa yang dilakukan skill ini",
  "category": "coding|system|analysis|writing|file_operation|general",
  "tags": ["tag1", "tag2"],
  "trigger_keywords": ["kata kunci1", "kata kunci2"],
  "steps": [
    "Langkah 1...",
    "Langkah 2...",
    "Langkah 3..."
  ],
  "examples": [
    "Contoh perintah/tugas yang bisa diselesaikan dengan skill ini"
  ]
}}

Jawab HANYA dengan JSON valid, tanpa penjelasan tambahan."""

        try:
            fast_model = None
            # Coba dapatkan model tercepat yang tersedia
            if hasattr(model_manager, "get_model_for_intent"):
                fast_model = model_manager.get_model_for_intent("general")

            if not fast_model:
                return None

            from core.model_manager import ModelRequest
            request = ModelRequest(
                messages=[{"role": "user", "content": prompt}],
                model_id=fast_model.id,
                max_tokens=600,
                temperature=0.3,
            )
            response = await model_manager.complete(request)
            raw = response.content.strip() if response and response.content else ""

            # Parse JSON
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())
            if data.get("skip", False):
                return None

            # Buat skill
            skill = self.create_skill({
                "name": data.get("name", "Auto-extracted Skill"),
                "description": data.get("description", ""),
                "category": data.get("category", "general"),
                "tags": data.get("tags", []),
                "trigger_keywords": data.get("trigger_keywords", []),
                "steps": data.get("steps", []),
                "examples": data.get("examples", []),
                "content": f"Auto-extracted dari: {task_description[:200]}",
            })
            log.info("SkillRegistry: auto-extracted skill", name=skill.name)
            return skill

        except ValueError as e:
            # Duplikat — skip tanpa error
            log.debug("SkillRegistry: auto-extract skip (duplikat)", error=str(e))
            return None
        except Exception as e:
            log.warning("SkillRegistry: auto-extract gagal", error=str(e)[:200])
            return None

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _save_to_disk(self, skill: Skill):
        path = SKILLS_DIR / f"{skill.id}.md"
        path.write_text(skill.to_markdown(), encoding="utf-8")

    def _find_duplicate(self, new_skill: Skill, threshold: float = 0.85) -> Optional[Skill]:
        """Cek apakah skill serupa sudah ada berdasarkan nama + deskripsi."""
        new_hash = new_skill.similarity_hash()
        for s in self._skills.values():
            if s.similarity_hash() == new_hash:
                return s
            # Simple name similarity
            if _jaccard_sim(new_skill.name.lower(), s.name.lower()) > threshold:
                return s
        return None


def _jaccard_sim(a: str, b: str) -> float:
    """Jaccard similarity sederhana berdasarkan token."""
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ── Singleton ─────────────────────────────────────────────────────────────────

skill_registry = SkillRegistry()

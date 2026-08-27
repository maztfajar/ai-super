"""
AI ORCHESTRATOR — Skills API Router
====================================
Endpoint CRUD, import, dan export untuk Skill.
"""

import json
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.skill_registry import skill_registry, Skill
from db.database import get_db

log = structlog.get_logger()

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    category: str = "general"
    tags: list[str] = []
    steps: list[str] = []
    examples: list[str] = []
    trigger_keywords: list[str] = []
    content: str = ""


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    steps: Optional[list[str]] = None
    examples: Optional[list[str]] = None
    trigger_keywords: Optional[list[str]] = None
    content: Optional[str] = None


def _skill_to_dict(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "tags": skill.tags,
        "steps": skill.steps,
        "examples": skill.examples,
        "trigger_keywords": skill.trigger_keywords,
        "content": skill.content,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
        "use_count": skill.use_count,
        "success_rate": round(skill.success_rate, 2),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_skills(
    category: str = Query(""),
    search: str = Query(""),
    current_user=Depends(get_current_user),
):
    """Ambil daftar semua skill."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    skills = skill_registry.list_skills(category=category, search=search)
    return {
        "skills": [_skill_to_dict(s) for s in skills],
        "total": len(skills),
    }


@router.get("/categories")
async def list_categories(current_user=Depends(get_current_user)):
    """Ambil daftar kategori yang tersedia."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    all_skills = skill_registry.list_skills()
    cats = sorted(set(s.category for s in all_skills))
    return {"categories": cats}


@router.get("/{skill_id}")
async def get_skill(skill_id: str, current_user=Depends(get_current_user)):
    """Ambil detail satu skill."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    skill = skill_registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill tidak ditemukan")
    return _skill_to_dict(skill)


@router.post("", status_code=201)
async def create_skill(body: SkillCreate, current_user=Depends(get_current_user)):
    """Buat skill baru."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    try:
        skill = skill_registry.create_skill(body.model_dump())
        return {"message": "Skill berhasil dibuat", "skill": _skill_to_dict(skill)}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{skill_id}")
async def update_skill(skill_id: str, body: SkillUpdate, current_user=Depends(get_current_user)):
    """Update skill yang sudah ada."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    try:
        data = {k: v for k, v in body.model_dump().items() if v is not None}
        skill = skill_registry.update_skill(skill_id, data)
        return {"message": "Skill berhasil diupdate", "skill": _skill_to_dict(skill)}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, current_user=Depends(get_current_user)):
    """Hapus skill."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    deleted = skill_registry.delete_skill(skill_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Skill tidak ditemukan")
    return {"message": "Skill berhasil dihapus", "id": skill_id}


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/import/json")
async def import_skills_json(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Import skill dari file JSON."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    try:
        content = await file.read()
        data = json.loads(content)
        if isinstance(data, dict) and "skills" in data:
            data = data["skills"]
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="Format JSON tidak valid. Harus list atau {skills: [...]}")
        imported = skill_registry.import_from_json(data)
        return {
            "message": f"{len(imported)} skill berhasil diimport",
            "imported": len(imported),
            "skills": [_skill_to_dict(s) for s in imported],
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="File bukan JSON valid")


@router.post("/import/markdown")
async def import_skills_markdown(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Import skill dari file Markdown."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    imported = skill_registry.import_from_markdown(text)
    return {
        "message": f"{len(imported)} skill berhasil diimport",
        "imported": len(imported),
        "skills": [_skill_to_dict(s) for s in imported],
    }


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export/json")
async def export_skills_json(current_user=Depends(get_current_user)):
    """Export semua skill ke JSON."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    data = skill_registry.export_all_json()
    content = json.dumps({"skills": data, "total": len(data)}, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=skills_export.json"},
    )


@router.get("/export/markdown")
async def export_skills_markdown(current_user=Depends(get_current_user)):
    """Export semua skill ke Markdown."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    content = skill_registry.export_all_markdown()
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=skills_export.md"},
    )


# ── Search / Match ─────────────────────────────────────────────────────────────

@router.get("/match/query")
async def match_skills(
    q: str = Query(..., description="Pesan/query pengguna"),
    top_k: int = Query(3, ge=1, le=10),
    current_user=Depends(get_current_user),
):
    """Cari skill yang relevan dengan query."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    matches = skill_registry.find_matching_skill(q, top_k=top_k)
    return {
        "matches": [
            {"skill": _skill_to_dict(s), "score": round(score, 2)}
            for s, score in matches
        ]
    }


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats/summary")
async def skill_stats(current_user=Depends(get_current_user)):
    """Statistik ringkas skill registry."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    all_skills = skill_registry.list_skills()
    cats: dict[str, int] = {}
    total_uses = 0
    for s in all_skills:
        cats[s.category] = cats.get(s.category, 0) + 1
        total_uses += s.use_count
    top_used = sorted(all_skills, key=lambda s: s.use_count, reverse=True)[:5]
    return {
        "total_skills": len(all_skills),
        "total_uses": total_uses,
        "by_category": cats,
        "top_used": [{"name": s.name, "use_count": s.use_count, "id": s.id} for s in top_used],
    }

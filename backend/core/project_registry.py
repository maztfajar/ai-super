"""
Project Registry — Memori Permanen Project Path per Session
===========================================================
Orchestrator tidak akan pernah lupa letak project-nya lagi.

Penyimpanan berlapis:
  1. In-memory cache (akses instan)
  2. Database (ChatSession.project_metadata) — bertahan restart
  3. File JSON fallback (~/.ai_projects.json) — jika DB tidak tersedia

Fitur:
  - get(session_id)          → path project aktif
  - set(session_id, path)    → simpan/update path
  - get_all()                → semua session → path
  - find_by_path(path)       → cari session dari path
  - get_recent(n)            → n project terbaru
  - delete(session_id)       → hapus record
"""

import os
import json
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
import structlog

log = structlog.get_logger()

# Fallback file jika DB tidak tersedia
_FALLBACK_FILE = os.path.expanduser("~/.ai_projects.json")

# In-memory cache: {session_id: path}
_CACHE: Dict[str, str] = {}
_CACHE_LOADED = False


class ProjectRegistry:
    """
    Single source of truth untuk project path.
    Semua operasi file system tools menggunakan registry ini.
    """

    async def _ensure_loaded(self):
        """Load dari DB + fallback file ke cache saat pertama kali."""
        global _CACHE_LOADED
        if _CACHE_LOADED:
            return

        # Load dari DB
        try:
            from db.database import AsyncSessionLocal
            from db.models import ChatSession
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ChatSession).where(
                        ChatSession.project_metadata.isnot(None)
                    )
                )
                sessions = result.scalars().all()
                for s in sessions:
                    if s.project_metadata and "project_path" in s.project_metadata:
                        _CACHE[s.id] = s.project_metadata["project_path"]

            log.debug("ProjectRegistry: loaded from DB", count=len(_CACHE))
        except Exception as e:
            log.debug("ProjectRegistry: DB load failed, using file fallback", error=str(e)[:60])

        # Load dari fallback file
        try:
            if os.path.exists(_FALLBACK_FILE):
                with open(_FALLBACK_FILE, "r") as f:
                    fallback = json.load(f)
                for sess_id, path in fallback.items():
                    if sess_id not in _CACHE:
                        _CACHE[sess_id] = path
                log.debug("ProjectRegistry: loaded from fallback file",
                          count=len(fallback))
        except Exception as e:
            log.debug("ProjectRegistry: fallback file load failed", error=str(e)[:60])

        _CACHE_LOADED = True

    async def get(self, session_id: str) -> Optional[str]:
        """Ambil project path untuk session. Returns None jika tidak ada."""
        await self._ensure_loaded()

        # Cache hit
        if session_id in _CACHE:
            return _CACHE[session_id]

        # DB lookup
        try:
            from db.database import AsyncSessionLocal
            from db.models import ChatSession

            async with AsyncSessionLocal() as db:
                session = await db.get(ChatSession, session_id)
                if session and session.project_metadata:
                    path = session.project_metadata.get("project_path")
                    if path:
                        _CACHE[session_id] = path
                        return path
        except Exception:
            pass

        return None

    def get_sync(self, session_id: str) -> Optional[str]:
        """Synchronous version untuk penggunaan di non-async context."""
        return _CACHE.get(session_id)

    async def set(self, session_id: str, project_path: str) -> bool:
        """
        Simpan project path untuk session.
        Disimpan ke cache + DB + fallback file.
        """
        resolved = os.path.realpath(os.path.abspath(project_path))
        _CACHE[session_id] = resolved

        # Simpan ke DB
        db_ok = False
        try:
            from db.database import AsyncSessionLocal
            from db.models import ChatSession

            async with AsyncSessionLocal() as db:
                session = await db.get(ChatSession, session_id)
                if session:
                    meta = session.project_metadata or {}
                    meta["project_path"] = resolved
                    meta["project_set_at"] = datetime.utcnow().isoformat()
                    session.project_metadata = meta
                    db.add(session)
                    await db.commit()
                    db_ok = True
                    log.info("ProjectRegistry: saved to DB",
                             session=session_id[:8], path=resolved)
        except Exception as e:
            log.warning("ProjectRegistry: DB save failed", error=str(e)[:80])

        # Simpan ke fallback file (selalu, sebagai backup)
        try:
            existing = {}
            if os.path.exists(_FALLBACK_FILE):
                with open(_FALLBACK_FILE, "r") as f:
                    existing = json.load(f)
            existing[session_id] = resolved
            with open(_FALLBACK_FILE, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            log.debug("ProjectRegistry: fallback file save failed", error=str(e)[:60])

        return db_ok

    async def get_all(self) -> Dict[str, str]:
        """Return semua session_id → project_path."""
        await self._ensure_loaded()
        return dict(_CACHE)

    async def find_by_path(self, project_path: str) -> Optional[str]:
        """
        Cari session_id dari project path.
        Berguna untuk operasi reverse lookup.
        """
        await self._ensure_loaded()
        resolved = os.path.realpath(os.path.abspath(project_path))
        for sess_id, path in _CACHE.items():
            if path == resolved or path.startswith(resolved):
                return sess_id
        return None

    async def get_recent(self, n: int = 5) -> List[Dict]:
        """
        Ambil n project terbaru berdasarkan waktu modifikasi folder.
        """
        await self._ensure_loaded()
        results = []
        for sess_id, path in _CACHE.items():
            if os.path.exists(path):
                try:
                    mtime = os.path.getmtime(path)
                    results.append({
                        "session_id": sess_id,
                        "path": path,
                        "modified": datetime.fromtimestamp(mtime).isoformat(),
                        "mtime": mtime,
                    })
                except Exception:
                    pass

        results.sort(key=lambda x: x["mtime"], reverse=True)
        return results[:n]

    async def delete(self, session_id: str) -> bool:
        """Hapus record project path untuk session."""
        _CACHE.pop(session_id, None)

        try:
            from db.database import AsyncSessionLocal
            from db.models import ChatSession

            async with AsyncSessionLocal() as db:
                session = await db.get(ChatSession, session_id)
                if session and session.project_metadata:
                    meta = session.project_metadata
                    meta.pop("project_path", None)
                    meta.pop("project_set_at", None)
                    session.project_metadata = meta
                    db.add(session)
                    await db.commit()
        except Exception:
            pass

        # Update fallback file
        try:
            if os.path.exists(_FALLBACK_FILE):
                with open(_FALLBACK_FILE, "r") as f:
                    existing = json.load(f)
                existing.pop(session_id, None)
                with open(_FALLBACK_FILE, "w") as f:
                    json.dump(existing, f, indent=2)
        except Exception:
            pass

        return True

    def invalidate_cache(self):
        """Force reload dari DB saat next access."""
        global _CACHE_LOADED
        _CACHE.clear()
        _CACHE_LOADED = False


project_registry = ProjectRegistry()

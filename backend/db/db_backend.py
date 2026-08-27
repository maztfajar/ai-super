"""
Database Backend Abstraction Layer
===================================
Abstract interface untuk database backend, memungkinkan:
  - SQLite (current default, single-node)
  - PostgreSQL (future, horizontal scaling)
  - Factory pattern: auto-detect dari DATABASE_URL

Usage:
    from db.db_backend import get_backend

    backend = get_backend()
    assert await backend.health_check()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog

log = structlog.get_logger()


class DatabaseBackend(ABC):
    """Abstract base class untuk database backends."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check apakah database connection healthy."""
        ...

    @abstractmethod
    def get_engine_info(self) -> Dict[str, Any]:
        """Return metadata tentang engine yang digunakan."""
        ...

    @abstractmethod
    def supports_horizontal_scaling(self) -> bool:
        """Apakah backend ini support horizontal scaling."""
        ...

    @abstractmethod
    def supports_full_text_search(self) -> bool:
        """Apakah backend ini support native full-text search."""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...


class SQLiteBackend(DatabaseBackend):
    """
    SQLite backend — default untuk single-node deployment.

    Kelebihan:
      - Zero config, file-based
      - WAL mode untuk concurrent reads
      - Cocok untuk single-server deployment

    Limitasi:
      - Single writer (serialized writes via DatabaseWriteQueue)
      - Tidak support horizontal scaling
      - Max database size ~281 TB (practical limit ~1TB)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def health_check(self) -> bool:
        try:
            from db.database import engine
            import sqlalchemy as sa
            async with engine.begin() as conn:
                result = await conn.execute(sa.text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            log.error("SQLite health check failed", error=str(e))
            return False

    def get_engine_info(self) -> Dict[str, Any]:
        import os
        file_size = 0
        try:
            file_size = os.path.getsize(self.db_path)
        except OSError:
            pass

        return {
            "backend": "sqlite",
            "path": self.db_path,
            "file_size_bytes": file_size,
            "wal_mode": True,
            "max_concurrent_readers": "unlimited",
            "max_concurrent_writers": 1,
        }

    def supports_horizontal_scaling(self) -> bool:
        return False

    def supports_full_text_search(self) -> bool:
        return True  # SQLite FTS5

    @property
    def backend_name(self) -> str:
        return "sqlite"


class PostgreSQLBackend(DatabaseBackend):
    """
    PostgreSQL backend — untuk multi-node / enterprise deployment.
    Status: STUB (future implementation)

    Kelebihan:
      - Multi-writer concurrent access
      - Horizontal scaling via read replicas
      - Native full-text search, JSONB, dan rich querying

    Requiremen:
      - PostgreSQL 14+ server
      - asyncpg driver
    """

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        log.info("PostgreSQL backend initialized (stub)",
                 url=connection_url[:30] + "...")

    async def health_check(self) -> bool:
        # TODO: Implement when PostgreSQL support is added
        log.warning("PostgreSQL backend health_check not yet implemented")
        return False

    def get_engine_info(self) -> Dict[str, Any]:
        return {
            "backend": "postgresql",
            "connection_url": self.connection_url[:30] + "...",
            "status": "stub — not yet implemented",
            "max_concurrent_readers": "unlimited",
            "max_concurrent_writers": "unlimited",
        }

    def supports_horizontal_scaling(self) -> bool:
        return True

    def supports_full_text_search(self) -> bool:
        return True

    @property
    def backend_name(self) -> str:
        return "postgresql"


# ══════════════════════════════════════════════════════════════════════════════
# Factory
# ══════════════════════════════════════════════════════════════════════════════

_backend_instance: Optional[DatabaseBackend] = None


def get_backend() -> DatabaseBackend:
    """
    Factory: auto-detect dan return database backend berdasarkan DATABASE_URL.

    Priority:
      1. Jika DATABASE_URL mengandung 'postgresql' → PostgreSQLBackend
      2. Default → SQLiteBackend
    """
    global _backend_instance
    if _backend_instance is not None:
        return _backend_instance

    from core.config import settings
    db_url = settings.get_db_url

    if "postgresql" in db_url or "postgres" in db_url:
        _backend_instance = PostgreSQLBackend(db_url)
    else:
        # Extract file path from SQLite URL
        db_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        _backend_instance = SQLiteBackend(db_path)

    log.info("Database backend selected", backend=_backend_instance.backend_name)
    return _backend_instance

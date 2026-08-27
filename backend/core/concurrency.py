"""
Concurrency Utilities — File Locking, Write Queue, Resource Semaphores
======================================================================
Mengatasi race condition pada multi-agent parallel execution:
  - FileLock: Async file locking via fcntl (POSIX) untuk mencegah concurrent edits
  - DatabaseWriteQueue: Serialize SQLite write operations via asyncio.Queue
  - ResourceSemaphore: Global semaphore pool untuk throttle resource access
  - OptimisticLockMixin: Version-based optimistic concurrency control
"""

import asyncio
import fcntl
import hashlib
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import structlog

log = structlog.get_logger()


# ══════════════════════════════════════════════════════════════════════════════
# 1. FileLock — Async POSIX file locking
# ══════════════════════════════════════════════════════════════════════════════

class FileLock:
    """
    Advisory file lock menggunakan fcntl.flock().
    Mencegah dua agent mengedit file yang sama secara bersamaan.

    Usage:
        async with FileLock("/path/to/file"):
            # safe to read/write
    """

    # Class-level registry: path -> asyncio.Lock
    # Mencegah dua coroutine dalam proses yang sama bertabrakan
    _internal_locks: Dict[str, asyncio.Lock] = {}

    def __init__(self, filepath: str, timeout: float = 30.0):
        self.filepath = os.path.abspath(filepath)
        self.timeout = timeout
        self._fd: Optional[int] = None

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    async def acquire(self):
        """Acquire both internal asyncio lock and OS-level file lock."""
        # 1. Internal asyncio lock (per-process)
        if self.filepath not in self._internal_locks:
            self._internal_locks[self.filepath] = asyncio.Lock()

        internal = self._internal_locks[self.filepath]
        try:
            await asyncio.wait_for(internal.acquire(), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"FileLock timeout ({self.timeout}s) waiting for internal lock: {self.filepath}"
            )

        # 2. OS-level file lock (cross-process)
        lock_path = self.filepath + ".lock"
        try:
            os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
            self._fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)

            # Non-blocking try in a loop with timeout
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (IOError, OSError):
                    if time.monotonic() >= deadline:
                        os.close(self._fd)
                        self._fd = None
                        internal.release()
                        raise TimeoutError(
                            f"FileLock timeout ({self.timeout}s) waiting for OS lock: {self.filepath}"
                        )
                    await asyncio.sleep(0.1)

            log.debug("FileLock acquired", path=self.filepath)

        except TimeoutError:
            raise
        except Exception as e:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            internal.release()
            log.error("FileLock acquire failed", path=self.filepath, error=str(e))
            raise

    def release(self):
        """Release both locks."""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

        internal = self._internal_locks.get(self.filepath)
        if internal and internal.locked():
            internal.release()

        log.debug("FileLock released", path=self.filepath)


# ══════════════════════════════════════════════════════════════════════════════
# 2. DatabaseWriteQueue — Serialize SQLite writes
# ══════════════════════════════════════════════════════════════════════════════

class DatabaseWriteQueue:
    """
    Serialize semua write operations ke SQLite melalui single asyncio queue.
    Mencegah SQLITE_BUSY dan WAL conflicts pada concurrent access.

    Usage:
        result = await db_write_queue.submit(my_async_write_fn, arg1, arg2)
    """

    def __init__(self, max_queue_size: int = 1000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._processed = 0
        self._errors = 0

    async def start(self):
        """Start the write queue worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        log.info("DatabaseWriteQueue started")

    async def stop(self):
        """Graceful stop — process remaining items then exit."""
        self._running = False
        if self._worker_task:
            # Signal worker to drain and exit
            await self._queue.put(None)
            try:
                await asyncio.wait_for(self._worker_task, timeout=30.0)
            except asyncio.TimeoutError:
                self._worker_task.cancel()
            self._worker_task = None
        log.info("DatabaseWriteQueue stopped",
                 processed=self._processed, errors=self._errors)

    async def submit(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Submit a write operation. Returns the result of fn(*args, **kwargs).
        Blocks until the operation completes.
        """
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        await self._queue.put((fn, args, kwargs, future))
        return await future

    async def _worker(self):
        """Single worker that processes writes sequentially."""
        while True:
            item = await self._queue.get()
            if item is None:
                # Drain remaining
                while not self._queue.empty():
                    remaining = self._queue.get_nowait()
                    if remaining is not None:
                        fn, args, kwargs, future = remaining
                        try:
                            result = await fn(*args, **kwargs)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)
                break

            fn, args, kwargs, future = item
            try:
                result = await fn(*args, **kwargs)
                future.set_result(result)
                self._processed += 1
            except Exception as e:
                future.set_exception(e)
                self._errors += 1
                log.warning("DatabaseWriteQueue operation failed", error=str(e))

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "queued": self._queue.qsize(),
            "processed": self._processed,
            "errors": self._errors,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 3. ResourceSemaphore — Global throttle pool
# ══════════════════════════════════════════════════════════════════════════════

class ResourceSemaphore:
    """
    Named semaphore pool untuk throttle concurrent access ke shared resources.

    Contoh:
        async with resource_semaphore.acquire("filesystem", max_concurrent=5):
            await write_file(...)

        async with resource_semaphore.acquire("database", max_concurrent=1):
            await db_write(...)
    """

    def __init__(self):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._configs: Dict[str, int] = {}
        self._stats: Dict[str, Dict[str, int]] = {}

    def configure(self, resource_name: str, max_concurrent: int):
        """Pre-configure a named resource limit."""
        self._configs[resource_name] = max_concurrent
        self._semaphores[resource_name] = asyncio.Semaphore(max_concurrent)
        self._stats[resource_name] = {"acquired": 0, "released": 0, "contention": 0}

    @asynccontextmanager
    async def acquire(self, resource_name: str, max_concurrent: int = 5,
                      timeout: float = 60.0):
        """Acquire a named semaphore slot."""
        if resource_name not in self._semaphores:
            self.configure(resource_name, max_concurrent)

        sem = self._semaphores[resource_name]
        stats = self._stats[resource_name]

        # Track contention
        if sem.locked():
            stats["contention"] += 1

        try:
            acquired = await asyncio.wait_for(sem.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"ResourceSemaphore timeout ({timeout}s) for '{resource_name}'"
            )

        stats["acquired"] += 1
        try:
            yield
        finally:
            sem.release()
            stats["released"] += 1

    @property
    def all_stats(self) -> Dict[str, Dict[str, int]]:
        return dict(self._stats)


# ══════════════════════════════════════════════════════════════════════════════
# 4. OptimisticLockMixin
# ══════════════════════════════════════════════════════════════════════════════

class OptimisticLockError(Exception):
    """Raised when a concurrent modification is detected."""
    pass


class OptimisticLockMixin:
    """
    Mixin untuk SQLModel yang menambahkan version-based optimistic locking.

    Usage:
        class MyModel(SQLModel, OptimisticLockMixin, table=True):
            id: int
            data: str

        # Before update:
        obj = await session.get(MyModel, id)
        obj.check_and_increment_version(expected_version=obj.version)
        await session.commit()
    """

    version: int = 0

    def check_and_increment_version(self, expected_version: int):
        """
        Verify current version matches expected, then increment.
        Raise OptimisticLockError on mismatch.
        """
        if self.version != expected_version:
            raise OptimisticLockError(
                f"Concurrent modification detected: "
                f"expected version {expected_version}, got {self.version}"
            )
        self.version += 1


# ══════════════════════════════════════════════════════════════════════════════
# Global Instances
# ══════════════════════════════════════════════════════════════════════════════

db_write_queue = DatabaseWriteQueue()
resource_semaphore = ResourceSemaphore()

# Pre-configure default limits
resource_semaphore.configure("filesystem", max_concurrent=5)
resource_semaphore.configure("database", max_concurrent=1)
resource_semaphore.configure("network", max_concurrent=10)
resource_semaphore.configure("model_api", max_concurrent=3)

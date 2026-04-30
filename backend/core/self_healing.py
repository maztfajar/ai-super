"""
AI ORCHESTRATOR — Self-Healing Infrastructure Engine
Mendeteksi crash, menganalisis penyebab, memperbaiki otomatis,
dan mengirim laporan ke pengguna via Telegram.
"""
import asyncio
import os
import subprocess
import time
import psutil
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

log = structlog.get_logger()

# ── Konfigurasi threshold ─────────────────────────────────────
DISK_WARN_PERCENT  = 85   # % disk usage sebelum mulai bersih-bersih
MEMORY_WARN_MB     = 200  # MB free memory sebelum warning
CPU_WARN_PERCENT   = 90   # % CPU usage sebelum warning
CHECK_INTERVAL_SEC = 30   # cek setiap N detik
MAX_LOG_SIZE_MB    = 50   # log file > ini akan di-rotate

BASE_DIR = Path(__file__).parent.parent


@dataclass
class HealingEvent:
    """Satu kejadian self-healing."""
    issue_type:  str           # permission | port | disk | memory | db | redis | import
    description: str           # deskripsi masalah
    action_taken: str          # langkah yang diambil
    success:     bool          # berhasil atau tidak
    details:     str = ""      # detail tambahan
    timestamp:   float = field(default_factory=time.time)


class SelfHealingEngine:
    """
    Engine utama self-healing.
    Dijalankan sebagai background task saat aplikasi start.
    """

    def __init__(self):
        self._running    = False
        self._events: list[HealingEvent] = []
        self._last_report_time = 0.0
        self._consecutive_failures = 0

    # ══════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════

    async def start(self):
        """Mulai background monitoring loop."""
        self._running = True
        log.info("Self-Healing Engine started", interval=CHECK_INTERVAL_SEC)
        asyncio.create_task(self._monitor_loop())

    def stop(self):
        self._running = False

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        return [
            {
                "issue_type":   e.issue_type,
                "description":  e.description,
                "action_taken": e.action_taken,
                "success":      e.success,
                "details":      e.details,
                "timestamp":    datetime.fromtimestamp(e.timestamp).isoformat(),
            }
            for e in self._events[-limit:]
        ]

    # ══════════════════════════════════════════════════════
    # MONITORING LOOP
    # ══════════════════════════════════════════════════════

    async def _monitor_loop(self):
        """Loop utama — jalankan semua health check secara berkala."""
        while self._running:
            try:
                await self._run_all_checks()
            except Exception as e:
                log.error("Self-healing monitor error", error=str(e)[:100])
            await asyncio.sleep(CHECK_INTERVAL_SEC)

    async def _run_all_checks(self):
        """Jalankan semua health check paralel."""
        checks = [
            self._check_disk(),
            self._check_memory(),
            self._check_permissions(),
            self._check_db_connection(),
            self._check_redis(),
            self._check_log_rotation(),
            self._check_missing_packages(),
        ]
        results = await asyncio.gather(*checks, return_exceptions=True)

        # Kumpulkan events dari semua check
        new_events = []
        for r in results:
            if isinstance(r, HealingEvent):
                new_events.append(r)
                self._events.append(r)

        # Kirim laporan jika ada event penting
        if new_events:
            await self._send_report(new_events)

    # ══════════════════════════════════════════════════════
    # HEALTH CHECKS
    # ══════════════════════════════════════════════════════

    async def _check_disk(self) -> Optional[HealingEvent]:
        """Cek disk usage — bersihkan log & cache jika hampir penuh."""
        try:
            usage = psutil.disk_usage("/")
            percent = usage.percent

            if percent < DISK_WARN_PERCENT:
                return None

            log.warning("Disk usage high", percent=percent)

            # Aksi 1: hapus log lama (> 7 hari)
            cleaned_mb = 0
            log_dirs = [
                BASE_DIR / "data" / "logs",
                BASE_DIR / "logs",
                Path("/var/log"),
            ]
            for log_dir in log_dirs:
                if not log_dir.exists():
                    continue
                for f in log_dir.glob("*.log*"):
                    try:
                        age_days = (time.time() - f.stat().st_mtime) / 86400
                        if age_days > 7:
                            size_mb = f.stat().st_size / (1024 * 1024)
                            f.unlink()
                            cleaned_mb += size_mb
                    except Exception:
                        pass

            # Aksi 2: hapus __pycache__
            for pycache in BASE_DIR.rglob("__pycache__"):
                try:
                    import shutil
                    shutil.rmtree(pycache, ignore_errors=True)
                    cleaned_mb += 0.1
                except Exception:
                    pass

            # Aksi 3: hapus file upload temp > 24 jam
            uploads_dir = BASE_DIR / "data" / "uploads"
            if uploads_dir.exists():
                for f in uploads_dir.glob("tmp_*"):
                    try:
                        age_hours = (time.time() - f.stat().st_mtime) / 3600
                        if age_hours > 24:
                            f.unlink()
                            cleaned_mb += f.stat().st_size / (1024 * 1024)
                    except Exception:
                        pass

            action = f"Dibersihkan {cleaned_mb:.1f} MB (log lama + cache + tmp)"
            success = cleaned_mb > 0

            return HealingEvent(
                issue_type="disk",
                description=f"Disk usage {percent:.0f}% — melebihi threshold {DISK_WARN_PERCENT}%",
                action_taken=action,
                success=success,
                details=f"Sisa ruang: {usage.free / (1024**3):.1f} GB",
            )

        except Exception as e:
            log.debug("Disk check error", error=str(e)[:80])
            return None

    async def _check_memory(self) -> Optional[HealingEvent]:
        """Cek memory — warning jika hampir habis."""
        try:
            mem = psutil.virtual_memory()
            free_mb = mem.available / (1024 * 1024)

            if free_mb > MEMORY_WARN_MB:
                return None

            log.warning("Low memory", free_mb=free_mb)

            # Tidak ada aksi destruktif — hanya log dan report
            return HealingEvent(
                issue_type="memory",
                description=f"Memory tersisa hanya {free_mb:.0f} MB",
                action_taken="Monitoring aktif — pertimbangkan upgrade RAM atau restart service berat",
                success=True,
                details=f"Total: {mem.total/(1024**2):.0f} MB | Used: {mem.percent:.0f}%",
            )

        except Exception as e:
            log.debug("Memory check error", error=str(e)[:80])
            return None

    async def _check_permissions(self) -> Optional[HealingEvent]:
        """Cek dan perbaiki permission folder kritis."""
        critical_dirs = [
            BASE_DIR / "data",
            BASE_DIR / "data" / "uploads",
            BASE_DIR / "data" / "logs",
            BASE_DIR / "data" / "chroma_db",
        ]

        fixed = []
        for d in critical_dirs:
            try:
                # Buat folder jika tidak ada
                d.mkdir(parents=True, exist_ok=True)

                # Test apakah bisa write
                test_file = d / ".write_test"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                except PermissionError:
                    # Perbaiki permission
                    os.chmod(d, 0o755)
                    # Coba lagi
                    try:
                        test_file.write_text("test")
                        test_file.unlink()
                        fixed.append(str(d))
                        log.info("Permission fixed", path=str(d))
                    except Exception:
                        pass
            except Exception as e:
                log.debug("Permission check error", path=str(d), error=str(e)[:60])

        if not fixed:
            return None

        return HealingEvent(
            issue_type="permission",
            description=f"Permission error di {len(fixed)} folder",
            action_taken=f"chmod 755 diterapkan ke: {', '.join(fixed)}",
            success=True,
            details="Folder sekarang bisa ditulis",
        )

    async def _check_db_connection(self) -> Optional[HealingEvent]:
        """Cek koneksi database — coba reconnect jika gagal."""
        try:
            from db.database import AsyncSessionLocal
            from sqlmodel import text

            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            return None  # Koneksi OK

        except Exception as e:
            err = str(e)[:200]
            log.error("DB connection failed", error=err)

            # Coba init ulang
            action = "Mencoba reinisialisasi koneksi database"
            success = False
            details = err

            try:
                from db.database import init_db
                await init_db()
                success = True
                action = "Koneksi database berhasil dipulihkan via reinit"
                log.info("DB reconnected successfully")
            except Exception as e2:
                details = f"Reconnect gagal: {str(e2)[:100]}"
                log.error("DB reconnect failed", error=str(e2)[:100])

            return HealingEvent(
                issue_type="database",
                description=f"Koneksi database gagal: {err[:80]}",
                action_taken=action,
                success=success,
                details=details,
            )

    async def _check_redis(self) -> Optional[HealingEvent]:
        """Cek Redis — coba restart jika tidak responsif."""
        try:
            from memory.manager import memory_manager
            if not getattr(memory_manager, "_redis_available", False):
                return None  # Redis tidak dipakai, skip

            redis = memory_manager.redis
            if not redis:
                return None

            await redis.ping()
            return None  # Redis OK

        except Exception as e:
            log.warning("Redis not responding", error=str(e)[:80])

            # Coba restart Redis jika ada akses systemd
            action = "Redis tidak responsif"
            success = False

            try:
                result = subprocess.run(
                    ["systemctl", "restart", "redis-server"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    action = "Redis berhasil di-restart via systemctl"
                    success = True
                    log.info("Redis restarted successfully")
                else:
                    action = f"Restart Redis gagal: {result.stderr[:80]}"
            except Exception as e2:
                action = f"Tidak bisa restart Redis: {str(e2)[:80]}"

            return HealingEvent(
                issue_type="redis",
                description="Redis tidak merespons",
                action_taken=action,
                success=success,
            )

    async def _check_log_rotation(self) -> Optional[HealingEvent]:
        """Rotate log file yang terlalu besar."""
        rotated = []

        log_dirs = [
            BASE_DIR / "data" / "logs",
            BASE_DIR / "logs",
        ]

        for log_dir in log_dirs:
            if not log_dir.exists():
                continue
            for f in log_dir.glob("*.log"):
                try:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    if size_mb > MAX_LOG_SIZE_MB:
                        # Rename ke .old dan buat yang baru
                        old_path = f.with_suffix(".log.old")
                        if old_path.exists():
                            old_path.unlink()
                        f.rename(old_path)
                        f.write_text("")  # buat file baru kosong
                        rotated.append(f"{f.name} ({size_mb:.0f}MB → rotated)")
                        log.info("Log rotated", file=str(f), size_mb=size_mb)
                except Exception:
                    pass

        if not rotated:
            return None

        return HealingEvent(
            issue_type="log_rotation",
            description=f"{len(rotated)} log file melebihi {MAX_LOG_SIZE_MB}MB",
            action_taken="Log di-rotate otomatis",
            success=True,
            details="\n".join(rotated),
        )

    async def _check_missing_packages(self) -> Optional[HealingEvent]:
        """Cek apakah ada package Python yang hilang dan install otomatis."""
        # Package kritis yang harus ada
        critical_packages = [
            ("psutil",       "psutil"),
            ("httpx",        "httpx"),
            ("structlog",    "structlog"),
            ("passlib",      "passlib[bcrypt]"),
            ("tavily",       "tavily-python"),
        ]

        missing = []
        for import_name, pip_name in critical_packages:
            try:
                __import__(import_name)
            except ImportError:
                missing.append((import_name, pip_name))

        if not missing:
            return None

        log.warning("Missing packages detected", packages=[m[0] for m in missing])

        installed = []
        failed = []

        for import_name, pip_name in missing:
            try:
                result = subprocess.run(
                    ["pip", "install", pip_name, "--quiet", "--break-system-packages"],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    installed.append(pip_name)
                    log.info("Package auto-installed", package=pip_name)
                else:
                    failed.append(pip_name)
            except Exception as e:
                failed.append(f"{pip_name} ({str(e)[:40]})")

        return HealingEvent(
            issue_type="missing_package",
            description=f"Package hilang: {', '.join(m[0] for m in missing)}",
            action_taken=f"Auto-install: berhasil={installed}, gagal={failed}",
            success=len(installed) > 0,
            details=f"Installed: {installed}" if installed else f"Failed: {failed}",
        )

    # ══════════════════════════════════════════════════════
    # REPORTING
    # ══════════════════════════════════════════════════════

    async def _send_report(self, events: list[HealingEvent]):
        """Kirim laporan healing ke Telegram yang sudah dikonfigurasi user."""
        # Rate limit: max 1 laporan per 5 menit
        now = time.time()
        if now - self._last_report_time < 300:
            return
        self._last_report_time = now

        try:
            token, chat_id = await self._get_telegram_config()

            if not token or not chat_id:
                # Log saja jika Telegram belum dikonfigurasi
                for e in events:
                    log.info(
                        "Self-Healing Event (no Telegram)",
                        issue=e.issue_type,
                        description=e.description,
                        action=e.action_taken,
                        success=e.success,
                    )
                return

            msg = self._build_report_message(events)
            await self._send_telegram(token, chat_id, msg)
            log.info("Self-healing report sent to Telegram",
                     events=len(events), chat_id=chat_id[:6] + "***")

        except Exception as e:
            log.error("Failed to send healing report", error=str(e)[:100])

    async def _get_telegram_config(self) -> tuple[str, str]:
        """
        Ambil token bot dan chat_id admin dari konfigurasi yang sudah ada.
        
        Urutan prioritas:
        1. TELEGRAM_BOT_TOKEN dari settings/env (sudah diset di Integrasi Platform)
        2. Chat ID dari user admin pertama yang punya telegram_chat_id di DB
        3. ADMIN_TELEGRAM_CHAT_ID dari env (fallback manual)
        """
        from core.config import settings

        # Token bot — sama yang dipakai Integrasi Platform
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or \
                os.environ.get("TELEGRAM_BOT_TOKEN", "")

        if not token:
            return "", ""

        # Cari chat_id admin — ambil dari DB user yang is_admin=True
        # dan sudah setup telegram_chat_id
        chat_id = ""
        try:
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
                if admin and admin.telegram_chat_id:
                    chat_id = admin.telegram_chat_id
                    log.debug("Using admin telegram_chat_id",
                              username=admin.username,
                              chat_id=chat_id[:6] + "***")
        except Exception as e:
            log.debug("Could not get chat_id from DB", error=str(e)[:60])

        # Fallback ke ADMIN_TELEGRAM_CHAT_ID di .env jika ada
        if not chat_id:
            chat_id = getattr(settings, "ADMIN_TELEGRAM_CHAT_ID", "") or \
                      os.environ.get("ADMIN_TELEGRAM_CHAT_ID", "")

        return token, chat_id

    def _build_report_message(self, events: list[HealingEvent]) -> str:
        """Format pesan laporan untuk Telegram."""
        # Status server
        try:
            cpu   = psutil.cpu_percent(interval=1)
            mem   = psutil.virtual_memory()
            disk  = psutil.disk_usage("/")
            uptime_secs = time.time() - psutil.boot_time()
            uptime_str  = self._format_uptime(uptime_secs)
            server_status = (
                f"📊 *Status Server:*\n"
                f"  CPU: {cpu:.0f}% | RAM: {mem.percent:.0f}% "
                f"({mem.available/(1024**2):.0f}MB free)\n"
                f"  Disk: {disk.percent:.0f}% | Uptime: {uptime_str}"
            )
        except Exception:
            server_status = "📊 Status server tidak tersedia"

        # Detail events
        event_lines = []
        for e in events:
            icon   = "✅" if e.success else "❌"
            icon_t = {
                "disk":            "💾",
                "memory":          "🧠",
                "permission":      "🔐",
                "database":        "🗄️",
                "redis":           "⚡",
                "log_rotation":    "📋",
                "missing_package": "📦",
            }.get(e.issue_type, "🔧")

            event_lines.append(
                f"{icon_t} *Masalah:* {e.description}\n"
                f"{icon} *Tindakan:* {e.action_taken}"
                + (f"\n   _{e.details}_" if e.details else "")
            )

        now_str = datetime.now().strftime("%d %b %Y, %H:%M:%S")
        events_text = "\n\n".join(event_lines)

        return (
            f"🔧 *\\[AI ORCHESTRATOR\\] Self-Healing Report*\n"
            f"_{now_str}_\n\n"
            f"{events_text}\n\n"
            f"{server_status}"
        )

    async def _send_telegram(self, token: str, chat_id: str, message: str):
        """Kirim pesan ke Telegram."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id":    chat_id,
                        "text":       message,
                        "parse_mode": "Markdown",
                    },
                )
                if r.status_code != 200:
                    log.warning("Telegram send failed", status=r.status_code)
        except Exception as e:
            log.error("Telegram send error", error=str(e)[:80])

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime ke string yang readable."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        if h > 24:
            d = h // 24
            h = h % 24
            return f"{d}h {h}j {m}m"
        return f"{h}j {m}m"


# ── Singleton ─────────────────────────────────────────────────
self_healing_engine = SelfHealingEngine()

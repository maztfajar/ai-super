from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import get_db
from db.models import User, Message, ChatSession, KnowledgeDoc, WorkflowRun
from core.auth import get_current_user
from core.model_manager import model_manager
from datetime import datetime, timedelta
from core.config import settings
from pathlib import Path as _Path
import shutil as _shutil
import glob as _glob
import hashlib
import os

router = APIRouter()

# Detect database dialect for raw SQL compatibility
_is_postgres = 'postgresql' in settings.DATABASE_URL

def _timeline_sql():
    """Return the timeline query string appropriate for the active DB."""
    if _is_postgres:
        return """SELECT CAST(created_at AS DATE) as day, COUNT(*) as cnt,
                         SUM(tokens_input + tokens_output) as tokens
                  FROM messages WHERE user_id = :uid
                    AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                  GROUP BY day ORDER BY day"""
    return """SELECT DATE(created_at) as day, COUNT(*) as cnt,
                     SUM(tokens_input + tokens_output) as tokens
              FROM messages WHERE user_id = :uid
                AND created_at >= DATE('now','-7 days')
              GROUP BY day ORDER BY day"""

def _timeline_full_sql():
    """Timeline query with cost column."""
    if _is_postgres:
        return """SELECT CAST(created_at AS DATE) as day, COUNT(*) as cnt,
                         SUM(tokens_input + tokens_output) as tokens,
                         SUM(cost_usd) as cost
                  FROM messages WHERE user_id = :uid
                    AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                  GROUP BY day ORDER BY day"""
    return """SELECT DATE(created_at) as day, COUNT(*) as cnt,
                     SUM(tokens_input + tokens_output) as tokens,
                     SUM(cost_usd) as cost
              FROM messages WHERE user_id = :uid
                AND created_at >= DATE('now','-7 days')
              GROUP BY day ORDER BY day"""


# ── Log Fetcher Helper ──────────────────────────────────────
async def _fetch_recent_logs_helper(lines: int = 100, level: str = ""):
    """Helper function to fetch recent logs without dependency injection."""
    try:
        log_path = _Path(settings.LOG_FILE)
        if not log_path.is_absolute():
            base = _Path(__file__).parent.parent
            log_path = base / log_path.as_posix().lstrip("./")
        log_dir = str(log_path.parent)

        log_files = sorted(_glob.glob(f"{log_dir}/*.log"), reverse=True)[:3]
        entries = []

        if not log_files:
            return {"logs": [], "source": "no_log_file", "hint": "Log file belum ada"}

        for lf in log_files:
            try:
                with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f.readlines()[-lines:]:
                        line = line.strip()
                        if not line:
                            continue
                        lvl = "INFO"
                        if "ERROR" in line or "error" in line.lower():
                            lvl = "ERROR"
                        elif "WARN" in line or "warn" in line.lower():
                            lvl = "WARN"
                        elif "DEBUG" in line:
                            lvl = "DEBUG"

                        if level and lvl != level.upper():
                            continue

                        entries.append({
                            "text": line,
                            "level": lvl,
                            "file": os.path.basename(lf),
                        })
            except Exception:
                pass

        return {"logs": entries[-lines:], "total": len(entries)}
    except Exception as e:
        return {"logs": [], "error": str(e)}


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    msgs  = await db.execute(select(func.count(Message.id)).where(Message.user_id == user.id))
    sess  = await db.execute(select(func.count(ChatSession.id)).where(ChatSession.user_id == user.id))
    docs  = await db.execute(select(func.count(KnowledgeDoc.id)).where(KnowledgeDoc.user_id == user.id))
    runs  = await db.execute(select(func.count(WorkflowRun.id)))
    recent = await db.execute(
        select(Message).where(Message.user_id == user.id)
        .order_by(Message.created_at.desc()).limit(10)
    )
    recent_msgs = recent.scalars().all()
    # Fetch usage data for charts
    usage_res = await db.execute(
        select(Message.model,
               func.count(Message.id).label("count"),
               func.sum(Message.tokens_input + Message.tokens_output).label("tokens"))
        .where(Message.user_id == user.id).group_by(Message.model)
    )
    # Mock Latency and Error Rate for high-fidelity UI (Deterministically generated for visual variety)
    def get_mock_stats(name):
        h = int(hashlib.md5(name.encode()).hexdigest(), 16)
        lat = 10 + (h % 90) # 10-100ms
        err = 0.1 + (h % 3) / 10 # 0.1-0.4%
        return lat, err

    usage_data = []
    for r in usage_res.all():
        lat, err = get_mock_stats(r.model or "unknown")
        usage_data.append({
            "model": r.model or "unknown", 
            "count": r.count, 
            "tokens": r.tokens or 0,
            "latency": lat,
            "error_rate": err
        })
    
    # Fetch timeline data for charts (including tokens and messages)
    timeline_rows = await db.execute(
        text(_timeline_sql()),
        {"uid": user.id}
    )
    res_timeline = {}
    for i in range(7):
        d = (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        res_timeline[d] = {"day": d, "messages": 0, "tokens": 0}
    for r in timeline_rows.fetchall():
        key = str(r.day)[:10]
        if key in res_timeline:
            res_timeline[key]["messages"] = r.cnt
            res_timeline[key]["tokens"] = int(r.tokens or 0)
            
    # Fetch recent logs for event feed
    logs_res = await _fetch_recent_logs_helper(lines=5)
    
    return {
        "stats": {
            "total_messages":  msgs.scalar() or 0,
            "total_sessions":  sess.scalar() or 0,
            "total_docs":      docs.scalar() or 0,
            "workflow_runs":   runs.scalar() or 0,
        },
        "models": await model_manager.get_status(),
        "usage": usage_data,
        "timeline": list(res_timeline.values()),
        "logs": logs_res.get("logs", []),
    }


@router.get("/usage")
async def usage(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Message.model,
               func.count(Message.id).label("count"),
               func.sum(Message.tokens_input + Message.tokens_output).label("tokens"),
               func.sum(Message.cost_usd).label("cost"))
        .where(Message.user_id == user.id).group_by(Message.model)
    )
    return [{"model": r.model or "unknown", "count": r.count,
             "tokens": r.tokens or 0, "cost_usd": round(r.cost or 0, 4)}
            for r in result.all()]


@router.get("/system")
async def system_stats(user: User = Depends(get_current_user)):
    """CPU, RAM, GPU, Disk — realtime via psutil + nvidia-smi"""
    try:
        import psutil, time as _t
    except ImportError:
        return {"available": False, "install_hint": "pip install psutil",
                "cpu": {"percent": 0, "count": 0},
                "memory": {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0},
                "swap":   {"total_mb": 0, "used_mb": 0, "percent": 0},
                "disk":   {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0},
                "network": {"sent_mb": 0, "recv_mb": 0},
                "gpu": [], "uptime": "—"}

    # Wrap in try-except to handle runtime psutil errors gracefully
    try:
        cpu  = psutil.cpu_percent(interval=0.3)
    except Exception:
        cpu  = 0.0
    try:
        cpuf = psutil.cpu_freq()
    except Exception:
        cpuf = None
    try:
        mem  = psutil.virtual_memory()
    except Exception:
        mem  = None
    try:
        swap = psutil.swap_memory()
    except Exception:
        swap = None
    try:
        disk = psutil.disk_usage('/')
    except Exception:
        disk = None
    try:
        net  = psutil.net_io_counters()
    except Exception:
        net  = None
    boot = 0
    try:
        boot = psutil.boot_time()
        h, rem = divmod(int(_t.time() - boot), 3600)
        m, s   = divmod(rem, 60)
    except Exception:
        h, m, s = 0, 0, 0

    # Per-core CPU
    per_core = psutil.cpu_percent(percpu=True, interval=None)

    # GPU via nvidia-smi (opsional)
    gpus = []
    try:
        import subprocess, json as _json
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if out.returncode == 0:
            for line in out.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "name":     parts[0],
                        "util_pct": float(parts[1]) if parts[1].isdigit() else 0,
                        "mem_used_mb":  int(parts[2]) if parts[2].isdigit() else 0,
                        "mem_total_mb": int(parts[3]) if parts[3].isdigit() else 0,
                        "temp_c":   int(parts[4]) if parts[4].isdigit() else 0,
                    })
    except Exception:
        pass

    # Coba via GPUtil sebagai fallback
    if not gpus:
        try:
            import GPUtil
            for g in GPUtil.getGPUs():
                gpus.append({
                    "name":          g.name,
                    "util_pct":      g.load * 100,
                    "mem_used_mb":   int(g.memoryUsed),
                    "mem_total_mb":  int(g.memoryTotal),
                    "temp_c":        g.temperature,
                })
        except Exception:
            pass

    return {
        "available": True,
        "cpu": {
            "percent":    cpu,
            "count":      psutil.cpu_count(logical=True),
            "count_phys": psutil.cpu_count(logical=False),
            "freq_mhz":   round(cpuf.current) if cpuf else 0,
            "per_core":   per_core,
        },
        "memory": {
            "total_mb": round(mem.total   / 1024**2) if mem else 0,
            "used_mb":  round(mem.used    / 1024**2) if mem else 0,
            "free_mb":  round(mem.available / 1024**2) if mem else 0,
            "cached_mb":round((mem.cached if mem and hasattr(mem,'cached') else 0) / 1024**2),
            "percent":  mem.percent if mem else 0,
        },
        "swap": {
            "total_mb": round(swap.total / 1024**2) if swap else 0,
            "used_mb":  round(swap.used  / 1024**2) if swap else 0,
            "percent":  swap.percent if swap else 0,
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 1) if disk else 0,
            "used_gb":  round(disk.used  / 1024**3, 1) if disk else 0,
            "free_gb":  round(disk.free  / 1024**3, 1) if disk else 0,
            "percent":  disk.percent if disk else 0,
        },
        "network": {
            "sent_mb":  round(net.bytes_sent / 1024**2, 1) if net else 0,
            "recv_mb":  round(net.bytes_recv / 1024**2, 1) if net else 0,
            "pkt_sent": net.packets_sent if net else 0,
            "pkt_recv": net.packets_recv if net else 0,
        },
        "gpu":    gpus,
        "uptime": f"{h}j {m}m {s}d",
        "uptime_sec": int(_t.time() - boot) if boot else 0,
    }


@router.get("/timeline")
async def message_timeline(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import text
    rows = await db.execute(
        text(_timeline_full_sql()),
        {"uid": user.id}
    )
    result = {}
    for i in range(7):
        d = (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        result[d] = {"day": d, "messages": 0, "tokens": 0, "cost": 0.0}
    for r in rows.fetchall():
        key = str(r.day)[:10]
        if key in result:
            result[key] = {"day": key, "messages": r.cnt,
                           "tokens": int(r.tokens or 0), "cost": round(float(r.cost or 0), 4)}
    return list(result.values())


@router.delete("/reset")
async def reset_analytics(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import text
    await db.execute(text("DELETE FROM messages WHERE user_id = :uid"), {"uid": user.id})
    await db.execute(text("DELETE FROM chat_sessions WHERE user_id = :uid"), {"uid": user.id})
    await db.execute(text("DELETE FROM api_logs WHERE user_id = :uid"), {"uid": user.id})
    await db.commit()
    return {"status": "reset", "message": "Data analytics berhasil direset"}


# ══════════════════════════════════════════════════════════════
# STORAGE MANAGEMENT
# ══════════════════════════════════════════════════════════════
import shutil as _shutil
from pathlib import Path as _Path
from datetime import datetime as _dt, timedelta as _td


def _fmt_size(b: int) -> str:
    if b < 1024: return f"{b} B"
    if b < 1024**2: return f"{b/1024:.1f} KB"
    if b < 1024**3: return f"{b/1024**2:.1f} MB"
    return f"{b/1024**3:.2f} GB"


def _dir_size(p: _Path) -> int:
    if not p.exists(): return 0
    return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())


def _count_files(p: _Path) -> int:
    if not p.exists(): return 0
    return sum(1 for f in p.rglob('*') if f.is_file())


@router.get("/storage")
async def storage_info(user: User = Depends(get_current_user)):
    """Info lengkap penggunaan storage semua komponen."""
    import os
    from core.config import settings

    base = _Path(__file__).parent.parent

    db_path    = _Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("./", str(base) + "/"))
    upload_dir = _Path(settings.UPLOAD_DIR) if _Path(settings.UPLOAD_DIR).is_absolute() else base / settings.UPLOAD_DIR.lstrip("./")
    chroma_dir = _Path(settings.CHROMA_PERSIST_DIR) if _Path(settings.CHROMA_PERSIST_DIR).is_absolute() else base / settings.CHROMA_PERSIST_DIR.lstrip("./")
    log_dir    = _Path(settings.LOG_FILE).parent if not _Path(settings.LOG_FILE).is_absolute() else _Path(settings.LOG_FILE).parent

    # Hitung ukuran masing-masing
    db_size      = db_path.stat().st_size if db_path.exists() else 0
    upload_size  = _dir_size(upload_dir)
    chroma_size  = _dir_size(chroma_dir)
    log_size     = _dir_size(log_dir)

    # Redis info (opsional)
    redis_used = 0
    redis_keys = 0
    try:
        import redis as _redis
        r = _redis.from_url(settings.REDIS_URL)
        info = r.info("memory")
        redis_used = info.get("used_memory", 0)
        redis_keys = r.dbsize()
        r.close()
    except Exception:
        pass

    total = db_size + upload_size + chroma_size + log_size

    return {
        "total":        _fmt_size(total),
        "total_bytes":  total,
        "components": [
            {
                "id":          "database",
                "name":        "Database (SQLite)",
                "desc":        "Chat history, sesi, user, memory, analytics",
                "size":        _fmt_size(db_size),
                "size_bytes":  db_size,
                "path":        str(db_path),
                "can_clean":   False,
                "icon":        "🗄️",
            },
            {
                "id":          "uploads",
                "name":        "Dokumen Upload (RAG)",
                "desc":        "File PDF/DOCX/TXT yang diupload ke knowledge base",
                "size":        _fmt_size(upload_size),
                "size_bytes":  upload_size,
                "files":       _count_files(upload_dir),
                "path":        str(upload_dir),
                "can_clean":   True,
                "icon":        "📁",
            },
            {
                "id":          "chroma",
                "name":        "Vector Store (ChromaDB)",
                "desc":        "Indeks embedding untuk RAG search — dibuat ulang otomatis",
                "size":        _fmt_size(chroma_size),
                "size_bytes":  chroma_size,
                "path":        str(chroma_dir),
                "can_clean":   True,
                "icon":        "🧬",
            },
            {
                "id":          "logs",
                "name":        "Log File",
                "desc":        "Log aktivitas server (terus bertambah tanpa rotasi)",
                "size":        _fmt_size(log_size),
                "size_bytes":  log_size,
                "path":        str(log_dir),
                "can_clean":   True,
                "icon":        "📋",
            },
            {
                "id":          "redis",
                "name":        "Redis Cache",
                "desc":        "Konteks chat aktif — TTL 24 jam, auto-expire",
                "size":        _fmt_size(redis_used),
                "size_bytes":  redis_used,
                "keys":        redis_keys,
                "can_clean":   True,
                "icon":        "⚡",
            },
        ],
    }


@router.post("/storage/clean")
async def clean_storage(
    target: str,   # logs | redis | uploads_orphan
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bersihkan storage tertentu:
    - logs        : truncate log file
    - redis       : flush semua key chat (chat:ctx:*)
    - old_chats   : hapus sesi chat > 90 hari
    - uploads_orphan: hapus file upload yang dokumennya sudah dihapus dari DB
    """
    from core.config import settings
    from sqlalchemy import text
    from sqlmodel import select
    from db.models import KnowledgeDoc

    base = _Path(__file__).parent.parent
    freed = 0
    detail = ""

    if target == "logs":
        log_file = _Path(settings.LOG_FILE) if _Path(settings.LOG_FILE).is_absolute() \
                   else base / settings.LOG_FILE.lstrip("./")
        if log_file.exists():
            freed = log_file.stat().st_size
            log_file.write_text("")   # truncate
            detail = f"Log file dikosongkan ({_fmt_size(freed)})"
        else:
            detail = "Log file tidak ditemukan"

    elif target == "redis":
        try:
            import redis as _redis
            r = _redis.from_url(settings.REDIS_URL)
            keys = r.keys("chat:ctx:*")
            if keys:
                freed = sum(len(r.get(k) or b"") for k in keys)
                r.delete(*keys)
            r.close()
            detail = f"{len(keys)} key cache dihapus ({_fmt_size(freed)})"
        except Exception as e:
            detail = f"Redis tidak tersedia: {str(e)[:100]}"

    elif target == "old_chats":
        cutoff = _dt.utcnow() - _td(days=90)
        result = await db.execute(
            text("DELETE FROM messages WHERE created_at < :cutoff"),
            {"cutoff": cutoff.isoformat()}
        )
        deleted_msgs = result.rowcount
        result2 = await db.execute(
            text("DELETE FROM chat_sessions WHERE updated_at < :cutoff"),
            {"cutoff": cutoff.isoformat()}
        )
        deleted_sess = result2.rowcount
        try:
            await db.execute(text("VACUUM"))
        except Exception:
            pass  # VACUUM is SQLite-only, skip on PostgreSQL
        await db.commit()
        detail = f"Dihapus {deleted_sess} sesi dan {deleted_msgs} pesan (>90 hari)"

    elif target == "uploads_orphan":
        # Hapus file upload yang KnowledgeDoc-nya sudah tidak ada
        result = await db.execute(select(KnowledgeDoc))
        docs   = result.scalars().all()
        valid_files = {d.filename for d in docs}

        upload_dir = _Path(settings.UPLOAD_DIR) if _Path(settings.UPLOAD_DIR).is_absolute() \
                     else base / settings.UPLOAD_DIR.lstrip("./")
        removed = 0
        if upload_dir.exists():
            for f in upload_dir.rglob("*"):
                if f.is_file() and str(f) not in valid_files:
                    freed += f.stat().st_size
                    f.unlink()
                    removed += 1
        detail = f"{removed} file orphan dihapus ({_fmt_size(freed)})"

    else:
        raise HTTPException(400, f"Target tidak dikenal: {target}")

    return {"status": "ok", "freed": _fmt_size(freed), "freed_bytes": freed, "detail": detail}


@router.post("/storage/rotate-log")
async def setup_log_rotation(user: User = Depends(get_current_user)):
    """Setup logrotate config untuk otomasi rotasi log."""
    from core.config import settings
    base = _Path(__file__).parent.parent
    log_file = _Path(settings.LOG_FILE) if _Path(settings.LOG_FILE).is_absolute() \
               else base / settings.LOG_FILE.lstrip("./")

    config = f"""{log_file} {{
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}}
"""
    config_path = _Path("/etc/logrotate.d/ai-super-assistant")
    try:
        import subprocess
        proc = subprocess.run(
            ["sudo", "-n", "tee", str(config_path)],
            input=config.encode(),
            capture_output=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return {"status": "ok", "message": "Logrotate dikonfigurasi (rotasi harian, simpan 7 hari)"}
        else:
            return {
                "status": "manual",
                "message": "Tidak bisa tulis config otomatis (perlu sudo)",
                "config": config,
                "path": str(config_path),
                "hint": f"Jalankan manual: sudo nano {config_path} lalu paste config di bawah",
            }
    except Exception as e:
        return {"status": "error", "message": str(e), "config": config}


# ── Logs Endpoint ───────────────────────────────────────────────

@router.get("/logs/recent")
async def get_recent_logs(
    lines: int = 100,
    level: str = "",
    user: User = Depends(get_current_user),
):
    """Baca log terbaru dari file."""
    return await _fetch_recent_logs_helper(lines=lines, level=level)

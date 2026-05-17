import asyncio
import os
import json
import re
import re as _re
import socket
import structlog
import hashlib
from datetime import datetime

log = structlog.get_logger()


# ─── Foreground Server Detection ────────────────────────────────────────────
FOREGROUND_SERVER_PATTERNS = [
    r'\bnode\s+\S+\.(?:js|mjs|cjs)\b',
    r'\bnpm\s+start\b',
    r'\bnpm\s+run\s+(?:dev|serve|start)\b',
    r'\byarn\s+(?:start|dev)\b',
    r'\bpnpm\s+(?:start|dev)\b',
    r'\bstreamlit\s+run\b',
    r'\buvicorn\b',
    r'\bgunicorn\b',
    r'\bflask\s+run\b',
    r'\bserve\s+-s\b',
    r'\bnpx\s+serve\b',
    r'\bhttp-server\b',
    r'\blive-server\b',
    r'\bphp\s+-S\b',
    r'\bruby\s+\S+\.rb\b',
    r'\bvite\s+(?:preview|dev)?\s*$',
    r'\bnext\s+(?:dev|start)\b',
]

_BACKGROUND_MARKERS = ['&', 'nohup ', '> /dev/null', 'disown', 'setsid']

def _is_foreground_server(command: str) -> bool:
    cmd_stripped = command.strip()
    if any(marker in cmd_stripped for marker in _BACKGROUND_MARKERS):
        return False
    for pattern in FOREGROUND_SERVER_PATTERNS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            return True
    return False

def _wrap_as_background(command: str, project_base_path: str) -> tuple[str, str]:
    import hashlib
    cmd_hash = hashlib.md5(command.encode()).hexdigest()[:8]
    log_file = os.path.join(project_base_path, f".server_{cmd_hash}.log")
    wrapped = f"nohup {command} > {log_file} 2>&1 &"
    return wrapped, log_file

def _classify_command_timeout(command: str) -> float:
    cmd_lower = command.lower().strip()
    if any(p in cmd_lower for p in [
        'npm install', 'npm i ', 'npm ci',
        'pip install', 'pip3 install',
        'apt-get install', 'apt install',
        'yarn install', 'yarn add',
        'pnpm install', 'pnpm add',
        'npx prisma',  # FIX: prisma commands butuh waktu lama
    ]):
        return 300.0
    if any(p in cmd_lower for p in [
        'npm run build', 'yarn build', 'pnpm build',
        'webpack', 'tsc ', 'vite build',
        'next build', 'cargo build', 'make ',
    ]):
        return 180.0
    if cmd_lower.rstrip().endswith('&'):
        return 15.0
    return 60.0


# ─── Port Safety System ─────────────────────────────────────────────────────
RESERVED_PORTS = {7860, 6379, 5432, 3306, 11434}

def _get_safe_port(preferred: int = 0, range_start: int = 8100, range_end: int = 9000) -> int:
    if preferred and preferred not in RESERVED_PORTS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", preferred))
                return preferred
        except OSError:
            pass

    for port in range(range_start, range_end):
        if port in RESERVED_PORTS:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return 0

def _rewrite_port_in_command(command: str) -> tuple[str, str]:
    port_patterns = [
        _re.compile(r'(--port[= ]+)(\d+)'),
        _re.compile(r'(-p\s+)(\d+)'),
        _re.compile(r'(PORT=)(\d+)'),
        _re.compile(r'((?:0\.0\.0\.0|127\.0\.0\.1|localhost):)(\d+)'),
        _re.compile(r'(--bind\s+\S+:)(\d+)'),
        _re.compile(r'(run\s+-p\s+)(\d+)'),
        _re.compile(r'(--port\s+)(\d+)'),
    ]
    warning = ""
    modified = command
    for pattern in port_patterns:
        match = pattern.search(modified)
        if match:
            port_str = match.group(2)
            try:
                port = int(port_str)
            except ValueError:
                continue
            if port in RESERVED_PORTS:
                safe_port = _get_safe_port(range_start=port + 1)
                if not safe_port:
                    safe_port = _get_safe_port()
                if safe_port:
                    modified = modified[:match.start(2)] + str(safe_port) + modified[match.end(2):]
                    warning = (
                        f"PORT COLLISION PREVENTED: Port {port} is reserved. "
                        f"Automatically reassigned to port {safe_port}.\n"
                    )
                    break
    return modified, warning


async def find_safe_port(preferred: int = 0) -> str:
    port = _get_safe_port(preferred)
    if port:
        return f"Safe port found: {port}. Free and does NOT conflict with AI Orchestrator (port 7860)."
    return "Error: Could not find a free port in range 8100-9000."


async def execute_bash(command: str, session_id: str = None) -> str:
    """Run a bash command and return output."""
    try:
        # ── Resolve project base path ─────────────────────────────────────
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except Exception:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if not project_base_path:
            safe_folder = (session_id[:8] if session_id else "agent")
            project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")

        os.makedirs(project_base_path, exist_ok=True)

        # ── FIX: Jika command mengandung 'cd X && ...', jalankan dari home
        # bukan dari project_base_path agar path relatif dalam cd bisa resolve
        # Deteksi apakah command sudah punya 'cd' di awal
        cmd_stripped = command.strip()
        has_explicit_cd = bool(re.match(r'^cd\s+', cmd_stripped))

        # Tentukan cwd yang tepat:
        # - Jika command dimulai dengan 'cd /absolute/path', pakai home sebagai base
        # - Jika command dimulai dengan 'cd relative/path', pakai home sebagai base
        # - Jika tidak ada cd, pakai project_base_path
        if has_explicit_cd:
            # FIX: Jalankan dari home agar cd bisa navigate ke mana saja
            cwd = os.path.expanduser("~")
        else:
            cwd = project_base_path

        # ── Security: Normalize dan cek perintah berbahaya ───────────────
        normalized_cmd = re.sub(r'\s+', ' ', command.lower().strip())

        RESTRICTED_PATTERNS = [
            (r'\brm\s+-rf\s+[/~]', "Destructive rm -rf on root/home"),
            (r'\brm\s+-r\s+[/~]', "Destructive rm -r on root/home"),
            (r'\brmdir\s+/', "rmdir on root"),
            (r'\bmkfs\b', "Disk format command"),
            (r'\bdd\s+if=', "Raw disk write via dd"),
            (r'\b(shutdown|reboot|halt|poweroff)\b', "System power control"),
            (r'\bsystemctl\s+(stop|disable)\s+.*orchestrator', "Stopping AI Orchestrator service"),
            (r':\(\)\s*\{', "Fork bomb pattern"),
            (r':\s*\(\s*\)\s*\{', "Fork bomb pattern"),
            (r'cat\s+.*/\.ssh/', "Reading SSH keys"),
            (r'cat\s+.*/etc/shadow', "Reading shadow passwords"),
            (r'>\s*.*\.env\b', "Overwriting .env"),
            (r'nc\s+.*-e\s+/bin', "Netcat reverse shell"),
            (r'curl\s+.*\|\s*(bash|sh)', "Remote code execution via curl pipe"),
            (r'wget\s+.*\|\s*(bash|sh)', "Remote code execution via wget pipe"),
            (r'\bchmod\s+[0-7]*[67][0-7]\s+/(etc|bin|usr)', "Privilege escalation via chmod"),
            (r'lsof\s+.*:7860', "Querying Orchestrator port 7860"),
            (r'fuser\s+.*7860', "Killing Orchestrator port 7860"),
            (r'\b(pkill|killall)\s+.*(uvicorn|python|orchestrator|main\.py)', "Killing Orchestrator process by name"),
        ]

        for pattern, reason in RESTRICTED_PATTERNS:
            if re.search(pattern, normalized_cmd):
                log.warning("Blocked dangerous command", reason=reason, cmd=command[:80])
                return f"Security Exception: Command blocked — {reason}."

        # Protect Orchestrator PIDs dynamically to prevent suicide
        my_pid = str(os.getpid())
        parent_pid = str(os.getppid())
        if "kill" in normalized_cmd and (my_pid in normalized_cmd or parent_pid in normalized_cmd):
            log.warning("Blocked attempt to kill Orchestrator PID", cmd=command[:80])
            return "Security Exception: Attempting to kill the Orchestrator process is strictly blocked."

        PROTECTED_PATHS = ["/etc/passwd", "/etc/shadow", "/.ssh/id_", "ai-orchestrator.db"]
        cmd_lower = command.lower()
        for protected in PROTECTED_PATHS:
            if protected in cmd_lower and any(op in cmd_lower for op in [" > ", ">>", "tee ", "write"]):
                return f"Security Exception: Writing to protected file '{protected}' is blocked."

        # ── Port collision prevention ──────────────────────────────────────
        port_warning = ""
        command, port_warning = _rewrite_port_in_command(command)

        # ── Auto-background foreground servers ────────────────────────────
        bg_log_file = None
        was_auto_backgrounded = False
        if _is_foreground_server(command):
            log.info("Auto-backgrounding foreground server command", cmd=command[:80])
            command, bg_log_file = _wrap_as_background(command, project_base_path)
            was_auto_backgrounded = True

        # ── Adaptive timeout ──────────────────────────────────────────────
        timeout = _classify_command_timeout(command)

        # FIX: Log command dengan %s bukan f-string untuk hindari format specifier error
        log.info("execute_bash running", cmd=command[:120], cwd=cwd, timeout=timeout)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,   # FIX: gunakan cwd yang sudah dihitung di atas
        )

        async def read_stream(stream, max_lines=10000):
            lines = []
            truncated = False
            if stream is None:
                return "", False
            async for line in stream:
                if len(lines) < max_lines:
                    lines.append(line.decode(errors="replace"))
                else:
                    if not truncated:
                        truncated = True
                        try:
                            proc.terminate()
                        except Exception:
                            pass
            return "".join(lines), truncated

        async def run_with_timeout():
            stdout_task = asyncio.create_task(read_stream(proc.stdout))
            stderr_task = asyncio.create_task(read_stream(proc.stderr))
            await proc.wait()
            out, out_trunc = await stdout_task
            err, err_trunc = await stderr_task
            return out, out_trunc, err, err_trunc

        out, out_trunc, err, err_trunc = await asyncio.wait_for(
            run_with_timeout(), timeout=timeout
        )

        output = f"[Working Directory: {cwd}]\n"
        if port_warning:
            output += port_warning

        if was_auto_backgrounded and bg_log_file:
            await asyncio.sleep(3)
            try:
                if os.path.exists(bg_log_file):
                    with open(bg_log_file, 'r', errors='replace') as f:
                        startup_log = f.read(4000)
                    output += "Server started in background (auto-detected foreground command).\n"
                    output += f"Log file: {bg_log_file}\n"
                    if startup_log.strip():
                        output += f"--- Startup Log ---\n{startup_log}\n---\n"
                    else:
                        output += "(Server starting, no log output yet)\n"
                else:
                    output += f"Server started in background. Log file: {bg_log_file}\n"
            except Exception as log_err:
                output += f"Server started in background. (Could not read log: {log_err})\n"
        else:
            if out:
                output += out
                if out_trunc:
                    output += "\n...[STDOUT TRUNCATED]..."
            if err:
                output += "\n[stderr]\n" + err
                if err_trunc:
                    output += "\n...[STDERR TRUNCATED]..."

        result = output.strip() or "Command executed successfully with no output."

        # FIX: Tambahkan hint berguna jika npm/prisma gagal karena package.json tidak ada
        if "missing script" in result.lower() or "no such file" in result.lower():
            result += (
                "\n\n[HINT: Pastikan Anda sudah 'cd' ke direktori project yang benar "
                "sebelum menjalankan npm/prisma. Gunakan: cd /path/ke/project && npm install]"
            )
        if "enoent" in result.lower() and "package.json" in result.lower():
            result += (
                "\n\n[HINT: package.json tidak ditemukan. "
                "Buat dulu dengan write_file atau pastikan path project sudah benar.]"
            )

        return result

    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return (
            f"Error: Command timed out after {int(timeout)} seconds. "
            "If this is a server command, run it in background: "
            "nohup <command> > app.log 2>&1 &"
        )
    except Exception as e:
        # FIX: Gunakan str(e) bukan f-string dengan format specifier
        return "Error executing command: " + str(e)


async def read_file(path: str, session_id: str = None) -> str:
    """Read a file."""
    try:
        import aiofiles

        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except Exception:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if project_base_path and not os.path.isabs(path):
            abs_path = os.path.join(project_base_path, path)
        elif not os.path.isabs(path) and session_id:
            safe_folder = session_id[:8]
            abs_path = os.path.join(os.path.expanduser(f"~/projects/{safe_folder}"), path)
        else:
            abs_path = os.path.abspath(path)

        abs_real = os.path.realpath(abs_path)

        _BLOCKED_READ_PATTERNS = [
            "/etc/shadow", "/etc/passwd", "/etc/sudoers",
            "/.ssh/", "/.gnupg/", "/proc/", "/sys/",
        ]
        _BLOCKED_READ_EXTENSIONS = [".pem", ".key", ".p12", ".pfx"]
        _is_blocked = any(p in abs_real for p in _BLOCKED_READ_PATTERNS)
        _is_blocked = _is_blocked or any(abs_real.endswith(ext) for ext in _BLOCKED_READ_EXTENSIONS)

        # Blokir baca file .env milik orchestrator sendiri
        _env_path = os.path.realpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        )
        if abs_real == _env_path:
            _is_blocked = True

        if _is_blocked:
            log.warning("Blocked read_file on sensitive path", path=abs_real[:100])
            return f"Security Exception: Reading '{os.path.basename(abs_real)}' is blocked."

        if not os.path.exists(abs_path):
            return f"Error: File not found: {abs_path}"

        async def _read():
            async with aiofiles.open(abs_path, "r", encoding="utf-8") as f:
                return await f.read()

        return await asyncio.wait_for(_read(), timeout=30.0)

    except asyncio.TimeoutError:
        return f"Error: Reading file {path} timed out after 30 seconds."
async def _update_artifact_registry(session_id: str, abs_path: str, content: str):
    """Helper to track file changes and their hashes."""
    if not session_id:
        return
    try:
        from db.database import AsyncSessionLocal
        from db.models import ArtifactRegistry
        from sqlmodel import select
        
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ArtifactRegistry).where(
                    ArtifactRegistry.session_id == session_id,
                    ArtifactRegistry.file_path == abs_path
                )
            )
            existing = result.scalars().first()
            if existing:
                existing.file_hash = file_hash
                existing.last_modified = datetime.now().replace(tzinfo=None)
                db.add(existing)
            else:
                new_entry = ArtifactRegistry(
                    session_id=session_id,
                    file_path=abs_path,
                    file_hash=file_hash
                )
                db.add(new_entry)
            await db.commit()
    except Exception as e:
        log.debug("Artifact Registry update skipped", error=str(e))


async def write_file(path: str, content: str, session_id: str = None, confirm: bool = False) -> str:
    """Write content to a file with safety checks for overwrites."""
    try:
        import aiofiles

        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except Exception:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if not project_base_path and not os.path.isabs(path):
            safe_folder = session_id[:8] if session_id else "agent"
            project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")

        if project_base_path and not os.path.isabs(path):
            path = os.path.join(project_base_path, path)

        abs_path = os.path.abspath(path)

        # ── Safety Checks ──────────────────────────────────────────────────
        projects_base = os.path.expanduser("~/projects")
        is_outside = not abs_path.startswith(projects_base)
        
        if os.path.exists(abs_path):
            size = os.path.getsize(abs_path)
            # Require confirmation for large overwrites or writing outside projects
            if (size > 100 * 1024 or is_outside) and not confirm:
                return (
                    f"⚠️ File '{abs_path}' sudah ada "
                    f"({size/1024:.1f}KB" + (" dan di luar workspace" if is_outside else "") + ").\n"
                    f"   Gunakan confirm=True untuk menimpa file ini secara paksa."
                )

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        async def _write():
            async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
                await f.write(content)

        await asyncio.wait_for(_write(), timeout=30.0)

        # Update Artifact Registry
        await _update_artifact_registry(session_id, abs_path, content)

        display_path = os.path.relpath(abs_path, project_base_path) if project_base_path else path
        result = "Successfully wrote to " + display_path
        if project_base_path:
            result = "Project: " + project_base_path + "\n" + result
            try:
                from core.project_indexer import project_indexer
                asyncio.create_task(project_indexer.scan_project(session_id or "", project_base_path))
            except Exception:
                pass

        return result

    except asyncio.TimeoutError:
        return "Error: Writing file " + path + " timed out after 30 seconds."
    except Exception as e:
        return "Error writing file " + path + ": " + str(e)


async def write_multiple_files(files_data: list, session_id: str = None) -> str:
    """Write multiple files at once."""
    try:
        import aiofiles

        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except Exception:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if not project_base_path:
            first_relative = next(
                (f.get("path", "") for f in files_data
                 if f.get("path") and not os.path.isabs(f.get("path", ""))),
                None
            )
            if first_relative:
                safe_folder = session_id[:8] if session_id else "agent"
                project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")

        results = []
        for file_obj in files_data:
            path = file_obj.get("path")
            content = file_obj.get("content", "")
            if not path:
                results.append("Skipped invalid entry: " + str(file_obj))
                continue

            if project_base_path and not os.path.isabs(path):
                path = os.path.join(project_base_path, path)

            try:
                abs_path = os.path.abspath(path)
                
                # ── Safety Checks ──────────────────────────────────────────
                projects_base = os.path.expanduser("~/projects")
                is_outside = not abs_path.startswith(projects_base)
                
                if os.path.exists(abs_path):
                    size = os.path.getsize(abs_path)
                    if (size > 100 * 1024 or is_outside) and not confirm:
                        results.append(
                            f"Skipped {path}: File exists ({size/1024:.1f}KB" +
                            (" and outside workspace" if is_outside else "") + "). Needs confirm=True."
                        )
                        continue

                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
                    await f.write(content)
                display_path = os.path.relpath(abs_path, project_base_path) if project_base_path else path
                results.append("OK: " + display_path)
                # Update Artifact Registry
                await _update_artifact_registry(session_id, abs_path, content)
            except Exception as e:
                results.append("Error writing " + path + ": " + str(e))

        if project_base_path:
            try:
                from core.project_indexer import project_indexer
                asyncio.create_task(project_indexer.scan_project(session_id or "", project_base_path))
            except Exception:
                pass
            return "Project: " + project_base_path + "\n" + "\n".join(results)
        else:
            return "\n".join(results)

    except Exception as e:
        return "Fatal error in write_multiple_files: " + str(e)


async def write_file_chunk(path: str, content: str, chunk_index: int, total_chunks: int, session_id: str = None) -> str:
    """
    Write file in chunks for large files or truncation recovery.
    Appends content if chunk_index > 0.
    """
    try:
        import aiofiles
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if not project_base_path and not os.path.isabs(path):
            safe_folder = session_id[:8] if session_id else "agent"
            project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")

        if project_base_path and not os.path.isabs(path):
            path = os.path.join(project_base_path, path)

        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        mode = "w" if chunk_index == 0 else "a"
        async with aiofiles.open(abs_path, mode, encoding="utf-8") as f:
            await f.write(content)

        if chunk_index + 1 == total_chunks:
            # Final chunk, update registry
            with open(abs_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
            await _update_artifact_registry(session_id, abs_path, full_content)
            
            try:
                from core.project_indexer import project_indexer
                asyncio.create_task(project_indexer.scan_project(session_id or "", project_base_path or os.path.dirname(abs_path)))
            except Exception:
                pass

        return f"Successfully wrote chunk {chunk_index + 1}/{total_chunks} to {os.path.basename(abs_path)}"
    except Exception as e:
        return f"Error writing chunk: {str(e)}"


async def ask_model(model_id: str, prompt: str) -> str:
    """Ask another AI model a question."""
    from core.model_manager import model_manager
    try:
        if model_id not in model_manager.available_models:
            return "Error: Model '" + model_id + "' is not available."
        messages = [{"role": "user", "content": prompt}]
        response = ""
        async for chunk in model_manager.chat_stream(
            model_id, messages, temperature=0.7, max_tokens=4096
        ):
            if chunk and not chunk.startswith("\n[Error"):
                response += chunk
        return response.strip() or "No response from model."
    except Exception as e:
        return "Error asking model " + model_id + ": " + str(e)

async def list_dir(path: str, session_id: str = None) -> str:
    """List directory contents."""
    try:
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if project_base_path and not os.path.isabs(path):
            abs_path = os.path.join(project_base_path, path)
        elif not os.path.isabs(path) and session_id:
            safe_folder = session_id[:8]
            abs_path = os.path.join(os.path.expanduser(f"~/projects/{safe_folder}"), path)
        else:
            abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return f"Error: Directory not found or is not a directory: {abs_path}"

        items = os.listdir(abs_path)
        result = []
        for item in sorted(items):
            full_item = os.path.join(abs_path, item)
            if os.path.isdir(full_item):
                result.append(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(full_item)
                result.append(f"[FILE] {item} ({size} bytes)")

        return f"Contents of {abs_path}:\n" + "\n".join(result)
    except Exception as e:
        return "Error listing directory: " + str(e)

async def search_files(query: str, path: str = ".", session_id: str = None) -> str:
    """Search for files matching query or content."""
    try:
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                import json as _json
                                meta = _json.loads(meta)
                            except:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if project_base_path and not os.path.isabs(path):
            abs_path = os.path.join(project_base_path, path)
        elif not os.path.isabs(path) and session_id:
            safe_folder = session_id[:8]
            abs_path = os.path.join(os.path.expanduser(f"~/projects/{safe_folder}"), path)
        else:
            abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return f"Error: Path not found: {abs_path}"

        import shlex
        safe_query = shlex.quote(query)
        safe_path = shlex.quote(abs_path)
        
        # 1. Cari konten
        cmd_content = f"grep -irl {safe_query} {safe_path} --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv | head -n 20"
        proc = await asyncio.create_subprocess_shell(cmd_content, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        output = stdout.decode().strip()

        # 2. Jika tidak ada konten, cari nama file
        if not output:
            cmd_name = f"find {safe_path} -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -iname '*{query}*' | head -n 20"
            proc2 = await asyncio.create_subprocess_shell(cmd_name, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=30.0)
            output = stdout2.decode().strip()

        if not output:
            return f"No results found for '{query}' in {abs_path}"
        return f"Search results for '{query}' in {abs_path}:\n{output}"
    except asyncio.TimeoutError:
        return "Error: Search timed out after 30 seconds."
    except Exception as e:
        return "Error searching files: " + str(e)



async def read_document(path: str, session_id: str = None) -> str:
    """Read a document (PDF, DOCX, XLSX, PPTX, CSV, TXT) seamlessly."""
    try:
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        import json as _json
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                meta = _json.loads(meta)
                            except Exception:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if project_base_path and not os.path.isabs(path):
            abs_path = os.path.join(project_base_path, path)
        elif not os.path.isabs(path) and session_id:
            safe_folder = session_id[:8]
            abs_path = os.path.join(os.path.expanduser(f"~/projects/{safe_folder}"), path)
        else:
            abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return f"Error: File not found: {abs_path}"

        # Delegate to RAG document processor
        from rag.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        segments = processor.extract_text(abs_path)
        
        full_text = "\n\n".join(segments)
        
        # Truncate if too long to prevent blowing up the context window
        if len(full_text) > 20000:
            full_text = full_text[:20000] + "\n\n...[DOCUMENT TRUNCATED DUE TO LENGTH]..."
            
        return f"--- Content of {os.path.basename(abs_path)} ---\n{full_text}"

    except Exception as e:
        return f"Error reading document: {str(e)}"


async def replace_in_file(path: str, old_string: str, new_string: str, session_id: str = None) -> str:
    """Surgically replace text in a file."""
    try:
        import aiofiles
        
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        import json as _json
                        meta = session.project_metadata
                        if isinstance(meta, str):
                            try:
                                meta = _json.loads(meta)
                            except Exception:
                                meta = {}
                        project_base_path = meta.get("project_path") if isinstance(meta, dict) else None
            except Exception:
                pass

        if project_base_path and not os.path.isabs(path):
            abs_path = os.path.join(project_base_path, path)
        elif not os.path.isabs(path) and session_id:
            safe_folder = session_id[:8]
            abs_path = os.path.join(os.path.expanduser(f"~/projects/{safe_folder}"), path)
        else:
            abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return f"Error: File not found: {abs_path}"

        async with aiofiles.open(abs_path, "r", encoding="utf-8") as f:
            content = await f.read()

        if old_string not in content:
            # Maybe it has different line endings, try to normalize
            normalized_content = content.replace("\r\n", "\n")
            normalized_old = old_string.replace("\r\n", "\n")
            if normalized_old not in normalized_content:
                return f"Error: The exact old_string was not found in {path}. Make sure to include the exact literal text including spaces and newlines."
            else:
                content = normalized_content
                old_string = normalized_old
                new_string = new_string.replace("\r\n", "\n")

        count = content.count(old_string)
        if count > 1:
            return f"Error: old_string is ambiguous. Found {count} occurrences in {path}. Please provide a larger snippet to uniquely identify the section to replace."

        new_content = content.replace(old_string, new_string)

        async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
            await f.write(new_content)
            
        await _update_artifact_registry(session_id, abs_path, new_content)

        return f"Successfully replaced {len(old_string)} chars with {len(new_string)} chars in {path}."

    except Exception as e:
        return f"Error replacing text in file: {str(e)}"

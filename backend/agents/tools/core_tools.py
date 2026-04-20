import asyncio
import os
import json
import re as _re
import socket


# ─── Port Safety System ─────────────────────────────────────────────────────
# Ports reserved by the AI Orchestrator and critical system services.
# Any app created by the agent MUST NOT use these ports.
RESERVED_PORTS = {
    7860,   # AI Orchestrator (FastAPI main)
    6379,   # Redis
    5432,   # PostgreSQL (if used)
    3306,   # MySQL (if used)
    11434,  # Ollama
}

def _get_safe_port(preferred: int = 0, range_start: int = 8100, range_end: int = 9000) -> int:
    """Find a free port that doesn't collide with reserved ports."""
    if preferred and preferred not in RESERVED_PORTS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", preferred))
                return preferred
        except OSError:
            pass  # port busy, find another

    for port in range(range_start, range_end):
        if port in RESERVED_PORTS:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return 0  # OS will assign

def _rewrite_port_in_command(command: str) -> tuple[str, str]:
    """
    Detect if a command tries to bind to a reserved port and rewrite it.
    Returns (possibly_rewritten_command, warning_message_or_empty).
    """
    # Patterns that indicate a server binding to a port
    port_patterns = [
        # --port 7860  or  --port=7860  or  -p 7860
        _re.compile(r'(--port[= ]+)(\d+)'),
        _re.compile(r'(-p\s+)(\d+)'),
        # PORT=7860 (env var)
        _re.compile(r'(PORT=)(\d+)'),
        # :7860 in URLs like 0.0.0.0:7860 or localhost:7860
        _re.compile(r'((?:0\.0\.0\.0|127\.0\.0\.1|localhost):)(\d+)'),
        # uvicorn/gunicorn --bind 0.0.0.0:7860
        _re.compile(r'(--bind\s+\S+:)(\d+)'),
        # flask run -p 7860
        _re.compile(r'(run\s+-p\s+)(\d+)'),
        # npm start -- --port 7860, vite --port 7860
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
                    # If port+1 exceeds default range, fall back to standard safe range
                    safe_port = _get_safe_port()
                if safe_port:
                    modified = modified[:match.start(2)] + str(safe_port) + modified[match.end(2):]
                    warning = (
                        f"⚠️ PORT COLLISION PREVENTED: Port {port} is reserved by the AI Orchestrator system. "
                        f"Automatically reassigned to port {safe_port}.\n"
                    )
                    break
    
    return modified, warning


async def find_safe_port(preferred: int = 0) -> str:
    """Find a safe, available port that won't conflict with the AI Orchestrator.
    Use this before starting any server application."""
    port = _get_safe_port(preferred)
    if port:
        return f"Safe port found: {port}. This port is free and does NOT conflict with the AI Orchestrator (port 7860) or other system services."
    return "Error: Could not find a free port in range 8100-9000."


async def execute_bash(command: str, session_id: str = None) -> str:
    """Run a bash command and return output."""
    try:
        # Get project location from session if available
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        project_base_path = session.project_metadata.get("project_path")
            except Exception:
                pass
                
        if not project_base_path:
            safe_folder = session_id[:8] if session_id else "agent"
            project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")
            
        os.makedirs(project_base_path, exist_ok=True)

        # Agent Safeguards: Blocklist to prevent catastrophic mistakes
        RESTRICTED_COMMANDS = [
            "rm -rf /", "mkfs", "dd if=", "shutdown", "reboot", "halt", 
            "mv /", ":(){:|:&};:"
        ]
        cmd_lower = command.lower()
        if any(bad_cmd in cmd_lower for bad_cmd in RESTRICTED_COMMANDS):
            return f"Security Exception: Command '{command}' contains restricted patterns and is blocked by system safeguards."

        # ── Port Collision Prevention ─────────────────────────────
        port_warning = ""
        command, port_warning = _rewrite_port_in_command(command)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_base_path
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

        out, out_trunc, err, err_trunc = await asyncio.wait_for(run_with_timeout(), timeout=120.0)
        
        output = f"📁 [Working Directory: {project_base_path}]\n"
        output += port_warning  # Prepend port warning if any
        if out:
            output += out
            if out_trunc:
                output += "\n...[STDOUT TRUNCATED: EXCEEDED 10000 LINES]..."
        if err:
            output += "\n[stderr]\n" + err
            if err_trunc:
                output += "\n...[STDERR TRUNCATED: EXCEEDED 10000 LINES]..."
                
        return output.strip() or "Command executed successfully with no output."
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except:
            pass
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

async def read_file(path: str, session_id: str = None) -> str:
    """Read a file."""
    try:
        import aiofiles
        
        # Get project location from session if available
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        project_base_path = session.project_metadata.get("project_path")
            except Exception:
                pass
                
        if not project_base_path and not os.path.isabs(path):
            safe_folder = session_id[:8] if session_id else "agent"
            project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")
            
        if project_base_path and not os.path.isabs(path):
            abs_path = os.path.join(project_base_path, path)
        else:
            abs_path = os.path.abspath(path)
            
        if not os.path.exists(abs_path):
            return f"Error: File {abs_path} not found."
        async def _read():
            async with aiofiles.open(abs_path, "r", encoding="utf-8") as f:
                return await f.read()
        return await asyncio.wait_for(_read(), timeout=30.0)
    except asyncio.TimeoutError:
        return f"Error: Reading file {path} timed out after 30 seconds."
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

async def write_file(path: str, content: str, session_id: str = None) -> str:
    """Write content to a file."""
    try:
        import aiofiles
        
        # Get project location from session if available
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        project_base_path = session.project_metadata.get("project_path")
            except Exception:
                pass  # Continue without project path if database error
        
        # DEFAULT: never write inside AI Orchestrator folders.
        # If no explicit project_path is set for the session, sandbox in ~/projects/
        if not project_base_path and not os.path.isabs(path):
            safe_folder = session_id[:8] if session_id else "agent"
            project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")
        
        # Apply project base path if set and path is relative
        if project_base_path and not os.path.isabs(path):
            path = os.path.join(project_base_path, path)
        
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        async def _write():
            async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
                await f.write(content)
        await asyncio.wait_for(_write(), timeout=30.0)
        
        # Show relative path in result for cleaner output
        display_path = os.path.relpath(abs_path, project_base_path) if project_base_path else path
        
        result = f"Successfully wrote to {display_path}"
        if project_base_path:
            result = f"📁 Project: {project_base_path}\n{result}"
        
        return result
    except asyncio.TimeoutError:
        return f"Error: Writing file {path} timed out after 30 seconds."
    except Exception as e:
        return f"Error writing file {path}: {str(e)}"

async def write_multiple_files(files_data: list, session_id: str = None) -> str:
    """Write multiple files at once. files_data is a list of dicts: [{'path': '...', 'content': '...'}]"""
    try:
        import aiofiles
        
        # Get project location from session if available
        project_base_path = None
        if session_id:
            try:
                from db.database import AsyncSessionLocal
                from db.models import ChatSession
                async with AsyncSessionLocal() as db:
                    session = await db.get(ChatSession, session_id)
                    if session and session.project_metadata:
                        project_base_path = session.project_metadata.get("project_path")
            except Exception:
                pass  # Continue without project path if database error
        
        # DEFAULT: sandbox in ~/projects/ when no explicit project_path set
        if not project_base_path:
            # Check if any first file path is relative (not absolute)
            first_relative = next((f.get("path", "") for f in files_data if f.get("path") and not os.path.isabs(f.get("path", ""))), None)
            if first_relative:
                safe_folder = session_id[:8] if session_id else "agent"
                project_base_path = os.path.expanduser(f"~/projects/{safe_folder}")
        
        results = []
        for file_obj in files_data:
            path = file_obj.get("path")
            content = file_obj.get("content", "")
            if not path:
                results.append(f"Skipped invalid entry: {file_obj}")
                continue
            
            # Apply project base path if set and path is relative
            if project_base_path and not os.path.isabs(path):
                path = os.path.join(project_base_path, path)
            
            try:
                abs_path = os.path.abspath(path)
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
                    await f.write(content)
                
                # Show relative path in result for cleaner output
                display_path = os.path.relpath(abs_path, project_base_path) if project_base_path else path
                results.append(f"Successfully wrote to {display_path}")
            except Exception as e:
                results.append(f"Error writing to {path}: {str(e)}")
        
        # Add project location info if available
        if project_base_path:
            project_info = f"\n📁 Project Location: {project_base_path}"
            return project_info + "\n" + "\n".join(results)
        else:
            return "\n".join(results)
    except Exception as e:
        return f"Fatal error in write_multiple_files: {str(e)}"

async def ask_model(model_id: str, prompt: str) -> str:
    """Ask another AI model installed in the system a question or to perform a task."""
    from core.model_manager import model_manager
    try:
        if model_id not in model_manager.available_models:
            return f"Error: Model '{model_id}' is not available."
        messages = [{"role": "user", "content": prompt}]
        response = ""
        async for chunk in model_manager.chat_stream(model_id, messages, temperature=0.7, max_tokens=4096):
            if chunk and not chunk.startswith("\n[Error"):
                response += chunk
        return response.strip() or "No response from model."
    except Exception as e:
        return f"Error asking model {model_id}: {str(e)}"





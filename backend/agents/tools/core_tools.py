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


async def execute_bash(command: str) -> str:
    """Run a bash command and return output."""
    try:
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
        
        output = port_warning  # Prepend port warning if any
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

async def read_file(path: str) -> str:
    """Read a file."""
    try:
        import aiofiles
        if not os.path.exists(path):
            return f"Error: File {path} not found."
        async def _read():
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                return await f.read()
        return await asyncio.wait_for(_read(), timeout=30.0)
    except asyncio.TimeoutError:
        return f"Error: Reading file {path} timed out after 30 seconds."
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        import aiofiles
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        async def _write():
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)
        await asyncio.wait_for(_write(), timeout=30.0)
        return f"Successfully wrote to {path}"
    except asyncio.TimeoutError:
        return f"Error: Writing file {path} timed out after 30 seconds."
    except Exception as e:
        return f"Error writing file {path}: {str(e)}"

async def write_multiple_files(files_data: list) -> str:
    """Write multiple files at once. files_data is a list of dicts: [{'path': '...', 'content': '...'}]"""
    try:
        import aiofiles
        results = []
        for file_obj in files_data:
            path = file_obj.get("path")
            content = file_obj.get("content", "")
            if not path:
                results.append(f"Skipped invalid entry: {file_obj}")
                continue
            
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                async with aiofiles.open(path, "w", encoding="utf-8") as f:
                    await f.write(content)
                results.append(f"Successfully wrote to {path}")
            except Exception as e:
                results.append(f"Error writing to {path}: {str(e)}")
        
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





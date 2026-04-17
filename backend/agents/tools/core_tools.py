import asyncio
import os


async def execute_bash(command: str) -> str:
    """Run a bash command and return output."""
    try:
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
                            # Kill process if it exceeds our cap to prevent background resource hogging
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
        
        output = ""
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





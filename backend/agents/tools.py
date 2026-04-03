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
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        output = ""
        if stdout:
            output += stdout.decode(errors="replace")
        if stderr:
            output += "\n[stderr]\n" + stderr.decode(errors="replace")
        return output.strip() or "Command executed successfully with no output."
    except asyncio.TimeoutError:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

async def read_file(path: str) -> str:
    """Read a file."""
    try:
        if not os.path.exists(path):
            return f"Error: File {path} not found."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
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


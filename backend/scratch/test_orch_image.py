import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path.parent / ".env")

from core.orchestrator import orchestrator
from core.model_manager import model_manager

async def test():
    await model_manager.startup()
    
    print("Sending message...")
    try:
        async for event in orchestrator.process(
            message="Buatkan saya gambar kucing",
            user_id="test",
            session_id="test",
            include_tool_logs=False,
            emit_thinking=False,
            auto_execute=True,
        ):
            print("Event:", event.type, event.content if event.type in ["chunk", "error"] else "")
    except Exception as e:
        print(f"Exception caught: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())

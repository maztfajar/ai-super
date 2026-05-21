import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.orchestrator import orchestrator

async def main():
    try:
        async for event in orchestrator.process(
            message="buatkan saya gambar cicak berkepala naga",
            user_id="test_user",
            session_id="test_session",
            system_prompt="You are a helpful assistant.",
            history=[],
            include_tool_logs=False,
            emit_thinking=False,
            auto_execute=True,
        ):
            print(f"Event: {event.type} -> {str(event.content)[:100] if event.content else event.data}")
    except Exception as e:
        print(f"FATAL EXCEPTION IN MAIN: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

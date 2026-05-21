import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.orchestrator import orchestrator
from core.request_preprocessor import TaskSpecification

async def main():
    try:
        spec = TaskSpecification(
            primary_intent="image_generation",
            is_simple=False,
            requires_multi_agent=False,
            complexity_score=0.1,
            original_message="buatkan saya gambar cicak berkepala naga"
        )
        async for event in orchestrator._handle_image_gen(
            spec=spec,
            system_prompt="You are a helpful assistant.",
            history=[]
        ):
            print(f"Event: {event.type} -> {str(event.content)[:100] if event.content else event.data}")
    except Exception as e:
        print(f"FATAL EXCEPTION IN MAIN: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

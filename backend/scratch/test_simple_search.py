import asyncio
import os
from core.orchestrator import Orchestrator

async def run_test():
    # Make sure we have mock or real env setup if needed
    orchestrator = Orchestrator()
    print("Testing Orchestrator process with force_simple=True...")
    
    events = []
    async for event in orchestrator.process(
        message="Berita terbaru hari ini",
        user_id="test_user",
        session_id="test_session",
        force_simple=True,
    ):
        events.append(event)
        print(f"Event: {event.type} | Content: {event.content} | Data: {event.data}")

if __name__ == "__main__":
    asyncio.run(run_test())

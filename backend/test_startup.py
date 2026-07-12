import asyncio
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from main import app, lifespan

async def test_startup():
    print("Testing application startup...")
    try:
        async with lifespan(app):
            print("Lifespan started successfully!")
            await asyncio.sleep(2)
            print("Shutting down...")
        print("Startup test PASS.")
    except Exception as e:
        print(f"Startup test FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_startup())

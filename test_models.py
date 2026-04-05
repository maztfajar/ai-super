import asyncio
from backend.core.model_manager import model_manager

async def test():
    await model_manager.startup()
    print(model_manager.available_models)

asyncio.run(test())

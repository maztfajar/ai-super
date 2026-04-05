import asyncio
import os
from core.model_manager import model_manager

async def test():
    res = await model_manager.chat_completion("sumopod/gpt-5-nano", [{"role": "user", "content": "mana?"}])
    print(f"RESULT: {repr(res)}")

asyncio.run(test())

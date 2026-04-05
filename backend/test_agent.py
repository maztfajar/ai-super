import asyncio
from core.smart_router import smart_router
from agents.executor import agent_executor

async def test():
    messages = [{"role": "user", "content": "tolong cek memory RAM server inii"}]
    model = "sumopod/seed-2-0-pro"
    
    async for chunk in agent_executor.stream_chat(base_model=model, messages=messages, temperature=0.4):
        print(chunk, end="", flush=True)

asyncio.run(test())

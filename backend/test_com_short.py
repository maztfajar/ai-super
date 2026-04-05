import asyncio
from core.model_manager import model_manager

async def test():
    raw_result = 'Maksudnya?'
    com_messages = [
        {"role": "system", "content": "You are AL FATIH Communicator. Your strict rule: Rewrite the provided content into clear, professional Bahasa Indonesia. Do not change facts, just act as the formatter/communicator."},
        {"role": "user", "content": f"FORMAT THIS CONTENT FOR THE USER:\n\n{raw_result}"}
    ]
    res = await model_manager.chat_completion("sumopod/seed-2-0-pro", com_messages)
    print(f"COMMUNICATOR RESULT:\n{res}")

asyncio.run(test())

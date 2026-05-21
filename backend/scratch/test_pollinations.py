import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.model_manager import model_manager

async def main():
    try:
        messages = [{"role": "user", "content": "buatkan saya gambar cicak berkepala naga"}]
        async for chunk in model_manager.chat_stream(
            model="pollinations/flux",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        ):
            print(f"Chunk: {chunk}")
    except Exception as e:
        print(f"FATAL EXCEPTION: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

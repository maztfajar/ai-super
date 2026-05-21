import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.model_manager import model_manager

async def main():
    chunks = []
    try:
        async for chunk in model_manager.chat_stream(
            model="gemini/gemini-2.5-flash-lite",
            messages=[
                {"role": "system", "content": "Kamu adalah asisten yang membantu."},
                {"role": "user", "content": "Katakan: HELLO WORLD"}
            ],
            temperature=0.2,
            max_tokens=100
        ):
            chunks.append(chunk)
            print(f"Chunk: {chunk[:60]}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
    
    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Full response: {''.join(str(c) for c in chunks)[:200]}")

if __name__ == "__main__":
    asyncio.run(main())

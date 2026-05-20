import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from core.model_manager import model_manager

async def test():
    await model_manager.startup()
    
    # Simulate _handle_image_gen fallback
    image_model = "sumopod/gpt-5-mini" # or whatever
    messages = [{"role": "user", "content": "Buatkan saya gambar kucing"}]
    
    try:
        async for chunk in model_manager.chat_stream(
            model=image_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        ):
            print("Chunk:", repr(chunk))
    except Exception as e:
        print(f"Exception caught: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())

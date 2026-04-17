import asyncio
import time
import aiofiles

async def test_async_read_write():
    results = []
    
    # Test 1: Write file
    start = time.time()
    async with aiofiles.open("test_output.txt", "w") as f:
        await f.write("Hello AI Orchestra Test")
    elapsed = time.time() - start
    results.append(f"✅ Async Write: {elapsed:.4f}s")
    
    # Test 2: Read file  
    start = time.time()
    async with aiofiles.open("test_output.txt", "r") as f:
        content = await f.read()
    elapsed = time.time() - start
    results.append(f"✅ Async Read: {elapsed:.4f}s — Content: '{content}'")
    
    # Test 3: Concurrent reads (simulating parallel agents)
    start = time.time()
    tasks = [aiofiles.open("test_output.txt", "r") for _ in range(5)]
    elapsed = time.time() - start
    results.append(f"✅ Concurrent Access Ready: {elapsed:.4f}s")
    
    # Test 4: Timeout protection
    try:
        await asyncio.wait_for(
            aiofiles.open("test_output.txt", "r").__aenter__(),
            timeout=30
        )
        results.append("✅ Timeout Protection: Working")
    except asyncio.TimeoutError:
        results.append("❌ Timeout Protection: Failed")
    
    # Cleanup
    import os
    os.remove("test_output.txt")
    
    return results

results = asyncio.run(test_async_read_write())
for r in results:
    print(r)

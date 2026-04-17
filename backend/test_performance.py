import asyncio, time, sys
sys.path.insert(0, '.')

async def benchmark():
    print("═══ Performance Benchmark ═══")
    
    # Benchmark 1: Async vs Sync file operations
    import aiofiles
    
    # Async write speed
    start = time.time()
    for i in range(10):
        async with aiofiles.open(f"bench_{i}.txt", "w") as f:
            await f.write("x" * 10000)
    async_write_time = time.time() - start
    print(f"✅ Async write x10: {async_write_time:.3f}s")
    
    # Async read speed  
    start = time.time()
    tasks = [aiofiles.open(f"bench_{i}.txt", "r") for i in range(10)]
    async_read_time = time.time() - start
    print(f"✅ Concurrent read setup x10: {async_read_time:.4f}s")
    
    # Sync write speed (comparison)
    start = time.time()
    for i in range(10):
        with open(f"bench_sync_{i}.txt", "w") as f:
            f.write("x" * 10000)
    sync_write_time = time.time() - start
    print(f"📊 Sync write x10: {sync_write_time:.3f}s")
    
    improvement = ((sync_write_time - async_write_time) / sync_write_time) * 100
    print(f"⚡ Performance improvement: {improvement:.1f}%")
    
    # Cleanup
    import os
    for i in range(10):
        try: os.remove(f"bench_{i}.txt")
        except: pass
        try: os.remove(f"bench_sync_{i}.txt")
        except: pass

asyncio.run(benchmark())

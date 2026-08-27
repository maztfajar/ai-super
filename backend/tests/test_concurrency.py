import asyncio
import os
import tempfile
import pytest
from core.concurrency import FileLock, DatabaseWriteQueue, ResourceSemaphore, OptimisticLockMixin, OptimisticLockError

@pytest.mark.asyncio
async def test_file_lock_concurrent_access():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_concurrent.txt")
        counter = 0
        
        async def worker():
            nonlocal counter
            async with FileLock(test_file, timeout=5.0):
                # Read, modify, write
                current = counter
                await asyncio.sleep(0.01)
                counter = current + 1
        
        # Run 5 concurrent workers
        await asyncio.gather(*[worker() for _ in range(5)])
        assert counter == 5

@pytest.mark.asyncio
async def test_database_write_queue():
    queue = DatabaseWriteQueue()
    await queue.start()
    
    results = []
    
    async def write_op(val: int):
        await asyncio.sleep(0.005)
        results.append(val)
        return val * 2
    
    # Submit multiple concurrent writes
    futures = [queue.submit(write_op, i) for i in range(5)]
    res = await asyncio.gather(*futures)
    
    assert res == [0, 2, 4, 6, 8]
    assert len(results) == 5
    assert queue.stats["processed"] == 5
    
    await queue.stop()

@pytest.mark.asyncio
async def test_resource_semaphore():
    sem = ResourceSemaphore()
    sem.configure("test_res", max_concurrent=2)
    
    active = 0
    max_observed = 0
    
    async def worker():
        nonlocal active, max_observed
        async with sem.acquire("test_res", max_concurrent=2):
            active += 1
            max_observed = max(max_observed, active)
            await asyncio.sleep(0.02)
            active -= 1
            
    await asyncio.gather(*[worker() for _ in range(5)])
    assert max_observed <= 2

def test_optimistic_lock_mixin():
    class Item(OptimisticLockMixin):
        def __init__(self, name: str):
            self.name = name
            self.version = 1
            
    item = Item("test")
    item.check_and_increment_version(expected_version=1)
    assert item.version == 2
    
    # Version mismatch raises error
    with pytest.raises(OptimisticLockError):
        item.check_and_increment_version(expected_version=1)

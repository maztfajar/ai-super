import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_stability():
    print("--- Testing Tool Imports and Datetime ---")
    try:
        from agents.tools.filesystem import list_directory
        from agents.tools.web_search import web_search
        
        # Test list_directory (triggers datetime)
        print("Testing list_directory...")
        res_fs = await list_directory(".")
        print(f"FS Result Length: {len(res_fs)}")
        
        # Test web_search (triggers datetime)
        print("Testing web_search (mock/skip if no key)...")
        # Just check if it imports and can be called
        print("Tool imports OK.")
        
    except Exception as e:
        print(f"FAILED Tool Test: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n--- Testing AgentExecutor Initialization ---")
    try:
        from agents.executor import AgentExecutor
        executor = AgentExecutor()
        
        # Test stream_chat initialization (triggers system prompt building)
        print("Testing stream_chat generator initialization...")
        # We don't actually run it against a real model here to avoid cost/delay,
        # but we check if the setup code (Phase 0-6) works.
        
        # Mock model_manager to avoid real API calls
        from unittest.mock import MagicMock
        import core.model_manager
        original_mm = core.model_manager.model_manager
        core.model_manager.model_manager = MagicMock()
        
        async def mock_chat_stream(*args, **kwargs):
            yield "Test chunk"
        
        core.model_manager.model_manager.chat_stream = mock_chat_stream
        
        gen = executor.stream_chat(
            base_model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            session_id="test-session-123",
            execution_mode="chat" # Use chat to avoid planning phase complexity in test
        )
        
        async for chunk in gen:
            print(f"Gen chunk: {chunk}")
            break
            
        print("AgentExecutor stream test OK.")
        core.model_manager.model_manager = original_mm
        
    except Exception as e:
        print(f"FAILED AgentExecutor Test: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ ALL STABILITY TESTS PASSED")
    return True

if __name__ == "__main__":
    asyncio.run(test_stability())

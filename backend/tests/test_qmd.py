import pytest
from core.qmd import QueryMessageDistiller, QMDResult

def test_qmd_short_messages_bypass():
    distiller = QueryMessageDistiller()
    messages = [
        {"role": "system", "content": "You are an AI assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there! How can I help?"},
    ]
    distilled, result = distiller.distill(messages, query="Hello", max_token_budget=3500)
    assert len(distilled) == len(messages)
    assert result.distilled_messages == 3
    assert result.dropped_messages == 0

def test_qmd_long_messages_distillation():
    distiller = QueryMessageDistiller()
    
    # Create large synthetic history
    messages = [{"role": "system", "content": "You are an AI assistant specialized in Python."}]
    
    for i in range(25):
        messages.append({"role": "user", "content": f"Topic {i}: Tell me about something completely unrelated to databases." * 20})
        messages.append({"role": "assistant", "content": f"Response {i}: Here is some unrelated information." * 20})
    
    # Relevant message deep in history
    messages.insert(5, {"role": "user", "content": "How do I configure PostgreSQL connection pool in Python?"})
    messages.insert(6, {"role": "assistant", "content": "Use asyncpg.create_pool(min_size=5, max_size=20) with DATABASE_URL."})
    
    # Recent message
    messages.append({"role": "user", "content": "Can you give me the connection pool code for PostgreSQL?"})
    
    query = "PostgreSQL connection pool asyncpg"
    distilled, result = distiller.distill(messages, query=query, max_token_budget=1000)
    
    assert len(distilled) < len(messages)
    assert result.dropped_messages > 0
    assert result.original_tokens_est > result.distilled_tokens_est
    
    # Ensure system prompt is preserved
    assert distilled[0]["role"] == "system"
    # Ensure recent message is preserved
    assert distilled[-1]["role"] == "user"

def test_qmd_code_block_detection():
    distiller = QueryMessageDistiller()
    assert distiller._is_code_heavy("```python\nprint('hello')\n```") is True
    assert distiller._is_code_heavy("Just normal text explaining some concepts without any code.") is False

import json, re, sys
sys.path.insert(0, '.')

# Import the fixed parser from executor
from agents.executor import AgentExecutor

executor = AgentExecutor.__new__(AgentExecutor)

test_cases = [
    # (input, expected_name, description)
    ('{"name": "web_search", "args": {"query": "test"}}', 
     "web_search", "Normal JSON"),
    
    ("{'name': 'read_file', 'args': {'path': 'test.txt'}}", 
     "read_file", "Single quotes JSON"),
    
    ('{"name": "write_file", "args": {"path": "out.txt",},}', 
     "write_file", "Trailing comma JSON"),
    
    ('Some text before {"name": "ask_model", "args": {}} some text after', 
     "ask_model", "JSON embedded in text"),
    
    ('{"name": "execute_bash", "args": {"command": "ls"}}   ', 
     "execute_bash", "JSON with whitespace"),
    
    ("completely broken text no json here", 
     None, "Invalid input - should return None"),
    
    ('{"name": "web_search", "args": {"query": "hello world"}}', 
     "web_search", "Standard valid JSON"),
]

print("═══ JSON Parser Test Results ═══")
passed = 0
failed = 0

for i, (input_text, expected_name, desc) in enumerate(test_cases):
    result = executor._safe_parse_tool_json(input_text)
    
    if expected_name is None:
        if result is None:
            print(f"✅ Test {i+1}: {desc} — Correctly returned None")
            passed += 1
        else:
            print(f"❌ Test {i+1}: {desc} — Should be None but got: {result}")
            failed += 1
    else:
        if result and result.get("name") == expected_name:
            print(f"✅ Test {i+1}: {desc} — Parsed correctly: {result}")
            passed += 1
        else:
            print(f"❌ Test {i+1}: {desc} — Expected '{expected_name}' but got: {result}")
            failed += 1

print(f"\\n📊 JSON Parser Score: {passed}/{len(test_cases)} passed")

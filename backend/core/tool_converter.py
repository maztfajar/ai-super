import json
import copy

def openai_to_anthropic_tools(openai_tools: list) -> list:
    """Convert OpenAI tool schema to Anthropic tool schema."""
    if not openai_tools:
        return []
    anthropic_tools = []
    for tool in openai_tools:
        if tool.get("type") == "function":
            fn = tool["function"]
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
            })
    return anthropic_tools

def openai_to_gemini_tools(openai_tools: list) -> list:
    """Convert OpenAI tool schema to Gemini tool schema (dicts)."""
    if not openai_tools:
        return None
    gemini_tools = []
    for tool in openai_tools:
        if tool.get("type") == "function":
            fn = tool["function"]
            
            # Gemini function declarations need specific format
            params = copy.deepcopy(fn.get("parameters", {}))
            
            gemini_tools.append({
                "function_declarations": [{
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": params
                }]
            })
    return gemini_tools

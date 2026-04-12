from .core_tools import execute_bash, read_file, write_file, ask_model
from .web_search import web_search

# Mapping of tool names to callable functions for the orchestrator
TOOLS = {
    "execute_bash": execute_bash,
    "read_file": read_file,
    "write_file": write_file,
    "ask_model": ask_model,
    "web_search": web_search,
}

__all__ = ["TOOLS"]

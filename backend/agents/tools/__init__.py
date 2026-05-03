from .core_tools import execute_bash, read_file, write_file, write_multiple_files, ask_model, find_safe_port, list_dir, search_files
from .web_search import web_search

# Mapping of tool names to callable functions for the orchestrator
TOOLS = {
    "execute_bash": execute_bash,
    "read_file": read_file,
    "write_file": write_file,
    "write_multiple_files": write_multiple_files,
    "ask_model": ask_model,
    "web_search": web_search,
    "find_safe_port": find_safe_port,
    "list_dir": list_dir,
    "search_files": search_files,
}

__all__ = ["TOOLS"]

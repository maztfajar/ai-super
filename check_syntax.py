import py_compile
import sys
import traceback

files = [
    "backend/agents/executor.py",
    "backend/core/orchestrator.py",
    "backend/api/chat.py",
    "backend/main.py"
]

out = ""
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        out += f"{f}: OK\n"
    except Exception as e:
        out += f"{f}: ERROR\n{traceback.format_exc()}\n"

with open("/home/bamuskal/Documents/ai-super/compile_check.txt", "w") as f:
    f.write(out)

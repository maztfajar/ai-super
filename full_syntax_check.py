import py_compile
import os
import sys

root = "backend"
errors = []

for dirpath, dirnames, filenames in os.walk(root):
    if "venv" in dirpath or "__pycache__" in dirpath:
        continue
    for filename in filenames:
        if filename.endswith(".py"):
            filepath = os.path.join(dirpath, filename)
            try:
                py_compile.compile(filepath, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"Syntax Error in {filepath}:\n{str(e)}")
            except Exception as e:
                errors.append(f"Error in {filepath}: {str(e)}")

if errors:
    with open("syntax_errors.txt", "w") as f:
        f.write("\n\n".join(errors))
    print(f"Found {len(errors)} syntax errors. Check syntax_errors.txt")
    sys.exit(1)
else:
    print("No syntax errors found.")

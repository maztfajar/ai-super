import ast
import os
import sys

def check_syntax(directory):
    has_error = False
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        source = f.read()
                    ast.parse(source, filename=filepath)
                except SyntaxError as e:
                    print(f"SyntaxError in {filepath}: {e}")
                    has_error = True
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    if has_error:
        sys.exit(1)
    else:
        print("All files passed syntax check.")

check_syntax('/home/bamuskal/Documents/ai-super/backend')

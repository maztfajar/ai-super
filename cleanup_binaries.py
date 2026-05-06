import os

def cleanup():
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc') or file.endswith('.pyo') or '__pycache__' in root:
                filepath = os.path.join(root, file)
                try:
                    os.remove(filepath)
                    print(f"Removed {filepath}")
                except Exception as e:
                    print(f"Failed to remove {filepath}: {e}")

if __name__ == "__main__":
    cleanup()

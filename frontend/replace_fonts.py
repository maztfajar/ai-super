import os

directory = '/home/bamuskal/Documents/ai-super/frontend/src'

for root, dirs, files in os.walk(directory):
    for filename in files:
        if filename.endswith(('.jsx', '.js', '.css', '.html')):
            filepath = os.path.join(root, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # First change font-bold to font-semibold
            new_content = content.replace('font-bold', 'font-semibold')
            # Then change font-black to font-bold
            new_content = new_content.replace('font-black', 'font-bold')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f"Updated {filepath}")

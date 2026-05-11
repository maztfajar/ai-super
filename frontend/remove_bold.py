import os
import re

directory = '/home/bamuskal/Documents/ai-super/frontend/src'

for root, dirs, files in os.walk(directory):
    for filename in files:
        if filename.endswith(('.jsx', '.js', '.css', '.html')):
            filepath = os.path.join(root, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Ganti semua font weight yang tebal menjadi medium atau normal
            new_content = re.sub(r'\bfont-bold\b', 'font-medium', content)
            new_content = re.sub(r'\bfont-semibold\b', 'font-normal', new_content)
            new_content = re.sub(r'\bfont-black\b', 'font-medium', new_content)
            
            # Clean up spaces
            new_content = new_content.replace('font-normal', '') # Remove font-normal entirely as it's default
            new_content = re.sub(r' +', ' ', new_content) # collapse multiple spaces
            new_content = new_content.replace(' "', '"').replace('" ', '"').replace(" '", "'").replace("' ", "'")
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f"Updated {filepath}")

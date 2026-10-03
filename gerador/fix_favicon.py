import os, glob

for file_path in glob.glob('templates/*.html'):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace('type="image/svg+xml"', 'type="image/webp"')
        
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated type in {file_path}')

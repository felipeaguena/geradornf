import glob

for file_path in glob.glob('templates/*.html'):
    if 'portal.html' in file_path:
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '<link href="/static/img/brand/nftlogo.webp" rel="icon"' not in content:
        new_content = content.replace('<head>', '<head>\n    <!-- Favicon -->\n    <link href="/static/img/brand/nftlogo.webp" rel="icon" type="image/webp"/>')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Added favicon to {file_path}')

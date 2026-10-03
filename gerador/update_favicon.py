import os, glob

for file_path in glob.glob('templates/*.html'):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substituir o href no link do favicon
    new_content = content.replace(
        '<link href="/static/img/brand/NFT%20Logo%20(3).webp" rel="icon"', 
        '<link href="/static/img/brand/nftlogo.webp" rel="icon"'
    )
        
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated favicon in {file_path}')

import glob
import re

for f in glob.glob('gerador/templates/*.html'):
    c = open(f, encoding='utf-8').read()
    new_c = re.sub(r'<script\s+src=[\"\']/static/js/nft-sidebar\.js(\?[^\"\']*)?[\"\']\s*></script>', '<script defer src="/static/js/nft-sidebar.js?v=2.5"></script>', c)
    if new_c != c:
        open(f, 'w', encoding='utf-8').write(new_c)
        print('Updated defer in:', f)

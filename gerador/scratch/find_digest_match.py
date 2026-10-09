from lxml import etree
import hashlib
import base64

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'rb') as f:
    raw = f.read()

# Let's check sub-slices or substrings
target = b'Ok9T74tq4YwcUbvvon5YV3MuCG8='
doc = etree.fromstring(raw)
for el in doc.iter():
    for excl in [False, True]:
        for comm in [False, True]:
            try:
                c = etree.tostring(el, method='c14n', exclusive=excl, with_comments=comm)
                d = base64.b64encode(hashlib.sha1(c).digest())
                if d == target:
                    print(f"FOUND MATCH in element {el.tag}, excl={excl}, comm={comm}!")
            except Exception:
                pass

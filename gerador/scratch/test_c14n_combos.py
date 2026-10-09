from lxml import etree
import hashlib
import base64

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

doc = etree.fromstring(xml_str.encode('utf-8'))
inf = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

# Try different C14N methods on inf
for excl in [False, True]:
    for comm in [False, True]:
        b = etree.tostring(inf, method='c14n', exclusive=excl, with_comments=comm)
        d = base64.b64encode(hashlib.sha1(b).digest()).decode()
        print(f"excl={excl}, comm={comm}: {d}")

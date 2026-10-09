from lxml import etree

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'rb') as f:
    raw = f.read()

doc = etree.fromstring(raw)
inf = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
for child in list(inf):
    print("Child:", child.tag)
    for sub in list(child)[:3]:
        print("  Subchild:", sub.tag)

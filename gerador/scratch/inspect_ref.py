import xmlsec
from lxml import etree
import hashlib
import base64

# Let's inspect how xmlsec transforms the reference in last_290.xml
with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

doc = etree.fromstring(xml_str.encode('utf-8'))
xmlsec.tree.add_ids(doc, ['Id'])
sig = doc.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')

# Let's check the infNFe element in doc
inf = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

# Let's see what transforms are in the signature:
ref = sig.find('.//{http://www.w3.org/2000/09/xmldsig#}Reference')
print("Reference URI:", ref.attrib.get('URI'))
for t in ref.findall('.//{http://www.w3.org/2000/09/xmldsig#}Transform'):
    print("Transform:", t.attrib.get('Algorithm'))

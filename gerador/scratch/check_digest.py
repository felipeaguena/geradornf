from lxml import etree
import hashlib
import base64
import re

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

# 1. Clean out existing Signature
xml_no_sig = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_str, flags=re.DOTALL)
xml_no_sig = re.sub(r'<Signature.*?</Signature>', '', xml_no_sig, flags=re.DOTALL)
xml_no_sig = xml_no_sig.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')

doc = etree.fromstring(xml_no_sig.encode('utf-8'))
inf = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
c14n_inf = etree.tostring(inf, method='c14n', exclusive=False, with_comments=False)
digest = base64.b64encode(hashlib.sha1(c14n_inf).digest()).decode()

print('Direct C14N digest without ds on root:', digest)
print('First 100 bytes direct C14N:', c14n_inf[:100])
print('Digest in last_290.xml was: Ok9T74tq4YwcUbvvon5YV3MuCG8=')
print('Matches original digest?', digest == 'Ok9T74tq4YwcUbvvon5YV3MuCG8=')

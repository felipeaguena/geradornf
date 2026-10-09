from lxml import etree
import re
import hashlib
import base64

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

xml_clean = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_str, flags=re.DOTALL)
xml_clean = xml_clean.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')

doc = etree.fromstring(xml_clean.encode('utf-8'))
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

c14n_incl = etree.tostring(inf_nfe, method='c14n', exclusive=False, with_comments=False)
c14n_excl = etree.tostring(inf_nfe, method='c14n', exclusive=True, with_comments=False)

print("INCL length:", len(c14n_incl))
print("EXCL length:", len(c14n_excl))
print("INCL first 150 bytes:", c14n_incl[:150])
print("EXCL first 150 bytes:", c14n_excl[:150])
print("Diff at start:", set(c14n_incl[:150]) ^ set(c14n_excl[:150]))

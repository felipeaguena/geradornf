import xmlsec
from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
_, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
pem_c = certificate.public_bytes(serialization.Encoding.PEM)

def verify_xml(xml_string, name):
    doc = etree.fromstring(xml_string.encode('utf-8'))
    xmlsec.tree.add_ids(doc, ['Id'])
    node = doc.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
    if node is None:
        print(f"[{name}] Signature node not found")
        return
    ctx = xmlsec.SignatureContext()
    key = xmlsec.Key.from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)
    ctx.key = key
    try:
        ctx.verify(node)
        print(f"[{name}] VERIFY SUCCESS!")
    except Exception as e:
        print(f"[{name}] VERIFY FAILED: {e}")

# 1. Test last_290.xml
with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    verify_xml(f.read(), "last_290.xml")

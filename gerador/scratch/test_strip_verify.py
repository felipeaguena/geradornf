import xmlsec
from lxml import etree
import re
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
pem_c = certificate.public_bytes(serialization.Encoding.PEM)

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

xml_clean = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_str, flags=re.DOTALL)
xml_clean = xml_clean.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')

doc = etree.fromstring(xml_clean.encode('utf-8'))
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
ref_id = inf_nfe.attrib.get('Id', '')
xmlsec.tree.add_ids(doc, ['Id'])

sig = xmlsec.template.create(doc, xmlsec.constants.TransformInclC14N, xmlsec.constants.TransformRsaSha1, ns=None)
doc.append(sig)

ref = xmlsec.template.add_reference(sig, xmlsec.constants.TransformSha1, uri='#' + ref_id)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)

ki = xmlsec.template.ensure_key_info(sig)
xmlsec.template.add_x509_data(ki)

key = xmlsec.Key.from_memory(pem_k, xmlsec.constants.KeyDataFormatPem)
key.load_cert_from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)

ctx = xmlsec.SignatureContext()
ctx.key = key
ctx.sign(sig)

xml_assinado = etree.tostring(doc, encoding='utf-8').decode('utf-8')
print("--- RAW SIGNED XML AROUND SIGNATURE ---")
sig_idx = xml_assinado.find('<Signature')
print(xml_assinado[sig_idx:sig_idx+400])

# Now verify what happens if we verify xml_assinado as is vs with replace('\n', '')
def check_ver(s, label):
    d = etree.fromstring(s.encode('utf-8'))
    xmlsec.tree.add_ids(d, ['Id'])
    sn = d.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
    c = xmlsec.SignatureContext()
    c.key = xmlsec.Key.from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)
    try:
        c.verify(sn)
        print(f"[{label}] VERIFY: SUCCESS")
    except Exception as e:
        print(f"[{label}] VERIFY: FAILED ({e})")

check_ver(xml_assinado, "raw xml_assinado")
check_ver(xml_assinado.replace('\n', '').replace('\r', '').strip(), "stripped xml_assinado")

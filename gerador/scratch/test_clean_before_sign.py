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
xml_clean = xml_clean.replace('\n', '').replace('\r', '').strip()

doc = etree.fromstring(xml_clean.encode('utf-8'))
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
ref_id = inf_nfe.attrib.get('Id', '')
xmlsec.tree.add_ids(doc, ['Id'])

# Create Signature template with ns=None
sig = xmlsec.template.create(doc, xmlsec.constants.TransformInclC14N, xmlsec.constants.TransformRsaSha1, ns=None)
doc.append(sig)

ref = xmlsec.template.add_reference(sig, xmlsec.constants.TransformSha1, uri='#' + ref_id)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)

ki = xmlsec.template.ensure_key_info(sig)
xmlsec.template.add_x509_data(ki)

# Check: Why does xmlsec put whitespace/newlines inside sig?
# In lxml/libxml2, each element created by xmlsec might have text or tail with \n.
# Let's see: what if we strip all text/tail whitespace inside sig BEFORE signing?
for el in sig.iter():
    if el.text and el.text.isspace():
        el.text = None
    if el.tail and el.tail.isspace():
        el.tail = None

key = xmlsec.Key.from_memory(pem_k, xmlsec.constants.KeyDataFormatPem)
key.load_cert_from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)

ctx = xmlsec.SignatureContext()
ctx.key = key
ctx.sign(sig)

# After signing, also check if SignatureValue or X509Certificate has whitespace
# Note: Base64 in XML can have whitespace according to XML schema, BUT SEFAZ 588 rejects \n between tags.
# Does \n inside SignatureValue text count as 'entre as tags'?
# In SignatureValue, the \n is INSIDE the text content of <SignatureValue>!
# BUT let's see what etree.tostring produces:
xml_assinado = etree.tostring(doc, encoding='utf-8').decode('utf-8')
print("Contains newlines?", '\n' in xml_assinado)

# Let's test verify on xml_assinado
d = etree.fromstring(xml_assinado.encode('utf-8'))
xmlsec.tree.add_ids(d, ['Id'])
sn = d.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
c = xmlsec.SignatureContext()
c.key = xmlsec.Key.from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)
try:
    c.verify(sn)
    print("VERIFY:", "SUCCESS")
except Exception as e:
    print("VERIFY FAILED:", e)

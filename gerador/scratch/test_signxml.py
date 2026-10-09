from signxml import XMLSigner, methods
from lxml import etree
import re
from cryptography.hazmat.primitives.serialization import pkcs12

XMLSigner.check_deprecated_methods = lambda self: None

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

xml_clean = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_str, flags=re.DOTALL)
xml_clean = xml_clean.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')

doc = etree.fromstring(xml_clean.encode('utf-8'))
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
ref_id = inf_nfe.attrib.get('Id', '')

signer = XMLSigner(
    method=methods.enveloped,
    signature_algorithm="rsa-sha1",
    digest_algorithm="sha1",
    c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
)

signed_root = signer.sign(
    doc,
    key=private_key,
    cert=[certificate],
    reference_uri='#' + ref_id
)

signed_str = etree.tostring(signed_root, encoding='utf-8').decode('utf-8')
dv = signed_root.find('.//{http://www.w3.org/2000/09/xmldsig#}DigestValue').text
print('SignXML DigestValue:', dv)
print('Direct INCLUSIVE C14N was: f+Nj2A6FZtS1t3+BhIsjyvzK3Uk=')
print('Matches INCLUSIVE?', dv == 'f+Nj2A6FZtS1t3+BhIsjyvzK3Uk=')
print('Signed snippet:\n', signed_str[:200])
print('Signature snippet:\n', signed_str[-400:])

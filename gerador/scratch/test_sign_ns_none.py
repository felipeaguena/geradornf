import xmlsec
from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
pem_c = certificate.public_bytes(serialization.Encoding.PEM)

xml_str = '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe35260847998441000198550010000008961652507640"><ide><cUF>35</cUF></ide></infNFe></NFe>'
doc = etree.fromstring(xml_str.encode('utf-8'))
xmlsec.tree.add_ids(doc, ['Id'])

sig = xmlsec.template.create(doc, xmlsec.constants.TransformInclC14N, xmlsec.constants.TransformRsaSha1, ns=None)
doc.append(sig)

ref = xmlsec.template.add_reference(sig, xmlsec.constants.TransformSha1, uri='#NFe35260847998441000198550010000008961652507640')
xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)

ki = xmlsec.template.ensure_key_info(sig)
xmlsec.template.add_x509_data(ki)

key = xmlsec.Key.from_memory(pem_k, xmlsec.constants.KeyDataFormatPem)
key.load_cert_from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)

ctx = xmlsec.SignatureContext()
ctx.key = key
ctx.sign(sig)

res = etree.tostring(doc, encoding='utf-8').decode('utf-8')
print('Result:\n', res)

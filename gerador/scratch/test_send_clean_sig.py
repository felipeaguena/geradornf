import os
import requests
import tempfile
import xmlsec
from lxml import etree
import urllib3
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

# 1. Load cert and key
with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
pem_c = certificate.public_bytes(serialization.Encoding.PEM)

# 2. Read last_290.xml, strip existing signature and xmlns:ds
with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

doc = etree.fromstring(xml_str.encode('utf-8'))
for sig in doc.findall('.//{http://www.w3.org/2000/09/xmldsig#}Signature'):
    sig.getparent().remove(sig)

# Clean root namespaces to make sure no ds prefix remains on NFe
nfe_clean = etree.Element('{http://www.portalfiscal.inf.br/nfe}NFe', nsmap={None: 'http://www.portalfiscal.inf.br/nfe'})
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
nfe_clean.append(inf_nfe)

ref_id = inf_nfe.attrib.get('Id', '')
xmlsec.tree.add_ids(nfe_clean, ['Id'])

# Create Signature without prefix (ns=None)
sig = xmlsec.template.create(nfe_clean, xmlsec.constants.TransformInclC14N, xmlsec.constants.TransformRsaSha1, ns=None)
nfe_clean.append(sig)

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

# Clean string without line breaks
xml_assinado_limpo = etree.tostring(nfe_clean, encoding='utf-8').decode('utf-8').replace('\n', '').replace('\r', '').strip()

print("XML ASSINADO (PRIMEIROS 200 E ULTIMOS 400 CARACTERES):")
print(xml_assinado_limpo[:200])
print("...")
print(xml_assinado_limpo[-400:])

# 3. Enviar para SEFAZ
url = 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx'
soap_request = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
    '<soap12:Header>'
    '<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">'
    '<cUF>35</cUF>'
    '<versaoDados>4.00</versaoDados>'
    '</nfeCabecMsg>'
    '</soap12:Header>'
    '<soap12:Body>'
    '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">'
    f'<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>1</idLote><indSinc>1</indSinc>{xml_assinado_limpo}</enviNFe>'
    '</nfeDadosMsg>'
    '</soap12:Body>'
    '</soap12:Envelope>'
)

headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as cert_file:
    cert_file.write(pem_k)
    cert_file.write(pem_c)
    pem_path = cert_file.name

try:
    response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=20)
    print("\nSTATUS HTTP:", response.status_code)
    print("RESPOSTA SEFAZ:\n", response.text)
finally:
    if os.path.exists(pem_path):
        os.unlink(pem_path)

import test_clean_before_sign as t
from lxml import etree
import xmlsec
import requests
import tempfile
import time

doc = etree.fromstring(t.xml_assinado.encode('utf-8'))
xmlsec.tree.add_ids(doc, ['Id'])

# Clean SignatureValue and X509Certificate to single-line Base64
sv_el = doc.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
if sv_el is not None and sv_el.text:
    sv_el.text = ''.join(sv_el.text.split())

cert_el = doc.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
if cert_el is not None and cert_el.text:
    cert_el.text = ''.join(cert_el.text.split())

for el in doc.iter():
    if el.text and el.text.isspace():
        el.text = None
    if el.tail and el.tail.isspace():
        el.tail = None

clean_xml_1line = etree.tostring(doc, encoding='utf-8').decode('utf-8').replace('\r', '').replace('\n', '')

# Test verify on clean_xml_1line
d = etree.fromstring(clean_xml_1line.encode('utf-8'))
xmlsec.tree.add_ids(d, ['Id'])
sn = d.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
c = xmlsec.SignatureContext()
c.key = xmlsec.Key.from_memory(t.pem_c, xmlsec.constants.KeyDataFormatCertPem)
try:
    c.verify(sn)
    print("VERIFY 1LINE: SUCCESS!")
except Exception as e:
    print("VERIFY 1LINE: FAILED:", e)

# Use dynamic idLote (timestamp)
id_lote = str(int(time.time()))[-8:]

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
    f'<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>{id_lote}</idLote><indSinc>1</indSinc>{clean_xml_1line}</enviNFe>'
    '</nfeDadosMsg>'
    '</soap12:Body>'
    '</soap12:Envelope>'
)

headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as cert_file:
    cert_file.write(t.pem_k)
    cert_file.write(t.pem_c)
    pem_path = cert_file.name

try:
    response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=20)
    print("\nSTATUS HTTP:", response.status_code)
    print("RESPOSTA SEFAZ:\n", response.text)
finally:
    if os.path.exists(pem_path):
        os.unlink(pem_path)

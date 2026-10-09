import requests
import tempfile
import os
import urllib3
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
pk, cert, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)

with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as f:
    f.write(pk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    f.write(cert.public_bytes(serialization.Encoding.PEM))
    pem_path = f.name

url = 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx'
soap = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
    '<soap12:Header>'
    '<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4">'
    '<cUF>35</cUF>'
    '<versaoDados>4.00</versaoDados>'
    '</nfeCabecMsg>'
    '</soap12:Header>'
    '<soap12:Body>'
    '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4">'
    '<consStatServ xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
    '<tpAmb>2</tpAmb>'
    '<cUF>35</cUF>'
    '<xServ>STATUS</xServ>'
    '</consStatServ>'
    '</nfeDadosMsg>'
    '</soap12:Body>'
    '</soap12:Envelope>'
)

headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
try:
    r = requests.post(url, data=soap.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=15)
    print('Status Code:', r.status_code)
    print('Response:', r.text)
finally:
    if os.path.exists(pem_path):
        os.unlink(pem_path)

import requests
import tempfile
import os
import urllib3
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from lxml import etree

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

headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}

results = {}

# 1. Testar Status Servico Producao
soap_status = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
    '<soap12:Header><nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4"><cUF>35</cUF><versaoDados>4.00</versaoDados></nfeCabecMsg></soap12:Header>'
    '<soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4"><consStatServ xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><tpAmb>1</tpAmb><cUF>35</cUF><xServ>STATUS</xServ></consStatServ></nfeDadosMsg></soap12:Body>'
    '</soap12:Envelope>'
)

try:
    r = requests.post('https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx', data=soap_status.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=12)
    root = etree.fromstring(r.content)
    cstat = root.findtext('.//{http://www.portalfiscal.inf.br/nfe}cStat')
    xmotivo = root.findtext('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
    results['NFeStatusServico4_PRODUCAO'] = {'http': r.status_code, 'cStat': cstat, 'xMotivo': xmotivo}
except Exception as e:
    results['NFeStatusServico4_PRODUCAO'] = {'error': str(e)}

# 2. Testar NFeAutorizacao4 Producao (ping de envelope sem lote para testar mTLS e recepcao)
soap_aut = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
    '<soap12:Header><nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"><cUF>35</cUF><versaoDados>4.00</versaoDados></nfeCabecMsg></soap12:Header>'
    '<soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"><enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>99999999</idLote><indSinc>1</indSinc></enviNFe></nfeDadosMsg></soap12:Body>'
    '</soap12:Envelope>'
)

try:
    r = requests.post('https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx', data=soap_aut.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=12)
    root = etree.fromstring(r.content)
    cstat = root.findtext('.//{http://www.portalfiscal.inf.br/nfe}cStat')
    xmotivo = root.findtext('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
    results['NFeAutorizacao4_PRODUCAO'] = {'http': r.status_code, 'cStat': cstat, 'xMotivo': xmotivo}
except Exception as e:
    results['NFeAutorizacao4_PRODUCAO'] = {'error': str(e)}

# 3. Testar NFeRecepcaoEvento4 Producao
soap_evt = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
    '<soap12:Header><nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><cUF>35</cUF><versaoDados>1.00</versaoDados></nfeCabecMsg></soap12:Header>'
    '<soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><idLote>99999999</idLote></envEvento></nfeDadosMsg></soap12:Body>'
    '</soap12:Envelope>'
)

try:
    r = requests.post('https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx', data=soap_evt.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=12)
    root = etree.fromstring(r.content)
    cstat = root.findtext('.//{http://www.portalfiscal.inf.br/nfe}cStat')
    xmotivo = root.findtext('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
    results['NFeRecepcaoEvento4_PRODUCAO'] = {'http': r.status_code, 'cStat': cstat, 'xMotivo': xmotivo}
except Exception as e:
    results['NFeRecepcaoEvento4_PRODUCAO'] = {'error': str(e)}

if os.path.exists(pem_path):
    os.unlink(pem_path)

import pprint
pprint.pprint(results)

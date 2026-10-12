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

try:
    for tpAmb, name, url in [
        (1, 'PRODUCAO', 'https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx'),
        (2, 'HOMOLOGACAO', 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx')
    ]:
        body_xml = f'<consStatServ xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><tpAmb>{tpAmb}</tpAmb><cUF>35</cUF><xServ>STATUS</xServ></consStatServ>'
        soap = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Header><nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4"><cUF>35</cUF><versaoDados>4.00</versaoDados></nfeCabecMsg></soap12:Header>'
            f'<soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4">{body_xml}</nfeDadosMsg></soap12:Body>'
            '</soap12:Envelope>'
        )
        try:
            r = requests.post(url, data=soap.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=12)
            root = etree.fromstring(r.content)
            cstat = root.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
            xmotivo = root.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
            tmed = root.find('.//{http://www.portalfiscal.inf.br/nfe}tMed')
            print(f"[{name} - tpAmb={tpAmb}] HTTP {r.status_code}")
            print(f"  cStat: {cstat.text if cstat is not None else 'N/A'}")
            print(f"  xMotivo: {xmotivo.text if xmotivo is not None else 'N/A'}")
            print(f"  Tempo Medio: {tmed.text if tmed is not None else 'N/A'}s")
        except Exception as e:
            print(f"[{name} - tpAmb={tpAmb}] ERRO: {e}")
finally:
    if os.path.exists(pem_path):
        os.unlink(pem_path)

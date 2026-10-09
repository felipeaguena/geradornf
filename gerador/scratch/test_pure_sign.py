import requests
import tempfile
import os
import hashlib
import base64
import re
from lxml import etree
import urllib3
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

# 1. Carregar certificado e chave privada
with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
pem_c = certificate.public_bytes(serialization.Encoding.PEM)

cert_b64 = base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode('ascii')

# 2. Ler last_290.xml limpo
with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

# Remover assinatura existente e xmlns:ds
xml_clean = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_str, flags=re.DOTALL)
xml_clean = re.sub(r'<Signature.*?</Signature>', '', xml_clean, flags=re.DOTALL)
xml_clean = xml_clean.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')

doc = etree.fromstring(xml_clean.encode('utf-8'))
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
ref_id = inf_nfe.attrib.get('Id', '')

# Canonicalizar o nó infNFe (C14N padrão W3C inclusivo)
c14n_inf = etree.tostring(inf_nfe, method='c14n', exclusive=False, with_comments=False)
digest_value = base64.b64encode(hashlib.sha1(c14n_inf).digest()).decode('ascii')
print(f"DigestValue calculado: {digest_value}")

# Montar SignedInfo
# Namespace padrão xmldsig
ns_ds = "http://www.w3.org/2000/09/xmldsig#"
signed_info_xml = (
    f'<SignedInfo xmlns="{ns_ds}">'
    '<CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
    '<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
    f'<Reference URI="#{ref_id}">'
    '<Transforms>'
    '<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
    '<Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
    '</Transforms>'
    '<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
    f'<DigestValue>{digest_value}</DigestValue>'
    '</Reference>'
    '</SignedInfo>'
)

signed_info_el = etree.fromstring(signed_info_xml.encode('utf-8'))
c14n_signed_info = etree.tostring(signed_info_el, method='c14n', exclusive=False, with_comments=False)

# Assinar o SignedInfo com RSA-SHA1
sig_bytes = private_key.sign(
    c14n_signed_info,
    padding.PKCS1v15(),
    hashes.SHA1()
)
signature_value = base64.b64encode(sig_bytes).decode('ascii')
print(f"SignatureValue calculado: {signature_value[:30]}...")

# Montar a tag <Signature>
signature_xml = (
    f'<Signature xmlns="{ns_ds}">'
    f'{signed_info_xml}'
    f'<SignatureValue>{signature_value}</SignatureValue>'
    '<KeyInfo>'
    '<X509Data>'
    f'<X509Certificate>{cert_b64}</X509Certificate>'
    '</X509Data>'
    '</KeyInfo>'
    '</Signature>'
)

signature_el = etree.fromstring(signature_xml.encode('utf-8'))
doc.append(signature_el)

xml_assinado_final = etree.tostring(doc, encoding='utf-8').decode('utf-8').replace('\n', '').replace('\r', '').strip()

print(f"Tamanho do XML final assinado: {len(xml_assinado_final)}")
print(f"Primeiros 150 chars: {xml_assinado_final[:150]}")
print(f"Últimos 200 chars: {xml_assinado_final[-200:]}")

# 3. Enviar para a SEFAZ
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
    f'<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>1</idLote><indSinc>1</indSinc>{xml_assinado_final}</enviNFe>'
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

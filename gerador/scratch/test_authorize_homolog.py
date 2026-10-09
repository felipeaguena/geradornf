import os
import requests
import tempfile
import time
from datetime import datetime, timezone, timedelta
from lxml import etree
import xmlsec
import urllib3
import re
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

with open(CERT_PATH, 'rb') as f:
    pfx_data = f.read()
private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
pem_c = certificate.public_bytes(serialization.Encoding.PEM)

def calcular_cdv(chave43):
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    p_idx = 0
    for ch in reversed(chave43):
        soma += int(ch) * pesos[p_idx % len(pesos)]
        p_idx += 1
    resto = soma % 11
    return 0 if resto in (0, 1) else 11 - resto

with open(r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml', 'r', encoding='utf-8') as f:
    xml_str = f.read()

xml_clean = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_str, flags=re.DOTALL)
xml_clean = re.sub(r'<Signature.*?</Signature>', '', xml_clean, flags=re.DOTALL)
xml_clean = xml_clean.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')

doc = etree.fromstring(xml_clean.encode('utf-8'))
inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

ide = inf_nfe.find('{http://www.portalfiscal.inf.br/nfe}ide')
tpAmb_el = ide.find('{http://www.portalfiscal.inf.br/nfe}tpAmb')
if tpAmb_el is not None: tpAmb_el.text = '2'

fuso_sp = timezone(timedelta(hours=-3))
now_sp = datetime.now(fuso_sp)
dh_str = now_sp.strftime('%Y-%m-%dT%H:%M:%S-03:00')
aamm = now_sp.strftime('%y%m')

dhEmi_el = ide.find('{http://www.portalfiscal.inf.br/nfe}dhEmi')
if dhEmi_el is not None: dhEmi_el.text = dh_str
dhSai_el = ide.find('{http://www.portalfiscal.inf.br/nfe}dhSaiEnt')
if dhSai_el is not None: dhSai_el.text = dh_str

nNF_el = ide.find('{http://www.portalfiscal.inf.br/nfe}nNF')
nnf_num = 903
if nNF_el is not None: nNF_el.text = str(nnf_num)

c_uf = "35"
cnpj = "47998441000198"
mod = "55"
serie = "1".zfill(3)
n_nf_9 = str(nnf_num).zfill(9)
tp_emis = "1"
c_nf_8 = str(int(time.time()))[-8:]
cNF_el = ide.find('{http://www.portalfiscal.inf.br/nfe}cNF')
if cNF_el is not None: cNF_el.text = c_nf_8

chave43 = f"{c_uf}{aamm}{cnpj}{mod}{serie}{n_nf_9}{tp_emis}{c_nf_8}"
cdv = calcular_cdv(chave43)
chave44 = f"{chave43}{cdv}"

cDV_el = ide.find('{http://www.portalfiscal.inf.br/nfe}cDV')
if cDV_el is not None: cDV_el.text = str(cdv)

ref_id = f"NFe{chave44}"
inf_nfe.attrib['Id'] = ref_id

dest = inf_nfe.find('{http://www.portalfiscal.inf.br/nfe}dest')
if dest is not None:
    xNome_dest = dest.find('{http://www.portalfiscal.inf.br/nfe}xNome')
    if xNome_dest is not None:
        xNome_dest.text = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
    
    # Corrigir cPais para 1600 (China)
    cPais_el = dest.find('.//{http://www.portalfiscal.inf.br/nfe}cPais')
    if cPais_el is not None:
        cPais_el.text = '1600'
    xPais_el = dest.find('.//{http://www.portalfiscal.inf.br/nfe}xPais')
    if xPais_el is not None:
        xPais_el.text = 'CHINA REPUBLICA POPULAR'

# Corrigir vUnTrib dos itens para bater exatamente com vProd (tolerância SEFAZ 0.01)
for det in inf_nfe.findall('{http://www.portalfiscal.inf.br/nfe}det'):
    prod = det.find('{http://www.portalfiscal.inf.br/nfe}prod')
    if prod is not None:
        v_prod = float(prod.find('{http://www.portalfiscal.inf.br/nfe}vProd').text)
        q_trib_el = prod.find('{http://www.portalfiscal.inf.br/nfe}qTrib')
        v_un_trib_el = prod.find('{http://www.portalfiscal.inf.br/nfe}vUnTrib')
        if q_trib_el is not None and v_un_trib_el is not None:
            q_trib = float(q_trib_el.text)
            if q_trib > 0:
                calc_v_un_trib = v_prod / q_trib
                # Se houver discrepância > 0.01, ajusta com 4 a 8 casas
                if abs(v_prod - round(q_trib * float(v_un_trib_el.text), 2)) > 0.01:
                    v_un_trib_el.text = f"{calc_v_un_trib:.8f}".rstrip('0').rstrip('.')

for el in doc.iter():
    if el.text and el.text.isspace(): el.text = None
    if el.tail and el.tail.isspace(): el.tail = None

xmlsec.tree.add_ids(doc, ['Id'])
sig = xmlsec.template.create(doc, xmlsec.constants.TransformInclC14N, xmlsec.constants.TransformRsaSha1, ns=None)
doc.append(sig)

ref = xmlsec.template.add_reference(sig, xmlsec.constants.TransformSha1, uri='#' + ref_id)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)

ki = xmlsec.template.ensure_key_info(sig)
xmlsec.template.add_x509_data(ki)

for el in sig.iter():
    if el.text and el.text.isspace(): el.text = None
    if el.tail and el.tail.isspace(): el.tail = None

key = xmlsec.Key.from_memory(pem_k, xmlsec.constants.KeyDataFormatPem)
key.load_cert_from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)

ctx = xmlsec.SignatureContext()
ctx.key = key
ctx.sign(sig)

sv_el = sig.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
if sv_el is not None and sv_el.text: sv_el.text = ''.join(sv_el.text.split())

cert_el = sig.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
if cert_el is not None and cert_el.text: cert_el.text = ''.join(cert_el.text.split())

for el in doc.iter():
    if el.text and el.text.isspace(): el.text = None
    if el.tail and el.tail.isspace(): el.tail = None

xml_assinado_1line = etree.tostring(doc, encoding='utf-8').decode('utf-8').replace('\r', '').replace('\n', '')

print("Chave gerada:", chave44)

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
    f'<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>{id_lote}</idLote><indSinc>1</indSinc>{xml_assinado_1line}</enviNFe>'
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
    response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, cert=pem_path, verify=False, timeout=25)
    print("\nSTATUS HTTP:", response.status_code)
    print("RESPOSTA SEFAZ:\n", response.text)
finally:
    if os.path.exists(pem_path):
        os.unlink(pem_path)

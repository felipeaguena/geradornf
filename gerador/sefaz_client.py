import os
import requests
import base64
from lxml import etree
from signxml import XMLSigner, methods

# Bypass check for deprecated methods to allow rsa-sha1 which is required by SEFAZ
XMLSigner.check_deprecated_methods = lambda self: None

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CERT_PATH = r'C:\Users\felipeaguena\Documents\XMLNFT\gerador\certificado\NFT_LOGISTICS_LTDA_47998441000198_1771873069312658700_nftcnpj.pfx'
CERT_PASS = b'nftecnpj'

def get_certificate_info():
    if not os.path.exists(CERT_PATH):
        return {'status': 'error', 'message': 'Arquivo PFX não encontrado'}
    
    try:
        with open(CERT_PATH, 'rb') as f:
            pfx_data = f.read()
            
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
        
        # Extrair CNPJ do Subject se possível
        subject = certificate.subject.rfc4514_string()
        issuer = certificate.issuer.rfc4514_string()
        
        cnpj = ""
        m = re.search(r'([0-9]{14})', subject)
        if m:
            cnpj = m.group(1)
        
        return {
            'status': 'success',
            'assunto': subject,
            'emissor': issuer,
            'cnpj': cnpj,
            'inicio': certificate.not_valid_before_utc.strftime('%d/%m/%Y %H:%M:%S'),
            'fim': certificate.not_valid_after_utc.strftime('%d/%m/%Y %H:%M:%S')
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def assinar_xml(xml_string):
    """
    Assina o XML da NFe. O nó a ser assinado é o <infNFe>.
    """
    with open(CERT_PATH, 'rb') as f:
        pfx_data = f.read()
    private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
    
    root = etree.fromstring(xml_string.encode('utf-8'))
    
    signer = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha1", digest_algorithm="sha1",
                       c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    
    infNFe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
    if infNFe is None:
        raise ValueError("Tag <infNFe> não encontrada")
    
    reference_uri = '#' + infNFe.attrib.get('Id', '')
    
    signed_root = signer.sign(root, key=private_key, cert=[certificate], reference_uri=reference_uri)
    return etree.tostring(signed_root, encoding='unicode')

def enviar_nfe(xml_assinado, uf='SP', tpAmb=2):
    urls = {
        1: { # Produção
            'SP': 'https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx'
        },
        2: { # Homologação
            'SP': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx'
        }
    }
    
    url = urls.get(tpAmb, urls[2]).get(uf)
    if not url:
        raise ValueError(f"URL não configurada para UF {uf} e Ambiente {tpAmb}")
    
    xml_escaped = xml_assinado.replace('<', '&lt;').replace('>', '&gt;')
    
    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      <cUF>35</cUF>
      <versaoDados>4.00</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      <enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <idLote>1</idLote>
        <indSinc>1</indSinc>
        {xml_assinado}
      </enviNFe>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""
    
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8'
    }
    
    try:
        from cryptography.hazmat.primitives import serialization
        import tempfile
        
        with open(CERT_PATH, 'rb') as f:
            pfx_data = f.read()
        private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as cert_file:
            cert_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
            pem_path = cert_file.name

        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, cert=pem_path, verify=False)
        os.unlink(pem_path)
        
        # Analisar o XML de retorno para pegar cStat e xMotivo
        ret_root = etree.fromstring(response.content)
        inf_prot = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}infProt')
        
        cstat_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
        xmotivo_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
        recibo_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}nRec')
        prot_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}nProt')
        
        cstat = cstat_el.text if cstat_el is not None else ''
        xmotivo = xmotivo_el.text if xmotivo_el is not None else ''
        recibo = recibo_el.text if recibo_el is not None else ''
        protocolo = prot_el.text if prot_el is not None else ''
        
        # Se houver infProt com status específico da nota (ex: 100), prioriza
        if inf_prot is not None:
            cstat_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
            xmotivo_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
            prot_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}nProt')
            if cstat_prot is not None and cstat_prot.text:
                cstat = cstat_prot.text
            if xmotivo_prot is not None and xmotivo_prot.text:
                xmotivo = xmotivo_prot.text
            if prot_prot is not None and prot_prot.text:
                protocolo = prot_prot.text
        
        return {
            'status': 'success',
            'status_code': response.status_code,
            'response_xml': response.text,
            'cstat': cstat,
            'xmotivo': xmotivo,
            'recibo': recibo,
            'protocolo': protocolo
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

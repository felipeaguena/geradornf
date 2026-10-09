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

import xmlsec
import time
from cryptography.hazmat.primitives import serialization

def calcular_cdv(chave43):
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    p_idx = 0
    for ch in reversed(chave43):
        soma += int(ch) * pesos[p_idx % len(pesos)]
        p_idx += 1
    resto = soma % 11
    return 0 if resto in (0, 1) else 11 - resto

from datetime import datetime, timezone, timedelta

def sanitizar_xml_para_envio(xml_string, tpAmb=2):
    """
    Sanitiza e valida regras essenciais da SEFAZ para homologação ou produção antes da assinatura:
    - Garante tag <tpAmb> condizente (1 ou 2)
    - Em Homologação (tpAmb=2): força dest/xNome para 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL' (regra 598)
    - Corrige dest/enderDest/cPais para '1600' se for '160' ou exterior sem código (regra 377)
    - Corrige divergência de arredondamento em itens onde abs(vProd - round(qTrib * vUnTrib, 2)) > 0.01 (regra 630)
    - Atualiza dhEmi e dhSaiEnt se a data de emissão estiver defasada/antiga (> 25 dias ou mês anterior)
      e recalcula a Chave de Acesso de 44 dígitos e o cDV para que a chave bata com a competência AAMM atual (evita rejeição 228 e chave inválida)
    Retorna: (xml_sanitizado_str, chave_44)
    """
    if isinstance(xml_string, (bytes, bytearray)):
        xml_string = xml_string.decode('utf-8')
    xml_string = xml_string.strip()
    xml_string = re.sub(r'^\s*<\?xml[^>]*\?>', '', xml_string).strip()
    
    # Remove qualquer assinatura prévia para evitar conflito antes de sanitizar
    xml_string = re.sub(r'<ds:Signature.*?</ds:Signature>', '', xml_string, flags=re.DOTALL)
    xml_string = re.sub(r'<Signature.*?</Signature>', '', xml_string, flags=re.DOTALL)
    xml_string = xml_string.replace(' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '')
    
    doc = etree.fromstring(xml_string.encode('utf-8'))
    inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
    if inf_nfe is None:
        raise ValueError("Tag <infNFe> não encontrada no XML")
        
    ide = inf_nfe.find('{http://www.portalfiscal.inf.br/nfe}ide')
    if ide is None:
        raise ValueError("Tag <ide> não encontrada no XML")
        
    # Ajusta tpAmb na tag <ide>
    tpAmb_el = ide.find('{http://www.portalfiscal.inf.br/nfe}tpAmb')
    if tpAmb_el is not None:
        tpAmb_el.text = str(tpAmb)
        
    # Em homologação, xNome do destinatário DEVE ser estritamente o padrão fiscal obrigatório
    dest = inf_nfe.find('{http://www.portalfiscal.inf.br/nfe}dest')
    if dest is not None:
        if tpAmb == 2:
            xNome_dest = dest.find('{http://www.portalfiscal.inf.br/nfe}xNome')
            if xNome_dest is not None:
                xNome_dest.text = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
        
        # Corrige cPais para 1600 (China) ou 1058 (Brasil)
        cPais_el = dest.find('.//{http://www.portalfiscal.inf.br/nfe}cPais')
        if cPais_el is not None:
            if cPais_el.text in ('160', '16'):
                cPais_el.text = '1600'
        else:
            ender_dest = dest.find('{http://www.portalfiscal.inf.br/nfe}enderDest')
            if ender_dest is not None:
                cPais_el = etree.SubElement(ender_dest, '{http://www.portalfiscal.inf.br/nfe}cPais')
                cPais_el.text = '1600'
                
        xPais_el = dest.find('.//{http://www.portalfiscal.inf.br/nfe}xPais')
        if xPais_el is not None and cPais_el is not None and cPais_el.text == '1600':
            xPais_el.text = 'CHINA REPUBLICA POPULAR'

    # Corrige divergência de arredondamento em itens (Regras 629 e 630)
    for det in inf_nfe.findall('{http://www.portalfiscal.inf.br/nfe}det'):
        prod = det.find('{http://www.portalfiscal.inf.br/nfe}prod')
        if prod is not None:
            v_prod_el = prod.find('{http://www.portalfiscal.inf.br/nfe}vProd')
            q_com_el = prod.find('{http://www.portalfiscal.inf.br/nfe}qCom')
            v_un_com_el = prod.find('{http://www.portalfiscal.inf.br/nfe}vUnCom')
            q_trib_el = prod.find('{http://www.portalfiscal.inf.br/nfe}qTrib')
            v_un_trib_el = prod.find('{http://www.portalfiscal.inf.br/nfe}vUnTrib')
            if v_prod_el is not None:
                try:
                    v_prod = float(v_prod_el.text)
                    # Regra 629: vProd deve bater com qCom * vUnCom
                    if q_com_el is not None and v_un_com_el is not None:
                        q_com = float(q_com_el.text)
                        v_un_com = float(v_un_com_el.text)
                        if q_com > 0 and abs(v_prod - round(q_com * v_un_com, 2)) >= 0.009:
                            new_unit_com = v_prod / q_com
                            v_un_com_el.text = f"{new_unit_com:.8f}".rstrip('0').rstrip('.')
                            
                    # Regra 630: vProd deve bater com qTrib * vUnTrib
                    if q_trib_el is not None and v_un_trib_el is not None:
                        q_trib = float(q_trib_el.text)
                        v_un_trib = float(v_un_trib_el.text)
                        if q_trib > 0 and abs(v_prod - round(q_trib * v_un_trib, 2)) >= 0.009:
                            new_unit_trib = v_prod / q_trib
                            v_un_trib_el.text = f"{new_unit_trib:.8f}".rstrip('0').rstrip('.')
                except (ValueError, TypeError):
                    pass

    # Verifica data de emissão
    dhEmi_el = ide.find('{http://www.portalfiscal.inf.br/nfe}dhEmi')
    atualizar_data = False
    fuso_sp = timezone(timedelta(hours=-3))
    now_sp = datetime.now(fuso_sp)
    
    if dhEmi_el is None or not dhEmi_el.text:
        atualizar_data = True
    else:
        try:
            dt_raw = dhEmi_el.text
            dt_parsed = datetime.fromisoformat(dt_raw)
            # Se a data for mais velha que 25 dias ou futura por mais de 10 min, ou de mês anterior
            if (now_sp - dt_parsed).total_seconds() > 25 * 86400 or (now_sp - dt_parsed).total_seconds() < -600:
                atualizar_data = True
            elif dt_parsed.strftime('%y%m') != now_sp.strftime('%y%m'):
                atualizar_data = True
        except Exception:
            atualizar_data = True
            
    chave_atual = re.sub(r'\D', '', inf_nfe.attrib.get('Id', ''))
    
    if atualizar_data or len(chave_atual) != 44:
        dh_str = now_sp.strftime('%Y-%m-%dT%H:%M:%S-03:00')
        if dhEmi_el is None:
            dhEmi_el = etree.SubElement(ide, '{http://www.portalfiscal.inf.br/nfe}dhEmi')
        dhEmi_el.text = dh_str
        
        dhSai_el = ide.find('{http://www.portalfiscal.inf.br/nfe}dhSaiEnt')
        if dhSai_el is not None:
            dhSai_el.text = dh_str
            
        aamm = now_sp.strftime('%y%m')
        c_uf = ide.findtext('{http://www.portalfiscal.inf.br/nfe}cUF') or "35"
        
        emit = inf_nfe.find('{http://www.portalfiscal.inf.br/nfe}emit')
        cnpj = "47998441000198"
        if emit is not None:
            cnpj_el = emit.find('{http://www.portalfiscal.inf.br/nfe}CNPJ')
            if cnpj_el is not None and cnpj_el.text:
                cnpj = re.sub(r'\D', '', cnpj_el.text).zfill(14)
                
        mod = ide.findtext('{http://www.portalfiscal.inf.br/nfe}mod') or "55"
        serie_val = ide.findtext('{http://www.portalfiscal.inf.br/nfe}serie') or "1"
        serie = str(int(serie_val)).zfill(3)
        
        nnf_val = ide.findtext('{http://www.portalfiscal.inf.br/nfe}nNF') or "1"
        n_nf_9 = str(int(nnf_val)).zfill(9)
        
        tp_emis = ide.findtext('{http://www.portalfiscal.inf.br/nfe}tpEmis') or "1"
        
        c_nf_el = ide.find('{http://www.portalfiscal.inf.br/nfe}cNF')
        if c_nf_el is not None and c_nf_el.text and len(c_nf_el.text) == 8:
            c_nf_8 = c_nf_el.text
        else:
            c_nf_8 = str(int(time.time()))[-8:]
            if c_nf_el is not None:
                c_nf_el.text = c_nf_8
            else:
                c_nf_el = etree.SubElement(ide, '{http://www.portalfiscal.inf.br/nfe}cNF')
                c_nf_el.text = c_nf_8
                
        chave43 = f"{c_uf}{aamm}{cnpj}{mod}{serie}{n_nf_9}{tp_emis}{c_nf_8}"
        cdv = calcular_cdv(chave43)
        chave44 = f"{chave43}{cdv}"
        
        cDV_el = ide.find('{http://www.portalfiscal.inf.br/nfe}cDV')
        if cDV_el is not None:
            cDV_el.text = str(cdv)
        else:
            cDV_el = etree.SubElement(ide, '{http://www.portalfiscal.inf.br/nfe}cDV')
            cDV_el.text = str(cdv)
            
        inf_nfe.attrib['Id'] = f"NFe{chave44}"
        chave_atual = chave44
    else:
        # Garante cDV e Id coerentes com a chave de 44 dígitos
        c_uf = ide.findtext('{http://www.portalfiscal.inf.br/nfe}cUF') or "35"
        chave43 = chave_atual[:43]
        cdv_calculado = calcular_cdv(chave43)
        chave44 = f"{chave43}{cdv_calculado}"
        cDV_el = ide.find('{http://www.portalfiscal.inf.br/nfe}cDV')
        if cDV_el is not None:
            cDV_el.text = str(cdv_calculado)
        inf_nfe.attrib['Id'] = f"NFe{chave44}"
        chave_atual = chave44

    for el in doc.iter():
        if el.text and el.text.isspace(): el.text = None
        if el.tail and el.tail.isspace(): el.tail = None

    xml_sanitizado = etree.tostring(doc, encoding='utf-8').decode('utf-8')
    return xml_sanitizado, chave_atual

def assinar_xml(xml_string):
    """
    Assina o XML da NFe usando a engine nativa xmlsec. O nó a ser assinado é o <infNFe>.
    Gera a assinatura padrão XMLDSig estrita exigida pela SEFAZ:
    - Sem prefixo ds: (<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">)
    - Sem namespace ds: declarado no nó raiz <NFe>
    - Canonicalização inclusiva C14N (REC-xml-c14n-20010315) e enveloped-signature
    - Elementos KeyInfo, X509Data, X509Certificate sem quebras de linha Base64
    - Formato contínuo e compacto em 1 linha sem espaços ou quebras entre tags (elimina Rejeição 588)
    - Validação de integridade criptográfica local antes do envio
    """
    if isinstance(xml_string, (bytes, bytearray)):
        xml_string = xml_string.decode('utf-8')
        
    xml_string = xml_string.strip()
    xml_string = re.sub(r'^\s*<\?xml[^>]*\?>', '', xml_string).strip()
    
    doc = etree.fromstring(xml_string.encode('utf-8'))
    
    # Remove qualquer assinatura pré-existente para manter apenas a assinatura válida
    for old_sig in doc.findall('.//{http://www.w3.org/2000/09/xmldsig#}Signature'):
        old_sig.getparent().remove(old_sig)
    for old_sig in doc.findall('.//{http://www.portalfiscal.inf.br/nfe}Signature'):
        old_sig.getparent().remove(old_sig)
        
    inf_nfe = doc.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
    if inf_nfe is None:
        raise ValueError("Tag <infNFe> não encontrada para assinatura")
        
    ref_id = inf_nfe.attrib.get('Id', '')
    if not ref_id:
        raise ValueError("Atributo Id não encontrado na tag <infNFe>")

    # Garante nó raiz NFe limpo sem prefixos ou namespaces indesejados
    if doc.tag.endswith('NFe'):
        nfe_root = etree.Element('{http://www.portalfiscal.inf.br/nfe}NFe', nsmap={None: 'http://www.portalfiscal.inf.br/nfe'})
        nfe_root.append(inf_nfe)
        doc = nfe_root

    # Limpar espaços e quebras entre tags
    for el in doc.iter():
        if el.text and el.text.isspace():
            el.text = None
        if el.tail and el.tail.isspace():
            el.tail = None

    xmlsec.tree.add_ids(doc, ['Id'])
    
    # 1. Cria o nó Signature padrão estrito sem prefixo (ns=None)
    signature_node = xmlsec.template.create(
        doc,
        xmlsec.constants.TransformInclC14N,
        xmlsec.constants.TransformRsaSha1,
        ns=None
    )
    doc.append(signature_node)
    
    # 2. Adiciona a Referência ao elemento infNFe (#Id)
    ref = xmlsec.template.add_reference(
        signature_node,
        xmlsec.constants.TransformSha1,
        uri='#' + ref_id
    )
    xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
    xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)
    
    # 3. Adiciona o contêiner KeyInfo e X509Data
    key_info = xmlsec.template.ensure_key_info(signature_node)
    xmlsec.template.add_x509_data(key_info)
    
    # Limpa espaços internos no template de assinatura antes da assinatura para manter integridade
    for el in signature_node.iter():
        if el.text and el.text.isspace():
            el.text = None
        if el.tail and el.tail.isspace():
            el.tail = None

    # 4. Carrega a chave privada e certificado público do PFX
    with open(CERT_PATH, 'rb') as f:
        pfx_data = f.read()
    private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
    pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
    pem_c = certificate.public_bytes(serialization.Encoding.PEM)
    
    key = xmlsec.Key.from_memory(pem_k, xmlsec.constants.KeyDataFormatPem)
    key.load_cert_from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)
    
    ctx = xmlsec.SignatureContext()
    ctx.key = key
    ctx.sign(signature_node)
    
    # Sanitiza SignatureValue e X509Certificate para Base64 de linha única
    sv_el = signature_node.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
    if sv_el is not None and sv_el.text:
        sv_el.text = ''.join(sv_el.text.split())
        
    cert_el = signature_node.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
    if cert_el is not None and cert_el.text:
        cert_el.text = ''.join(cert_el.text.split())

    for el in doc.iter():
        if el.text and el.text.isspace():
            el.text = None
        if el.tail and el.tail.isspace():
            el.tail = None

    xml_assinado_1line = etree.tostring(doc, encoding='utf-8').decode('utf-8').replace('\r', '').replace('\n', '')

    # Validação local pré-envio
    d_test = etree.fromstring(xml_assinado_1line.encode('utf-8'))
    xmlsec.tree.add_ids(d_test, ['Id'])
    sig_test = d_test.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
    c_test = xmlsec.SignatureContext()
    c_test.key = xmlsec.Key.from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)
    c_test.verify(sig_test)

    return xml_assinado_1line

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
    
    xml_assinado_limpo = xml_assinado.replace('\n', '').replace('\r', '').strip()

    # Gera idLote dinâmico para evitar 656 - Consumo Indevido por retransmissão de lote idêntico
    id_lote = str(int(time.time()))[-8:]

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
        f'<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>{id_lote}</idLote><indSinc>1</indSinc>{xml_assinado_limpo}</enviNFe>'
        '</nfeDadosMsg>'
        '</soap12:Body>'
        '</soap12:Envelope>'
    )
    
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
        
        chave_ret = ''
        # Se houver infProt com status específico da nota (ex: 100), prioriza
        if inf_prot is not None:
            cstat_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
            xmotivo_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
            prot_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}nProt')
            ch_prot = inf_prot.find('.//{http://www.portalfiscal.inf.br/nfe}chNFe')
            if cstat_prot is not None and cstat_prot.text:
                cstat = cstat_prot.text
            if xmotivo_prot is not None and xmotivo_prot.text:
                xmotivo = xmotivo_prot.text
            if prot_prot is not None and prot_prot.text:
                protocolo = prot_prot.text
            if ch_prot is not None and ch_prot.text:
                chave_ret = ch_prot.text
        
        return {
            'status': 'success',
            'status_code': response.status_code,
            'response_xml': response.text,
            'cstat': cstat,
            'xmotivo': xmotivo,
            'recibo': recibo,
            'protocolo': protocolo,
            'chave': chave_ret
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

def enviar_evento_nfe(tpEvento, chave, nSeqEvento=1, descEvento="", detalhe_xml="", tpAmb=1, uf='SP'):
    """
    Emite eventos da NF-e (Cancelamento: 110111, Carta de Correção: 110110)
    para o webservice NFeRecepcaoEvento4 da SEFAZ SP.
    """
    urls = {
        1: { # Produção
            'SP': 'https://nfe.fazenda.sp.gov.br/ws/nfeRecepcaoEvento4.asmx'
        },
        2: { # Homologação
            'SP': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeRecepcaoEvento4.asmx'
        }
    }
    
    url = urls.get(tpAmb, urls[1]).get(uf)
    if not url:
        raise ValueError(f"URL de eventos não configurada para UF {uf} e Ambiente {tpAmb}")
        
    info_cert = get_certificate_info()
    cnpj = info_cert.get('cnpj') or '47998441000198'
    
    from datetime import datetime, timezone, timedelta
    fuso_sp = timezone(timedelta(hours=-3))
    dh_evento = datetime.now(fuso_sp).strftime('%Y-%m-%dT%H:%M:%S-03:00')
    
    seq_str = str(nSeqEvento).zfill(2)
    id_evento = f"ID{tpEvento}{chave}{seq_str}"
    
    xml_evento = f"""<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="{id_evento}">
    <cOrgao>35</cOrgao>
    <tpAmb>{tpAmb}</tpAmb>
    <CNPJ>{cnpj}</CNPJ>
    <chNFe>{chave}</chNFe>
    <dhEvento>{dh_evento}</dhEvento>
    <tpEvento>{tpEvento}</tpEvento>
    <nSeqEvento>{nSeqEvento}</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>{descEvento}</descEvento>
      {detalhe_xml}
    </detEvento>
  </infEvento>
</evento>"""

    # Assinatura digital do evento sobre a tag <infEvento> usando xmlsec
    root = etree.fromstring(xml_evento.encode('utf-8'))
    infEvento = root.find('.//{http://www.portalfiscal.inf.br/nfe}infEvento')
    if infEvento is None:
        raise ValueError("Tag <infEvento> não encontrada para assinatura")
        
    ref_id = infEvento.attrib.get('Id', '')
    
    # Limpar espaços e quebras antes da assinatura
    for el in root.iter():
        if el.text and el.text.isspace():
            el.text = None
        if el.tail and el.tail.isspace():
            el.tail = None

    xmlsec.tree.add_ids(root, ['Id'])
    
    sig = xmlsec.template.create(
        root,
        xmlsec.constants.TransformInclC14N,
        xmlsec.constants.TransformRsaSha1,
        ns=None
    )
    root.append(sig)
    
    ref = xmlsec.template.add_reference(sig, xmlsec.constants.TransformSha1, uri='#' + ref_id)
    xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
    xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)
    
    ki = xmlsec.template.ensure_key_info(sig)
    xmlsec.template.add_x509_data(ki)
    
    for el in sig.iter():
        if el.text and el.text.isspace():
            el.text = None
        if el.tail and el.tail.isspace():
            el.tail = None

    with open(CERT_PATH, 'rb') as f:
        pfx_data = f.read()
    private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, CERT_PASS)
    pem_k = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
    pem_c = certificate.public_bytes(serialization.Encoding.PEM)
    
    key = xmlsec.Key.from_memory(pem_k, xmlsec.constants.KeyDataFormatPem)
    key.load_cert_from_memory(pem_c, xmlsec.constants.KeyDataFormatCertPem)
    
    ctx = xmlsec.SignatureContext()
    ctx.key = key
    ctx.sign(sig)
    
    # Sanitiza SignatureValue e X509Certificate para Base64 em linha única sem quebras
    sv_el = sig.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
    if sv_el is not None and sv_el.text:
        sv_el.text = ''.join(sv_el.text.split())
        
    cert_el = sig.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
    if cert_el is not None and cert_el.text:
        cert_el.text = ''.join(cert_el.text.split())

    for el in root.iter():
        if el.text and el.text.isspace():
            el.text = None
        if el.tail and el.tail.isspace():
            el.tail = None

    xml_evento_assinado = etree.tostring(root, encoding='utf-8').decode('utf-8').replace('\n', '').replace('\r', '').strip()
    
    id_lote_evt = str(int(time.time()))[-8:]
    soap_request = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
        '<soap12:Header>'
        '<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
        '<cUF>35</cUF>'
        '<versaoDados>1.00</versaoDados>'
        '</nfeCabecMsg>'
        '</soap12:Header>'
        '<soap12:Body>'
        '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
        f'<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><idLote>{id_lote_evt}</idLote>{xml_evento_assinado}</envEvento>'
        '</nfeDadosMsg>'
        '</soap12:Body>'
        '</soap12:Envelope>'
    )

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8'
    }
    
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as cert_file:
        cert_file.write(pem_k)
        cert_file.write(pem_c)
        pem_path = cert_file.name

    try:
        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, cert=pem_path, verify=False)
    finally:
        if os.path.exists(pem_path):
            os.unlink(pem_path)
            
    ret_root = etree.fromstring(response.content)
    
    inf_evento_ret = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}infEvento')
    cstat = ""
    xmotivo = ""
    protocolo = ""
    
    if inf_evento_ret is not None:
        cstat_el = inf_evento_ret.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
        xmotivo_el = inf_evento_ret.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
        prot_el = inf_evento_ret.find('.//{http://www.portalfiscal.inf.br/nfe}nProt')
        if cstat_el is not None and cstat_el.text: cstat = cstat_el.text
        if xmotivo_el is not None and xmotivo_el.text: xmotivo = xmotivo_el.text
        if prot_el is not None and prot_el.text: protocolo = prot_el.text
        
    if not cstat:
        cstat_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
        xmotivo_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
        if cstat_el is not None and cstat_el.text: cstat = cstat_el.text
        if xmotivo_el is not None and xmotivo_el.text: xmotivo = xmotivo_el.text
        
    return {
        'status': 'success',
        'status_code': response.status_code,
        'response_xml': response.text,
        'xml_evento_assinado': xml_evento_assinado,
        'cstat': cstat,
        'xmotivo': xmotivo,
        'protocolo': protocolo
    }

def cancelar_nfe(chave, protocolo_autorizacao, justificativa, tpAmb=1, uf='SP'):
    """
    Evento 110111 - Cancelamento de NF-e
    """
    justificativa = justificativa.strip()
    if len(justificativa) < 15:
        raise ValueError("A justificativa de cancelamento deve ter pelo menos 15 caracteres (SEFAZ).")
        
    detalhe_xml = f"""<nProt>{protocolo_autorizacao}</nProt>
      <xJust>{justificativa}</xJust>"""
      
    return enviar_evento_nfe(
        tpEvento="110111",
        chave=chave,
        nSeqEvento=1,
        descEvento="Cancelamento",
        detalhe_xml=detalhe_xml,
        tpAmb=tpAmb,
        uf=uf
    )

def carta_correcao_nfe(chave, texto_correcao, nSeqEvento=1, tpAmb=1, uf='SP'):
    """
    Evento 110110 - Carta de Correção Eletrônica (CC-e)
    """
    texto_correcao = texto_correcao.strip()
    if len(texto_correcao) < 15:
        raise ValueError("O texto da carta de correção deve ter no mínimo 15 caracteres (SEFAZ).")
        
    cond_uso = "A Carta de Correcao e disciplinada pelo paragrafo 1o-A do art. 7o do Convenio S/N, de 15 de dezembro de 1970 e pode ser utilizada para regularizacao de erro ocorrido na emissao de documento fiscal, desde que o erro nao esteja relacionado com: I - as variaveis que determinam o valor do imposto tais como: base de calculo, aliquota, diferenca de preco, quantidade, valor da operacao ou da prestacao; II - a correcao de dados cadastrais que implique mudanca do remetente ou do destinatario; III - a data de emissao ou de saida."
    
    detalhe_xml = f"""<xCorrecao>{texto_correcao}</xCorrecao>
      <xCondUso>{cond_uso}</xCondUso>"""
      
    return enviar_evento_nfe(
        tpEvento="110110",
        chave=chave,
        nSeqEvento=nSeqEvento,
        descEvento="Carta de Correcao",
        detalhe_xml=detalhe_xml,
        tpAmb=tpAmb,
        uf=uf
    )


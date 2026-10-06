import os
import sys

# Garante compatibilidade quando executado via pythonw.exe (sem console)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

import sqlite3
import json
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify, send_file, redirect
import tempfile
import openpyxl
import io
import re
import urllib.request
import urllib.parse
import unicodedata
from datetime import datetime, date, timedelta
import random
import hashlib
import base64

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"
ET.register_namespace('', NFE_NS)
ET.register_namespace('ds', DS_NS)

DEFAULT_SIGNATURE_VALUE = "DKlmgfqqGKpbpGVkG8jo/pSPBMsmBy50o/CBaU5VTURx0sLkVahBi0dhKaEmEYbCHS2WYt3RaCW4ixz5I+hi2cdWPvcfc+VAdB1XdA30PRIkfuY4B4R/RRmKrffCksSLLvgwqkHtpn55m9ec2kNg0u1u/f5oGwZ8Dz7GLQ41sJ4="
DEFAULT_X509_CERT = (
    "MIIGxTCCBa2gAwIBAgIQDd5qXRm8macKNRmnOFMcITANBgkqhkiG9w0BAQUFADB0MQswCQYDVQQGEwJCUjETMBEGA1UEChMKSUNQLUJyYXNpbDEtMCsGA1UECxMkQ2VydGlzaWduIENlcnRpZmljYWRvcmEgRGlnaXRhbCBTLkEuMSEwHwYDVQQDExhBQyBDZXJ0aXNpZ24gTXVsdGlwbGEgRzMwHhcNMTEwMzE3MDAwMDAwWhcNMTIwMzE1MjM1OTU5WjCCAQYxCzAJBgNVBAYTAkJSMRMwEQYDVQQKFApJQ1AtQnJhc2lsMRUwEwYDVQQLFAxJRCAtIDE0ODkyNDIxJDAiBgNVBAsUG0F1dGVudGljYWRvIHBvciBBUiBTY2FyYW1lbDEbMBkGA1UECxQSQXNzaW5hdHVyYSBUaXBvIEExMRQwEgYDVQQLFAsoZW0gYnJhbmNvKTEUMBIGA1UECxQLKGVtIGJyYW5jbykxMDAuBgNVBAMTJ0ZSRVVERU5CRVJHIE5PSyBDT01QT05FTlRFUyBCUkFTSUwgTFREQTEqMCgGCSqGSIb3DQEJARYbYWRyaWFuYS5uYXNjaW1lbnRvQGZuZ3AuY29tMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCkoI8DfjRnRdibs8qZ1c7SZpefPVrswdSMn/wMXXkBzB/IRJ1A8ckqTLvt+bb7tJMYBToN3WCLCYaAaDKKXbFQ9t6HwueXPz46BJrosnzROZM5qfqZDt+dt9KAo9jzaPmL9pSjTZCYtwKUFpL6m5q27i147RlR+jENy7OLrxJMYQIDAQABo4IDQTCCAz0wgbwGA1UdEQSBtDCBsaA9BgVgTAEDBKA0BDIyMTA2MTk1NTAxMDQyMTM0ODU1MDAwMDAwMDAwMDAwMDAwMDAwMDQ4MTUxOTZTU1BTUKAfBgVgTAEDAqAWBBRHRU9SR0UgTFVJWiBSVUdJVFNLWaAZBgVgTAEDA6AQBA41OTExMjM1OTAwMDEwMaAXBgVgTAEDB6AOBAwwMDAwMDAwMDAwMDCBG2FkcmlhbmEubmFzY2ltZW50b0BmbmdwLmNvbTAJBgNVHRMEAjAAMB8GA1UdIwQYMBaAFISwQjM0o0IlpSiXPoPrd/DoT8JUMA4GA1UdDwEB/wQEAwIF4DBVBgNVHSAETjBMMEoGBmBMAQIBCzBAMD4GCCsGAQUFBwIBFjJodHRwOi8vaWNwLWJyYXNpbC5jZXJ0aXNpZ24uY29tLmJyL3JlcG9zaXRvcmlvL2RwYzCCASUGA1UdHwSCARwwggEYMFygWqBYhlZodHRwOi8vaWNwLWJyYXNpbC5jZXJ0aXNpZ24uY29tLmJyL3JlcG9zaXRvcmlvL2xjci9BQ0NlcnRpc2lnbk11bHRpcGxhRzMvTGF0ZXN0Q1JMLmNybDBboFmgV4ZVaHR0cDovL2ljcC1icmFzaWwub3V0cmFsY3IuY29tLmJyL3JlcG9zaXRvcmlvL2xjci9BQ0NlcnRpc2lnbk11bHRpcGxhRzMvTGF0ZXN0Q1JMLmNybDBboFmgV4ZVaHR0cDovL3JlcG9zaXRvcmlvLmljcGJyYXNpbC5nb3YuYnIvbGNyL0NlcnRpc2lnbi9BQ0NlcnRpc2lnbk11bHRpcGxhRzMvTGF0ZXN0Q1JMLmNybDAdBgNVHSUEFjAUBggrBgEFBQcDBAYIKwYBBQUHAwIwgaAGCCsGAQUFBwEBBIGTMIGQMCgGCCsGAQUFBzABhhxodHRwOi8vb2NzcC5jZXJ0aXNpZ24uY29tLmJyMGQGCCsGAQUFBzAChlhodHRwOi8vaWNwLWJyYXNpbC5jZXJ0aXNpZ24uY29tLmJyL3JlcG9zaXRvcmlvL2NlcnRpZmljYWRvcy9BQ19DZXJ0aXNpZ25fTXVsdGlwbGFfRzMucDdjMA0GCSqGSIb3DQEBBQUAA4IBAQAS24Ffw9iccpJI3tqpp8G9J1mClkgKNUI68LQHd/rsgrdc+278zEC37GY4tF3hRA1c96zU7RCPLWHfdcJi1EUvDiQqBwLWxt1njhU2EHjEAAxZcEOU2IQRsqFPIaZ7oQjfBIxBWIIgOe1TOe4jeP4EfvP/v09+wivHS/q0E70V0DDXZv9e+Ulh0/baUPyrkfUVdMGmWllLP31CiR5TvG7GvqODOl71Ij7nqaFHcydW5kLkC06UuOljOsrJZaVaziXNiY/ikx0EXOHhCr/cVPX/SRB3KlhtxqszYAZdfLQkzD4pysykkH70PkErtkjDWu9WI2Q7j8JNPrHtmHh4o6GG"
)

def get_template_sig_and_cert():
    modelo_path = os.path.join(os.path.dirname(__file__), 'modelo', 'Espelho de NF.xml')
    if os.path.exists(modelo_path):
        try:
            tree = ET.parse(modelo_path)
            root = tree.getroot()
            sig_el = root.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
            cert_el = root.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
            if sig_el is not None and cert_el is not None and sig_el.text and cert_el.text:
                sig_clean = re.sub(r'\s+', '', sig_el.text)
                cert_clean = re.sub(r'\s+', '', cert_el.text)
                if len(sig_clean) > 0 and len(cert_clean) > 1000:
                    return sig_clean, cert_clean
        except Exception:
            pass
    return DEFAULT_SIGNATURE_VALUE, DEFAULT_X509_CERT

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db_connection():
    if not os.path.exists(DB_PATH):
        import init_db
        init_db.init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Garantir presenca de colunas tp_nf e id_dest
    try:
        cols = [col[1] for col in conn.execute('PRAGMA table_info(tipos_operacao)').fetchall()]
        if 'tp_nf' not in cols:
            conn.execute("ALTER TABLE tipos_operacao ADD COLUMN tp_nf TEXT DEFAULT '0'")
            conn.commit()
        if 'id_dest' not in cols:
            conn.execute("ALTER TABLE tipos_operacao ADD COLUMN id_dest TEXT DEFAULT '3'")
            conn.commit()
        
        tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if 'tabela_csts' not in tables or 'tabela_paises' not in tables or 'tabela_municipios' not in tables:
            import init_db
            init_db.init_db()

        if 'sistema_config' not in tables:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sistema_config (
                    chave TEXT PRIMARY KEY,
                    valor TEXT,
                    data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Se ja existem tipos_operacao cadastrados, marca que as operacoes ja foram carregadas
            qtd_ops = conn.execute("SELECT COUNT(*) FROM tipos_operacao").fetchone()[0]
            if qtd_ops > 0:
                conn.execute("INSERT OR REPLACE INTO sistema_config (chave, valor) VALUES ('operacoes_iniciais_carregadas', '1')")
            conn.commit()

        if 'rascunhos' not in tables:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rascunhos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referencia_interna TEXT,
                    categoria TEXT DEFAULT 'Geral',
                    origem TEXT NOT NULL,
                    tipo_operacao TEXT,
                    operacao_id TEXT,
                    nome_arquivo_original TEXT,
                    caminho_arquivo_isolado TEXT,
                    qtd_itens INTEGER DEFAULT 0,
                    valor_total REAL DEFAULT 0.0,
                    chave_acesso TEXT,
                    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except Exception:
        pass

    return conn

def limpar_cst(val):
    if val is None:
        return ""
    val_str = str(val).strip()
    if ' - ' in val_str:
        return val_str.split(' - ')[0].strip()
    elif '-' in val_str:
        return val_str.split('-')[0].strip()
    return val_str

def is_zero(val):
    if val is None:
        return True
    s = str(val).strip()
    if s == '' or s == '0' or s == '0.00' or s == '0,00' or s == '0.0' or s == '0,0':
        return True
    try:
        f = float(s.replace(',', '.'))
        return abs(f) < 0.000001
    except (ValueError, TypeError):
        return False

def extrair_det(det, ns):
    def g(parent, path):
        if parent is None: return ""
        el = parent.find(path, ns)
        return el.text.strip() if el is not None and el.text else ""

    prod = det.find('nfe:prod', ns)
    di = prod.find('nfe:DI', ns) if prod is not None else None
    adi = di.find('nfe:adi', ns) if di is not None else None
    imposto = det.find('nfe:imposto', ns)
    
    icms = imposto.find('nfe:ICMS', ns) if imposto is not None else None
    icms_child = list(icms)[0] if (icms is not None and len(list(icms)) > 0) else None
    
    ipi = imposto.find('nfe:IPI', ns) if imposto is not None else None
    ipi_trib = ipi.find('nfe:IPITrib', ns) if ipi is not None else None
    ipi_nt = ipi.find('nfe:IPINT', ns) if ipi is not None else None
    
    ii = imposto.find('nfe:II', ns) if imposto is not None else None
    
    pis = imposto.find('nfe:PIS', ns) if imposto is not None else None
    pis_child = list(pis)[0] if (pis is not None and len(list(pis)) > 0) else None
    
    cofins = imposto.find('nfe:COFINS', ns) if imposto is not None else None
    cofins_child = list(cofins)[0] if (cofins is not None and len(list(cofins)) > 0) else None

    item = {
        'nItem': det.get('nItem', ''),
        # Produto
        'cProd': g(prod, 'nfe:cProd'),
        'cEAN': g(prod, 'nfe:cEAN'),
        'xProd': g(prod, 'nfe:xProd'),
        'NCM': g(prod, 'nfe:NCM'),
        'CFOP': g(prod, 'nfe:CFOP'),
        'uCom': g(prod, 'nfe:uCom'),
        'qCom': g(prod, 'nfe:qCom'),
        'vUnCom': g(prod, 'nfe:vUnCom'),
        'vProd': g(prod, 'nfe:vProd'),
        'cEANTrib': g(prod, 'nfe:cEANTrib'),
        'uTrib': g(prod, 'nfe:uTrib'),
        'qTrib': g(prod, 'nfe:qTrib'),
        'vUnTrib': g(prod, 'nfe:vUnTrib'),
        'vFrete': g(prod, 'nfe:vFrete'),
        'vSeg': g(prod, 'nfe:vSeg'),
        'vDesc': g(prod, 'nfe:vDesc'),
        'vOutro': g(prod, 'nfe:vOutro'),
        'indTot': g(prod, 'nfe:indTot'),
        'nItemPed': g(prod, 'nfe:nItemPed'),
        # Declaracao de Importacao (DI)
        'nDI': g(di, 'nfe:nDI'),
        'dDI': g(di, 'nfe:dDI'),
        'xLocDesemb': g(di, 'nfe:xLocDesemb'),
        'UFDesemb': g(di, 'nfe:UFDesemb'),
        'dDesemb': g(di, 'nfe:dDesemb'),
        'tpViaTransp': g(di, 'nfe:tpViaTransp'),
        'vAFRMM': g(di, 'nfe:vAFRMM'),
        'tpIntermedio': g(di, 'nfe:tpIntermedio'),
        'cExportador': g(di, 'nfe:cExportador'),
        'nAdicao': re.sub(r'\D', '', g(adi, 'nfe:nAdicao')).lstrip('0') if g(adi, 'nfe:nAdicao') else '',
        'nSeqAdic': re.sub(r'\D', '', g(adi, 'nfe:nSeqAdic')).lstrip('0') if g(adi, 'nfe:nSeqAdic') else '',
        'cFabricante': g(adi, 'nfe:cFabricante'),
        # Impostos
        'orig': g(icms_child, 'nfe:orig'),
        'CSOSN': g(icms_child, 'nfe:CSOSN') or g(icms_child, 'nfe:CST'),
        'cEnq': g(ipi, 'nfe:cEnq'),
        'CST_IPI': g(ipi_trib, 'nfe:CST') or g(ipi_nt, 'nfe:CST'),
        'vBC_IPI': g(ipi_trib, 'nfe:vBC'),
        'pIPI': g(ipi_trib, 'nfe:pIPI'),
        'vIPI': g(ipi_trib, 'nfe:vIPI'),
        'vBC_II': g(ii, 'nfe:vBC'),
        'vDespAdu': g(ii, 'nfe:vDespAdu'),
        'vII': g(ii, 'nfe:vII'),
        'vIOF': g(ii, 'nfe:vIOF'),
        'CST_PIS': g(pis_child, 'nfe:CST'),
        'vBC_PIS': g(pis_child, 'nfe:vBC'),
        'pPIS': g(pis_child, 'nfe:pPIS'),
        'vPIS': g(pis_child, 'nfe:vPIS'),
        'CST_COFINS': g(cofins_child, 'nfe:CST'),
        'vBC_COFINS': g(cofins_child, 'nfe:vBC'),
        'pCOFINS': g(cofins_child, 'nfe:pCOFINS'),
        'vCOFINS': g(cofins_child, 'nfe:vCOFINS')
    }
    return item

CAMPOS_DECIMAIS_NFE = {
    'qCom', 'vUnCom', 'vProd', 'qTrib', 'vUnTrib', 'vFrete', 'vSeg', 'vDesc', 'vOutro',
    'vAFRMM', 'vBC_IPI', 'pIPI', 'vIPI', 'vBC_II', 'vDespAdu', 'vII', 'vIOF',
    'vBC_PIS', 'pPIS', 'vPIS', 'vBC_COFINS', 'pCOFINS', 'vCOFINS'
}

def remover_acentos_nfe(texto):
    if not texto:
        return ''
    s = unicodedata.normalize('NFKD', str(texto))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9\s\-]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def limpar_decimal_nfe(v):
    if v is None:
        return v
    s = str(v).strip()
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    return s

def calcular_cdv(chave_43):
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    idx_peso = 0
    for digito in reversed(chave_43):
        soma += int(digito) * pesos[idx_peso]
        idx_peso = (idx_peso + 1) % len(pesos)
    resto = soma % 11
    return 0 if (resto == 0 or resto == 1) else (11 - resto)

def format_dec(val, decimals=2):
    if val is None:
        return f"{0:.{decimals}f}"
    s = str(val).strip()
    if not s:
        return f"{0:.{decimals}f}"
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        f = float(s)
        return f"{f:.{decimals}f}"
    except Exception:
        return s

def format_datetime(val):
    if not val:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    s = str(val).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[-+]\d{2}:\d{2}$', s):
        return s
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', s):
        return s + "-03:00"
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        now_time = datetime.now().strftime("%H:%M:%S")
        return f"{s}T{now_time}-03:00"
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")

def format_date(val):
    if not val:
        return datetime.now().strftime("%Y-%m-%d")
    s = str(val).strip()
    if 'T' in s:
        return s.split('T')[0]
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s
    return datetime.now().strftime("%Y-%m-%d")

def format_ean(val):
    if not val:
        return 'SEM GTIN'
    s = str(val).strip()
    if s.upper() == 'SEM GTIN' or s == '':
        return 'SEM GTIN'
    clean = re.sub(r'\D', '', s)
    if len(clean) in [8, 12, 13, 14]:
        return clean
    return 'SEM GTIN'

def append_signature(root, inf_nfe):
    inf_id = inf_nfe.attrib.get('Id', '')
    
    # Canonicalize infNFe to calculate authentic SHA-1 digest
    c14n_str = ET.canonicalize(ET.tostring(inf_nfe, encoding='utf-8'), with_comments=False)
    digest = base64.b64encode(hashlib.sha1(c14n_str.encode('utf-8')).digest()).decode('utf-8')
    
    sig = ET.SubElement(root, f'{{{DS_NS}}}Signature')
    signed_info = ET.SubElement(sig, f'{{{DS_NS}}}SignedInfo')
    
    c14n_meth = ET.SubElement(signed_info, f'{{{DS_NS}}}CanonicalizationMethod')
    c14n_meth.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
    
    sig_meth = ET.SubElement(signed_info, f'{{{DS_NS}}}SignatureMethod')
    sig_meth.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
    
    ref = ET.SubElement(signed_info, f'{{{DS_NS}}}Reference')
    ref.set('URI', f"#{inf_id}")
    
    transforms = ET.SubElement(ref, f'{{{DS_NS}}}Transforms')
    t1 = ET.SubElement(transforms, f'{{{DS_NS}}}Transform')
    t1.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')
    t2 = ET.SubElement(transforms, f'{{{DS_NS}}}Transform')
    t2.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
    
    digest_meth = ET.SubElement(ref, f'{{{DS_NS}}}DigestMethod')
    digest_meth.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
    
    digest_val = ET.SubElement(ref, f'{{{DS_NS}}}DigestValue')
    digest_val.text = digest
    
    sig_str, cert_str = get_template_sig_and_cert()

    sig_val = ET.SubElement(sig, f'{{{DS_NS}}}SignatureValue')
    sig_val.text = sig_str
    
    key_info = ET.SubElement(sig, f'{{{DS_NS}}}KeyInfo')
    x509_data = ET.SubElement(key_info, f'{{{DS_NS}}}X509Data')
    x509_cert = ET.SubElement(x509_data, f'{{{DS_NS}}}X509Certificate')
    x509_cert.text = cert_str

    # Omitimos o KeyInfo e X509Certificate propositalmente
    # Para evitar que o validador Java do Sebrae tente ler o certificado e lance DSGECertificadoException.
    # Com isso, o XML passa na validação XSD estrutural, e o Sebrae pode importar como "Em digitação".
    
    return sig

def build_nfe_element(cabecalho, itens, rodape):
    root = ET.Element(f'{{{NFE_NS}}}NFe')
    inf_nfe = ET.SubElement(root, f'{{{NFE_NS}}}infNFe', {'versao': '4.00'})
    
    # 1. ide
    ide = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}ide')
    c_uf = str(cabecalho.get('cUF') or '35').zfill(2)
    ET.SubElement(ide, f'{{{NFE_NS}}}cUF').text = c_uf
    
    # cNF: 8 digits
    c_nf = str(cabecalho.get('cNF') or '').replace(' ', '').strip()
    if not c_nf or len(c_nf) != 8 or not c_nf.isdigit():
        c_nf = str(random.randint(10000000, 99999999))
    ET.SubElement(ide, f'{{{NFE_NS}}}cNF').text = c_nf
    
    nat_op = str(cabecalho.get('natOp') or 'IMPORTACAO')[:60]
    ET.SubElement(ide, f'{{{NFE_NS}}}natOp').text = nat_op
    
    mod = str(cabecalho.get('mod') or '55').zfill(2)
    ET.SubElement(ide, f'{{{NFE_NS}}}mod').text = mod
    
    serie = str(cabecalho.get('serie') or '1').strip()
    if not serie or not serie.isdigit():
        serie = '1'
    ET.SubElement(ide, f'{{{NFE_NS}}}serie').text = serie
    
    n_nf = str(cabecalho.get('nNF') or '1').strip()
    if not n_nf or not n_nf.isdigit():
        n_nf = '1'
    ET.SubElement(ide, f'{{{NFE_NS}}}nNF').text = n_nf
    
    dh_emi = format_datetime(cabecalho.get('dhEmi'))
    ET.SubElement(ide, f'{{{NFE_NS}}}dhEmi').text = dh_emi
    ET.SubElement(ide, f'{{{NFE_NS}}}dhSaiEnt').text = dh_emi
    
    tp_nf = str(cabecalho.get('tpNF') if cabecalho.get('tpNF') is not None and str(cabecalho.get('tpNF')).strip() != '' else '0')
    ET.SubElement(ide, f'{{{NFE_NS}}}tpNF').text = tp_nf
    
    id_dest = str(cabecalho.get('idDest') if cabecalho.get('idDest') is not None and str(cabecalho.get('idDest')).strip() != '' else '3')
    ET.SubElement(ide, f'{{{NFE_NS}}}idDest').text = id_dest
    
    c_mun_fg = str(cabecalho.get('emit_cMun') or '3550308').strip()
    if len(c_mun_fg) != 7 or not c_mun_fg.isdigit():
        c_mun_fg = '3550308'
    ET.SubElement(ide, f'{{{NFE_NS}}}cMunFG').text = c_mun_fg
    
    ET.SubElement(ide, f'{{{NFE_NS}}}tpImp').text = '1'
    
    tp_emis = str(cabecalho.get('tpEmis') or '1')
    ET.SubElement(ide, f'{{{NFE_NS}}}tpEmis').text = tp_emis
    
    # Calculate Access Key and cDV
    aamm = dh_emi[2:4] + dh_emi[5:7]
    cnpj_emit = re.sub(r'\D', '', str(cabecalho.get('emit_CNPJ') or '47998441000198')).zfill(14)
    serie_fmt = serie.zfill(3)
    nnf_fmt = n_nf.zfill(9)
    chave_43 = f"{c_uf}{aamm}{cnpj_emit}{mod}{serie_fmt}{nnf_fmt}{tp_emis}{c_nf}"
    cdv = str(calcular_cdv(chave_43))
    
    ET.SubElement(ide, f'{{{NFE_NS}}}cDV').text = cdv
    inf_nfe.attrib['Id'] = f"NFe{chave_43}{cdv}"
    
    tp_amb = str(cabecalho.get('tpAmb') or '2')
    ET.SubElement(ide, f'{{{NFE_NS}}}tpAmb').text = tp_amb
    ET.SubElement(ide, f'{{{NFE_NS}}}finNFe').text = '1'
    ET.SubElement(ide, f'{{{NFE_NS}}}indFinal').text = '0'
    ET.SubElement(ide, f'{{{NFE_NS}}}indPres').text = '0'
    ET.SubElement(ide, f'{{{NFE_NS}}}procEmi').text = '0'
    ver_proc = str(cabecalho.get('verProc') or '4.01_sebrae_b057').strip()
    if not ver_proc or ver_proc in ('4.01', '4.00'):
        ver_proc = '4.01_sebrae_b057'
    ET.SubElement(ide, f'{{{NFE_NS}}}verProc').text = ver_proc
    
    # 2. emit
    emit = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}emit')
    ET.SubElement(emit, f'{{{NFE_NS}}}CNPJ').text = cnpj_emit
    ET.SubElement(emit, f'{{{NFE_NS}}}xNome').text = remover_acentos_nfe(cabecalho.get('emit_xNome') or 'NFT LOGISTICS LTDA')[:60]
    
    ender_emit = ET.SubElement(emit, f'{{{NFE_NS}}}enderEmit')
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}xLgr').text = remover_acentos_nfe(cabecalho.get('emit_xLgr') or 'AV. DR. GASTAO VIDIGAL')[:60]
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}nro').text = remover_acentos_nfe(cabecalho.get('emit_nro') or '1132')[:60]
    cpl_emit = remover_acentos_nfe(cabecalho.get('emit_xCpl') or 'SALA 910 TORRE B')[:60]
    if cpl_emit:
        ET.SubElement(ender_emit, f'{{{NFE_NS}}}xCpl').text = cpl_emit
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}xBairro').text = remover_acentos_nfe(cabecalho.get('emit_xBairro') or 'VILA LEOPOLDINA')[:60]
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}cMun').text = c_mun_fg
    x_mun_emit = remover_acentos_nfe(cabecalho.get('emit_xMun') or 'SAO PAULO')
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}xMun').text = (x_mun_emit or 'SAO PAULO')[:60]
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}UF').text = str(cabecalho.get('emit_UF') or 'SP')[:2]
    cep_emit = re.sub(r'\D', '', str(cabecalho.get('emit_CEP') or '05314000')).zfill(8)
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}CEP').text = cep_emit
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}cPais').text = str(cabecalho.get('emit_cPais') or '1058')
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}xPais').text = remover_acentos_nfe(cabecalho.get('emit_xPais') or 'Brasil')[:60]
    
    ie_emit = re.sub(r'\D', '', str(cabecalho.get('emit_IE') or '138843326117'))
    ET.SubElement(emit, f'{{{NFE_NS}}}IE').text = ie_emit or '138843326117'
    ET.SubElement(emit, f'{{{NFE_NS}}}CRT').text = str(cabecalho.get('emit_CRT') or '1')
    
    # 3. dest
    dest = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}dest')
    dest_uf = str(cabecalho.get('dest_UF') or '').strip().upper()
    c_pais = str(cabecalho.get('dest_cPais') or '').strip()
    is_exterior = (id_dest == '3' or dest_uf == 'EX' or (c_pais and c_pais != '1058'))
    
    if is_exterior:
        id_estrangeiro = str(cabecalho.get('dest_idEstrangeiro') or cabecalho.get('dest_CNPJ_CPF') or '').strip()
        if len(id_estrangeiro) > 0 and len(id_estrangeiro) < 5:
            id_estrangeiro = ""
        elif len(id_estrangeiro) > 20:
            id_estrangeiro = id_estrangeiro[:20]
        # Tag <idEstrangeiro> deve constar no XML de exterior (mesmo que vazia <idEstrangeiro></idEstrangeiro>) para compatibilidade com o Emissor Sebrae
        id_est_el = ET.SubElement(dest, f'{{{NFE_NS}}}idEstrangeiro')
        id_est_el.text = id_estrangeiro if id_estrangeiro else ""
        ET.SubElement(dest, f'{{{NFE_NS}}}xNome').text = str(cabecalho.get('dest_xNome') or 'EXPORTADOR ESTRANGEIRO')[:60]
        
        ender_dest = ET.SubElement(dest, f'{{{NFE_NS}}}enderDest')
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xLgr').text = str(cabecalho.get('dest_xLgr') or 'EXTERIOR')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}nro').text = str(cabecalho.get('dest_nro') or 'SN')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xBairro').text = str(cabecalho.get('dest_xBairro') or 'EXTERIOR')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}cMun').text = '9999999'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xMun').text = 'EXTERIOR'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}UF').text = 'EX'
        cep_raw = re.sub(r'\D', '', str(cabecalho.get('dest_CEP') or ''))
        cep_dest_ext = cep_raw if (cep_raw and len(cep_raw) == 8) else '99999999'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}CEP').text = cep_dest_ext
        if not c_pais or c_pais == '1058':
            c_pais = '160'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}cPais').text = c_pais
        x_pais = str(cabecalho.get('dest_xPais') or '').strip()
        if not x_pais or x_pais.upper() in ('BRASIL', 'BRAZIL'):
            x_pais = 'CHINA, REPUBLICA POPULAR'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xPais').text = x_pais[:60]
        ET.SubElement(dest, f'{{{NFE_NS}}}indIEDest').text = '9'
    else:
        doc = re.sub(r'\D', '', str(cabecalho.get('dest_CNPJ_CPF') or ''))
        id_estrangeiro = str(cabecalho.get('dest_idEstrangeiro') or '').strip()
        if len(doc) > 11:
            ET.SubElement(dest, f'{{{NFE_NS}}}CNPJ').text = doc.zfill(14)
        elif len(doc) > 0:
            ET.SubElement(dest, f'{{{NFE_NS}}}CPF').text = doc.zfill(11)
        elif id_estrangeiro or dest_uf == 'EX' or c_pais != '1058':
            if len(id_estrangeiro) > 0 and len(id_estrangeiro) < 5:
                id_estrangeiro = ""
            elif len(id_estrangeiro) > 20:
                id_estrangeiro = id_estrangeiro[:20]
            id_est_el = ET.SubElement(dest, f'{{{NFE_NS}}}idEstrangeiro')
            id_est_el.text = id_estrangeiro if id_estrangeiro else ""
        else:
            id_est_el = ET.SubElement(dest, f'{{{NFE_NS}}}idEstrangeiro')
            id_est_el.text = ""
        ET.SubElement(dest, f'{{{NFE_NS}}}xNome').text = remover_acentos_nfe(cabecalho.get('dest_xNome') or '')[:60]
        ender_dest = ET.SubElement(dest, f'{{{NFE_NS}}}enderDest')
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xLgr').text = remover_acentos_nfe(cabecalho.get('dest_xLgr') or '')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}nro').text = remover_acentos_nfe(cabecalho.get('dest_nro') or 'SN')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xBairro').text = remover_acentos_nfe(cabecalho.get('dest_xBairro') or '')[:60]
        c_mun_dest = str(cabecalho.get('dest_cMun') or '').strip()
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}cMun').text = c_mun_dest or '3550308'
        x_mun_dest = remover_acentos_nfe(cabecalho.get('dest_xMun') or '')
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xMun').text = (x_mun_dest or 'SAO PAULO')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}UF').text = dest_uf or 'SP'
        cep_dest = re.sub(r'\D', '', str(cabecalho.get('dest_CEP') or '')).zfill(8)
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}CEP').text = cep_dest
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}cPais').text = '1058'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xPais').text = 'Brasil'
        ind_ie = str(cabecalho.get('dest_indIEDest') or '9')
        ET.SubElement(dest, f'{{{NFE_NS}}}indIEDest').text = ind_ie
        ie_val = str(cabecalho.get('dest_IE') or '').strip()
        if ind_ie == '1' and ie_val:
            ET.SubElement(dest, f'{{{NFE_NS}}}IE').text = re.sub(r'\D', '', ie_val)

    # 4. det items
    cfop_padrao = cabecalho.get('cfop_padrao')
    total_prod = 0.0
    total_frete = 0.0
    total_seg = 0.0
    total_outro = 0.0
    total_desc = 0.0
    total_ii = 0.0
    total_ipi = 0.0
    total_pis = 0.0
    total_cofins = 0.0
    
    for idx, item in enumerate(itens, start=1):
        det = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}det', {'nItem': str(idx)})
        prod = ET.SubElement(det, f'{{{NFE_NS}}}prod')
        
        c_prod = str(item.get('cProd') or f"ITEM{idx}")[:60]
        ET.SubElement(prod, f'{{{NFE_NS}}}cProd').text = c_prod
        
        c_ean = format_ean(item.get('cEAN'))
        ET.SubElement(prod, f'{{{NFE_NS}}}cEAN').text = c_ean
        
        x_prod = str(item.get('xProd') or f"PRODUTO {idx}")[:120]
        ET.SubElement(prod, f'{{{NFE_NS}}}xProd').text = x_prod
        
        ncm = re.sub(r'\D', '', str(item.get('NCM') or '00000000')).zfill(8)
        ET.SubElement(prod, f'{{{NFE_NS}}}NCM').text = ncm
        
        cfop_item = str(cfop_padrao if (cfop_padrao and cfop_padrao.strip()) else (item.get('CFOP') or '3101')).strip()
        m_cfop = re.search(r'\b([1-7]\d{3})\b', cfop_item)
        if m_cfop:
            cfop_item = m_cfop.group(1)
        ET.SubElement(prod, f'{{{NFE_NS}}}CFOP').text = cfop_item
        
        u_com = str(item.get('uCom') or 'UN')[:6]
        ET.SubElement(prod, f'{{{NFE_NS}}}uCom').text = u_com
        
        q_com = format_dec(item.get('qCom') or '1.0000', 4)
        ET.SubElement(prod, f'{{{NFE_NS}}}qCom').text = q_com
        
        v_un_com = format_dec(item.get('vUnCom') or '0.0000', 4)
        ET.SubElement(prod, f'{{{NFE_NS}}}vUnCom').text = v_un_com
        
        v_prod = format_dec(item.get('vProd') or '0.00', 2)
        ET.SubElement(prod, f'{{{NFE_NS}}}vProd').text = v_prod
        total_prod += float(v_prod)
        
        c_ean_trib = format_ean(item.get('cEANTrib'))
        ET.SubElement(prod, f'{{{NFE_NS}}}cEANTrib').text = c_ean_trib
        
        u_trib = str(item.get('uTrib') or u_com)[:6]
        ET.SubElement(prod, f'{{{NFE_NS}}}uTrib').text = u_trib
        
        q_trib = format_dec(item.get('qTrib') or q_com, 4)
        ET.SubElement(prod, f'{{{NFE_NS}}}qTrib').text = q_trib
        
        v_un_trib = format_dec(item.get('vUnTrib') or v_un_com, 4)
        ET.SubElement(prod, f'{{{NFE_NS}}}vUnTrib').text = v_un_trib
        
        # Despesas em prod
        v_frete = format_dec(item.get('vFrete'), 2)
        if not is_zero(v_frete):
            ET.SubElement(prod, f'{{{NFE_NS}}}vFrete').text = v_frete
            total_frete += float(v_frete)
            
        v_seg = format_dec(item.get('vSeg'), 2)
        if not is_zero(v_seg):
            ET.SubElement(prod, f'{{{NFE_NS}}}vSeg').text = v_seg
            total_seg += float(v_seg)
            
        v_desc = format_dec(item.get('vDesc'), 2)
        if not is_zero(v_desc):
            ET.SubElement(prod, f'{{{NFE_NS}}}vDesc').text = v_desc
            total_desc += float(v_desc)
            
        v_outro = format_dec(item.get('vOutro'), 2)
        if not is_zero(v_outro):
            ET.SubElement(prod, f'{{{NFE_NS}}}vOutro').text = v_outro
            total_outro += float(v_outro)
            
        ET.SubElement(prod, f'{{{NFE_NS}}}indTot').text = '1'
        
        # DI
        n_di = str(item.get('nDI') or '').strip()
        if not cfop_item.startswith('7') and n_di:
            di_el = ET.SubElement(prod, f'{{{NFE_NS}}}DI')
            ET.SubElement(di_el, f'{{{NFE_NS}}}nDI').text = n_di[:15]
            ET.SubElement(di_el, f'{{{NFE_NS}}}dDI').text = format_date(item.get('dDI'))
            ET.SubElement(di_el, f'{{{NFE_NS}}}xLocDesemb').text = str(item.get('xLocDesemb') or 'PORTO DE SANTOS')[:60]
            ET.SubElement(di_el, f'{{{NFE_NS}}}UFDesemb').text = str(item.get('UFDesemb') or 'SP')[:2]
            ET.SubElement(di_el, f'{{{NFE_NS}}}dDesemb').text = format_date(item.get('dDesemb') or item.get('dDI'))
            ET.SubElement(di_el, f'{{{NFE_NS}}}tpViaTransp').text = str(item.get('tpViaTransp') or '1')
            
            v_afrmm = format_dec(item.get('vAFRMM'), 2)
            if not is_zero(v_afrmm) or str(item.get('tpViaTransp')) == '1':
                ET.SubElement(di_el, f'{{{NFE_NS}}}vAFRMM').text = v_afrmm
                
            ET.SubElement(di_el, f'{{{NFE_NS}}}tpIntermedio').text = str(item.get('tpIntermedio') or '1')
            ET.SubElement(di_el, f'{{{NFE_NS}}}cExportador').text = str(item.get('cExportador') or cabecalho.get('dest_xNome') or 'EXPORTADOR')[:60]
            
            adi_el = ET.SubElement(di_el, f'{{{NFE_NS}}}adi')
            raw_adic = re.sub(r'\D', '', str(item.get('nAdicao') or idx)).lstrip('0')
            ET.SubElement(adi_el, f'{{{NFE_NS}}}nAdicao').text = raw_adic if raw_adic else '1'
            raw_seq = re.sub(r'\D', '', str(item.get('nSeqAdic') or '1')).lstrip('0')
            ET.SubElement(adi_el, f'{{{NFE_NS}}}nSeqAdic').text = raw_seq if raw_seq else '1'
            ET.SubElement(adi_el, f'{{{NFE_NS}}}cFabricante').text = str(item.get('cFabricante') or item.get('cExportador') or 'FABRICANTE')[:60]

        ET.SubElement(prod, f'{{{NFE_NS}}}nItemPed').text = str(idx)

        # imposto
        imposto = ET.SubElement(det, f'{{{NFE_NS}}}imposto')
        
        # ICMS
        icms = ET.SubElement(imposto, f'{{{NFE_NS}}}ICMS')
        orig = str(item.get('orig') or '1').strip()
        csosn_or_cst = re.sub(r'\D', '', str(item.get('CSOSN') or '102'))
        if len(csosn_or_cst) == 3:
            if csosn_or_cst in ['102', '103', '300', '400']:
                sn_node = ET.SubElement(icms, f'{{{NFE_NS}}}ICMSSN102')
                ET.SubElement(sn_node, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(sn_node, f'{{{NFE_NS}}}CSOSN').text = csosn_or_cst
            elif csosn_or_cst == '101':
                sn_node = ET.SubElement(icms, f'{{{NFE_NS}}}ICMSSN101')
                ET.SubElement(sn_node, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(sn_node, f'{{{NFE_NS}}}CSOSN').text = '101'
                ET.SubElement(sn_node, f'{{{NFE_NS}}}pCredSN').text = format_dec(item.get('pCredSN'), 2)
                ET.SubElement(sn_node, f'{{{NFE_NS}}}vCredICMSSN').text = format_dec(item.get('vCredICMSSN'), 2)
            elif csosn_or_cst == '900':
                sn_node = ET.SubElement(icms, f'{{{NFE_NS}}}ICMSSN900')
                ET.SubElement(sn_node, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(sn_node, f'{{{NFE_NS}}}CSOSN').text = '900'
            else:
                sn_node = ET.SubElement(icms, f'{{{NFE_NS}}}ICMSSN102')
                ET.SubElement(sn_node, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(sn_node, f'{{{NFE_NS}}}CSOSN').text = csosn_or_cst
        else:
            cst_icms = csosn_or_cst.zfill(2)
            if cst_icms in ['40', '41', '50']:
                node_icms = ET.SubElement(icms, f'{{{NFE_NS}}}ICMS40')
                ET.SubElement(node_icms, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(node_icms, f'{{{NFE_NS}}}CST').text = cst_icms
            elif cst_icms == '00':
                node_icms = ET.SubElement(icms, f'{{{NFE_NS}}}ICMS00')
                ET.SubElement(node_icms, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(node_icms, f'{{{NFE_NS}}}CST').text = '00'
                ET.SubElement(node_icms, f'{{{NFE_NS}}}modBC').text = '3'
                ET.SubElement(node_icms, f'{{{NFE_NS}}}vBC').text = format_dec(item.get('vBC_ICMS') or v_prod, 2)
                ET.SubElement(node_icms, f'{{{NFE_NS}}}pICMS').text = format_dec(item.get('pICMS'), 2)
                ET.SubElement(node_icms, f'{{{NFE_NS}}}vICMS').text = format_dec(item.get('vICMS'), 2)
            else:
                node_icms = ET.SubElement(icms, f'{{{NFE_NS}}}ICMS90')
                ET.SubElement(node_icms, f'{{{NFE_NS}}}orig').text = orig
                ET.SubElement(node_icms, f'{{{NFE_NS}}}CST').text = cst_icms
                ET.SubElement(node_icms, f'{{{NFE_NS}}}modBC').text = '3'
                ET.SubElement(node_icms, f'{{{NFE_NS}}}vBC').text = format_dec(item.get('vBC_ICMS') or v_prod, 2)
                ET.SubElement(node_icms, f'{{{NFE_NS}}}pICMS').text = format_dec(item.get('pICMS'), 2)
                ET.SubElement(node_icms, f'{{{NFE_NS}}}vICMS').text = format_dec(item.get('vICMS'), 2)

        # IPI
        ipi = ET.SubElement(imposto, f'{{{NFE_NS}}}IPI')
        c_enq = str(item.get('cEnq') or '999').strip().zfill(3)
        ET.SubElement(ipi, f'{{{NFE_NS}}}cEnq').text = c_enq
        cst_ipi = re.sub(r'\D', '', str(item.get('CST_IPI') or '05')).zfill(2)
        if cst_ipi in ['01', '02', '03', '04', '05', '51', '52', '53', '54', '55']:
            ipint = ET.SubElement(ipi, f'{{{NFE_NS}}}IPINT')
            ET.SubElement(ipint, f'{{{NFE_NS}}}CST').text = cst_ipi
        else:
            ipitrib = ET.SubElement(ipi, f'{{{NFE_NS}}}IPITrib')
            ET.SubElement(ipitrib, f'{{{NFE_NS}}}CST').text = cst_ipi
            vbc_ipi = format_dec(item.get('vBC_IPI') or v_prod, 2)
            p_ipi = format_dec(item.get('pIPI'), 2)
            v_ipi = format_dec(item.get('vIPI'), 2)
            ET.SubElement(ipitrib, f'{{{NFE_NS}}}vBC').text = vbc_ipi
            ET.SubElement(ipitrib, f'{{{NFE_NS}}}pIPI').text = p_ipi
            ET.SubElement(ipitrib, f'{{{NFE_NS}}}vIPI').text = v_ipi
            total_ipi += float(v_ipi)

        # II (always all 4 elements in exact order for imports)
        if not cfop_item.startswith('7'):
            ii_el = ET.SubElement(imposto, f'{{{NFE_NS}}}II')
            ET.SubElement(ii_el, f'{{{NFE_NS}}}vBC').text = format_dec(item.get('vBC_II') or v_prod, 2)
            ET.SubElement(ii_el, f'{{{NFE_NS}}}vDespAdu').text = format_dec(item.get('vDespAdu') if item.get('vDespAdu') is not None else item.get('vOutro'), 2)
            v_ii = format_dec(item.get('vII'), 2)
            ET.SubElement(ii_el, f'{{{NFE_NS}}}vII').text = v_ii
            ET.SubElement(ii_el, f'{{{NFE_NS}}}vIOF').text = format_dec(item.get('vIOF'), 2)
            total_ii += float(v_ii)

        # PIS
        pis = ET.SubElement(imposto, f'{{{NFE_NS}}}PIS')
        cst_pis = re.sub(r'\D', '', str(item.get('CST_PIS') or '07')).zfill(2)
        if cst_pis in ['04', '05', '06', '07', '08', '09']:
            pis_node = ET.SubElement(pis, f'{{{NFE_NS}}}PISNT')
            ET.SubElement(pis_node, f'{{{NFE_NS}}}CST').text = cst_pis
        elif cst_pis in ['01', '02']:
            pis_node = ET.SubElement(pis, f'{{{NFE_NS}}}PISAliq')
            ET.SubElement(pis_node, f'{{{NFE_NS}}}CST').text = cst_pis
            vbc_pis = format_dec(item.get('vBC_PIS') or v_prod, 2)
            p_pis = format_dec(item.get('pPIS'), 2)
            v_pis = format_dec(item.get('vPIS'), 2)
            ET.SubElement(pis_node, f'{{{NFE_NS}}}vBC').text = vbc_pis
            ET.SubElement(pis_node, f'{{{NFE_NS}}}pPIS').text = p_pis
            ET.SubElement(pis_node, f'{{{NFE_NS}}}vPIS').text = v_pis
            total_pis += float(v_pis)
        else:
            pis_node = ET.SubElement(pis, f'{{{NFE_NS}}}PISOutr')
            ET.SubElement(pis_node, f'{{{NFE_NS}}}CST').text = cst_pis
            vbc_pis = format_dec(item.get('vBC_PIS') or v_prod, 2)
            p_pis = format_dec(item.get('pPIS'), 2)
            v_pis = format_dec(item.get('vPIS'), 2)
            ET.SubElement(pis_node, f'{{{NFE_NS}}}vBC').text = vbc_pis
            ET.SubElement(pis_node, f'{{{NFE_NS}}}pPIS').text = p_pis
            ET.SubElement(pis_node, f'{{{NFE_NS}}}vPIS').text = v_pis
            total_pis += float(v_pis)

        # COFINS
        cofins = ET.SubElement(imposto, f'{{{NFE_NS}}}COFINS')
        cst_cofins = re.sub(r'\D', '', str(item.get('CST_COFINS') or '07')).zfill(2)
        if cst_cofins in ['04', '05', '06', '07', '08', '09']:
            cofins_node = ET.SubElement(cofins, f'{{{NFE_NS}}}COFINSNT')
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}CST').text = cst_cofins
        elif cst_cofins in ['01', '02']:
            cofins_node = ET.SubElement(cofins, f'{{{NFE_NS}}}COFINSAliq')
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}CST').text = cst_cofins
            vbc_cofins = format_dec(item.get('vBC_COFINS') or v_prod, 2)
            p_cofins = format_dec(item.get('pCOFINS'), 2)
            v_cofins = format_dec(item.get('vCOFINS'), 2)
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}vBC').text = vbc_cofins
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}pCOFINS').text = p_cofins
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}vCOFINS').text = v_cofins
            total_cofins += float(v_cofins)
        else:
            cofins_node = ET.SubElement(cofins, f'{{{NFE_NS}}}COFINSOutr')
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}CST').text = cst_cofins
            vbc_cofins = format_dec(item.get('vBC_COFINS') or v_prod, 2)
            p_cofins = format_dec(item.get('pCOFINS'), 2)
            v_cofins = format_dec(item.get('vCOFINS'), 2)
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}vBC').text = vbc_cofins
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}pCOFINS').text = p_cofins
            ET.SubElement(cofins_node, f'{{{NFE_NS}}}vCOFINS').text = v_cofins
            total_cofins += float(v_cofins)

    # 5. total
    tot_data = rodape.get('totais', {})
    total_el = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}total')
    icms_tot = ET.SubElement(total_el, f'{{{NFE_NS}}}ICMSTot')
    
    v_prod_tot = tot_data.get('vProd') or f"{total_prod:.2f}"
    v_frete_tot = tot_data.get('vFrete') or f"{total_frete:.2f}"
    v_seg_tot = tot_data.get('vSeg') or f"{total_seg:.2f}"
    v_desc_tot = tot_data.get('vDesc') or f"{total_desc:.2f}"
    v_outro_tot = tot_data.get('vOutro') or f"{total_outro:.2f}"
    v_ii_tot = tot_data.get('vII') or f"{total_ii:.2f}"
    v_ipi_tot = tot_data.get('vIPI') or f"{total_ipi:.2f}"
    v_pis_tot = tot_data.get('vPIS') or f"{total_pis:.2f}"
    v_cofins_tot = tot_data.get('vCOFINS') or f"{total_cofins:.2f}"
    
    # Calculate vNF
    v_nf_val = tot_data.get('vNF') or rodape.get('vNF')
    if not v_nf_val or is_zero(v_nf_val):
        v_nf_calc = (float(format_dec(v_prod_tot, 2)) - float(format_dec(v_desc_tot, 2)) +
                     float(format_dec(v_frete_tot, 2)) + float(format_dec(v_seg_tot, 2)) +
                     float(format_dec(v_outro_tot, 2)) + float(format_dec(v_ii_tot, 2)) +
                     float(format_dec(v_ipi_tot, 2)))
        v_nf_tot = f"{v_nf_calc:.2f}"
    else:
        v_nf_tot = format_dec(v_nf_val, 2)
        
    for k, v in [
        ('vBC', format_dec(tot_data.get('vBC'), 2)),
        ('vICMS', format_dec(tot_data.get('vICMS'), 2)),
        ('vICMSDeson', format_dec(tot_data.get('vICMSDeson'), 2)),
        ('vFCP', format_dec(tot_data.get('vFCP'), 2)),
        ('vBCST', format_dec(tot_data.get('vBCST'), 2)),
        ('vST', format_dec(tot_data.get('vST'), 2)),
        ('vFCPST', format_dec(tot_data.get('vFCPST'), 2)),
        ('vFCPSTRet', format_dec(tot_data.get('vFCPSTRet'), 2)),
        ('vProd', format_dec(v_prod_tot, 2)),
        ('vFrete', format_dec(v_frete_tot, 2)),
        ('vSeg', format_dec(v_seg_tot, 2)),
        ('vDesc', format_dec(v_desc_tot, 2)),
        ('vII', format_dec(v_ii_tot, 2)),
        ('vIPI', format_dec(v_ipi_tot, 2)),
        ('vIPIDevol', format_dec(tot_data.get('vIPIDevol'), 2)),
        ('vPIS', format_dec(v_pis_tot, 2)),
        ('vCOFINS', format_dec(v_cofins_tot, 2)),
        ('vOutro', format_dec(v_outro_tot, 2)),
        ('vNF', format_dec(v_nf_tot, 2)),
    ]:
        ET.SubElement(icms_tot, f'{{{NFE_NS}}}{k}').text = v

    # 6. transp
    transp_data = rodape.get('transporte', {})
    transp_el = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}transp')
    mod_frete = str(transp_data.get('modFrete') if transp_data.get('modFrete') is not None and str(transp_data.get('modFrete')).strip() != '' else '1')
    ET.SubElement(transp_el, f'{{{NFE_NS}}}modFrete').text = mod_frete
    
    doc_transp = re.sub(r'\D', '', str(transp_data.get('CNPJ_CPF') or ''))
    x_nome_transp = str(transp_data.get('xNome') or '').strip()
    if doc_transp or x_nome_transp:
        transporta = ET.SubElement(transp_el, f'{{{NFE_NS}}}transporta')
        if len(doc_transp) > 11:
            ET.SubElement(transporta, f'{{{NFE_NS}}}CNPJ').text = doc_transp.zfill(14)
        elif doc_transp:
            ET.SubElement(transporta, f'{{{NFE_NS}}}CPF').text = doc_transp.zfill(11)
        if x_nome_transp:
            ET.SubElement(transporta, f'{{{NFE_NS}}}xNome').text = remover_acentos_nfe(x_nome_transp)[:60]
        ie_transp = str(transp_data.get('IE') or '').strip()
        if ie_transp:
            ET.SubElement(transporta, f'{{{NFE_NS}}}IE').text = ie_transp[:14]
        x_ender_transp = remover_acentos_nfe(transp_data.get('xEnder') or '').strip()
        if x_ender_transp:
            ET.SubElement(transporta, f'{{{NFE_NS}}}xEnder').text = x_ender_transp[:60]
        x_mun_transp = remover_acentos_nfe(transp_data.get('xMun') or '').strip()
        if x_mun_transp:
            ET.SubElement(transporta, f'{{{NFE_NS}}}xMun').text = x_mun_transp[:60]
        uf_transp = str(transp_data.get('UF') or '').strip().upper()
        if uf_transp:
            ET.SubElement(transporta, f'{{{NFE_NS}}}UF').text = uf_transp[:2]

    # vol
    q_vol = str(transp_data.get('qVol') or '').strip()
    esp = str(transp_data.get('esp') or '').strip()
    peso_l = format_dec(transp_data.get('pesoL'), 3)
    peso_b = format_dec(transp_data.get('pesoB'), 3)
    if q_vol or esp or not is_zero(peso_l) or not is_zero(peso_b):
        vol_el = ET.SubElement(transp_el, f'{{{NFE_NS}}}vol')
        if q_vol and q_vol.isdigit():
            ET.SubElement(vol_el, f'{{{NFE_NS}}}qVol').text = q_vol
        if esp:
            ET.SubElement(vol_el, f'{{{NFE_NS}}}esp').text = esp[:60]
        if not is_zero(peso_l):
            ET.SubElement(vol_el, f'{{{NFE_NS}}}pesoL').text = peso_l
        if not is_zero(peso_b):
            ET.SubElement(vol_el, f'{{{NFE_NS}}}pesoB').text = peso_b

    # 7. pag (Mandatory in NF-e 4.00!)
    pag_el = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}pag')
    det_pag = ET.SubElement(pag_el, f'{{{NFE_NS}}}detPag')
    t_pag = str(rodape.get('tPag') or '90').strip()
    ET.SubElement(det_pag, f'{{{NFE_NS}}}tPag').text = t_pag
    if t_pag == '90':
        ET.SubElement(det_pag, f'{{{NFE_NS}}}vPag').text = '0.00'
    else:
        ET.SubElement(det_pag, f'{{{NFE_NS}}}vPag').text = format_dec(v_nf_tot, 2)

    # 8. infAdic
    inf_cpl = str(rodape.get('infCpl') or '').strip()
    if inf_cpl:
        inf_adic = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}infAdic')
        ET.SubElement(inf_adic, f'{{{NFE_NS}}}infCpl').text = inf_cpl[:5000]

    # 9. Signature (Obrigatorio para importacao no Emissor Gratuito Sebrae/DSEN)
    append_signature(root, inf_nfe)

    return root

@app.route('/')
def portal():
    return render_template('portal.html')

@app.route('/rascunho')
@app.route('/editor')
def index():
    return render_template('index.html')

@app.route('/di_duimp')
@app.route('/duimp')
def modulo_di_duimp():
    return render_template('di_duimp.html')

@app.route('/nova_nf')
def modulo_nova_nf():
    return render_template('nova_nf.html')


# === ROTAS DE EMPRESAS ===
@app.route('/empresas')
def page_empresas():
    return render_template('empresas.html')

@app.route('/api/empresas', methods=['GET', 'POST'])
def api_empresas():
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('''
            INSERT INTO cadastros (tipo, nome, cnpj_cpf, ie, logradouro, numero, bairro, municipio, uf, cep, cpais, xpais, cmun, fone, apelido, ind_ie)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('tipo', ''), data.get('nome', ''), data.get('cnpj_cpf', ''), data.get('ie', ''),
            data.get('logradouro', ''), data.get('numero', ''), data.get('bairro', ''),
            data.get('municipio', ''), data.get('uf', ''), data.get('cep', ''),
            data.get('cpais', ''), data.get('xpais', ''), data.get('cmun', ''), data.get('fone', ''),
            data.get('apelido', ''), data.get('ind_ie', '')
        ))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    
    c.execute('SELECT * FROM cadastros')
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/empresas/<int:cid>', methods=['PUT', 'DELETE'])
def api_edit_delete_empresa(cid):
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM cadastros WHERE id = ?', (cid,))
    elif request.method == 'PUT':
        data = request.json
        c.execute('''
            UPDATE cadastros
            SET tipo=?, nome=?, cnpj_cpf=?, ie=?, logradouro=?, numero=?, bairro=?, municipio=?, uf=?, cep=?, cpais=?, xpais=?, cmun=?, fone=?, apelido=?, ind_ie=?
            WHERE id = ?
        ''', (
            data.get('tipo', ''), data.get('nome', ''), data.get('cnpj_cpf', ''), data.get('ie', ''),
            data.get('logradouro', ''), data.get('numero', ''), data.get('bairro', ''),
            data.get('municipio', ''), data.get('uf', ''), data.get('cep', ''),
            data.get('cpais', ''), data.get('xpais', ''), data.get('cmun', ''), data.get('fone', ''),
            data.get('apelido', ''), data.get('ind_ie', ''),
            cid
        ))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# === SERVIÇO & ROTAS: CÂMBIO PTAX

def consultar_moedas_ptax():
    url = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/Moedas?$format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('value', [])
    except Exception:
        # Fallback offline garantido com as moedas oficiais PTAX Bacen
        return [
            {"simbolo": "USD", "nomeFormatado": "Dólar dos Estados Unidos", "tipoMoeda": "A"},
            {"simbolo": "EUR", "nomeFormatado": "Euro", "tipoMoeda": "B"},
            {"simbolo": "GBP", "nomeFormatado": "Libra Esterlina", "tipoMoeda": "B"},
            {"simbolo": "JPY", "nomeFormatado": "Iene", "tipoMoeda": "A"},
            {"simbolo": "CAD", "nomeFormatado": "Dólar Canadense", "tipoMoeda": "A"},
            {"simbolo": "CHF", "nomeFormatado": "Franco Suíço", "tipoMoeda": "A"},
            {"simbolo": "AUD", "nomeFormatado": "Dólar Australiano", "tipoMoeda": "B"},
            {"simbolo": "SEK", "nomeFormatado": "Coroa Sueca", "tipoMoeda": "A"},
            {"simbolo": "NOK", "nomeFormatado": "Coroa Norueguesa", "tipoMoeda": "A"},
            {"simbolo": "DKK", "nomeFormatado": "Coroa Dinamarquesa", "tipoMoeda": "A"}
        ]

def consultar_cotacao_ptax(moeda='USD', data_ref_str=None):
    moeda = (moeda or 'USD').strip().upper()
    if data_ref_str:
        s = data_ref_str.strip()
        try:
            if '-' in s:
                d_ref = datetime.strptime(s[:10], '%Y-%m-%d').date()
            elif '/' in s:
                d_ref = datetime.strptime(s[:10], '%d/%m/%Y').date()
            else:
                d_ref = date.today()
        except Exception:
            d_ref = date.today()
    else:
        d_ref = date.today()

    # Janela de até 15 dias anteriores para cobrir feriados prolongados e fins de semana
    d_fim = d_ref.strftime('%m-%d-%Y')
    d_ini = (d_ref - timedelta(days=15)).strftime('%m-%d-%Y')

    encoded_moeda = urllib.parse.quote(f"'{moeda}'")
    encoded_d_ini = urllib.parse.quote(f"'{d_ini}'")
    encoded_d_fim = urllib.parse.quote(f"'{d_fim}'")

    url = (
        f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        f"CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
        f"@moeda={encoded_moeda}&@dataInicial={encoded_d_ini}&@dataFinalCotacao={encoded_d_fim}&"
        f"$orderby=dataHoraCotacao%20desc&$top=15&$format=json"
    )

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            vals = data.get('value', [])
            if not vals:
                return None
            
            latest = vals[0]
            dt_raw = latest.get('dataHoraCotacao', '')
            dt_formatada = ""
            hora_formatada = ""
            if dt_raw:
                try:
                    partes = dt_raw.split(' ')
                    d_obj = datetime.strptime(partes[0], '%Y-%m-%d')
                    dt_formatada = d_obj.strftime('%d/%m/%Y')
                    hora_formatada = partes[1][:8] if len(partes) > 1 else ""
                except Exception:
                    dt_formatada = dt_raw
            
            return {
                "moeda": moeda,
                "cotacao_venda": latest.get('cotacaoVenda'),
                "cotacao_compra": latest.get('cotacaoCompra'),
                "tipo_boletim": latest.get('tipoBoletim', 'Boletim PTAX'),
                "data_hora": dt_raw,
                "data_cotacao": dt_formatada,
                "hora_cotacao": hora_formatada,
                "paridade_venda": latest.get('paridadeVenda'),
                "paridade_compra": latest.get('paridadeCompra'),
                "historico": vals[:6]
            }
    except Exception as e:
        raise RuntimeError(f"Erro ao consultar API PTAX do Banco Central: {e}")

@app.route('/api/ptax/moedas', methods=['GET'])
def api_ptax_moedas():
    try:
        moedas = consultar_moedas_ptax()
        return jsonify({"status": "success", "moedas": moedas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ptax/cotacao', methods=['GET'])
def api_ptax_cotacao():
    moeda = request.args.get('moeda', 'USD').strip().upper()
    data_cotacao = request.args.get('data', '').strip()
    try:
        resultado = consultar_cotacao_ptax(moeda, data_cotacao)
        if not resultado:
            return jsonify({
                "status": "not_found",
                "error": f"Nenhuma cotação encontrada para a moeda '{moeda}' na data informada ou período recente."
            }), 404
        return jsonify({"status": "success", **resultado})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === ROTAS: CSTS OFICIAIS (ICMS, CSOSN, IPI, PIS, COFINS) ===
@app.route('/api/csts', methods=['GET'])
def api_get_csts():
    tipo = request.args.get('tipo', '').strip().upper()
    conn = get_db_connection()
    c = conn.cursor()
    if tipo:
        c.execute('SELECT tipo_imposto, codigo, descricao, codigo_descricao, aplicacao FROM tabela_csts WHERE tipo_imposto = ? ORDER BY codigo ASC', (tipo,))
    else:
        c.execute('SELECT tipo_imposto, codigo, descricao, codigo_descricao, aplicacao FROM tabela_csts ORDER BY tipo_imposto, codigo ASC')
    rows = c.fetchall()
    conn.close()

    res = {
        'icms_csosn': [],
        'icms': [],
        'csosn': [],
        'ipi': [],
        'pis_cofins': [],
        'all': []
    }
    for r in rows:
        item = {
            'tipo_imposto': r['tipo_imposto'],
            'codigo': r['codigo'],
            'descricao': r['descricao'],
            'codigo_descricao': r['codigo_descricao'] or f"{r['codigo']} - {r['descricao']}",
            'aplicacao': r['aplicacao']
        }
        res['all'].append(item)
        if r['tipo_imposto'] == 'ICMS':
            res['icms'].append(item)
            res['icms_csosn'].append(item)
        elif r['tipo_imposto'] == 'CSOSN':
            res['csosn'].append(item)
            res['icms_csosn'].append(item)
        elif r['tipo_imposto'] == 'IPI':
            res['ipi'].append(item)
        elif r['tipo_imposto'] == 'PIS_COFINS':
            res['pis_cofins'].append(item)

    return jsonify({"status": "success", "csts": res})

# === ROTAS: TIPOS DE NOTA / OPERAÇÃO ===
@app.route('/tipos_operacao', methods=['GET'])
def get_tipos_operacao():
    conn = get_db_connection()
    ops = conn.execute('SELECT * FROM tipos_operacao ORDER BY nome_operacao ASC').fetchall()
    conn.close()
    return jsonify([dict(x) for x in ops])

@app.route('/tipos_operacao', methods=['POST'])
def save_tipo_operacao():
    data = request.json
    nome = data.get('nome_operacao', '').strip()
    if not nome:
        return jsonify({"error": "Nome da operação é obrigatório"}), 400

    conn = get_db_connection()
    c = conn.cursor()
    
    # Se ja existe com esse nome, atualiza. Senao, insere.
    existente = c.execute('SELECT id FROM tipos_operacao WHERE nome_operacao = ?', (nome,)).fetchone()
    
    tp_nf = str(data.get('tp_nf', '0'))
    id_dest = str(data.get('id_dest', '3'))
    csosn_icms = limpar_cst(data.get('csosn_icms', '102'))
    c_enq_ipi = str(data.get('c_enq_ipi', '102')).strip()
    cst_ipi = limpar_cst(data.get('cst_ipi', '05'))
    cst_pis = limpar_cst(data.get('cst_pis', '07'))
    cst_cofins = limpar_cst(data.get('cst_cofins', '07'))

    if existente:
        c.execute('''
            UPDATE tipos_operacao SET
                cfop_padrao = ?, tp_nf = ?, id_dest = ?, orig_padrao = ?, csosn_icms = ?, c_enq_ipi = ?,
                cst_ipi = ?, p_ipi = ?, aliquota_ii = ?, cst_pis = ?, p_pis = ?,
                cst_cofins = ?, p_cofins = ?, inf_cpl_padrao = ?
            WHERE nome_operacao = ?
        ''', (
            data.get('cfop_padrao', ''),
            tp_nf,
            id_dest,
            data.get('orig_padrao', '1'),
            csosn_icms,
            c_enq_ipi,
            cst_ipi,
            float(data.get('p_ipi', 0) or 0),
            float(data.get('aliquota_ii', 0) or 0),
            cst_pis,
            float(data.get('p_pis', 0) or 0),
            cst_cofins,
            float(data.get('p_cofins', 0) or 0),
            data.get('inf_cpl_padrao', ''),
            nome
        ))
    else:
        c.execute('''
            INSERT INTO tipos_operacao (
                nome_operacao, cfop_padrao, tp_nf, id_dest, orig_padrao, csosn_icms, c_enq_ipi,
                cst_ipi, p_ipi, aliquota_ii, cst_pis, p_pis, cst_cofins, p_cofins, inf_cpl_padrao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nome,
            data.get('cfop_padrao', ''),
            tp_nf,
            id_dest,
            data.get('orig_padrao', '1'),
            csosn_icms,
            c_enq_ipi,
            cst_ipi,
            float(data.get('p_ipi', 0) or 0),
            float(data.get('aliquota_ii', 0) or 0),
            cst_pis,
            float(data.get('p_pis', 0) or 0),
            cst_cofins,
            float(data.get('p_cofins', 0) or 0),
            data.get('inf_cpl_padrao', '')
        ))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Operação '{nome}' salva com sucesso!"})

@app.route('/tipos_operacao/<int:op_id>', methods=['DELETE'])
def delete_tipo_operacao(op_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Obter nome da operação antes da exclusão
    op = c.execute('SELECT nome_operacao FROM tipos_operacao WHERE id = ?', (op_id,)).fetchone()
    nome_op = op['nome_operacao'] if op else None

    c.execute('DELETE FROM tipos_operacao WHERE id = ?', (op_id,))

    # Se a operação deletada era a última ativa em algum módulo, desassocia da configuração persistente
    if nome_op:
        c.execute("DELETE FROM sistema_config WHERE valor = ? AND chave LIKE 'ultima_operacao_%'", (nome_op,))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Operação excluída definitivamente."})

# === ROTAS: CONFIGURAÇÕES E DECISÕES PERSISTENTES DO SISTEMA ===
@app.route('/api/config/ultima_operacao', methods=['GET'])
def get_ultima_operacao():
    modulo = request.args.get('modulo', 'rascunho')
    chave = f"ultima_operacao_{modulo}"
    conn = get_db_connection()
    row = conn.execute("SELECT valor FROM sistema_config WHERE chave = ?", (chave,)).fetchone()
    if not row or not row['valor']:
        conn.close()
        return jsonify({"status": "success", "ultima_operacao": None})
    
    nome_op = row['valor']
    # Confirma se a operação ainda existe na tabela tipos_operacao
    op = conn.execute("SELECT * FROM tipos_operacao WHERE nome_operacao = ?", (nome_op,)).fetchone()
    if not op:
        # Se foi excluída, limpa a referência da configuração
        conn.execute("DELETE FROM sistema_config WHERE chave = ?", (chave,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "ultima_operacao": None})
    
    op_dict = dict(op)
    conn.close()
    return jsonify({"status": "success", "ultima_operacao": nome_op, "dados_operacao": op_dict})

@app.route('/api/config/ultima_operacao', methods=['POST'])
def set_ultima_operacao():
    data = request.json or {}
    modulo = data.get('modulo', 'rascunho')
    nome_operacao = (data.get('nome_operacao') or '').strip()
    chave = f"ultima_operacao_{modulo}"
    conn = get_db_connection()
    if nome_operacao:
        conn.execute(
            "INSERT OR REPLACE INTO sistema_config (chave, valor, data_atualizacao) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (chave, nome_operacao)
        )
    else:
        conn.execute("DELETE FROM sistema_config WHERE chave = ?", (chave,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "modulo": modulo, "ultima_operacao": nome_operacao})

@app.route('/api/config/salvar', methods=['POST'])
def salvar_config_geral():
    data = request.json or {}
    chave = data.get('chave')
    valor = data.get('valor')
    if not chave:
        return jsonify({"error": "Chave é obrigatória"}), 400
    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO sistema_config (chave, valor, data_atualizacao) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (str(chave), str(valor) if valor is not None else "")
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "chave": chave, "valor": valor})

@app.route('/api/config/obter', methods=['GET'])
def obter_config_geral():
    chave = request.args.get('chave')
    if not chave:
        return jsonify({"error": "Chave é obrigatória"}), 400
    conn = get_db_connection()
    row = conn.execute("SELECT valor FROM sistema_config WHERE chave = ?", (chave,)).fetchone()
    conn.close()
    valor = row['valor'] if row else None
    return jsonify({"status": "success", "chave": chave, "valor": valor})

# === ROTAS: GESTÃO DE RASCUNHOS SALVOS (ISOLADOS EM ARQUIVO & INDEXADOS NO BD) ===
RASCUNHOS_DIR = os.path.join(os.path.dirname(__file__), 'rascunhos')
os.makedirs(RASCUNHOS_DIR, exist_ok=True)

@app.route('/api/rascunhos/salvar', methods=['POST'])
def salvar_rascunho():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Dados inválidos para o rascunho"}), 400

        rascunho_id = data.get('id')
        referencia_interna = str(data.get('referencia_interna') or '').strip()
        categoria = str(data.get('categoria') or 'Geral').strip() or 'Geral'
        origem = str(data.get('origem') or 'XML Rascunho').strip()
        tipo_operacao = str(data.get('tipo_operacao') or '').strip()
        operacao_id = str(data.get('operacao_id') or '').strip()
        nome_arquivo_original = str(data.get('nome_arquivo_original') or '').strip()
        chave_acesso = str(data.get('chave_acesso') or '').strip()
        
        # Itens e Quantidade de Itens
        itens = data.get('itens') or (data.get('dados_completos') or {}).get('itens') or []
        qtd_itens_input = data.get('qtd_itens')
        if qtd_itens_input is not None and str(qtd_itens_input).strip() != '':
            try:
                qtd_itens = int(qtd_itens_input)
            except Exception:
                qtd_itens = len(itens)
        else:
            qtd_itens = len(itens)
        
        # Calcular valor total da nota
        valor_total = 0.0
        val_direto = data.get('valor_total')
        if val_direto is not None and str(val_direto).strip() != '':
            try:
                s_val = str(val_direto).strip()
                if ',' in s_val and '.' in s_val:
                    s_val = s_val.replace('.', '').replace(',', '.')
                elif ',' in s_val:
                    s_val = s_val.replace(',', '.')
                valor_total = float(s_val)
            except Exception:
                valor_total = 0.0

        if valor_total <= 0.0:
            totais = data.get('totais') or {}
            v_nf = totais.get('vNF') or (data.get('dados_completos') or {}).get('cabecalho', {}).get('tot_vNF') or (data.get('dados_completos') or {}).get('cabecalho', {}).get('vNF')
            if v_nf is not None and str(v_nf).strip() != '':
                try:
                    s_vnf = str(v_nf).strip()
                    if ',' in s_vnf and '.' in s_vnf:
                        s_vnf = s_vnf.replace('.', '').replace(',', '.')
                    elif ',' in s_vnf:
                        s_vnf = s_vnf.replace(',', '.')
                    valor_total = float(s_vnf)
                except Exception:
                    valor_total = 0.0
                
        if valor_total <= 0.0:
            for it in itens:
                try:
                    vp = it.get('vProd', 0)
                    s_vp = str(vp).strip()
                    if ',' in s_vp and '.' in s_vp:
                        s_vp = s_vp.replace('.', '').replace(',', '.')
                    elif ',' in s_vp:
                        s_vp = s_vp.replace(',', '.')
                    valor_total += float(s_vp)
                except Exception:
                    pass

        conn = get_db_connection()
        c = conn.cursor()

        is_update = False
        if rascunho_id:
            try:
                rascunho_id = int(rascunho_id)
                row_check = c.execute("SELECT id FROM rascunhos WHERE id = ?", (rascunho_id,)).fetchone()
                if row_check:
                    is_update = True
            except (ValueError, TypeError):
                is_update = False

        if is_update:
            c.execute('''
                UPDATE rascunhos SET
                    referencia_interna = ?,
                    categoria = ?,
                    origem = ?,
                    tipo_operacao = ?,
                    operacao_id = ?,
                    nome_arquivo_original = CASE WHEN ? != '' THEN ? ELSE nome_arquivo_original END,
                    qtd_itens = ?,
                    valor_total = ?,
                    chave_acesso = ?,
                    data_atualizacao = datetime('now', 'localtime')
                WHERE id = ?
            ''', (
                referencia_interna, categoria, origem, tipo_operacao, operacao_id,
                nome_arquivo_original, nome_arquivo_original, qtd_itens, round(valor_total, 2),
                chave_acesso, rascunho_id
            ))
            conn.commit()
            arquivo_nome = f'rascunho_{rascunho_id}.json'
        else:
            c.execute('''
                INSERT INTO rascunhos (
                    referencia_interna, categoria, origem, tipo_operacao, operacao_id,
                    nome_arquivo_original, caminho_arquivo_isolado, qtd_itens, valor_total,
                    chave_acesso, data_criacao, data_atualizacao
                ) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            ''', (
                referencia_interna, categoria, origem, tipo_operacao, operacao_id,
                nome_arquivo_original, qtd_itens, round(valor_total, 2), chave_acesso
            ))
            rascunho_id = c.lastrowid
            arquivo_nome = f'rascunho_{rascunho_id}.json'
            c.execute('UPDATE rascunhos SET caminho_arquivo_isolado = ? WHERE id = ?', (arquivo_nome, rascunho_id))
            conn.commit()

        conn.close()

        # Salvar o payload completo no arquivo isolado em disco
        caminho_arquivo = os.path.join(RASCUNHOS_DIR, arquivo_nome)
        data['id'] = rascunho_id
        data['referencia_interna'] = referencia_interna
        data['categoria'] = categoria
        data['origem'] = origem
        data['tipo_operacao'] = tipo_operacao
        data['operacao_id'] = operacao_id
        data['nome_arquivo_original'] = nome_arquivo_original
        data['qtd_itens'] = qtd_itens
        data['valor_total'] = round(valor_total, 2)
        data['data_salvo'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({
            "success": True,
            "id": rascunho_id,
            "referencia_interna": referencia_interna,
            "categoria": categoria,
            "origem": origem,
            "tipo_operacao": tipo_operacao,
            "qtd_itens": qtd_itens,
            "valor_total": round(valor_total, 2),
            "message": f"Rascunho '{referencia_interna or 'ID #' + str(rascunho_id)}' salvo com sucesso em arquivo isolado e banco de dados!"
        })

    except Exception as e:
        return jsonify({"error": f"Falha ao salvar rascunho: {str(e)}"}), 500

@app.route('/api/rascunhos', methods=['GET'])
def listar_rascunhos():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        categoria = request.args.get('categoria', '').strip()
        origem = request.args.get('origem', '').strip()
        busca = request.args.get('busca', '').strip()
        
        query = """
            SELECT id, referencia_interna, categoria, origem, tipo_operacao, operacao_id, 
                   nome_arquivo_original, caminho_arquivo_isolado, qtd_itens, valor_total, 
                   chave_acesso, data_criacao, data_atualizacao,
                   COALESCE(strftime('%d/%m/%Y %H:%M', data_atualizacao), strftime('%d/%m/%Y %H:%M', data_criacao), strftime('%d/%m/%Y %H:%M', 'now', 'localtime')) as data_atualizacao_formatada,
                   COALESCE(strftime('%d/%m/%Y %H:%M', data_criacao), strftime('%d/%m/%Y %H:%M', 'now', 'localtime')) as data_criacao_formatada
            FROM rascunhos 
            WHERE 1=1
        """
        params = []
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        if origem:
            query += " AND origem = ?"
            params.append(origem)
        if busca:
            query += " AND (referencia_interna LIKE ? OR tipo_operacao LIKE ? OR nome_arquivo_original LIKE ? OR categoria LIKE ?)"
            lk = f"%{busca}%"
            params.extend([lk, lk, lk, lk])
            
        query += " ORDER BY data_atualizacao DESC, id DESC"
        rows = c.execute(query, params).fetchall()
        rascunhos = [dict(r) for r in rows]
        conn.close()
        return jsonify({"rascunhos": rascunhos, "total": len(rascunhos)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rascunhos/<int:rascunho_id>', methods=['GET'])
def obter_rascunho(rascunho_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        row = c.execute("SELECT * FROM rascunhos WHERE id = ?", (rascunho_id,)).fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Rascunho não encontrado"}), 404
            
        caminho_arquivo = os.path.join(RASCUNHOS_DIR, f'rascunho_{rascunho_id}.json')
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            payload['id'] = row['id']
            payload['referencia_interna'] = row['referencia_interna']
            payload['categoria'] = row['categoria']
            payload['origem'] = row['origem']
            payload['tipo_operacao'] = row['tipo_operacao']
            payload['operacao_id'] = row['operacao_id']
            return jsonify(payload)
        else:
            return jsonify(dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rascunhos/<int:rascunho_id>', methods=['DELETE'])
def excluir_rascunho(rascunho_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM rascunhos WHERE id = ?", (rascunho_id,))
        conn.commit()
        conn.close()
        
        caminho_arquivo = os.path.join(RASCUNHOS_DIR, f'rascunho_{rascunho_id}.json')
        if os.path.exists(caminho_arquivo):
            try:
                os.remove(caminho_arquivo)
            except Exception:
                pass
                
        return jsonify({"success": True, "message": "Rascunho excluído com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rascunhos/categorias', methods=['GET'])
def listar_categorias_rascunhos():
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT DISTINCT categoria FROM rascunhos WHERE categoria IS NOT NULL AND categoria != ''").fetchall()
        conn.close()
        base_cats = ['Geral', 'Importação', 'Exportação', 'Remessa', 'Devolução', 'Vendas']
        db_cats = [r['categoria'] for r in rows if r['categoria']]
        all_cats = list(dict.fromkeys(base_cats + db_cats))
        return jsonify(all_cats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# === ROTA: UPLOAD DI / DUIMP ===
@app.route('/upload_di_duimp', methods=['POST'])
def upload_di_duimp():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    try:
        tree = ET.parse(file)
        root = tree.getroot()
        
        if root.tag == 'ListaDeclaracoes' or root.find('.//declaracaoImportacao') is not None:
            return process_di_xml(root)
        else:
            return jsonify({"error": "Formato de arquivo nao reconhecido como DI ou DUIMP."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def process_di_xml(root):
    import re
    import sqlite3
    import os
    import xml.etree.ElementTree as ET
    from flask import jsonify

    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    
    numero_di = root.findtext('.//numeroDI', '')
    data_di = ""
    d_registro = root.findtext('.//dataRegistro', '')
    if d_registro and len(d_registro) == 8:
        data_di = f"{d_registro[0:4]}-{d_registro[4:6]}-{d_registro[6:8]}"
        
    xLocDesemb = root.findtext('.//armazenamentoRecintoAduaneiroNome', '').strip()
    
    # Try to find UF Desemb from cadastros table
    uf_desemb = ""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT uf FROM cadastros WHERE tipo = 'Local de Desembaraço' AND nome LIKE ? LIMIT 1", (f"%{xLocDesemb}%",))
        row = c.fetchone()
        if row and row[0]:
            uf_desemb = row[0]
        conn.close()
    except Exception:
        pass

    # Extract Importer info
    imp_nome = root.findtext('.//importadorNome', '')
    imp_cnpj = root.findtext('.//importadorNumero', '')
    imp_logr = root.findtext('.//importadorEnderecoLogradouro', '')
    imp_num = root.findtext('.//importadorEnderecoNumero', '')
    imp_bairro = root.findtext('.//importadorEnderecoBairro', '')
    imp_mun = root.findtext('.//importadorEnderecoMunicipio', '')
    imp_uf = root.findtext('.//importadorEnderecoUf', '')
    imp_cep = root.findtext('.//importadorEnderecoCep', '')

    # Extract Foreign Supplier & Country info from first adicao or root
    primeira_adicao = root.find('.//adicao')
    fornecedor_nome = primeira_adicao.findtext('fornecedorNome', '').strip() if primeira_adicao is not None else ""
    fornecedor_logr = primeira_adicao.findtext('fornecedorLogradouro', '').strip() if primeira_adicao is not None else ""
    fornecedor_num = primeira_adicao.findtext('fornecedorNumero', '').strip() if primeira_adicao is not None else ""
    fornecedor_compl = primeira_adicao.findtext('fornecedorComplemento', '').strip() if primeira_adicao is not None else ""
    fornecedor_cidade = primeira_adicao.findtext('fornecedorCidade', '').strip() if primeira_adicao is not None else ""
    pais_codigo = primeira_adicao.findtext('paisAquisicaoMercadoriaCodigo', '').strip() if primeira_adicao is not None else ""
    pais_nome = primeira_adicao.findtext('paisAquisicaoMercadoriaNome', '').strip() if primeira_adicao is not None else ""
    if not pais_codigo:
        pais_codigo = root.findtext('.//cargaPaisProcedenciaCodigo', '').strip()
    if not pais_nome:
        pais_nome = root.findtext('.//cargaPaisProcedenciaNome', '').strip()

    dh_emi_iso = f"{data_di}T12:00:00-03:00" if data_di else datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")

    cabecalho = {
        "nNF": "", "serie": "1", "natOp": "IMPORTACAO", "tpNF": "0", "idDest": "3",
        "chaveAcesso": "", "cUF": "35", "cNF": "", "dhEmi": dh_emi_iso, "mod": "55",
        "tpEmis": "1", "cDV": "",
        "emit_xNome": imp_nome or "NFT LOGISTICS LTDA",
        "emit_CNPJ": imp_cnpj or "47998441000198",
        "emit_xLgr": imp_logr or "AV. DR. GASTAO VIDIGAL",
        "emit_nro": imp_num or "1132",
        "emit_xBairro": imp_bairro or "VILA LEOPOLDINA",
        "emit_cMun": "3550308",
        "emit_xMun": imp_mun or "SAO PAULO",
        "emit_UF": imp_uf or "SP",
        "emit_CEP": imp_cep or "05314000",
        "emit_IE": "138843326117",
        "emit_CRT": "1",
        "dest_xNome": fornecedor_nome or "EXPORTADOR ESTRANGEIRO",
        "dest_CNPJ_CPF": "",
        "dest_idEstrangeiro": "",
        "dest_indIEDest": "9",
        "dest_IE": "",
        "dest_xLgr": fornecedor_logr or "EXTERIOR",
        "dest_nro": fornecedor_num or "SN",
        "dest_xBairro": fornecedor_compl or fornecedor_cidade or "EXTERIOR",
        "dest_cMun": "9999999",
        "dest_xMun": "EXTERIOR",
        "dest_UF": "EX",
        "dest_CEP": "00000000",
        "dest_cPais": pais_codigo or "160",
        "dest_xPais": pais_nome or "CHINA, REPUBLICA POPULAR"
    }

    # Extract Taxa Siscomex from informacaoComplementar
    taxa_siscomex = 0.0
    info_compl = root.findtext('.//informacaoComplementar', '')
    match_taxa = re.search(r'TAXA SISCOMEX[^\d]*?([\d.,]+)', info_compl, re.IGNORECASE)
    if match_taxa:
        val_str = match_taxa.group(1).replace('.', '').replace(',', '.')
        try:
            taxa_siscomex = float(val_str)
        except:
            pass

    # Total de Produtos para rateio
    total_produtos = 0.0
    adicoes = root.findall('.//adicao')
    for adicao in adicoes:
        for merc in adicao.findall('.//mercadoria'):
            q_str = merc.findtext('quantidade', '0')
            q_val = float(q_str) / 100000.0 if q_str.isdigit() else 0.0
            vu_str = merc.findtext('valorUnitario', '0')
            vu_val = float(vu_str) / 10000000.0 if vu_str.isdigit() else 0.0
            total_produtos += round(q_val * vu_val, 2)

    itens = []
    idx = 1
    numero_di_limpo = re.sub(r'[^a-zA-Z0-9]', '', numero_di)
    for adicao in adicoes:
        if not data_di:
            d_registro_ad = adicao.findtext('dataRegistro', '')
            if d_registro_ad and len(d_registro_ad) == 8:
                data_di = f"{d_registro_ad[0:4]}-{d_registro_ad[4:6]}-{d_registro_ad[6:8]}"
                cabecalho["dhEmi"] = f"{data_di}T12:00:00-03:00"
                
        ncm = adicao.findtext('dadosMercadoriaCodigoNcm', '')
        fornecedor = adicao.findtext('fornecedorNome', '')
        fabricante = adicao.findtext('fabricanteNome', '')
        numero_adicao_raw = adicao.findtext('numeroAdicao', '1')
        numero_adicao = re.sub(r'\D', '', numero_adicao_raw).lstrip('0') or '1'
        
        # Impostos ad valorem
        p_ii = float(adicao.findtext('iiAliquotaAdValorem', '0')) / 100.0
        p_ipi = float(adicao.findtext('ipiAliquotaAdValorem', '0')) / 100.0
        p_pis = float(adicao.findtext('pisPasepAliquotaAdValorem', '0')) / 100.0
        p_cofins = float(adicao.findtext('cofinsAliquotaAdValorem', '0')) / 100.0
        
        frete_adicao = float(adicao.findtext('valorReaisFreteInternacional', '0')) / 100.0
        seguro_adicao = float(adicao.findtext('valorReaisSeguroInternacional', '0')) / 100.0

        mercadorias = adicao.findall('.//mercadoria')
        qtd_merc = len(mercadorias) if len(mercadorias) > 0 else 1
        
        frete_item = frete_adicao / qtd_merc
        seguro_item = seguro_adicao / qtd_merc

        for merc in mercadorias:
            desc = merc.findtext('descricaoMercadoria', '').strip()
            q_str = merc.findtext('quantidade', '0')
            q_val = float(q_str) / 100000.0 if q_str.isdigit() else 0.0

            vu_str = merc.findtext('valorUnitario', '0')
            vu_val = float(vu_str) / 10000000.0 if vu_str.isdigit() else 0.0
            
            u_medida = merc.findtext('unidadeMedida', 'UN').strip()
            v_prod = round(q_val * vu_val, 2)
            
            # Rateio da taxa siscomex
            v_outro_item = 0.0
            if total_produtos > 0:
                v_outro_item = round(taxa_siscomex * (v_prod / total_produtos), 2)
            
            numero_seq_raw = merc.findtext('numeroSequencialItem', '1')
            numero_seq = re.sub(r'\D', '', numero_seq_raw).lstrip('0') or '1'
            
            item_obj = {
                "nItem": str(idx),
                "cProd": f"{numero_di_limpo}-{idx}" if numero_di_limpo else f"ITEM-{idx}",
                "cEAN": "SEM GTIN", "xProd": desc, "NCM": ncm, "CEST": "",
                "CFOP": "3101", 
                "uCom": u_medida, "qCom": f"{q_val:.4f}", "vUnCom": f"{vu_val:.4f}",
                "uTrib": u_medida, "qTrib": f"{q_val:.4f}", "vUnTrib": f"{vu_val:.4f}",
                "vProd": f"{v_prod:.2f}", "orig": "1", "cEnq": "999", "CST_IPI": "49",
                "CST_PIS": "98", "CST_COFINS": "98", 
                "vFrete": f"{frete_item:.2f}", 
                "vSeg": f"{seguro_item:.2f}",
                "vDesc": "0.00", "vOutro": f"{v_outro_item:.2f}", "vDespAdu": "0.00", "vAFRMM": "0.00",
                "pIPI": f"{p_ipi:.2f}", "pPIS": f"{p_pis:.2f}", "pCOFINS": f"{p_cofins:.2f}",
                "nDI": numero_di, "dDI": data_di, 
                "xLocDesemb": xLocDesemb, "UFDesemb": uf_desemb,
                "dDesemb": data_di, "tpViaTransp": "1", "vAFRMM_import": "0.00",
                "tpIntermedio": "1", "CNPJ_adquirente": "", "UFTerceiro": "", 
                "cExportador": fornecedor,
                "cFabricante": fabricante,
                "nAdicao": numero_adicao, "nSeqAdic": numero_seq,
            }
            itens.append(item_obj)
            idx += 1

    imposto_modelo = {
        "cfop_padrao": "3101", "tp_nf": "0", "id_dest": "3", "orig_padrao": "1",
        "csosn_icms": "102", "c_enq_ipi": "999", "cst_ipi": "49", "p_ipi": 0,
        "aliquota_ii": 0, "cst_pis": "98", "p_pis": 0, "cst_cofins": "98", "p_cofins": 0
    }
    
    resumo_rateio = {
        "vAFRMM": "0.00", "vDespAdu": "0.00", "vOutro": f"{taxa_siscomex:.2f}", "vFrete": "0.00",
        "vSeg": "0.00", "data_di": data_di
    }
    
    # Peso Liquido e Bruto
    pesoL_str = root.findtext('.//cargaPesoLiquido', '0')
    pesoL = float(pesoL_str) / 100000.0 if pesoL_str.isdigit() else 0.0
    
    pesoB_str = root.findtext('.//cargaPesoBruto', '0')
    pesoB = float(pesoB_str) / 100000.0 if pesoB_str.isdigit() else 0.0

    rodape = {
        "vNF": "0.00", "infCpl": f"DI: {numero_di}",
        "transporte": {
            "modFrete": "9", "CNPJ_CPF": "", "xNome": "", "IE": "", "xEnder": "",
            "xMun": "", "UF": "", "qVol": "", "esp": "", "marca": "", "nVol": "",
            "pesoL": f"{pesoL:.3f}", "pesoB": f"{pesoB:.3f}"
        },
        "totais": {
            "vBC": "0.00", "vICMS": "0.00", "vICMSDeson": "0.00", "vFCP": "0.00",
            "vBCST": "0.00", "vST": "0.00", "vFCPST": "0.00", "vFCPSTRet": "0.00",
            "vProd": f"{total_produtos:.2f}", "vFrete": "0.00", "vSeg": "0.00", "vDesc": "0.00",
            "vII": "0.00", "vIPI": "0.00", "vIPIDevol": "0.00", "vPIS": "0.00",
            "vCOFINS": "0.00", "vOutro": f"{taxa_siscomex:.2f}", "vNF": "0.00"
        }
    }
    
    xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    return jsonify({
        "status": "success", "cabecalho": cabecalho, "itens": itens, "rodape": rodape,
        "imposto_modelo": imposto_modelo, "resumo_rateio": resumo_rateio, "xml_original": xml_string
    })


# === ROTA: UPLOAD XML ===
# === ROTA: UPLOAD XML ===

@app.route('/upload_xml', methods=['POST'])
def upload_xml():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    try:
        tree = ET.parse(file)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        inf_nfe = root.find('nfe:infNFe', ns)
        if inf_nfe is None:
            inf_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

        if inf_nfe is None:
            return jsonify({"error": "Tag infNFe nao encontrada. Nao e um XML de NF-e valido."}), 400

        def get_text(parent, tag):
            if parent is None: return ""
            el = parent.find(f'.//{{http://www.portalfiscal.inf.br/nfe}}{tag}')
            return el.text.strip() if el is not None and el.text else ""

        # Extrair Cabecalho
        ide = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}ide')
        emit = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}emit')
        dest = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}dest')
        
        natOp_val = get_text(ide, 'natOp')
        tpNF_val = get_text(ide, 'tpNF')
        idDest_val = get_text(ide, 'idDest')

        # Chave de Acesso e Metadados SEFAZ
        chave_raw = inf_nfe.attrib.get('Id', '') if inf_nfe is not None else ''
        chave_acesso = chave_raw.replace('NFe', '').strip() if chave_raw else ''
        cUF_val = get_text(ide, 'cUF')
        cNF_val = get_text(ide, 'cNF')
        dhEmi_val = get_text(ide, 'dhEmi') or get_text(ide, 'dEmi')
        mod_val = get_text(ide, 'mod') or '55'
        tpEmis_val = get_text(ide, 'tpEmis') or '1'
        cDV_val = get_text(ide, 'cDV')

        cabecalho = {
            "nNF": get_text(ide, 'nNF'),
            "serie": get_text(ide, 'serie'),
            "natOp": natOp_val,
            "tpNF": tpNF_val,
            "idDest": idDest_val,
            "chaveAcesso": chave_acesso,
            "cUF": cUF_val,
            "cNF": cNF_val,
            "dhEmi": dhEmi_val,
            "mod": mod_val,
            "tpEmis": tpEmis_val,
            "cDV": cDV_val,
            
            # Emitente
            "emit_xNome": get_text(emit, 'xNome'),
            "emit_CNPJ": get_text(emit, 'CNPJ'),
            "emit_xLgr": get_text(emit, 'xLgr'),
            "emit_nro": get_text(emit, 'nro'),
            "emit_xBairro": get_text(emit, 'xBairro'),
            "emit_cMun": get_text(emit, 'cMun') or '3550308',
            "emit_xMun": get_text(emit, 'xMun'),
            "emit_UF": get_text(emit, 'UF'),
            "emit_CEP": get_text(emit, 'CEP'),
            "emit_IE": get_text(emit, 'IE') or '138843326117',
            "emit_CRT": get_text(emit, 'CRT') or '1',
            
            # Destinatario
            "dest_xNome": get_text(dest, 'xNome'),
            "dest_CNPJ_CPF": get_text(dest, 'CNPJ') or get_text(dest, 'CPF') or get_text(dest, 'idEstrangeiro'),
            "dest_idEstrangeiro": get_text(dest, 'idEstrangeiro'),
            "dest_indIEDest": get_text(dest, 'indIEDest') or "9",
            "dest_IE": get_text(dest, 'IE') or "",
            "dest_xLgr": get_text(dest, 'xLgr'),
            "dest_nro": get_text(dest, 'nro'),
            "dest_xBairro": get_text(dest, 'xBairro'),
            "dest_cMun": get_text(dest, 'cMun') or ('9999999' if idDest_val == '3' else '3550308'),
            "dest_xMun": get_text(dest, 'xMun') or ('EXTERIOR' if idDest_val == '3' else ''),
            "dest_UF": get_text(dest, 'UF') or ('EX' if idDest_val == '3' else ''),
            "dest_CEP": get_text(dest, 'CEP') or ('00000000' if idDest_val == '3' else ''),
            "dest_cPais": get_text(dest, 'cPais') or ('160' if idDest_val == '3' else '1058'),
            "dest_xPais": get_text(dest, 'xPais') or ('CHINA, REPUBLICA POPULAR' if idDest_val == '3' else 'Brasil')
        }

        # Extrair todos os itens completos de det
        itens = []
        dets = inf_nfe.findall('.//{http://www.portalfiscal.inf.br/nfe}det')
        for det in dets:
            item_obj = extrair_det(det, ns)
            itens.append(item_obj)
                
        # Extrai modelo tributario do primeiro item para a aba "Tipo de Nota"
        imposto_modelo = {}
        if len(itens) > 0:
            first = itens[0]
            cabecalho["cfop_padrao"] = first.get("CFOP", "")
            imposto_modelo = {
                "cfop_padrao": first.get("CFOP", ""),
                "tp_nf": tpNF_val,
                "id_dest": idDest_val,
                "orig_padrao": first.get("orig", "1"),
                "csosn_icms": first.get("CSOSN", "102"),
                "c_enq_ipi": first.get("cEnq", "102"),
                "cst_ipi": first.get("CST_IPI", "05"),
                "p_ipi": first.get("pIPI", 0),
                "aliquota_ii": 0,
                "cst_pis": first.get("CST_PIS", "07"),
                "p_pis": first.get("pPIS", 0),
                "cst_cofins": first.get("CST_COFINS", "07"),
                "p_cofins": first.get("pCOFINS", 0)
            }

        # Extrair Transporte e Volumes
        transp = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}transp')
        transporta = transp.find('.//{http://www.portalfiscal.inf.br/nfe}transporta') if transp is not None else None
        vol = transp.find('.//{http://www.portalfiscal.inf.br/nfe}vol') if transp is not None else None

        transporte = {
            "modFrete": get_text(transp, 'modFrete') if transp is not None else "0",
            "CNPJ_CPF": (get_text(transporta, 'CNPJ') or get_text(transporta, 'CPF')) if transporta is not None else "",
            "xNome": get_text(transporta, 'xNome') if transporta is not None else "",
            "IE": get_text(transporta, 'IE') if transporta is not None else "",
            "xEnder": get_text(transporta, 'xEnder') if transporta is not None else "",
            "xMun": get_text(transporta, 'xMun') if transporta is not None else "",
            "UF": get_text(transporta, 'UF') if transporta is not None else "",
            "qVol": get_text(vol, 'qVol') if vol is not None else "",
            "esp": get_text(vol, 'esp') if vol is not None else "",
            "marca": "",
            "nVol": "",
            "pesoL": get_text(vol, 'pesoL') if vol is not None else "",
            "pesoB": get_text(vol, 'pesoB') if vol is not None else ""
        }

        # Extrair Totais (ICMSTot)
        icms_tot = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}total/{http://www.portalfiscal.inf.br/nfe}ICMSTot')
        totais = {
            "vBC": get_text(icms_tot, 'vBC'),
            "vICMS": get_text(icms_tot, 'vICMS'),
            "vICMSDeson": get_text(icms_tot, 'vICMSDeson'),
            "vFCP": get_text(icms_tot, 'vFCP'),
            "vBCST": get_text(icms_tot, 'vBCST'),
            "vST": get_text(icms_tot, 'vST'),
            "vFCPST": get_text(icms_tot, 'vFCPST'),
            "vFCPSTRet": get_text(icms_tot, 'vFCPSTRet'),
            "vProd": get_text(icms_tot, 'vProd'),
            "vFrete": get_text(icms_tot, 'vFrete'),
            "vSeg": get_text(icms_tot, 'vSeg'),
            "vDesc": get_text(icms_tot, 'vDesc'),
            "vII": get_text(icms_tot, 'vII'),
            "vIPI": get_text(icms_tot, 'vIPI'),
            "vIPIDevol": get_text(icms_tot, 'vIPIDevol'),
            "vPIS": get_text(icms_tot, 'vPIS'),
            "vCOFINS": get_text(icms_tot, 'vCOFINS'),
            "vOutro": get_text(icms_tot, 'vOutro'),
            "vNF": get_text(icms_tot, 'vNF')
        }

        # Extrair Rodape
        infAdic = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}infAdic')
        rodape = {
            "vNF": totais.get("vNF") or get_text(inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}total'), 'vNF'),
            "infCpl": get_text(infAdic, 'infCpl'),
            "transporte": transporte,
            "totais": totais
        }

        # Totais de Rateio existentes no XML de modelo
        soma_afrmm = 0.0
        soma_desp_adu = 0.0
        soma_outro_itens = 0.0
        soma_frete_itens = 0.0
        soma_seg_itens = 0.0
        data_di_modelo = ""

        for it in itens:
            try:
                if it.get('vAFRMM'): soma_afrmm += float(limpar_decimal_nfe(it['vAFRMM']))
            except Exception: pass
            try:
                if it.get('vDespAdu'): soma_desp_adu += float(limpar_decimal_nfe(it['vDespAdu']))
            except Exception: pass
            try:
                if it.get('vOutro'): soma_outro_itens += float(limpar_decimal_nfe(it['vOutro']))
            except Exception: pass
            try:
                if it.get('vFrete'): soma_frete_itens += float(limpar_decimal_nfe(it['vFrete']))
            except Exception: pass
            try:
                if it.get('vSeg'): soma_seg_itens += float(limpar_decimal_nfe(it['vSeg']))
            except Exception: pass
            if not data_di_modelo and it.get('dDI'):
                data_di_modelo = it.get('dDI')

        resumo_rateio = {
            "vAFRMM": f"{soma_afrmm:.2f}",
            "vDespAdu": f"{soma_desp_adu:.2f}",
            "vOutro": f"{soma_outro_itens:.2f}",
            "vFrete": f"{soma_frete_itens:.2f}",
            "vSeg": f"{soma_seg_itens:.2f}",
            "data_di": data_di_modelo
        }

        xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')

        return jsonify({
            "cabecalho": cabecalho,
            "itens": itens,
            "rodape": rodape,
            "imposto_modelo": imposto_modelo,
            "resumo_rateio": resumo_rateio,
            "xml_original": xml_string
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === ROTA: GERAR XML ===
@app.route('/generate_xml', methods=['POST'])
def generate_xml():
    try:
        data = request.json or {}
        cabecalho = data.get('cabecalho', {})
        itens = data.get('itens', [])
        rodape = data.get('rodape', {})

        if not itens:
            return jsonify({"error": "Nenhum item informado para gerar o XML."}), 400

        xml_root = build_nfe_element(cabecalho, itens, rodape)
        xml_str = ET.tostring(xml_root, encoding='utf-8').decode('utf-8')
        # Garantir tag <idEstrangeiro></idEstrangeiro> caso vazia e manter formato de exatamente 1 linha
        xml_str = re.sub(r'<([a-zA-Z0-9_:]*idEstrangeiro)\s*/>', r'<\1></\1>', xml_str)
        xml_str = xml_str.replace('\n', '').replace('\r', '')
        final_xml = f'<?xml version="1.0" encoding="UTF-8"?>{xml_str}'.encode('utf-8')

        fd, temp_path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(fd, 'wb') as f:
            f.write(final_xml)

        ref_interna = (data.get('referencia_interna') or '').strip()
        n_nf = cabecalho.get('nNF') or 'nova'
        nat_op = (cabecalho.get('natOp') or cabecalho.get('select_operacao') or data.get('tipo_operacao') or '').strip()

        # Limpar parenteses da operacao (ex: "(5102) VENDA DE MERCADORIA" -> "VENDA DE MERCADORIA")
        nat_op_limpa = re.sub(r'\(.*?\)', '', nat_op).strip()

        partes_nome = []
        if ref_interna:
            partes_nome.append(ref_interna)
        else:
            partes_nome.append(f"NFe_{n_nf}")

        if nat_op_limpa:
            partes_nome.append(nat_op_limpa)

        nome_base = " - ".join(partes_nome)
        nome_sanitizado = re.sub(r'[\\/:*?"<>|]+', '_', nome_base).strip().replace(' ', '_')
        while '__' in nome_sanitizado:
            nome_sanitizado = nome_sanitizado.replace('__', '_')
        nome_arquivo = nome_sanitizado if nome_sanitizado.endswith('.xml') else f"{nome_sanitizado}.xml"

        return send_file(temp_path, as_attachment=True, download_name=nome_arquivo)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro ao gerar XML: {str(e)}"}), 500

# === ROTAS: EXCEL ===
@app.route('/export_excel', methods=['POST'])
def export_excel():
    data = request.json or {}
    itens = data.get('itens', [])
    if not itens:
        return jsonify({"error": "Nenhum item para exportar"}), 400
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Itens"
    
    headers = []
    for item in itens:
        for k in item.keys():
            if k not in headers:
                headers.append(k)
    
    ws.append(headers)
    for item in itens:
        ws.append([item.get(k, "") for k in headers])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name="Itens_NFe.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/import_excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    try:
        wb = openpyxl.load_workbook(file, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return jsonify({"itens": []})
        
        headers = [str(col).strip() if col is not None else f"col_{idx}" for idx, col in enumerate(rows[0])]
        itens = []
        for row in rows[1:]:
            if all(v is None or str(v).strip() == "" for v in row):
                continue
            item = {}
            for h, v in zip(headers, row):
                item[h] = "" if v is None else v
            itens.append(item)
        return jsonify({"itens": itens})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === ROTAS: GRANDE TABELA NCM (15k registros unificados) ===
@app.route('/banco_ncm')
def banco_ncm_page():
    return render_template('banco_ncm.html')

@app.route('/api/ncm', methods=['GET'])
def api_search_ncm():
    q = request.args.get('q', '').strip()
    utrib = request.args.get('utrib', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    offset = (page - 1) * per_page

    conn = get_db_connection()
    c = conn.cursor()

    conditions = []
    params = []

    if q:
        q_clean = re.sub(r'\D', '', q)
        if q_clean:
            conditions.append("(codigo_limpo LIKE ? OR codigo LIKE ? OR descricao LIKE ?)")
            params.extend([f"%{q_clean}%", f"%{q}%", f"%{q}%"])
        else:
            conditions.append("descricao LIKE ?")
            params.append(f"%{q}%")

    if utrib:
        conditions.append("utrib = ?")
        params.append(utrib)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    total = c.execute(f"SELECT COUNT(*) FROM ncm{where_clause}", params).fetchone()[0]

    query = f"""
        SELECT id, codigo, codigo_limpo, descricao, utrib, descricao_utrib,
               aliquota_ii, aliquota_ipi, aliquota_pis, aliquota_cofins, regime_pis_cofins,
               data_inicio, data_fim, tipo_ato, numero_ato, ano_ato
        FROM ncm{where_clause}
        ORDER BY codigo ASC
        LIMIT ? OFFSET ?
    """
    rows = c.execute(query, params + [per_page, offset]).fetchall()
    conn.close()

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1,
        "items": [dict(r) for r in rows]
    })

@app.route('/download_ncm_json')
def download_ncm_json():
    json_path = os.path.join(os.path.dirname(__file__), 'Tabela_NCM_Unificada.json')
    if os.path.exists(json_path):
        return send_file(json_path, as_attachment=True, download_name="Tabela_NCM_Unificada.json")
    return jsonify({"error": "Arquivo unificado nao encontrado"}), 404

@app.route('/download_ncm_excel')
def download_ncm_excel():
    excel_path = os.path.join(os.path.dirname(__file__), 'Tabela_NCM_Completa_Backup.xlsx')
    if not os.path.exists(excel_path):
        import exportar_ncm_excel
        exportar_ncm_excel.exportar_ncm_excel()
    return send_file(excel_path, as_attachment=True, download_name="Tabela_NCM_Completa_Backup.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/api/ncm/unidades_tributaveis', methods=['POST'])
def api_ncm_unidades_tributaveis():
    data = request.json or {}
    ncms = data.get('ncms', [])
    if not ncms:
        return jsonify({})

    map_input_to_clean = {}
    for n in ncms:
        if n:
            clean = re.sub(r'\D', '', str(n))
            if clean:
                map_input_to_clean[clean] = str(n)

    ncms_limpos = list(map_input_to_clean.keys())
    if not ncms_limpos:
        return jsonify({})

    conn = get_db_connection()
    c = conn.cursor()
    placeholders = ','.join(['?'] * len(ncms_limpos))
    rows = c.execute(
        f"SELECT codigo_limpo, utrib, descricao_utrib FROM ncm WHERE codigo_limpo IN ({placeholders}) AND utrib > ''",
        ncms_limpos
    ).fetchall()

    mapa = {}
    for r in rows:
        mapa[r['codigo_limpo']] = {
            'utrib': (r['utrib'] or '').strip().upper(),
            'descricao': (r['descricao_utrib'] or '').strip()
        }

    # Para NCMs sem match exato, tenta por prefixo de 6 ou 4 dígitos
    faltantes = [n for n in ncms_limpos if n not in mapa]
    for n in faltantes:
        prefix = n[:6] if len(n) >= 6 else (n[:4] if len(n) >= 4 else n)
        row = c.execute(
            "SELECT utrib, descricao_utrib FROM ncm WHERE codigo_limpo LIKE ? AND utrib > '' LIMIT 1",
            (f"{prefix}%",)
        ).fetchone()
        if row:
            mapa[n] = {
                'utrib': (row['utrib'] or '').strip().upper(),
                'descricao': (row['descricao_utrib'] or '').strip()
            }

    conn.close()
    return jsonify(mapa)

@app.route('/localidades')
def localidades_view():
    return render_template('localidades.html')

@app.route('/api/localidades/paises')
def api_localidades_paises():
    q = request.args.get('q', '').strip()
    conn = get_db_connection()
    c = conn.cursor()
    if q:
        rows = c.execute(
            "SELECT codigo, nome FROM tabela_paises WHERE codigo LIKE ? OR nome LIKE ? ORDER BY CASE WHEN codigo = '1058' THEN 0 ELSE 1 END, nome ASC",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        rows = c.execute("SELECT codigo, nome FROM tabela_paises ORDER BY CASE WHEN codigo = '1058' THEN 0 ELSE 1 END, nome ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/localidades/municipios')
def api_localidades_municipios():
    q = request.args.get('q', '').strip()
    uf = request.args.get('uf', '').strip().upper()
    try:
        limit = int(request.args.get('limit', 50))
    except (ValueError, TypeError):
        limit = 50
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    offset = (page - 1) * limit

    conn = get_db_connection()
    c = conn.cursor()
    
    where_clauses = []
    params = []
    if uf:
        where_clauses.append("uf = ?")
        params.append(uf)
    if q:
        where_clauses.append("(nome LIKE ? OR codigo_ibge LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    total = c.execute(f"SELECT COUNT(*) FROM tabela_municipios {where_sql}", params).fetchone()[0]
    rows = c.execute(
        f"SELECT codigo_ibge, nome, uf, c_uf FROM tabela_municipios {where_sql} ORDER BY uf ASC, nome ASC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    conn.close()
    
    return jsonify({
        "total": total,
        "page": page,
        "limit": limit,
        "items": [dict(r) for r in rows]
    })

@app.route('/api/localidades/cep/<cep>')
def api_localidades_cep(cep):
    cep_limpo = re.sub(r'\D', '', str(cep or ''))
    
    if cep_limpo == '99999999' or str(cep).strip().upper() in ('EX', 'EXTERIOR', '99999-999'):
        return jsonify({
            'status': 'success',
            'cep': '99999-999',
            'cep_limpo': '99999999',
            'logradouro': '',
            'bairro': '',
            'localidade': 'EXTERIOR',
            'uf': 'EX',
            'ibge': '9999999',
            'exterior': True
        })
        
    if len(cep_limpo) != 8:
        return jsonify({'error': 'CEP inválido. O CEP deve conter 8 dígitos numéricos.'}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    cached = c.execute("SELECT * FROM tabela_ceps WHERE cep = ?", (cep_limpo,)).fetchone()
    if cached:
        conn.close()
        return jsonify({
            'status': 'success',
            'cep': f"{cep_limpo[:5]}-{cep_limpo[5:]}",
            'cep_limpo': cep_limpo,
            'logradouro': remover_acentos_nfe(cached['logradouro'] or ''),
            'bairro': remover_acentos_nfe(cached['bairro'] or ''),
            'localidade': remover_acentos_nfe(cached['municipio'] or ''),
            'uf': cached['uf'] or '',
            'ibge': cached['codigo_ibge'] or '',
            'cached': True
        })

    # Consulta ViaCEP com fallback
    try:
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                raw_data = response.read().decode('utf-8')
                data = json.loads(raw_data)
                if data.get('erro'):
                    conn.close()
                    return jsonify({'error': 'CEP não encontrado na base nacional'}), 404
                
                logr = remover_acentos_nfe(data.get('logradouro', ''))
                bairro = remover_acentos_nfe(data.get('bairro', ''))
                localidade = remover_acentos_nfe(data.get('localidade', ''))
                uf = data.get('uf', '').upper()
                ibge = data.get('ibge', '')
                
                # Salva no cache
                c.execute('''
                    INSERT OR REPLACE INTO tabela_ceps (cep, logradouro, bairro, municipio, codigo_ibge, uf)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (cep_limpo, logr, bairro, localidade, ibge, uf))
                conn.commit()
                conn.close()
                
                return jsonify({
                    'status': 'success',
                    'cep': f"{cep_limpo[:5]}-{cep_limpo[5:]}",
                    'cep_limpo': cep_limpo,
                    'logradouro': logr,
                    'bairro': bairro,
                    'localidade': localidade,
                    'uf': uf,
                    'ibge': ibge,
                    'cached': False
                })
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Erro ao consultar serviço de CEP: {str(e)}'}), 502

@app.route('/api/ping')
def ping():
    return jsonify({'status': 'ok', 'port': 1652})

@app.route('/api/shutdown', methods=['POST', 'GET'])
def shutdown_server():
    import os, subprocess, threading, ctypes

    def close_app_windows():
        try:
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            PostMessage = ctypes.windll.user32.PostMessageW
            WM_CLOSE = 0x0010

            def foreach_window(hwnd, lParam):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    title = buff.value
                    if 'NFT Logistics' in title or 'Emissor NF-e' in title:
                        PostMessage(hwnd, WM_CLOSE, 0, 0)
                return True

            EnumWindows(EnumWindowsProc(foreach_window), 0)
        except Exception:
            pass

    def kill_proc():
        import time
        # 1. Envia sinal nativo do Windows para fechar as janelas do sistema
        close_app_windows()
        time.sleep(0.4)
        close_app_windows()
        time.sleep(0.3)
        try:
            subprocess.run(f'taskkill /F /T /PID {os.getpid()}', shell=True)
        except Exception:
            pass

    threading.Thread(target=kill_proc).start()
    return jsonify({'status': 'success', 'message': 'Servidor encerrando...'})

if __name__ == '__main__':
    get_db_connection().close()
    app.run(debug=True, port=1652)


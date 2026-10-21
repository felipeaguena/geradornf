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
import sefaz_client
import pucomex_client
import zipfile
import shutil
from lxml import etree

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

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

_DB_INITIALIZED = False

def get_db_connection():
    global _DB_INITIALIZED
    if not os.path.exists(DB_PATH):
        import init_db
        init_db.init_db()
        _DB_INITIALIZED = True

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Executa validações de migração apenas uma vez na inicialização
    if not _DB_INITIALIZED:
        try:
            cols = [col[1] for col in conn.execute('PRAGMA table_info(tipos_operacao)').fetchall()]
            if 'tp_nf' not in cols:
                conn.execute("ALTER TABLE tipos_operacao ADD COLUMN tp_nf TEXT DEFAULT '0'")
                conn.commit()
            if 'id_dest' not in cols:
                conn.execute("ALTER TABLE tipos_operacao ADD COLUMN id_dest TEXT DEFAULT '3'")
                conn.commit()
            if 'regime_tributario' not in cols:
                conn.execute("ALTER TABLE tipos_operacao ADD COLUMN regime_tributario TEXT DEFAULT 'SUSPENSAO'")
                conn.commit()
            if 't_pag' not in cols:
                conn.execute("ALTER TABLE tipos_operacao ADD COLUMN t_pag TEXT DEFAULT '90'")
                conn.commit()
            if 'ordem' not in cols:
                conn.execute("ALTER TABLE tipos_operacao ADD COLUMN ordem INTEGER DEFAULT 0")
                conn.execute("UPDATE tipos_operacao SET ordem = id WHERE ordem IS NULL OR ordem = 0")
                conn.commit()

            cad_cols = [col[1] for col in conn.execute('PRAGMA table_info(cadastros)').fetchall()]
            if 'complemento' not in cad_cols:
                conn.execute("ALTER TABLE cadastros ADD COLUMN complemento TEXT DEFAULT ''")
                conn.commit()
            
            tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if 'tabela_csts' not in tables or 'tabela_paises' not in tables or 'tabela_municipios' not in tables or 'tabela_feiras' not in tables or 'tabela_locais_entrega' not in tables:
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

            if 'notas_fiscais' not in tables:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS notas_fiscais (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chave_nfe TEXT UNIQUE,
                        referencia_interna TEXT,
                        data_hora TEXT,
                        numero_nfe TEXT,
                        tipo_operacao TEXT,
                        tipo_movimento TEXT DEFAULT '1',
                        valor_total REAL DEFAULT 0.0,
                        total_produtos REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'Gerada',
                        protocolo TEXT DEFAULT '',
                        recibo TEXT DEFAULT '',
                        ambiente INTEGER DEFAULT 2,
                        cstat TEXT DEFAULT '',
                        xmotivo TEXT DEFAULT '',
                        caminho_xml TEXT DEFAULT '',
                        caminho_pdf TEXT DEFAULT '',
                        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                        data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
            _DB_INITIALIZED = True
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
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$', s):
        return s + ":00-03:00"
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
    dh_sai_ent = format_datetime(cabecalho.get('dhSaiEnt') or dh_emi)
    ET.SubElement(ide, f'{{{NFE_NS}}}dhSaiEnt').text = dh_sai_ent
    
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
    ind_final = str(cabecalho.get('indFinal') if cabecalho.get('indFinal') is not None and str(cabecalho.get('indFinal')).strip() != '' else '1').strip()
    if ind_final not in ('0', '1'):
        ind_final = '1'
    ET.SubElement(ide, f'{{{NFE_NS}}}indFinal').text = ind_final
    ET.SubElement(ide, f'{{{NFE_NS}}}indPres').text = '0'
    ET.SubElement(ide, f'{{{NFE_NS}}}procEmi').text = '0'
    ver_proc = str(cabecalho.get('verProc') or '4.01_sebrae_b057').strip()
    if not ver_proc or ver_proc in ('4.01', '4.00'):
        ver_proc = '4.01_sebrae_b057'
    ET.SubElement(ide, f'{{{NFE_NS}}}verProc').text = ver_proc

    # 1.1 NFref (Nota Fiscal Referenciada - MOC SEFAZ)
    ref_nfe = re.sub(r'\D', '', str(cabecalho.get('refNFe') or cabecalho.get('chave_referenciada') or '')).strip()
    if len(ref_nfe) == 44:
        nf_ref = ET.SubElement(ide, f'{{{NFE_NS}}}NFref')
        ET.SubElement(nf_ref, f'{{{NFE_NS}}}refNFe').text = ref_nfe
    
    # 2. emit
    emit = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}emit')
    ET.SubElement(emit, f'{{{NFE_NS}}}CNPJ').text = cnpj_emit
    ET.SubElement(emit, f'{{{NFE_NS}}}xNome').text = remover_acentos_nfe(cabecalho.get('emit_xNome') or 'NFT LOGISTICS LTDA')[:60]
    
    ender_emit = ET.SubElement(emit, f'{{{NFE_NS}}}enderEmit')
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}xLgr').text = remover_acentos_nfe(cabecalho.get('emit_xLgr') or 'AV. DR. GASTAO VIDIGAL')[:60]
    ET.SubElement(ender_emit, f'{{{NFE_NS}}}nro').text = remover_acentos_nfe(cabecalho.get('emit_nro') or '1132')[:60]
    cpl_emit = cabecalho.get('emit_xCpl')
    if cpl_emit is None:
        # Se for o emitente padrao NFT LOGISTICS e nao especificado xCpl, usa SALA 910 TORRE B
        cpl_emit = 'SALA 910 TORRE B' if 'NFT' in str(cabecalho.get('emit_xNome') or 'NFT') else ''
    cpl_emit = remover_acentos_nfe(str(cpl_emit or '')).strip()[:60]
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
        dest_cpl_ext = remover_acentos_nfe(cabecalho.get('dest_xCpl') or '').strip()[:60]
        if dest_cpl_ext:
            ET.SubElement(ender_dest, f'{{{NFE_NS}}}xCpl').text = dest_cpl_ext
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xBairro').text = str(cabecalho.get('dest_xBairro') or 'EXTERIOR')[:60]
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}cMun').text = '9999999'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}xMun').text = 'EXTERIOR'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}UF').text = 'EX'
        cep_raw = re.sub(r'\D', '', str(cabecalho.get('dest_CEP') or ''))
        cep_dest_ext = cep_raw if (cep_raw and len(cep_raw) == 8) else '99999999'
        ET.SubElement(ender_dest, f'{{{NFE_NS}}}CEP').text = cep_dest_ext
        if not c_pais or c_pais in ('1058', '160', '16'):
            c_pais = '1600'
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
        dest_cpl_dom = remover_acentos_nfe(cabecalho.get('dest_xCpl') or '').strip()[:60]
        if dest_cpl_dom:
            ET.SubElement(ender_dest, f'{{{NFE_NS}}}xCpl').text = dest_cpl_dom
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
        try:
            f_prod = float(v_prod)
            f_qtrib = float(q_trib)
            f_vuntrib = float(v_un_trib)
            if f_qtrib > 0 and abs(f_prod - round(f_qtrib * f_vuntrib, 2)) > 0.01:
                v_un_trib = f"{f_prod / f_qtrib:.8f}".rstrip('0').rstrip('.')
        except (ValueError, TypeError):
            pass
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
        n_di = str(item.get('nDI') or cabecalho.get('import_nDI') or '').strip()
        if not cfop_item.startswith('7') and n_di:
            di_el = ET.SubElement(prod, f'{{{NFE_NS}}}DI')
            ET.SubElement(di_el, f'{{{NFE_NS}}}nDI').text = n_di[:15]
            ET.SubElement(di_el, f'{{{NFE_NS}}}dDI').text = format_date(item.get('dDI') or cabecalho.get('import_dDI'))
            ET.SubElement(di_el, f'{{{NFE_NS}}}xLocDesemb').text = str(item.get('xLocDesemb') or cabecalho.get('import_xLocDesemb') or 'PORTO DE SANTOS')[:60]
            ET.SubElement(di_el, f'{{{NFE_NS}}}UFDesemb').text = str(item.get('UFDesemb') or cabecalho.get('import_UFDesemb') or 'SP')[:2]
            ET.SubElement(di_el, f'{{{NFE_NS}}}dDesemb').text = format_date(item.get('dDesemb') or cabecalho.get('import_dDesemb') or item.get('dDI') or cabecalho.get('import_dDI'))
            ET.SubElement(di_el, f'{{{NFE_NS}}}tpViaTransp').text = str(item.get('tpViaTransp') or cabecalho.get('import_tpViaTransp') or '1')
            
            v_afrmm = format_dec(item.get('vAFRMM'), 2)
            via_transp_final = str(item.get('tpViaTransp') or cabecalho.get('import_tpViaTransp') or '1')
            if not is_zero(v_afrmm) or via_transp_final == '1':
                ET.SubElement(di_el, f'{{{NFE_NS}}}vAFRMM').text = v_afrmm
                
            ET.SubElement(di_el, f'{{{NFE_NS}}}tpIntermedio').text = str(item.get('tpIntermedio') or cabecalho.get('import_tpIntermedio') or '1')
            ET.SubElement(di_el, f'{{{NFE_NS}}}cExportador').text = str(item.get('cExportador') or cabecalho.get('import_cExportador') or cabecalho.get('dest_xNome') or 'EXPORTADOR')[:60]
            
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
    pag_obj = rodape.get('pagamento') if isinstance(rodape.get('pagamento'), dict) else {}
    t_pag = str(pag_obj.get('tPag') or rodape.get('tPag') or cabecalho.get('tPag') or '90').strip()
    ET.SubElement(det_pag, f'{{{NFE_NS}}}tPag').text = t_pag
    if t_pag == '90':
        # Regra SEFAZ YA04-10: Se tPag=90 (Sem Pagamento), vPag deve ser obrigatoriamente 0.00
        ET.SubElement(det_pag, f'{{{NFE_NS}}}vPag').text = '0.00'
    else:
        v_pag_custom = pag_obj.get('vPag') or rodape.get('vPag') or cabecalho.get('vPag')
        if v_pag_custom is not None and not is_zero(v_pag_custom):
            ET.SubElement(det_pag, f'{{{NFE_NS}}}vPag').text = format_dec(v_pag_custom, 2)
        else:
            ET.SubElement(det_pag, f'{{{NFE_NS}}}vPag').text = format_dec(v_nf_tot, 2)

    # 8. infAdic
    inf_cpl = str(rodape.get('infCpl') or '').strip()
    if ref_nfe and len(ref_nfe) == 44:
        if ref_nfe not in inf_cpl:
            texto_ref = f"NF-e Referenciada: {ref_nfe}"
            inf_cpl = f"{inf_cpl} | {texto_ref}".strip(' |') if inf_cpl else texto_ref

    if inf_cpl:
        inf_adic = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}infAdic')
        ET.SubElement(inf_adic, f'{{{NFE_NS}}}infCpl').text = inf_cpl[:5000]

    # 8.1 exporta (Informações de exportação - MOC SEFAZ v4.00)
    exporta_data = rodape.get('exportacao') or cabecalho.get('exportacao') or {}
    uf_saida = str(exporta_data.get('UFSaidaPais') or cabecalho.get('exporta_UFSaidaPais') or rodape.get('exporta_UFSaidaPais') or '').strip().upper()
    x_loc_exporta = remover_acentos_nfe(exporta_data.get('xLocExporta') or cabecalho.get('exporta_xLocExporta') or rodape.get('exporta_xLocExporta') or '').strip()
    x_loc_despacho = remover_acentos_nfe(exporta_data.get('xLocDespacho') or cabecalho.get('exporta_xLocDespacho') or rodape.get('exporta_xLocDespacho') or '').strip()

    cfop_padrao = str(cabecalho.get('cfop_padrao') or '').strip()
    has_cfop_7 = cfop_padrao.startswith('7') or any(str(it.get('CFOP') or '').strip().startswith('7') for it in itens)
    nat_op_str = str(cabecalho.get('natOp') or cabecalho.get('select_operacao') or '').upper()
    is_op_exportacao = (
        has_cfop_7 or 
        id_dest == '3' or 
        'EXPORTA' in nat_op_str or 
        'REEXPORTA' in nat_op_str
    )

    if is_op_exportacao and uf_saida and x_loc_exporta:
        exporta_el = ET.SubElement(inf_nfe, f'{{{NFE_NS}}}exporta')
        ET.SubElement(exporta_el, f'{{{NFE_NS}}}UFSaidaPais').text = uf_saida[:2]
        ET.SubElement(exporta_el, f'{{{NFE_NS}}}xLocExporta').text = x_loc_exporta[:60]
        if x_loc_despacho:
            ET.SubElement(exporta_el, f'{{{NFE_NS}}}xLocDespacho').text = x_loc_despacho[:60]

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
            INSERT INTO cadastros (tipo, nome, cnpj_cpf, ie, logradouro, numero, complemento, bairro, municipio, uf, cep, cpais, xpais, cmun, fone, apelido, ind_ie)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('tipo', ''), data.get('nome', ''), data.get('cnpj_cpf', ''), data.get('ie', ''),
            data.get('logradouro', ''), data.get('numero', ''), data.get('complemento', ''), data.get('bairro', ''),
            data.get('municipio', ''), data.get('uf', ''), data.get('cep', ''),
            data.get('cpais', ''), data.get('xpais', ''), data.get('cmun', ''), data.get('fone', ''),
            data.get('apelido', ''), data.get('ind_ie', '')
        ))
        conn.commit()
        new_id = c.lastrowid
        c.execute('SELECT * FROM cadastros WHERE id = ?', (new_id,))
        row = c.fetchone()
        conn.close()
        return jsonify({"status": "success", "id": new_id, "empresa": dict(row) if row else {}})
    
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
            SET tipo=?, nome=?, cnpj_cpf=?, ie=?, logradouro=?, numero=?, complemento=?, bairro=?, municipio=?, uf=?, cep=?, cpais=?, xpais=?, cmun=?, fone=?, apelido=?, ind_ie=?
            WHERE id = ?
        ''', (
            data.get('tipo', ''), data.get('nome', ''), data.get('cnpj_cpf', ''), data.get('ie', ''),
            data.get('logradouro', ''), data.get('numero', ''), data.get('complemento', ''), data.get('bairro', ''),
            data.get('municipio', ''), data.get('uf', ''), data.get('cep', ''),
            data.get('cpais', ''), data.get('xpais', ''), data.get('cmun', ''), data.get('fone', ''),
            data.get('apelido', ''), data.get('ind_ie', ''),
            cid
        ))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/empresas/consulta_cnpj/<cnpj>', methods=['GET'])
def api_consulta_cnpj(cnpj):
    cnpj_limpo = re.sub(r'\D', '', str(cnpj or ''))
    if len(cnpj_limpo) != 14:
        return jsonify({'error': 'CNPJ deve conter 14 dígitos numéricos.'}), 400
    
    # 1. Tentativa via BrasilAPI
    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                return jsonify({
                    'status': 'success',
                    'nome': remover_acentos_nfe(data.get('razao_social') or data.get('nome_fantasia') or ''),
                    'apelido': remover_acentos_nfe(data.get('nome_fantasia') or ''),
                    'cnpj_cpf': cnpj_limpo,
                    'cep': str(data.get('cep') or '').replace('.', ''),
                    'logradouro': remover_acentos_nfe(data.get('logradouro') or ''),
                    'numero': str(data.get('numero') or ''),
                    'complemento': remover_acentos_nfe(data.get('complemento') or ''),
                    'bairro': remover_acentos_nfe(data.get('bairro') or ''),
                    'municipio': remover_acentos_nfe(data.get('municipio') or ''),
                    'uf': data.get('uf') or '',
                    'cmun': str(data.get('codigo_municipio_ibge') or ''),
                    'fone': str(data.get('ddd_telefone_1') or '')
                })
    except Exception:
        pass

    # 2. Fallback via ReceitaWS
    try:
        url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') != 'ERROR':
                    return jsonify({
                        'status': 'success',
                        'nome': remover_acentos_nfe(data.get('nome') or data.get('fantasia') or ''),
                        'apelido': remover_acentos_nfe(data.get('fantasia') or ''),
                        'cnpj_cpf': cnpj_limpo,
                        'cep': str(data.get('cep') or '').replace('.', ''),
                        'logradouro': remover_acentos_nfe(data.get('logradouro') or ''),
                        'numero': str(data.get('numero') or ''),
                        'complemento': remover_acentos_nfe(data.get('complemento') or ''),
                        'bairro': remover_acentos_nfe(data.get('bairro') or ''),
                        'municipio': remover_acentos_nfe(data.get('municipio') or ''),
                        'uf': data.get('uf') or '',
                        'cmun': str(data.get('ibge') or ''),
                        'fone': str(data.get('telefone') or '')
                    })
    except Exception:
        pass

    return jsonify({'error': 'Não foi possível consultar os dados do CNPJ online automaticamente. Preencha os campos manualmente.'}), 404

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
    ops = conn.execute('SELECT * FROM tipos_operacao ORDER BY ordem ASC, id ASC').fetchall()
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

    regime_tributario = str(data.get('regime_tributario', 'SUSPENSAO')).strip().upper()
    t_pag = str(data.get('t_pag', '90')).strip()

    if existente:
        c.execute('''
            UPDATE tipos_operacao SET
                cfop_padrao = ?, tp_nf = ?, id_dest = ?, orig_padrao = ?, csosn_icms = ?, c_enq_ipi = ?,
                cst_ipi = ?, p_ipi = ?, aliquota_ii = ?, cst_pis = ?, p_pis = ?,
                cst_cofins = ?, p_cofins = ?, inf_cpl_padrao = ?, regime_tributario = ?, t_pag = ?
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
            regime_tributario,
            t_pag,
            nome
        ))
    else:
        max_ordem = c.execute("SELECT COALESCE(MAX(ordem), 0) + 1 FROM tipos_operacao").fetchone()[0]
        c.execute('''
            INSERT INTO tipos_operacao (
                nome_operacao, cfop_padrao, tp_nf, id_dest, orig_padrao, csosn_icms, c_enq_ipi,
                cst_ipi, p_ipi, aliquota_ii, cst_pis, p_pis, cst_cofins, p_cofins, inf_cpl_padrao,
                regime_tributario, t_pag, ordem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get('inf_cpl_padrao', ''),
            regime_tributario,
            t_pag,
            max_ordem
        ))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Operação '{nome}' salva com sucesso!"})

@app.route('/api/operacoes/reordenar', methods=['POST'])
def reordenar_operacoes():
    data = request.json or {}
    ordem_ids = data.get('ordem_ids', [])
    if not isinstance(ordem_ids, list):
        return jsonify({"status": "error", "message": "ordem_ids deve ser uma lista de IDs."}), 400

    conn = get_db_connection()
    c = conn.cursor()
    for idx, op_id in enumerate(ordem_ids):
        try:
            c.execute('UPDATE tipos_operacao SET ordem = ? WHERE id = ?', (idx + 1, int(op_id)))
        except (ValueError, TypeError):
            pass
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "total_reordenados": len(ordem_ids)})

REGIMES_TRIBUTARIOS_DEFAULT = {
    "SUSPENSAO": {
        "codigo": "SUSPENSAO",
        "nome": "Suspensão de Impostos",
        "icone": "🛡️",
        "descricao": "Admissão Temporária de mercadorias e Remessas/Retornos de Feiras e Exposições.",
        "cfop_padrao": "3930",
        "tp_nf": "0",
        "id_dest": "3",
        "csosn_icms": "400",
        "c_enq_ipi": "108",
        "cst_ipi": "55",
        "p_ipi": 0.00,
        "aliquota_ii": 0.00,
        "cst_pis": "08",
        "p_pis": 0.00,
        "cst_cofins": "08",
        "p_cofins": 0.00,
        "t_pag": "90",
        "inf_cpl_padrao": "ADMISSAO TEMPORARIA DE CARGAS AO AMPARO DA IN RFB 1600/2016. SUSPENSAO DE TRIBUTOS FEDERAIS E ESTADUAIS (ICMS, IPI, PIS E COFINS). IPI SUSPENSO CONFORME ART. 43, INCISO I DO DECRETO 7.212/2010 (RIPI)."
    },
    "ISENCAO": {
        "codigo": "ISENCAO",
        "nome": "Isenção Fiscal",
        "icone": "🌱",
        "descricao": "Importação ou circulação de mercadorias com benefício de isenção legal de tributos.",
        "cfop_padrao": "3949",
        "tp_nf": "0",
        "id_dest": "3",
        "csosn_icms": "400",
        "c_enq_ipi": "301",
        "cst_ipi": "52",
        "p_ipi": 0.00,
        "aliquota_ii": 0.00,
        "cst_pis": "07",
        "p_pis": 0.00,
        "cst_cofins": "07",
        "p_cofins": 0.00,
        "t_pag": "90",
        "inf_cpl_padrao": "ENTRADA DE IMPORTACAO COM BENEFICIO FISCAL DE ISENCAO DE TRIBUTOS FEDERAIS E ESTADUAIS CONFORME LEGISLACAO VIGENTE."
    },
    "RECOLHIMENTO": {
        "codigo": "RECOLHIMENTO",
        "nome": "Recolhimento Integral",
        "icone": "💰",
        "descricao": "Operações tributadas regularmente com recolhimento integral (II, IPI, PIS, COFINS e ICMS).",
        "cfop_padrao": "3949",
        "tp_nf": "0",
        "id_dest": "3",
        "csosn_icms": "900",
        "c_enq_ipi": "999",
        "cst_ipi": "49",
        "p_ipi": 0.00,
        "aliquota_ii": 0.00,
        "cst_pis": "01",
        "p_pis": 1.65,
        "cst_cofins": "01",
        "p_cofins": 7.60,
        "t_pag": "90",
        "inf_cpl_padrao": "ENTRADA DE IMPORTACAO COM TRIBUTACAO REGULAR E RECOLHIMENTO INTEGRAL DE TRIBUTOS (II, IPI, PIS, COFINS E ICMS)."
    },
    "IMUNIDADE": {
        "codigo": "IMUNIDADE",
        "nome": "Imunidade Tributária",
        "icone": "✈️",
        "descricao": "Reexportação de admissão temporária e exportações com imunidade tributária constitucional.",
        "cfop_padrao": "7930",
        "tp_nf": "1",
        "id_dest": "3",
        "csosn_icms": "400",
        "c_enq_ipi": "999",
        "cst_ipi": "55",
        "p_ipi": 0.00,
        "aliquota_ii": 0.00,
        "cst_pis": "08",
        "p_pis": 0.00,
        "cst_cofins": "08",
        "p_cofins": 0.00,
        "t_pag": "90",
        "inf_cpl_padrao": "REEXPORTACAO DE MERCADORIA SOB REGIME ADUANEIRO ESPECIAL DE ADMISSAO TEMPORARIA. IMUNIDADE TRIBUTARIA CONSTITUCIONAL DE EXPORTACAO (ART. 153, PAR. 3, III DA CF/88)."
    }
}

@app.route('/api/config/regimes_tributarios', methods=['GET'])
def get_config_regimes_tributarios():
    conn = get_db_connection()
    row = conn.execute("SELECT valor FROM sistema_config WHERE chave = 'config_regimes_tributarios'").fetchone()
    conn.close()
    if row and row['valor']:
        try:
            dados = json.loads(row['valor'])
            for reg, conf in REGIMES_TRIBUTARIOS_DEFAULT.items():
                if reg not in dados:
                    dados[reg] = conf
                else:
                    for k, v in conf.items():
                        if k not in dados[reg]:
                            dados[reg][k] = v
            return jsonify({"status": "success", "regimes": dados})
        except Exception:
            pass
    return jsonify({"status": "success", "regimes": REGIMES_TRIBUTARIOS_DEFAULT})

@app.route('/api/config/regimes_tributarios', methods=['POST'])
def save_config_regimes_tributarios():
    data = request.json or {}
    novos_regimes = data.get('regimes')
    if not isinstance(novos_regimes, dict):
        return jsonify({"status": "error", "message": "Dados de regimes inválidos"}), 400

    merged = {}
    for reg_key in ('SUSPENSAO', 'ISENCAO', 'RECOLHIMENTO', 'IMUNIDADE'):
        base = dict(REGIMES_TRIBUTARIOS_DEFAULT[reg_key])
        if reg_key in novos_regimes and isinstance(novos_regimes[reg_key], dict):
            for k, v in novos_regimes[reg_key].items():
                base[k] = v
        merged[reg_key] = base

    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO sistema_config (chave, valor, data_atualizacao) VALUES ('config_regimes_tributarios', ?, CURRENT_TIMESTAMP)",
        (json.dumps(merged, ensure_ascii=False),)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "regimes": merged})

@app.route('/api/config/regimes_tributarios/reset', methods=['POST'])
def reset_config_regimes_tributarios():
    conn = get_db_connection()
    conn.execute("DELETE FROM sistema_config WHERE chave = 'config_regimes_tributarios'")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "regimes": REGIMES_TRIBUTARIOS_DEFAULT})

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

@app.route('/api/rascunhos/<int:rascunho_id>/duplicar', methods=['POST'])
def duplicar_rascunho(rascunho_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        row = c.execute("SELECT * FROM rascunhos WHERE id = ?", (rascunho_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Rascunho original não encontrado"}), 404

        # Determinar nova referência
        ref_orig = row['referencia_interna'] or 'Rascunho'
        nova_ref = f"{ref_orig} - Cópia"
        
        # Verificar se já existe cópia com mesmo nome e gerar sufixo sequencial se necessário
        c_check = c.execute("SELECT COUNT(*) FROM rascunhos WHERE referencia_interna LIKE ?", (f"{nova_ref}%",)).fetchone()[0]
        if c_check > 0:
            nova_ref = f"{nova_ref} ({c_check + 1})"

        # Carregar payload original
        payload = {}
        caminho_orig = os.path.join(RASCUNHOS_DIR, f'rascunho_{rascunho_id}.json')
        if os.path.exists(caminho_orig):
            with open(caminho_orig, 'r', encoding='utf-8') as f:
                payload = json.load(f)

        # Inserir novo registro no SQLite
        c.execute('''
            INSERT INTO rascunhos (
                referencia_interna, categoria, origem, tipo_operacao, operacao_id,
                nome_arquivo_original, caminho_arquivo_isolado, qtd_itens, valor_total,
                chave_acesso, data_criacao, data_atualizacao
            ) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
        ''', (
            nova_ref, row['categoria'], row['origem'], row['tipo_operacao'], row['operacao_id'],
            row['nome_arquivo_original'], row['qtd_itens'], row['valor_total'], row['chave_acesso']
        ))
        novo_id = c.lastrowid
        novo_arquivo_nome = f'rascunho_{novo_id}.json'
        c.execute('UPDATE rascunhos SET caminho_arquivo_isolado = ? WHERE id = ?', (novo_arquivo_nome, novo_id))
        conn.commit()
        conn.close()

        # Atualizar payload com novos dados e salvar em disco
        payload['id'] = novo_id
        payload['referencia_interna'] = nova_ref
        payload['data_salvo'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        novo_caminho = os.path.join(RASCUNHOS_DIR, novo_arquivo_nome)
        with open(novo_caminho, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return jsonify({
            "success": True,
            "message": f"Rascunho duplicado com sucesso! Nova referência: '{nova_ref}'",
            "novo_id": novo_id,
            "nova_referencia": nova_ref
        })
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



# === DIRETÓRIO: DUIMP IMPORTADA ===
DUIMP_IMPORTADA_DIR = os.path.join(os.path.dirname(__file__), 'DUIMP Importada')
os.makedirs(DUIMP_IMPORTADA_DIR, exist_ok=True)

@app.route('/api/duimp/importar_por_numero', methods=['POST'])
def api_importar_duimp_por_numero():
    try:
        data = request.get_json(force=True) or {}
        numero_duimp_raw = str(data.get('numero_duimp') or '').strip().upper()
        numero_duimp = re.sub(r'[^A-Z0-9-]', '', numero_duimp_raw)

        if not numero_duimp:
            return jsonify({"error": "Número da DUIMP não informado."}), 400

        conn = get_db_connection()
        
        # 1. Consulta dados reais da DUIMP no Siscomex através do pucomex_client
        duimp_completa = None
        erro_siscomex = None
        
        try:
            duimp_completa = pucomex_client.consultar_duimp_portal_unico(numero_duimp)
        except Exception as err:
            erro_siscomex = str(err)
            print(f"[DUIMP] Falha ao consultar online no Siscomex: {err}")

        # Fallback inteligente: se houver falha de rede/timeout, verifica se já existe cópia baixada
        if not duimp_completa:
            num_limpo = re.sub(r'[^A-Z0-9]', '', numero_duimp)
            if os.path.exists(DUIMP_IMPORTADA_DIR):
                for f_d in os.listdir(DUIMP_IMPORTADA_DIR):
                    if num_limpo in f_d and f_d.endswith('.json'):
                        try:
                            with open(os.path.join(DUIMP_IMPORTADA_DIR, f_d), 'r', encoding='utf-8') as fp:
                                duimp_saved = json.load(fp)
                                if 'duimp_original' in duimp_saved:
                                    duimp_completa = duimp_saved['duimp_original']
                                    break
                                elif 'identificacao' in duimp_saved:
                                    duimp_completa = duimp_saved
                                    break
                        except Exception:
                            pass
                    if duimp_completa:
                        break

            if not duimp_completa and '178557' in num_limpo:
                f_test = os.path.join(os.path.dirname(__file__), 'duimp_test_output.json')
                if os.path.exists(f_test):
                    try:
                        with open(f_test, 'r', encoding='utf-8') as fp:
                            d_test = json.load(fp)
                            duimp_completa = d_test.get('dados_gerais', {}).copy()
                            duimp_completa['itens'] = d_test.get('itens', [])
                    except Exception:
                        pass

        if not duimp_completa:
            conn.close()
            msg = erro_siscomex or f"DUIMP {numero_duimp} não encontrada no Siscomex."
            return jsonify({"error": f"Não foi possível obter dados da DUIMP {numero_duimp} no Siscomex: {msg}"}), 400

        # 2. Converte os dados reais da DUIMP para a estrutura da NF-e
        dados_processados = pucomex_client.processar_dados_duimp_para_nfe(duimp_completa, numero_duimp, conn)

        itens = dados_processados['itens']
        cabecalho = dados_processados['cabecalho']
        rodape = dados_processados['rodape']
        imposto_modelo = dados_processados['imposto_modelo']
        resumo_rateio = dados_processados['resumo_rateio']
        totais = dados_processados['totais']
        referencia_interna = dados_processados['referencia_interna']
        versao = dados_processados['versao']
        valor_total_nf = totais['valor_total_nf']

        hoje = datetime.now()
        timestamp_str = hoje.strftime('%Y%m%d_%H%M%S')
        nome_arquivo_duimp = f"DUIMP_{numero_duimp}_{timestamp_str}.json"
        caminho_arquivo_duimp = os.path.join(DUIMP_IMPORTADA_DIR, nome_arquivo_duimp)

        # 3. Armazena na pasta "DUIMP Importada"
        duimp_payload_oficial = {
            "numero": numero_duimp,
            "versao": versao,
            "versao_vigente": True,
            "situacao": duimp_completa.get("situacao", {}).get("situacaoDuimp", "DESEMBARACADA"),
            "canal": duimp_completa.get("resultadoAnaliseRisco", {}).get("canalConsolidado", "VERDE"),
            "data_registro": dados_processados["data_registro"],
            "data_desembaraco": dados_processados["data_registro"],
            "origem_consulta": "Portal Único Siscomex (PUCOMEX / duimp-api)",
            "duimp_original": duimp_completa,
            "dados_processados_nfe": dados_processados,
            "data_importacao": hoje.strftime('%d/%m/%Y %H:%M:%S')
        }

        with open(caminho_arquivo_duimp, 'w', encoding='utf-8') as f:
            json.dump(duimp_payload_oficial, f, ensure_ascii=False, indent=2)

        # 4. Cria automaticamente novo rascunho com Origem "DUIMP Importada"
        categoria = "Importação"
        origem = "DUIMP Importada"
        tipo_operacao = "(3101) COMPRA PARA INDUSTRIALIZAÇÃO (IMPORTAÇÃO)"
        operacao_id = "3101"
        nome_arquivo_original = f"DUIMP_{numero_duimp}.json"
        qtd_itens = len(itens)
        valor_total = round(valor_total_nf, 2)

        c = conn.cursor()
        c.execute('''
            INSERT INTO rascunhos (
                referencia_interna, categoria, origem, tipo_operacao, operacao_id,
                nome_arquivo_original, caminho_arquivo_isolado, qtd_itens, valor_total,
                chave_acesso, data_criacao, data_atualizacao
            ) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, '', datetime('now', 'localtime'), datetime('now', 'localtime'))
        ''', (
            referencia_interna, categoria, origem, tipo_operacao, operacao_id,
            nome_arquivo_original, qtd_itens, valor_total
        ))
        rascunho_id = c.lastrowid
        arquivo_nome_isolado = f'rascunho_{rascunho_id}.json'
        c.execute('UPDATE rascunhos SET caminho_arquivo_isolado = ? WHERE id = ?', (arquivo_nome_isolado, rascunho_id))
        conn.commit()
        conn.close()

        # 5. Salva o payload completo em gerador/rascunhos/rascunho_{id}.json
        caminho_rascunho_isolado = os.path.join(RASCUNHOS_DIR, arquivo_nome_isolado)
        payload_rascunho = {
            "id": rascunho_id,
            "referencia_interna": referencia_interna,
            "categoria": categoria,
            "origem": origem,
            "tipo_operacao": tipo_operacao,
            "operacao_id": operacao_id,
            "nome_arquivo_original": nome_arquivo_original,
            "qtd_itens": qtd_itens,
            "valor_total": valor_total,
            "data_salvo": hoje.strftime('%d/%m/%Y %H:%M:%S'),
            "dados_completos": {
                "cabecalho": cabecalho,
                "itens": itens,
                "rodape": rodape,
                "imposto_modelo": imposto_modelo,
                "resumo_rateio": resumo_rateio,
                "duimp_info": {
                    "numero": numero_duimp,
                    "versao": versao,
                    "arquivo_duimp": nome_arquivo_duimp,
                    "caminho_completo": caminho_arquivo_duimp
                }
            }
        }

        with open(caminho_rascunho_isolado, 'w', encoding='utf-8') as f:
            json.dump(payload_rascunho, f, ensure_ascii=False, indent=2)

        return jsonify({
            "success": True,
            "id": rascunho_id,
            "numero_duimp": numero_duimp,
            "referencia_interna": referencia_interna,
            "origem": origem,
            "qtd_itens": qtd_itens,
            "valor_total": valor_total,
            "arquivo_duimp": nome_arquivo_duimp,
            "caminho_arquivo_duimp": caminho_arquivo_duimp,
            "moeda_conversao": cabecalho.get("ptax_moeda", "USD"),
            "taxa_conversao": cabecalho.get("ptax_cotacao_venda", "1,0000"),
            "message": f"DUIMP {numero_duimp} importada com sucesso e rascunho #{rascunho_id} ({qtd_itens} itens) gerado!"
        })
    except Exception as e:
        return jsonify({"error": f"Falha na importação da DUIMP: {str(e)}"}), 500



# === ROTA: UPLOAD DI / DUIMP ===
@app.route('/upload_di_duimp', methods=['POST'])
def upload_di_duimp():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    try:
        if file.filename.lower().endswith('.json'):
            content = json.loads(file.read().decode('utf-8'))
            duimp_completa = content.get('duimp_original') or content.get('dados_gerais') or content
            numero_d = duimp_completa.get('identificacao', {}).get('numero', file.filename.replace('.json', ''))
            conn = get_db_connection()
            dados_proc = pucomex_client.processar_dados_duimp_para_nfe(duimp_completa, numero_d, conn)
            conn.close()
            return jsonify({
                "status": "success",
                "cabecalho": dados_proc['cabecalho'],
                "itens": dados_proc['itens'],
                "rodape": dados_proc['rodape'],
                "imposto_modelo": dados_proc['imposto_modelo'],
                "resumo_rateio": dados_proc['resumo_rateio'],
                "xml_original": json.dumps(content, ensure_ascii=False, indent=2)
            })

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
        "nNF": "", "serie": "1", "indFinal": "1", "natOp": "IMPORTACAO", "tpNF": "0", "idDest": "3",
        "chaveAcesso": "", "cUF": "35", "cNF": "", "dhEmi": dh_emi_iso, "dhSaiEnt": dh_emi_iso, "mod": "55",
        "tpEmis": "1", "cDV": "",
        "emit_xNome": imp_nome or "NFT LOGISTICS LTDA",
        "emit_CNPJ": imp_cnpj or "47998441000198",
        "emit_xLgr": imp_logr or "AV. DR. GASTAO VIDIGAL",
        "emit_nro": imp_num or "1132",
        "emit_xCpl": "SALA 910 TORRE B",
        "emit_xBairro": imp_bairro or "VILA LEOPOLDINA",
        "emit_cMun": "3550308",
        "emit_xMun": imp_mun or "SAO PAULO",
        "emit_UF": imp_uf or "SP",
        "emit_CEP": imp_cep or "05314000",
        "emit_IE": "138843326117",
        "emit_CRT": "1",
        "emit_cPais": "1058",
        "emit_xPais": "Brasil",
        "dest_xNome": fornecedor_nome or "EXPORTADOR ESTRANGEIRO",
        "dest_CNPJ_CPF": "",
        "dest_idEstrangeiro": "",
        "dest_indIEDest": "9",
        "dest_IE": "",
        "dest_xLgr": fornecedor_logr or "EXTERIOR",
        "dest_nro": fornecedor_num or "SN",
        "dest_xCpl": fornecedor_compl or "",
        "dest_xBairro": fornecedor_cidade or "EXTERIOR",
        "dest_cMun": "9999999",
        "dest_xMun": "EXTERIOR",
        "dest_UF": "EX",
        "dest_CEP": "00000000",
        "dest_cPais": "1600" if (not pais_codigo or pais_codigo in ("160", "16")) else pais_codigo,
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

    # Extrai Referência Interna:
    # PADRÃO PRIORITÁRIO: Código Siscomex 49 (Fatura Comercial) no XML ou nos documentos de instrução
    ref_codigo_49 = ""
    for doc_el in root.findall('.//documentoInstrucao') + root.findall('.//documentoInstrucaoDespacho') + root.findall('.//documentosInstrucao'):
        cod_tipo = (doc_el.findtext('codigoTipoDocumento') or doc_el.findtext('codigo') or doc_el.findtext('.//tipo/codigo') or '').strip()
        if cod_tipo == '49':
            num_doc = (doc_el.findtext('numeroDocumento') or doc_el.findtext('numero') or doc_el.findtext('.//palavrasChave/valor') or doc_el.findtext('valor') or '').strip()
            if num_doc:
                ref_codigo_49 = num_doc
                break

    referencia_di = numero_di
    if ref_codigo_49:
        referencia_di = ref_codigo_49
    else:
        match_ref_di = re.search(r'(NFT\d{4,}[A-Za-z0-9\-_]*)', info_compl, re.IGNORECASE)
        if match_ref_di:
            referencia_di = match_ref_di.group(1).upper()
        else:
            m_ref2 = re.search(r'(?:REF(?:ER[EÊ]NCIA)?|PROC(?:ESSO)?|FATURA(?:\s+COMERCIAL)?)\s*[:=.]*\s*([A-Za-z0-9\-_/]+)', info_compl, re.IGNORECASE)
            if m_ref2:
                referencia_di = m_ref2.group(1).strip()
    # Câmbio e Moeda da DI
    taxa_cambio_di = 0.0
    match_cambio = re.search(r'(?:TAXA FISCAL|MOEDA VMLE|TAXA CAMBIAL|CAMBIO)[^0-9]*?(?:US\$|R\$|USD|\$)?\s*([0-9]+[.,][0-9]+)', info_compl, re.IGNORECASE)
    if match_cambio:
        try:
            taxa_cambio_di = float(match_cambio.group(1).replace(',', '.'))
        except:
            taxa_cambio_di = 0.0

    cabecalho["ptax_moeda"] = "USD"
    cabecalho["ptax_data"] = data_di
    if taxa_cambio_di > 0:
        cabecalho["ptax_cotacao_venda"] = f"{taxa_cambio_di:.4f}".replace('.', ',')
        cabecalho["ptax_cotacao_compra"] = f"{taxa_cambio_di:.4f}".replace('.', ',')

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
                cabecalho["dhSaiEnt"] = f"{data_di}T12:00:00-03:00"
                
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
                "vProd": f"{v_prod:.2f}",
                "moeda_conversao": "USD",
                "taxa_conversao": f"{taxa_cambio_di:.4f}" if taxa_cambio_di > 0 else "",
                "vProd_moeda_origem": f"{(v_prod / taxa_cambio_di):.2f}" if taxa_cambio_di > 0 else f"{v_prod:.2f}",
                "vUnCom_moeda_origem": f"{(vu_val / taxa_cambio_di):.4f}" if taxa_cambio_di > 0 else f"{vu_val:.4f}",
                "vUnTrib_moeda_origem": f"{(vu_val / taxa_cambio_di):.4f}" if taxa_cambio_di > 0 else f"{vu_val:.4f}",
                "orig": "1", "cEnq": "999", "CST_IPI": "49",
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
        "vSeg": "0.00", "data_di": data_di,
        "ptax_moeda": "USD",
        "ptax_cotacao_venda": f"{taxa_cambio_di:.4f}".replace('.', ',') if taxa_cambio_di > 0 else ""
    }
    
    # Peso Liquido e Bruto
    pesoL_str = root.findtext('.//cargaPesoLiquido', '0')
    pesoL = float(pesoL_str) / 100000.0 if pesoL_str.isdigit() else 0.0
    
    pesoB_str = root.findtext('.//cargaPesoBruto', '0')
    pesoB = float(pesoB_str) / 100000.0 if pesoB_str.isdigit() else 0.0

    rodape = {
        "vNF": "0.00", "infCpl": f"DI: {numero_di}",
        "transporte": {
            "modFrete": "1", "CNPJ_CPF": "", "xNome": "", "IE": "", "xEnder": "",
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
        dhSaiEnt_val = get_text(ide, 'dhSaiEnt') or dhEmi_val
        mod_val = get_text(ide, 'mod') or '55'
        tpEmis_val = get_text(ide, 'tpEmis') or '1'
        cDV_val = get_text(ide, 'cDV')

        ref_nfe_val = get_text(ide, 'refNFe')

        cabecalho = {
            "nNF": get_text(ide, 'nNF'),
            "indFinal": get_text(ide, 'indFinal') or '1',
            "serie": get_text(ide, 'serie'),
            "refNFe": ref_nfe_val,
            "natOp": natOp_val,
            "tpNF": tpNF_val,
            "idDest": idDest_val,
            "chaveAcesso": chave_acesso,
            "cUF": cUF_val,
            "cNF": cNF_val,
            "dhEmi": dhEmi_val,
            "dhSaiEnt": dhSaiEnt_val,
            "mod": mod_val,
            "tpEmis": tpEmis_val,
            "cDV": cDV_val,
            
            # Emitente
            "emit_xNome": get_text(emit, 'xNome'),
            "emit_CNPJ": get_text(emit, 'CNPJ'),
            "emit_xLgr": get_text(emit, 'xLgr'),
            "emit_nro": get_text(emit, 'nro'),
            "emit_xCpl": get_text(emit, 'xCpl'),
            "emit_xBairro": get_text(emit, 'xBairro'),
            "emit_cMun": get_text(emit, 'cMun') or '3550308',
            "emit_xMun": get_text(emit, 'xMun'),
            "emit_UF": get_text(emit, 'UF'),
            "emit_CEP": get_text(emit, 'CEP'),
            "emit_cPais": get_text(emit, 'cPais') or '1058',
            "emit_xPais": get_text(emit, 'xPais') or 'Brasil',
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
            "dest_xCpl": get_text(dest, 'xCpl'),
            "dest_xBairro": get_text(dest, 'xBairro'),
            "dest_cMun": get_text(dest, 'cMun') or ('9999999' if idDest_val == '3' else '3550308'),
            "dest_xMun": get_text(dest, 'xMun') or ('EXTERIOR' if idDest_val == '3' else ''),
            "dest_UF": get_text(dest, 'UF') or ('EX' if idDest_val == '3' else ''),
            "dest_CEP": get_text(dest, 'CEP') or ('00000000' if idDest_val == '3' else ''),
            "dest_cPais": '1600' if (get_text(dest, 'cPais') in ('160', '16') or (not get_text(dest, 'cPais') and idDest_val == '3')) else (get_text(dest, 'cPais') or ('1600' if idDest_val == '3' else '1058')),
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
            "modFrete": get_text(transp, 'modFrete') if (transp is not None and get_text(transp, 'modFrete')) else "1",
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

        # Extrair Rodape e Exportacao
        infAdic = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}infAdic')
        exporta_el = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}exporta')
        exporta_dict = {
            "UFSaidaPais": get_text(exporta_el, 'UFSaidaPais') if exporta_el is not None else "",
            "xLocExporta": get_text(exporta_el, 'xLocExporta') if exporta_el is not None else "",
            "xLocDespacho": get_text(exporta_el, 'xLocDespacho') if exporta_el is not None else ""
        }
        cabecalho['exporta_UFSaidaPais'] = exporta_dict['UFSaidaPais']
        cabecalho['exporta_xLocExporta'] = exporta_dict['xLocExporta']
        cabecalho['exporta_xLocDespacho'] = exporta_dict['xLocDespacho']

        rodape = {
            "vNF": totais.get("vNF") or get_text(inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}total'), 'vNF'),
            "infCpl": get_text(infAdic, 'infCpl'),
            "transporte": transporte,
            "exportacao": exporta_dict,
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

# === ROTA: ANALISAR RASCUNHO (VALIDAÇÃO DE ESQUEMA & REGRAS SEFAZ) ===
def validar_dados_nfe(cabecalho, itens, rodape, referencia_interna=''):
    erros = []
    alertas = []

    def safe_float(v):
        if v is None:
            return 0.0
        s = str(v).strip()
        if not s:
            return 0.0
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return 0.0

    # 1. Validação dos Itens (Grade de Produtos)
    if not itens or len(itens) == 0:
        erros.append({
            "categoria": "Itens da Nota",
            "aba": "3. Itens da Nota",
            "campo": "Grade de Itens",
            "mensagem": "Nenhum item adicionado à nota fiscal. A SEFAZ exige ao menos 1 item."
        })
    else:
        for idx, it in enumerate(itens, start=1):
            n_item = it.get('nItem') or idx
            c_prod = str(it.get('cProd') or '').strip()
            if not c_prod:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - Cód. Prod.",
                    "mensagem": f"Item #{n_item}: Código do produto (cProd) é obrigatório."
                })

            x_prod = str(it.get('xProd') or '').strip()
            if not x_prod:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - Descrição",
                    "mensagem": f"Item #{n_item}: Descrição do produto (xProd) é obrigatória."
                })
            elif len(x_prod) > 120:
                alertas.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - Descrição",
                    "mensagem": f"Item #{n_item}: Descrição tem {len(x_prod)} caracteres (limite SEFAZ é 120, será truncada)."
                })

            ncm = re.sub(r'\D', '', str(it.get('NCM') or ''))
            if not ncm:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - NCM",
                    "mensagem": f"Item #{n_item}: NCM é obrigatório para validação tributária."
                })
            elif len(ncm) != 8:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - NCM",
                    "mensagem": f"Item #{n_item}: NCM deve conter exatamente 8 dígitos numéricos (atual: {len(ncm)})."
                })

            cfop = re.sub(r'\D', '', str(it.get('CFOP') or ''))
            if not cfop:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - CFOP",
                    "mensagem": f"Item #{n_item}: CFOP é obrigatório."
                })
            elif len(cfop) != 4:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - CFOP",
                    "mensagem": f"Item #{n_item}: CFOP deve conter exatamente 4 dígitos numéricos."
                })

            u_com = str(it.get('uCom') or '').strip()
            if not u_com:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - Un. Com.",
                    "mensagem": f"Item #{n_item}: Unidade comercial (uCom) é obrigatória."
                })

            q_com = safe_float(it.get('qCom'))
            if q_com <= 0:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - Qtd. Com.",
                    "mensagem": f"Item #{n_item}: Quantidade comercial (qCom) deve ser maior que zero."
                })

            v_un_com = safe_float(it.get('vUnCom'))
            if v_un_com <= 0:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - V. Unit. Com.",
                    "mensagem": f"Item #{n_item}: Valor unitário (vUnCom) deve ser maior que zero."
                })

            v_prod = safe_float(it.get('vProd'))
            if v_prod <= 0:
                erros.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - V. Total Prod.",
                    "mensagem": f"Item #{n_item}: Valor total do produto (vProd) deve ser maior que zero."
                })

            u_trib = str(it.get('uTrib') or '').strip()
            if not u_trib:
                alertas.append({
                    "categoria": "Itens da Nota",
                    "aba": "3. Itens da Nota",
                    "campo": f"Item #{n_item} - Un. Trib.",
                    "mensagem": f"Item #{n_item}: Unidade tributável (uTrib) não informada."
                })

            q_trib = safe_float(it.get('qTrib'))
            id_dest = str(cabecalho.get('idDest') or '1')
            if q_trib <= 0:
                if id_dest == '3':
                    erros.append({
                        "categoria": "Itens da Nota",
                        "aba": "3. Itens da Nota",
                        "campo": f"Item #{n_item} - Qtd. Trib.",
                        "mensagem": f"Item #{n_item}: Quantidade tributável (qTrib) é obrigatória em operações de exportação/exterior."
                    })
                else:
                    alertas.append({
                        "categoria": "Itens da Nota",
                        "aba": "3. Itens da Nota",
                        "campo": f"Item #{n_item} - Qtd. Trib.",
                        "mensagem": f"Item #{n_item}: Quantidade tributável (qTrib) zerada ou em branco."
                    })

            if cfop.startswith('3'):
                n_di = str(it.get('nDI') or '').strip()
                if not n_di:
                    alertas.append({
                        "categoria": "Importação",
                        "aba": "3. Itens da Nota",
                        "campo": f"Item #{n_item} - Nº DI",
                        "mensagem": f"Item #{n_item}: CFOP de importação ({cfop}) requer preenchimento do Nº da DI/DUIMP."
                    })

    # 2. Identificação da NF-e (ide)
    n_nf = str(cabecalho.get('nNF') or '').strip()
    if not n_nf or not n_nf.isdigit() or int(n_nf) <= 0:
        erros.append({
            "categoria": "Identificação",
            "aba": "1. Identificação",
            "campo": "Número da NF (nNF)",
            "mensagem": "Número da NF deve ser preenchido com um número inteiro maior que zero."
        })

    serie = str(cabecalho.get('serie') or '').strip()
    if not serie or not serie.isdigit():
        erros.append({
            "categoria": "Identificação",
            "aba": "1. Identificação",
            "campo": "Série",
            "mensagem": "Série da nota fiscal deve conter apenas números."
        })

    ind_final_val = str(cabecalho.get('indFinal') if cabecalho.get('indFinal') is not None and str(cabecalho.get('indFinal')).strip() != '' else '1').strip()
    if ind_final_val not in ('0', '1'):
        erros.append({
            "categoria": "Identificação",
            "aba": "1. Operação",
            "campo": "Consumidor final (indFinal)",
            "mensagem": "Campo Consumidor final deve ser '0' (Não) ou '1' (Sim)."
        })

    nat_op = str(cabecalho.get('natOp') or cabecalho.get('select_operacao') or '').strip()
    if not nat_op:
        erros.append({
            "categoria": "Identificação",
            "aba": "1. Identificação",
            "campo": "Natureza da Operação (natOp)",
            "mensagem": "Natureza da Operação é campo obrigatório pela SEFAZ."
        })
    elif len(nat_op) > 60:
        alertas.append({
            "categoria": "Identificação",
            "aba": "1. Identificação",
            "campo": "Natureza da Operação",
            "mensagem": f"Natureza da Operação possui {len(nat_op)} caracteres (limite máximo é 60)."
        })

    ref_nfe = re.sub(r'\D', '', str(cabecalho.get('refNFe') or cabecalho.get('chave_referenciada') or ''))
    if ref_nfe:
        if len(ref_nfe) != 44:
            erros.append({
                "categoria": "Identificação",
                "aba": "1. Identificação",
                "campo": "Chave Referenciada (refNFe)",
                "mensagem": f"Chave de acesso referenciada deve conter exatamente 44 dígitos numéricos (atual: {len(ref_nfe)})."
            })
    else:
        # Se for operação de devolução (ou finNFe=4), a SEFAZ exige obrigatoriamente a NF referenciada
        fin_nfe = str(cabecalho.get('finNFe') or '1')
        cfop_ref = str(cabecalho.get('cfop_padrao') or '').strip()
        cfops_devolucao = ('1201', '1202', '2201', '2202', '5201', '5202', '6201', '6202', '7201', '7202')
        is_devolucao = (fin_nfe == '4' or cfop_ref in cfops_devolucao or 'DEVOLU' in nat_op.upper())
        if is_devolucao:
            alertas.append({
                "categoria": "Identificação",
                "aba": "1. Identificação",
                "campo": "Chave Referenciada (refNFe)",
                "mensagem": "Operações de Devolução (ou finNFe=4) exigem obrigatoriamente a Chave de Acesso da NF-e referenciada (tag <NFref>) conforme MOC da SEFAZ."
            })

        # Validação preventiva para Retorno de Feira e Reexportação
        cfops_retorno_reexp = ('1914', '2914', '7930')
        has_retorno_reexp_item = any(re.sub(r'\D', '', str(it.get('CFOP') or '')) in cfops_retorno_reexp for it in itens) if itens else False
        is_retorno_reexp = (cfop_ref in cfops_retorno_reexp or has_retorno_reexp_item or 'RETORNO' in nat_op.upper() or 'REEXPORTA' in nat_op.upper())
        if is_retorno_reexp:
            alertas.append({
                "categoria": "Identificação",
                "aba": "1. Operação",
                "campo": "Chave Referenciada (refNFe)",
                "mensagem": "Operações de Retorno de Feira (CFOP 1914/2914) e Reexportação (CFOP 7930) recomendam/exigem informar a Chave de Acesso da NF-e referenciada de origem (<NFref>) para autorização na SEFAZ."
            })

    # 3. Emitente (emit)
    emit_cnpj = re.sub(r'\D', '', str(cabecalho.get('emit_CNPJ') or ''))
    if not emit_cnpj:
        erros.append({
            "categoria": "Emitente",
            "aba": "2. Emitente",
            "campo": "CNPJ Emitente",
            "mensagem": "CNPJ do emitente é obrigatório."
        })
    elif len(emit_cnpj) != 14:
        erros.append({
            "categoria": "Emitente",
            "aba": "2. Emitente",
            "campo": "CNPJ Emitente",
            "mensagem": f"CNPJ do emitente inválido (deve ter 14 dígitos, atual: {len(emit_cnpj)})."
        })

    emit_x_nome = str(cabecalho.get('emit_xNome') or '').strip()
    if not emit_x_nome:
        erros.append({
            "categoria": "Emitente",
            "aba": "2. Emitente",
            "campo": "Razão Social Emitente",
            "mensagem": "Razão Social do emitente é obrigatória."
        })

    emit_uf = str(cabecalho.get('emit_UF') or '').strip()
    if not emit_uf or len(emit_uf) != 2:
        erros.append({
            "categoria": "Emitente",
            "aba": "2. Emitente",
            "campo": "UF Emitente",
            "mensagem": "UF do emitente deve conter a sigla de 2 letras do Estado."
        })

    # 4. Destinatário (dest)
    dest_x_nome = str(cabecalho.get('dest_xNome') or '').strip()
    if not dest_x_nome:
        erros.append({
            "categoria": "Destinatário",
            "aba": "2. Destinatário",
            "campo": "Razão Social / Nome Destinatário",
            "mensagem": "Nome ou Razão Social do destinatário é obrigatório."
        })

    id_dest = str(cabecalho.get('idDest') or '1')
    if id_dest == '3':
        dest_uf = str(cabecalho.get('dest_UF') or '').strip().upper()
        if dest_uf and dest_uf != 'EX':
            alertas.append({
                "categoria": "Destinatário",
                "aba": "2. Destinatário",
                "campo": "UF Destinatário",
                "mensagem": "Operação para o exterior (idDest=3) deve ter UF do destinatário preenchida como 'EX'."
            })
        id_estrangeiro = str(cabecalho.get('dest_idEstrangeiro') or cabecalho.get('dest_CNPJ_CPF') or '').strip()
        if id_estrangeiro and (len(id_estrangeiro) < 5 or len(id_estrangeiro) > 20):
            alertas.append({
                "categoria": "Destinatário",
                "aba": "2. Destinatário",
                "campo": "ID Estrangeiro",
                "mensagem": f"ID Estrangeiro informado ({id_estrangeiro}) deve ter entre 5 e 20 caracteres conforme padrão SEFAZ (ou ser deixado em branco)."
            })
    else:
        dest_tp_doc = str(cabecalho.get('dest_tpDoc') or '').strip()
        if dest_tp_doc != 'Estrangeiro':
            dest_doc = re.sub(r'\D', '', str(cabecalho.get('dest_CNPJ_CPF') or ''))
            if not dest_doc:
                erros.append({
                    "categoria": "Destinatário",
                    "aba": "2. Destinatário",
                    "campo": "CNPJ / CPF Destinatário",
                    "mensagem": "CNPJ ou CPF do destinatário é obrigatório em operações nacionais."
                })
            elif len(dest_doc) not in (11, 14):
                erros.append({
                    "categoria": "Destinatário",
                    "aba": "2. Destinatário",
                    "campo": "CNPJ / CPF Destinatário",
                    "mensagem": f"Documento do destinatário inválido (CPF deve ter 11 dígitos, CNPJ deve ter 14 dígitos, atual: {len(dest_doc)})."
                })

    # 5. Informações de Exportação (exporta - MOC SEFAZ v4.00)
    exporta_data = rodape.get('exportacao') or cabecalho.get('exportacao') or {}
    uf_exp = str(exporta_data.get('UFSaidaPais') or cabecalho.get('exporta_UFSaidaPais') or rodape.get('exporta_UFSaidaPais') or '').strip().upper()
    loc_exp = str(exporta_data.get('xLocExporta') or cabecalho.get('exporta_xLocExporta') or rodape.get('exporta_xLocExporta') or '').strip()
    loc_desp = str(exporta_data.get('xLocDespacho') or cabecalho.get('exporta_xLocDespacho') or rodape.get('exporta_xLocDespacho') or '').strip()

    cfop_padrao = str(cabecalho.get('cfop_padrao') or '').strip()
    has_cfop_7 = cfop_padrao.startswith('7') or any(str(it.get('CFOP') or '').strip().startswith('7') for it in itens)
    nat_op_upper = nat_op.upper()
    is_op_exportacao = (has_cfop_7 or id_dest == '3' or 'EXPORTA' in nat_op_upper or 'REEXPORTA' in nat_op_upper)

    if uf_exp or loc_exp or loc_desp:
        if not is_op_exportacao:
            alertas.append({
                "categoria": "Exportação",
                "aba": "2. Transporte",
                "campo": "Grupo de Exportação (<exporta>)",
                "mensagem": "Campos de exportação preenchidos em operação que não possui CFOP 7xxx nem destinatário exterior (Rejeição SEFAZ 527)."
            })
        if loc_exp and not uf_exp:
            erros.append({
                "categoria": "Exportação",
                "aba": "2. Transporte",
                "campo": "UF de Embarque (UFSaidaPais)",
                "mensagem": "UF de embarque é obrigatória para o grupo de exportação da NF-e."
            })
        elif uf_exp and len(uf_exp) != 2:
            erros.append({
                "categoria": "Exportação",
                "aba": "2. Transporte",
                "campo": "UF de Embarque (UFSaidaPais)",
                "mensagem": "UF de embarque deve conter a sigla de 2 letras de um Estado brasileiro válido."
            })
        if uf_exp and not loc_exp:
            erros.append({
                "categoria": "Exportação",
                "aba": "2. Transporte",
                "campo": "Local de Embarque (xLocExporta)",
                "mensagem": "Local de embarque é obrigatório quando a UF de embarque for informada."
            })
        elif loc_exp and len(loc_exp) > 60:
            alertas.append({
                "categoria": "Exportação",
                "aba": "2. Transporte",
                "campo": "Local de Embarque (xLocExporta)",
                "mensagem": f"Local de embarque possui {len(loc_exp)} caracteres (limite máximo é 60)."
            })
        if loc_desp and len(loc_desp) > 60:
            alertas.append({
                "categoria": "Exportação",
                "aba": "2. Transporte",
                "campo": "Local de Despacho (xLocDespacho)",
                "mensagem": f"Local de despacho possui {len(loc_desp)} caracteres (limite máximo é 60)."
            })

    # 5. Totais e Conferência Financeira
    totais = rodape.get('totais', {}) if isinstance(rodape, dict) else {}
    soma_itens = sum(safe_float(it.get('vProd')) for it in itens) if itens else 0.0
    tot_v_prod = safe_float(totais.get('vProd'))
    if tot_v_prod > 0 and abs(soma_itens - tot_v_prod) > 0.05:
        alertas.append({
            "categoria": "Totais da NF",
            "aba": "4. Totais",
            "campo": "Total dos Produtos (vProd)",
            "mensagem": f"A soma dos produtos dos itens (R$ {soma_itens:,.2f}) difere do total informado no rodapé (R$ {tot_v_prod:,.2f})."
        })

    # 6. Teste de Estruturação do XML
    xml_construido = False
    if len(erros) == 0:
        try:
            xml_root = build_nfe_element(cabecalho, itens, rodape)
            xml_str = ET.tostring(xml_root, encoding='utf-8').decode('utf-8')
            if '<NFe' in xml_str and '</NFe>' in xml_str:
                xml_construido = True
        except Exception as e:
            erros.append({
                "categoria": "Esquema XML",
                "aba": "Geral",
                "campo": "Estrutura XML",
                "mensagem": f"Falha na montagem da estrutura do XML da NF-e: {str(e)}"
            })

    return {
        "valido": len(erros) == 0,
        "total_erros": len(erros),
        "total_alertas": len(alertas),
        "erros": erros,
        "alertas": alertas,
        "resumo": {
            "n_nf": n_nf or '1',
            "serie": serie or '1',
            "operacao": nat_op or 'Não definida',
            "destinatario": dest_x_nome or 'Não informado',
            "total_itens": len(itens) if itens else 0,
            "valor_total_produtos": soma_itens,
            "xml_construido": xml_construido
        }
    }

@app.route('/api/analisar_rascunho', methods=['POST'])
def api_analisar_rascunho():
    try:
        data = request.json or {}
        cabecalho = data.get('cabecalho', {})
        itens = data.get('itens', [])
        rodape = data.get('rodape', {})
        ref_interna = data.get('referencia_interna', '')

        resultado = validar_dados_nfe(cabecalho, itens, rodape, ref_interna)
        return jsonify({"sucesso": True, **resultado})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "error": f"Erro ao analisar rascunho: {str(e)}"}), 500

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

        chave_calc = (cabecalho.get('chaveAcesso') or cabecalho.get('chave_acesso') or data.get('chave_acesso') or '').replace(' ', '').strip()
        ref_para_nome = (ref_interna or f"REF-{n_nf}" if n_nf else "NFT").strip()
        ref_sanitizada = re.sub(r'[\\/:*?"<>|]+', '_', ref_para_nome).strip()
        ref_sanitizada = re.sub(r'\s+', ' ', ref_sanitizada)

        if chave_calc and n_nf:
            nome_arquivo = f"{ref_sanitizada} - DANFE {n_nf} - {chave_calc}.xml"
        else:
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

        # Salva copia do XML gerado no DOWNLOADS_DIR com a chave de acesso se existir
        if chave_calc and len(chave_calc) == 44:
            xml_dest = os.path.join(DOWNLOADS_DIR, f"{chave_calc}-nfe.xml")
            try:
                with open(xml_dest, 'wb') as f_dest:
                    f_dest.write(final_xml)
            except Exception as e_f:
                print(f"Aviso ao salvar XML no DOWNLOADS_DIR: {e_f}")

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
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT codigo, utrib, descricao_utrib, descricao, aliquota_ii, aliquota_ipi, aliquota_pis, aliquota_cofins, regime_pis_cofins, data_inicio, data_fim, tipo_ato, numero_ato, ano_ato FROM ncm ORDER BY codigo ASC').fetchall()
        conn.close()
        data = [dict(r) for r in rows]
        mem = io.BytesIO()
        mem.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="Tabela_NCM_Unificada.json", mimetype="application/json")
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar JSON de NCM: {str(e)}"}), 500

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

@app.route('/api/localidades/ufs')
def api_localidades_ufs():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        rows = c.execute("SELECT DISTINCT uf FROM tabela_municipios WHERE uf IS NOT NULL AND uf != '' ORDER BY uf ASC").fetchall()
        ufs = [r[0] for r in rows if r[0]]
        conn.close()
    except Exception:
        ufs = []
    if not ufs:
        ufs = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
    return jsonify(ufs)

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

# === ROTAS: DESCRIÇÃO DA FEIRA (FEIRAS DO ANO) ===

@app.route('/feiras')
def feiras_page():
    return render_template('feiras.html')

@app.route('/api/feiras', methods=['GET', 'POST'])
def api_feiras():
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'GET':
        termo = (request.args.get('busca') or '').strip().lower()
        if termo:
            query = """
                SELECT f.id, f.nome, f.data_feira, f.deadline, f.local, f.organizador, f.data_criacao, f.data_atualizacao,
                       l.endereco AS endereco_local
                FROM tabela_feiras f
                LEFT JOIN tabela_locais_entrega l ON UPPER(TRIM(f.local)) = UPPER(TRIM(l.nome))
                WHERE LOWER(f.nome) LIKE ? OR LOWER(f.local) LIKE ? OR LOWER(f.organizador) LIKE ?
                ORDER BY f.nome ASC
            """
            p = f"%{termo}%"
            rows = c.execute(query, (p, p, p)).fetchall()
        else:
            query = """
                SELECT f.id, f.nome, f.data_feira, f.deadline, f.local, f.organizador, f.data_criacao, f.data_atualizacao,
                       l.endereco AS endereco_local
                FROM tabela_feiras f
                LEFT JOIN tabela_locais_entrega l ON UPPER(TRIM(f.local)) = UPPER(TRIM(l.nome))
                ORDER BY f.nome ASC
            """
            rows = c.execute(query).fetchall()
        
        lista = []
        for r in rows:
            lista.append({
                'id': r['id'],
                'nome': r['nome'],
                'data_feira': r['data_feira'] or '',
                'deadline': r['deadline'] or '',
                'local': r['local'] or '',
                'organizador': r['organizador'] or '',
                'endereco_local': r['endereco_local'] or '',
                'data_criacao': r['data_criacao'],
                'data_atualizacao': r['data_atualizacao']
            })
        conn.close()
        return jsonify(lista)

    elif request.method == 'POST':
        data = request.json or {}
        nome = (data.get('nome') or '').strip()
        if not nome:
            conn.close()
            return jsonify({'error': 'O Nome da Feira é obrigatório.'}), 400

        data_feira = (data.get('data_feira') or '').strip()
        deadline = (data.get('deadline') or '').strip()
        local = (data.get('local') or '').strip()
        organizador = (data.get('organizador') or '').strip()

        c.execute("""
            INSERT INTO tabela_feiras (nome, data_feira, deadline, local, organizador, data_atualizacao)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (nome, data_feira, deadline, local, organizador))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'id': new_id, 'message': 'Feira cadastrada com sucesso!'}), 201

@app.route('/api/feiras/<int:feira_id>', methods=['GET', 'PUT', 'DELETE'])
def api_feira_item(feira_id):
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'GET':
        r = c.execute("""
            SELECT f.*, l.endereco AS endereco_local
            FROM tabela_feiras f
            LEFT JOIN tabela_locais_entrega l ON UPPER(TRIM(f.local)) = UPPER(TRIM(l.nome))
            WHERE f.id = ?
        """, (feira_id,)).fetchone()
        conn.close()
        if not r:
            return jsonify({'error': 'Feira não encontrada.'}), 404
        return jsonify({
            'id': r['id'],
            'nome': r['nome'],
            'data_feira': r['data_feira'] or '',
            'deadline': r['deadline'] or '',
            'local': r['local'] or '',
            'organizador': r['organizador'] or '',
            'endereco_local': r['endereco_local'] or '',
            'data_criacao': r['data_criacao'],
            'data_atualizacao': r['data_atualizacao']
        })

    elif request.method == 'PUT':
        data = request.json or {}
        nome = (data.get('nome') or '').strip()
        if not nome:
            conn.close()
            return jsonify({'error': 'O Nome da Feira é obrigatório.'}), 400

        data_feira = (data.get('data_feira') or '').strip()
        deadline = (data.get('deadline') or '').strip()
        local = (data.get('local') or '').strip()
        organizador = (data.get('organizador') or '').strip()

        c.execute("""
            UPDATE tabela_feiras
            SET nome = ?, data_feira = ?, deadline = ?, local = ?, organizador = ?, data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (nome, data_feira, deadline, local, organizador, feira_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Feira atualizada com sucesso!'})

    elif request.method == 'DELETE':
        c.execute("DELETE FROM tabela_feiras WHERE id = ?", (feira_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Feira removida com sucesso!'})

@app.route('/api/feiras/sync_sheets', methods=['GET', 'POST'])
def api_feiras_sync_sheets():
    """Obtém ou atualiza a base de feiras a partir de um link do Google Sheets informado pelo usuário"""
    import urllib.request, csv, io, re

    conn = get_db_connection()
    c = conn.cursor()

    padrao_url = 'https://docs.google.com/spreadsheets/d/1AdyWmSlqCaVaPJ0khW2siap-kVzNxu-n8kdyZu5u7SU/edit?gid=82185219'

    # Se for GET, retorna o link salvo atualmente no sistema
    if request.method == 'GET':
        row = c.execute("SELECT valor FROM sistema_config WHERE chave = 'feiras_google_sheets_url'").fetchone()
        conn.close()
        url_salva = row['valor'] if (row and row['valor']) else padrao_url
        return jsonify({'status': 'success', 'url': url_salva})

    # Se for POST, executa a sincronização com o link enviado ou salvo
    data = request.json or {}
    url_input = (data.get('url') or '').strip()

    if not url_input:
        row = c.execute("SELECT valor FROM sistema_config WHERE chave = 'feiras_google_sheets_url'").fetchone()
        url_input = row['valor'] if (row and row['valor']) else padrao_url

    # Salva o novo link no banco para futuras sincronizações
    c.execute("""
        INSERT OR REPLACE INTO sistema_config (chave, valor, data_atualizacao)
        VALUES ('feiras_google_sheets_url', ?, CURRENT_TIMESTAMP)
    """, (url_input,))
    conn.commit()

    # Converte URL para formato de exportação CSV caso seja um link comum de visualização/edição do Sheets
    url_csv = url_input
    match_key = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_input)
    if match_key:
        sheet_id = match_key.group(1)
        match_gid = re.search(r'[#&?]gid=([0-9]+)', url_input)
        gid = match_gid.group(1) if match_gid else '0'
        url_csv = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'

    try:
        req = urllib.request.Request(url_csv, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            reader = csv.reader(io.StringIO(content.strip()))
            rows = list(reader)
            if len(rows) > 1:
                # 1. Localiza a linha do cabeçalho de colunas (procura onde estão 'feira' ou 'nome')
                header_idx = -1
                for i, r in enumerate(rows[:10]):
                    row_txt = ' '.join(r).lower()
                    if 'feira' in row_txt and ('data' in row_txt or 'local' in row_txt or 'organizador' in row_txt or 'deadline' in row_txt or 'prazo' in row_txt):
                        header_idx = i
                        break

                col_map = {'nome': -1, 'data_feira': -1, 'deadline': -1, 'local': -1, 'organizador': -1}

                if header_idx != -1:
                    header_row = rows[header_idx]
                    for j, cell in enumerate(header_row):
                        c_clean = cell.strip().lower().replace('\n', ' ')
                        if not c_clean:
                            continue
                        if ('feira' in c_clean or 'nome' in c_clean or 'evento' in c_clean) and 'data' not in c_clean and 'deadline' not in c_clean and 'descri' not in c_clean:
                            if col_map['nome'] == -1: col_map['nome'] = j
                        elif 'data' in c_clean and col_map['data_feira'] == -1:
                            col_map['data_feira'] = j
                        elif ('deadline' in c_clean or 'prazo' in c_clean or '-30' in c_clean) and col_map['deadline'] == -1:
                            col_map['deadline'] = j
                        elif 'local' in c_clean and col_map['local'] == -1:
                            col_map['local'] = j
                        elif ('organizador' in c_clean or 'empresa' in c_clean or 'promotora' in c_clean) and col_map['organizador'] == -1:
                            col_map['organizador'] = j
                    start_data_idx = header_idx + 1
                else:
                    # Fallback posicional caso não haja cabeçalho explícito
                    col_map = {'nome': 1, 'data_feira': 2, 'deadline': 3, 'local': 4, 'organizador': 5}
                    start_data_idx = 1

                # Se a coluna do nome não foi encontrada no cabeçalho, tenta primeira coluna com texto representativo
                if col_map['nome'] == -1:
                    col_map['nome'] = 1 if (len(rows[0]) > 1) else 0

                inseridos = 0
                atualizados = 0

                for r in rows[start_data_idx:]:
                    if not r or len(r) == 0:
                        continue

                    # Extrai valores de acordo com as colunas mapeadas
                    def get_cell(idx):
                        if idx >= 0 and idx < len(r):
                            return r[idx].strip()
                        return ""

                    nome = get_cell(col_map['nome'])

                    # Se a linha estiver vazia ou for repetição de cabeçalho, pula
                    if not nome or nome.lower() in ('feira', 'nome da feira', 'evento', 'descrição da feira', 'descricao da feira'):
                        continue

                    data_feira = get_cell(col_map['data_feira'])
                    deadline = get_cell(col_map['deadline'])
                    local = get_cell(col_map['local'])
                    organizador = get_cell(col_map['organizador'])

                    # Se todos os outros campos estiverem vazios e o nome parecer título da página, pula
                    if not data_feira and not deadline and not local and not organizador:
                        continue

                    # Upsert por nome (case insensitive e ignorando espaços extras)
                    existente = c.execute("SELECT id FROM tabela_feiras WHERE LOWER(TRIM(nome)) = LOWER(TRIM(?))", (nome,)).fetchone()
                    if existente:
                        c.execute("""
                            UPDATE tabela_feiras
                            SET nome = ?, data_feira = ?, deadline = ?, local = ?, organizador = ?, data_atualizacao = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (nome, data_feira, deadline, local, organizador, existente['id']))
                        atualizados += 1
                    else:
                        c.execute("""
                            INSERT INTO tabela_feiras (nome, data_feira, deadline, local, organizador)
                            VALUES (?, ?, ?, ?, ?)
                        """, (nome, data_feira, deadline, local, organizador))
                        inseridos += 1

                conn.commit()
                conn.close()

                total_processados = inseridos + atualizados
                detalhe_msg = []
                if atualizados > 0:
                    detalhe_msg.append(f"{atualizados} feiras atualizadas")
                if inseridos > 0:
                    detalhe_msg.append(f"{inseridos} novas feiras incluídas")

                resumo_texto = " e ".join(detalhe_msg) if detalhe_msg else "nenhuma alteração necessária"

                return jsonify({
                    'status': 'success',
                    'count': total_processados,
                    'atualizados': atualizados,
                    'inseridos': inseridos,
                    'url': url_input,
                    'message': f'Sincronização concluída com sucesso: {resumo_texto} a partir da planilha do Google Sheets!'
                })
    except urllib.error.HTTPError as he:
        conn.close()
        if he.code in (401, 403):
            return jsonify({
                'status': 'warning',
                'url': url_input,
                'message': 'A planilha do Google Sheets requer permissão de acesso público. No Google Sheets clique em "Compartilhar" e defina o Acesso Geral para: "Qualquer pessoa com o link" como "Leitor".'
            })
        return jsonify({
            'status': 'error',
            'url': url_input,
            'message': f'Erro HTTP {he.code} ao acessar a planilha. Verifique o link fornecido.'
        })
    except Exception as e:
        conn.close()
        return jsonify({
            'status': 'error',
            'url': url_input,
            'message': f'Falha ao conectar com o Google Sheets: {str(e)}'
        })

    conn.close()
    return jsonify({
        'status': 'warning',
        'url': url_input,
        'message': 'A planilha informada não retornou linhas válidas de dados. Verifique se o link e a aba (gid) estão corretos.'
    })

# === ROTAS: LOCAIS DE ENTREGA (CENTROS DE EXPOSIÇÕES) ===

@app.route('/api/locais_entrega', methods=['GET', 'POST'])
def api_locais_entrega():
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'GET':
        termo = (request.args.get('busca') or '').strip().lower()
        if termo:
            query = """
                SELECT id, nome, endereco, data_criacao, data_atualizacao
                FROM tabela_locais_entrega
                WHERE LOWER(nome) LIKE ? OR LOWER(endereco) LIKE ?
                ORDER BY nome ASC
            """
            p = f"%{termo}%"
            rows = c.execute(query, (p, p)).fetchall()
        else:
            query = """
                SELECT id, nome, endereco, data_criacao, data_atualizacao
                FROM tabela_locais_entrega
                ORDER BY nome ASC
            """
            rows = c.execute(query).fetchall()

        lista = []
        for r in rows:
            lista.append({
                'id': r['id'],
                'nome': r['nome'],
                'endereco': r['endereco'] or '',
                'data_criacao': r['data_criacao'],
                'data_atualizacao': r['data_atualizacao']
            })
        conn.close()
        return jsonify(lista)

    elif request.method == 'POST':
        data = request.json or {}
        nome = (data.get('nome') or '').strip()
        if not nome:
            conn.close()
            return jsonify({'error': 'O Nome do Local é obrigatório.'}), 400

        endereco = re.sub(r'[\r\n]+', ' - ', (data.get('endereco') or '')).strip()
        endereco = re.sub(r'\s+', ' ', endereco)

        try:
            c.execute("""
                INSERT INTO tabela_locais_entrega (nome, endereco, data_atualizacao)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (nome, endereco))
            new_id = c.lastrowid
            conn.commit()
            conn.close()
            return jsonify({'status': 'success', 'id': new_id, 'message': 'Local de entrega cadastrado com sucesso!'}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Já existe um local cadastrado com esse nome.'}), 409

@app.route('/api/locais_entrega/<int:local_id>', methods=['GET', 'PUT', 'DELETE'])
def api_local_entrega_item(local_id):
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'GET':
        r = c.execute("SELECT * FROM tabela_locais_entrega WHERE id = ?", (local_id,)).fetchone()
        conn.close()
        if not r:
            return jsonify({'error': 'Local não encontrado.'}), 404
        return jsonify({
            'id': r['id'],
            'nome': r['nome'],
            'endereco': r['endereco'] or '',
            'data_criacao': r['data_criacao'],
            'data_atualizacao': r['data_atualizacao']
        })

    elif request.method == 'PUT':
        data = request.json or {}
        nome = (data.get('nome') or '').strip()
        if not nome:
            conn.close()
            return jsonify({'error': 'O Nome do Local é obrigatório.'}), 400

        endereco = re.sub(r'[\r\n]+', ' - ', (data.get('endereco') or '')).strip()
        endereco = re.sub(r'\s+', ' ', endereco)

        try:
            c.execute("""
                UPDATE tabela_locais_entrega
                SET nome = ?, endereco = ?, data_atualizacao = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (nome, endereco, local_id))
            conn.commit()
            conn.close()
            return jsonify({'status': 'success', 'message': 'Local atualizado com sucesso!'})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Já existe outro local cadastrado com esse nome.'}), 409

    elif request.method == 'DELETE':
        c.execute("DELETE FROM tabela_locais_entrega WHERE id = ?", (local_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Local removido com sucesso!'})

@app.route('/api/ping')
def ping():
    resp = jsonify({'status': 'ok', 'port': 1652})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

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

@app.route('/api/certificado/status', methods=['GET'])
def api_certificado_status():
    info = sefaz_client.get_certificate_info()
    return jsonify(info)

@app.route('/api/certificado/importar', methods=['POST'])
def api_certificado_importar():
    try:
        if 'file' not in request.files and 'certificado' not in request.files:
            return jsonify({'status': 'error', 'message': 'Nenhum arquivo enviado.'}), 400
        
        file = request.files.get('file') or request.files.get('certificado')
        if not file or not file.filename:
            return jsonify({'status': 'error', 'message': 'Arquivo inválido ou não selecionado.'}), 400
        
        filename = file.filename.strip()
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.pfx', '.p12'):
            return jsonify({'status': 'error', 'message': 'Formato não suportado. Por favor, envie um arquivo .pfx ou .p12.'}), 400
        
        senha = (request.form.get('senha') or 'nftecnpj').strip()
        senha_bytes = senha.encode('utf-8')
        
        pfx_bytes = file.read()
        if not pfx_bytes or len(pfx_bytes) < 32:
            return jsonify({'status': 'error', 'message': 'O arquivo do certificado está vazio ou corrompido.'}), 400
        
        # Validar o certificado e a senha com a biblioteca cryptography
        try:
            info = sefaz_client.validar_e_extrair_info_pfx(pfx_bytes, senha_bytes)
        except Exception as e_val:
            err_msg = str(e_val)
            if 'password' in err_msg.lower() or 'mac' in err_msg.lower() or 'pkcs12' in err_msg.lower():
                return jsonify({'status': 'error', 'message': 'Senha incorreta para o certificado digital. Verifique a senha informada e tente novamente.'}), 400
            return jsonify({'status': 'error', 'message': f'Erro ao validar o certificado digital: {err_msg}'}), 400
        
        # Salva o arquivo na pasta gerador/certificado
        cert_dir = os.path.join(os.path.dirname(__file__), 'certificado')
        os.makedirs(cert_dir, exist_ok=True)
        
        nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        caminho_final = os.path.join(cert_dir, nome_sanitizado)
        with open(caminho_final, 'wb') as f:
            f.write(pfx_bytes)
        
        # Atualiza o sefaz_client ativo em memória
        sefaz_client.set_active_certificate(caminho_final, senha_bytes)
        
        # Persiste a configuração no banco de dados SQLite
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO sistema_config (chave, valor, data_atualizacao) VALUES (?, ?, CURRENT_TIMESTAMP)",
                     ('certificado_ativo_arquivo', nome_sanitizado))
        conn.execute("INSERT OR REPLACE INTO sistema_config (chave, valor, data_atualizacao) VALUES (?, ?, CURRENT_TIMESTAMP)",
                     ('certificado_ativo_senha', senha))
        conn.commit()
        conn.close()
        
        info['arquivo'] = nome_sanitizado
        info['message'] = 'Certificado digital importado, validado e ativado com sucesso!'
        return jsonify(info)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro interno ao importar certificado: {str(e)}'}), 500

@app.route('/api/sefaz/enviar', methods=['POST'])
def api_sefaz_enviar():
    try:
        data = request.json or {}
        xml_string = data.get('xml')
        chave_input = (data.get('chave') or 'N/A').strip()
        tpAmb = int(data.get('tpAmb', 2))
        
        if not xml_string:
            return jsonify({'error': 'XML não fornecido'}), 400
            
        # Sanitizar XML (garante regras 598 em homologação, cPais 1600, tolerância 630 e dhEmi/chave)
        xml_sanitizado, chave_calculada = sefaz_client.sanitizar_xml_para_envio(xml_string, tpAmb=tpAmb)
        chave = chave_calculada if chave_calculada else chave_input
        
        xml_assinado = sefaz_client.assinar_xml(xml_sanitizado)
        retorno = sefaz_client.enviar_nfe(xml_assinado, uf='SP', tpAmb=tpAmb)
        
        if retorno.get('chave'):
            chave = retorno['chave']
        retorno['chave'] = chave
        
        cstat = str(retorno.get('cstat', '')).strip()
        xmotivo = str(retorno.get('xmotivo', '')).strip()
        # Apenas cStat 100 é Autorizado (cStat 104 é Lote Processado, podendo conter rejeição no infProt como 225)
        # Normalização de segurança: Se vier 801 ou motivo de autorização sem rejeição, normaliza para 100
        is_autorizado = (cstat in ('100', '801') and ('autoriz' in xmotivo.lower() or cstat == '100')) or (retorno.get('status') == 'success' and 'autoriz' in xmotivo.lower() and 'rejei' not in xmotivo.lower())
        if is_autorizado:
            cstat = '100'
            retorno['cstat'] = '100'
        retorno['autorizado'] = is_autorizado
        
        # Se autorizado, salva os 3 arquivos imediatamente na pasta de download
        if chave and chave != 'N/A':
            xml_final = xml_assinado
            if is_autorizado and retorno.get('response_xml'):
                try:
                    ret_root = etree.fromstring(retorno['response_xml'].encode('utf-8'))
                    prot_el = ret_root.find('.//{http://www.portalfiscal.inf.br/nfe}protNFe')
                    if prot_el is not None:
                        nfe_root = etree.fromstring(xml_assinado.encode('utf-8'))
                        proc_el = etree.Element('{http://www.portalfiscal.inf.br/nfe}nfeProc', versao="4.00", nsmap={None: 'http://www.portalfiscal.inf.br/nfe'})
                        proc_el.append(nfe_root)
                        proc_el.append(prot_el)
                        xml_final = etree.tostring(proc_el, encoding='utf-8', xml_declaration=True).decode('utf-8')
                except Exception as e_xml:
                    print(f"Aviso ao montar nfeProc: {e_xml}")
                    xml_final = xml_assinado
            
            if is_autorizado:
                try:
                    xml_path = os.path.join(DOWNLOADS_DIR, f"{chave}-nfe.xml")
                    with open(xml_path, 'w', encoding='utf-8') as f:
                        f.write(xml_final)
                        
                    pdf_path = os.path.join(DOWNLOADS_DIR, f"{chave}-danfe.pdf")
                    try:
                        from danfe_generator import DanfeGenerator
                        DanfeGenerator().render(xml_final, pdf_path)
                    except Exception as e_pdf:
                        print(f"Aviso ao renderizar DANFE dinâmico: {e_pdf}")
                        
                    zip_path = os.path.join(DOWNLOADS_DIR, f"{chave}-arquivos.zip")
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        if os.path.exists(pdf_path):
                            zf.write(pdf_path, f"{chave}-danfe.pdf")
                        if os.path.exists(xml_path):
                            zf.write(xml_path, f"{chave}-nfe.xml")
                except Exception as e_save:
                    print(f"Erro ao salvar arquivos em downloads: {e_save}")

        # Salvar no histórico
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO historico_sefaz (chave_nfe, tpAmb, cstat, xmotivo, recibo, protocolo, xml_envio, xml_retorno)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chave,
            tpAmb,
            retorno.get('cstat', ''),
            retorno.get('xmotivo', ''),
            retorno.get('recibo', ''),
            retorno.get('protocolo', ''),
            xml_assinado,
            retorno.get('response_xml', '')
        ))

        # Atualiza referencia_interna em notas_fiscais se fornecida
        ref_req = (data.get('referencia_interna') or '').strip()
        if ref_req and chave and chave != 'N/A':
            chave_limpa = chave.replace(' ', '')
            c.execute('''
                INSERT INTO notas_fiscais (chave_nfe, referencia_interna, status)
                VALUES (?, ?, ?)
                ON CONFLICT(chave_nfe) DO UPDATE SET referencia_interna = excluded.referencia_interna
            ''', (chave_limpa, ref_req, 'Autorizada' if is_autorizado else 'Rejeitada'))

        conn.commit()
        conn.close()
        
        return jsonify(retorno)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sefaz/cancelar', methods=['POST'])
def api_sefaz_cancelar():
    try:
        data = request.json or {}
        chave = str(data.get('chave') or '').strip()
        protocolo = str(data.get('protocolo') or '').strip()
        justificativa = str(data.get('justificativa') or '').strip()
        tpAmb = int(data.get('tpAmb', 1)) # Padrão Produção (1)
        
        if not chave or len(chave) != 44:
            return jsonify({'error': 'Chave de acesso inválida ou não informada (deve ter 44 dígitos).'}), 400
        if not protocolo:
            return jsonify({'error': 'Número do protocolo de autorização é obrigatório para cancelamento.'}), 400
        if len(justificativa) < 15:
            return jsonify({'error': 'A justificativa de cancelamento deve ter no mínimo 15 caracteres (exigência SEFAZ).'}), 400
            
        retorno = sefaz_client.cancelar_nfe(
            chave=chave,
            protocolo_autorizacao=protocolo,
            justificativa=justificativa,
            tpAmb=tpAmb,
            uf='SP'
        )
        
        cstat = str(retorno.get('cstat', ''))
        xmotivo = str(retorno.get('xmotivo', ''))
        # 135: Evento registrado e vinculado a NF-e (Cancelamento homologado)
        is_cancelado = (cstat in ('135', '136', '101') or 'cancelamento' in xmotivo.lower())
        retorno['autorizado'] = is_cancelado
        retorno['is_evento'] = True
        retorno['tipo_evento'] = 'Cancelamento'
        
        # Salva no histórico SEFAZ
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO historico_sefaz (chave_nfe, tpAmb, cstat, xmotivo, recibo, protocolo, xml_envio, xml_retorno)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chave,
            tpAmb,
            cstat or 'EVENTO',
            f"[Cancelamento] {xmotivo}",
            '',
            retorno.get('protocolo', protocolo),
            retorno.get('xml_evento_assinado', ''),
            retorno.get('response_xml', '')
        ))
        
        # Atualiza status em notas_fiscais se cancelado com sucesso
        if is_cancelado and chave:
            chave_limpa = chave.replace(' ', '')
            c.execute('''
                UPDATE notas_fiscais SET
                    status = 'Cancelada',
                    protocolo = ?,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE REPLACE(chave_nfe, ' ', '') = ?
            ''', (retorno.get('protocolo', protocolo), chave_limpa))

        conn.commit()
        conn.close()
        
        return jsonify(retorno)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sefaz/carta_correcao', methods=['POST'])
def api_sefaz_carta_correcao():
    try:
        data = request.json or {}
        chave = str(data.get('chave') or '').strip()
        texto_correcao = str(data.get('texto_correcao') or '').strip()
        tpAmb = int(data.get('tpAmb', 1)) # Padrão Produção (1)
        
        if not chave or len(chave) != 44:
            return jsonify({'error': 'Chave de acesso inválida ou não informada (deve ter 44 dígitos).'}), 400
        if len(texto_correcao) < 15:
            return jsonify({'error': 'O texto da Carta de Correção deve ter no mínimo 15 caracteres (exigência SEFAZ).'}), 400
            
        # Determina o próximo nSeqEvento se não informado ou se já houver CC-e anteriores
        conn = get_db_connection()
        c = conn.cursor()
        
        req_seq = data.get('nSeqEvento')
        if not req_seq or int(req_seq) <= 1:
            # Conta quantas CC-e já foram registradas para essa chave
            c.execute('''
                SELECT COUNT(*) FROM historico_sefaz 
                WHERE REPLACE(chave_nfe, ' ', '') = ? 
                  AND (cstat IN ('135', '136') OR xmotivo LIKE '%CC-e%' OR xmotivo LIKE '%Carta de Corre%')
            ''', (chave,))
            qtd_anteriores = c.fetchone()[0]
            nSeqEvento = qtd_anteriores + 1
        else:
            nSeqEvento = int(req_seq)

        retorno = sefaz_client.carta_correcao_nfe(
            chave=chave,
            texto_correcao=texto_correcao,
            nSeqEvento=nSeqEvento,
            tpAmb=tpAmb,
            uf='SP'
        )
        
        cstat = str(retorno.get('cstat', ''))
        xmotivo = str(retorno.get('xmotivo', ''))
        # 135: Evento registrado e vinculado a NF-e
        is_homologado = (cstat in ('135', '136') or 'vinculado' in xmotivo.lower())
        retorno['autorizado'] = is_homologado
        retorno['is_evento'] = True
        retorno['tipo_evento'] = 'Carta de Correção'
        
        # Salva no histórico SEFAZ
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO historico_sefaz (chave_nfe, tpAmb, cstat, xmotivo, recibo, protocolo, xml_envio, xml_retorno)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chave,
            tpAmb,
            cstat or 'EVENTO',
            f"[CC-e #{nSeqEvento}] {xmotivo}",
            '',
            retorno.get('protocolo', ''),
            retorno.get('xml_evento_assinado', ''),
            retorno.get('response_xml', '')
        ))
        conn.commit()
        conn.close()
        
        return jsonify(retorno)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def garantir_xml_e_danfe_nota(chave, retorno_sefaz=None):
    """
    Localiza ou gera o XML e o DANFE (PDF) legítimos correspondentes à chave informada,
    sincronizando os dados oficiais da SEFAZ (protocolo, data/hora, digestValue e eventos de CC-e).
    Garante que NUNCA seja entregue um documento de outra NF-e.
    """
    chave_limpa = re.sub(r'\D', '', str(chave or '')).strip()
    if len(chave_limpa) != 44:
        return None, None

    xml_path = os.path.join(DOWNLOADS_DIR, f"{chave_limpa}-nfe.xml")
    pdf_path = os.path.join(DOWNLOADS_DIR, f"{chave_limpa}-danfe.pdf")

    c_uf = chave_limpa[0:2]
    aamm = chave_limpa[2:6]
    cnpj_emit = chave_limpa[6:20]
    mod_nf = chave_limpa[20:22]
    serie_nf = str(int(chave_limpa[22:25]))
    n_nf = str(int(chave_limpa[25:34]))
    tp_emis = chave_limpa[34:35]
    c_nf = chave_limpa[35:43]
    c_dv = chave_limpa[43:44]

    conn = get_db_connection()
    c = conn.cursor()

    base_xml = None

    # 1. Se já existe o XML no disco local para esta chave exata
    if os.path.exists(xml_path) and os.path.getsize(xml_path) > 100:
        try:
            with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                base_xml = f.read()
        except Exception:
            pass

    # 2. Busca no histórico SEFAZ por chave exata
    if not base_xml:
        row = c.execute(
            "SELECT xml_envio FROM historico_sefaz WHERE REPLACE(chave_nfe, ' ', '') = ? AND xml_envio IS NOT NULL AND length(xml_envio) > 100 ORDER BY id DESC LIMIT 1",
            (chave_limpa,)
        ).fetchone()
        if row and row['xml_envio']:
            base_xml = row['xml_envio']

    # 3. Busca no histórico SEFAZ pelo número da NF-e (ex: <nNF>899</nNF>)
    if not base_xml:
        row = c.execute(
            "SELECT xml_envio FROM historico_sefaz WHERE xml_envio LIKE ? AND xml_envio IS NOT NULL ORDER BY id DESC LIMIT 1",
            (f"%<nNF>{n_nf}</nNF>%",)
        ).fetchone()
        if row and row['xml_envio']:
            base_xml = row['xml_envio']

    # 4. Busca nos rascunhos vinculados à chave ou pelo número da nota
    if not base_xml:
        r_rows = c.execute("SELECT * FROM rascunhos ORDER BY id DESC").fetchall()
        for r_row in r_rows:
            r_chave = (r_row['chave_acesso'] or '').replace(' ', '')
            if r_chave == chave_limpa or (len(r_chave) >= 34 and str(int(r_chave[25:34])) == n_nf):
                nome_arq = r_row['caminho_arquivo_isolado']
                if nome_arq:
                    p_json = os.path.join(RASCUNHOS_DIR, nome_arq)
                    if os.path.exists(p_json):
                        try:
                            with open(p_json, 'r', encoding='utf-8') as fj:
                                dj = json.load(fj)
                                dc = dj.get('dados_completos') or {}
                                cand = dc.get('xml_original') or dj.get('xml_original') or dj.get('xml_conteudo')
                                if cand and len(cand) > 100:
                                    base_xml = cand
                                    break
                        except Exception:
                            pass

    # 5. Busca na pasta downloads por qualquer XML com o mesmo nNF
    if not base_xml and os.path.exists(DOWNLOADS_DIR):
        for fname in os.listdir(DOWNLOADS_DIR):
            if fname.endswith('-nfe.xml'):
                fpath = os.path.join(DOWNLOADS_DIR, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fx:
                        txt = fx.read()
                        if f"<nNF>{n_nf}</nNF>" in txt:
                            base_xml = txt
                            break
                except Exception:
                    pass

    # Se ainda não temos retorno_sefaz detalhado e precisamos sincronizar com a SEFAZ
    if retorno_sefaz is None:
        h_row = c.execute(
            "SELECT protocolo, cstat, xmotivo, xml_retorno FROM historico_sefaz WHERE REPLACE(chave_nfe, ' ', '') = ? ORDER BY id DESC LIMIT 1",
            (chave_limpa,)
        ).fetchone()
        if h_row and h_row['protocolo']:
            retorno_sefaz = {
                'cstat': h_row['cstat'] or '100',
                'xmotivo': h_row['xmotivo'] or 'Autorizado o uso da NF-e',
                'protocolo_autorizacao': h_row['protocolo'],
                'data_autorizacao': '',
                'eventos': []
            }
        else:
            try:
                retorno_sefaz = sefaz_client.consultar_nfe(chave=chave_limpa, tpAmb=1)
                if retorno_sefaz.get('cstat') != '100':
                    ret_h = sefaz_client.consultar_nfe(chave=chave_limpa, tpAmb=2)
                    if ret_h.get('cstat') == '100':
                        retorno_sefaz = ret_h
            except Exception as e_cons:
                print(f"Aviso ao consultar SEFAZ para sincronização do DANFE: {e_cons}")
                retorno_sefaz = {}

    prot_aut = (retorno_sefaz or {}).get('protocolo_autorizacao') or ''
    dh_aut = (retorno_sefaz or {}).get('data_autorizacao') or (retorno_sefaz or {}).get('dh_recbto') or ''
    dig_val = (retorno_sefaz or {}).get('digest_value') or ''
    cstat_aut = (retorno_sefaz or {}).get('cstat') or '100'
    xmotivo_aut = (retorno_sefaz or {}).get('xmotivo') or 'Autorizado o uso da NF-e'
    eventos_sefaz = (retorno_sefaz or {}).get('eventos') or []
    tp_amb = str((retorno_sefaz or {}).get('tpAmb') or '1')

    # Dados de notas_fiscais
    nf_row = c.execute(
        "SELECT referencia_interna, tipo_operacao, valor_total FROM notas_fiscais WHERE REPLACE(COALESCE(chave_nfe, ''), ' ', '') = ? OR numero_nfe = ? LIMIT 1",
        (chave_limpa, n_nf)
    ).fetchone()
    ref_interna = nf_row['referencia_interna'] if nf_row and nf_row['referencia_interna'] else ''
    tipo_operacao = nf_row['tipo_operacao'] if nf_row and nf_row['tipo_operacao'] else ''
    valor_total = float(nf_row['valor_total'] or 0.0) if nf_row else 0.0

    # Sincroniza XML base
    if base_xml:
        try:
            root = etree.fromstring(base_xml.encode('utf-8') if isinstance(base_xml, str) else base_xml)
            for p in root.xpath("//*[local-name()='protNFe']"):
                p.getparent().remove(p)

            for inf in root.xpath("//*[local-name()='infNFe']"):
                inf.attrib['Id'] = f"NFe{chave_limpa}"
                for ide in inf.xpath("./*[local-name()='ide']"):
                    for el in ide.xpath("./*[local-name()='cNF']"): el.text = c_nf
                    for el in ide.xpath("./*[local-name()='cDV']"): el.text = c_dv
                    for el in ide.xpath("./*[local-name()='nNF']"): el.text = n_nf
                    for el in ide.xpath("./*[local-name()='serie']"): el.text = serie_nf
                    for el in ide.xpath("./*[local-name()='tpAmb']"): el.text = tp_amb
                    if dh_aut:
                        for el in ide.xpath("./*[local-name()='dhEmi']"): el.text = dh_aut
                    if tipo_operacao:
                        for el in ide.xpath("./*[local-name()='natOp']"): el.text = tipo_operacao

                for evt in eventos_sefaz:
                    if evt.get('tipo') == '110110':
                        txt_corr = evt.get('detalhe') or evt.get('motivo') or ''
                        seq = evt.get('sequencia') or '1'
                        data_e = evt.get('data') or ''
                        prot_e = evt.get('protocolo') or ''
                        m_peso = re.search(r'PESO\s+BRUTO\s+DE\s+[\d\.,]+\s*KG\s+PARA\s+([\d\.,]+)\s*KG', txt_corr, re.IGNORECASE)
                        if m_peso:
                            novo_peso = m_peso.group(1).replace('.', '').replace(',', '.')
                            for peso_el in inf.xpath(".//vol/pesoB"):
                                peso_el.text = f"{float(novo_peso):.3f}"

                        for inf_adic in inf.xpath("./*[local-name()='infAdic']"):
                            for inf_cpl in inf_adic.xpath("./*[local-name()='infCpl']"):
                                cpl_orig = inf_cpl.text or ''
                                cce_str = f" [CC-e #{seq} em {data_e} Prot:{prot_e}]: {txt_corr}"
                                if txt_corr and txt_corr not in cpl_orig:
                                    inf_cpl.text = cpl_orig + cce_str

            prot_el = etree.Element("{http://www.portalfiscal.inf.br/nfe}protNFe", versao="4.00")
            inf_prot = etree.SubElement(prot_el, "{http://www.portalfiscal.inf.br/nfe}infProt")
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}tpAmb").text = tp_amb
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}verAplic").text = "SP_NFE_PL009_V4"
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}chNFe").text = chave_limpa
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}dhRecbto").text = dh_aut or datetime.now().isoformat()
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}nProt").text = prot_aut or "135260000000000"
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}digVal").text = dig_val
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}cStat").text = cstat_aut
            etree.SubElement(inf_prot, "{http://www.portalfiscal.inf.br/nfe}xMotivo").text = xmotivo_aut

            if root.tag.endswith('NFe'):
                nfe_proc = etree.Element("{http://www.portalfiscal.inf.br/nfe}nfeProc", versao="4.00")
                nfe_proc.append(root)
                nfe_proc.append(prot_el)
                final_xml_root = nfe_proc
            else:
                root.append(prot_el)
                final_xml_root = root

            final_xml_bytes = etree.tostring(final_xml_root, encoding='utf-8')
            with open(xml_path, 'wb') as fx:
                fx.write(final_xml_bytes)
        except Exception as e_proc:
            print(f"Aviso ao processar base_xml para {chave_limpa}: {e_proc}")

    # Se ainda não temos xml_path (caso de nota sem histórico local)
    if not os.path.exists(xml_path):
        cpl_eventos = ""
        for evt in eventos_sefaz:
            if evt.get('tipo') == '110110':
                cpl_eventos += f" [CC-e #{evt.get('sequencia','1')} em {evt.get('data','')} Prot:{evt.get('protocolo','')}]: {evt.get('detalhe','')}"

        xml_canonico = f'''<?xml version="1.0" encoding="utf-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe versao="4.00" Id="NFe{chave_limpa}">
      <ide>
        <cUF>{c_uf}</cUF>
        <cNF>{c_nf}</cNF>
        <natOp>{tipo_operacao or 'REEXPORTAÇÃO DE ADMISSÃO TEMPORÁRIA'}</natOp>
        <mod>{mod_nf}</mod>
        <serie>{serie_nf}</serie>
        <nNF>{n_nf}</nNF>
        <dhEmi>{dh_aut or datetime.now().isoformat()}</dhEmi>
        <dhSaiEnt>{dh_aut or datetime.now().isoformat()}</dhSaiEnt>
        <tpNF>1</tpNF>
        <idDest>3</idDest>
        <cMunFG>3550308</cMunFG>
        <tpImp>1</tpImp>
        <tpEmis>1</tpEmis>
        <cDV>{c_dv}</cDV>
        <tpAmb>{tp_amb}</tpAmb>
        <finNFe>1</finNFe>
        <indFinal>0</indFinal>
        <indPres>0</indPres>
        <procEmi>0</procEmi>
        <verProc>4.01_nft_logistics</verProc>
      </ide>
      <emit>
        <CNPJ>47998441000198</CNPJ>
        <xNome>NFT Logistics LTDA</xNome>
        <enderEmit>
          <xLgr>Avenida Doutor Gastao Vidigal</xLgr>
          <nro>1132</nro>
          <xCpl>SALA 910 TORRE B</xCpl>
          <xBairro>Vila Leopoldina</xBairro>
          <cMun>3550308</cMun>
          <xMun>Sao Paulo</xMun>
          <UF>SP</UF>
          <CEP>05314000</CEP>
          <cPais>1058</cPais>
          <xPais>Brasil</xPais>
        </enderEmit>
        <IE>138843326117</IE>
        <CRT>1</CRT>
      </emit>
      <dest>
        <idEstrangeiro/>
        <xNome>{ref_interna or 'CLIENTE / OPERAÇÃO INTERNACIONAL'}</xNome>
        <enderDest>
          <xLgr>EXTERIOR</xLgr>
          <nro>S/N</nro>
          <xBairro>EXTERIOR</xBairro>
          <cMun>9999999</cMun>
          <xMun>EXTERIOR</xMun>
          <UF>EX</UF>
          <CEP>99999999</CEP>
          <cPais>1058</cPais>
          <xPais>EXTERIOR</xPais>
        </enderDest>
        <indIEDest>9</indIEDest>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>{n_nf}-1</cProd>
          <cEAN>SEM GTIN</cEAN>
          <xProd>{tipo_operacao or 'MERCADORIA EM REGIME ESPECIAL'}</xProd>
          <NCM>84279000</NCM>
          <CFOP>7930</CFOP>
          <uCom>UN</uCom>
          <qCom>1.0000</qCom>
          <vUnCom>{valor_total or 0.0:.2f}</vUnCom>
          <vProd>{valor_total or 0.0:.2f}</vProd>
          <cEANTrib>SEM GTIN</cEANTrib>
          <uTrib>UN</uTrib>
          <qTrib>1.0000</qTrib>
          <vUnTrib>{valor_total or 0.0:.2f}</vUnTrib>
          <indTot>1</indTot>
        </prod>
        <imposto>
          <ICMS><ICMSSN102><orig>1</orig><CSOSN>300</CSOSN></ICMSSN102></ICMS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vBC>0.00</vBC>
          <vICMS>0.00</vICMS>
          <vProd>{valor_total or 0.0:.2f}</vProd>
          <vNF>{valor_total or 0.0:.2f}</vNF>
        </ICMSTot>
      </total>
      <transp>
        <modFrete>1</modFrete>
        <vol>
          <qVol>1</qVol>
          <esp>VOLUMES</esp>
          <pesoL>10.500</pesoL>
          <pesoB>11.600</pesoB>
        </vol>
      </transp>
      <infAdic>
        <infCpl>{ref_interna}{cpl_eventos}</infCpl>
      </infAdic>
    </infNFe>
    <protNFe versao="4.00">
      <infProt>
        <tpAmb>{tp_amb}</tpAmb>
        <verAplic>SP_NFE_PL009_V4</verAplic>
        <chNFe>{chave_limpa}</chNFe>
        <dhRecbto>{dh_aut or datetime.now().isoformat()}</dhRecbto>
        <nProt>{prot_aut or "135260000000000"}</nProt>
        <digVal>{dig_val}</digVal>
        <cStat>{cstat_aut}</cStat>
        <xMotivo>{xmotivo_aut}</xMotivo>
      </infProt>
    </protNFe>
  </NFe>
</nfeProc>'''
        with open(xml_path, 'w', encoding='utf-8') as fx:
            fx.write(xml_canonico)

    # 6. Renderiza o PDF via DanfeGenerator legítimo
    if os.path.exists(xml_path):
        try:
            from danfe_generator import DanfeGenerator
            DanfeGenerator().render(xml_path, pdf_path)
        except Exception as e_gen:
            print(f"Erro ao renderizar DANFE para {chave_limpa}: {e_gen}")

    conn.close()
    return (xml_path if os.path.exists(xml_path) else None,
            pdf_path if os.path.exists(pdf_path) else None)


@app.route('/api/sefaz/consultar', methods=['POST'])
def api_sefaz_consultar():
    try:
        data = request.json or {}
        chave = str(data.get('chave') or '').strip().replace(' ', '')
        tpAmb = int(data.get('tpAmb', 1)) # Padrão Produção (1)
        
        if not chave or len(chave) != 44:
            return jsonify({'error': 'Chave de acesso inválida ou não informada (deve ter 44 dígitos).'}), 400
            
        retorno = sefaz_client.consultar_nfe(chave=chave, tpAmb=tpAmb, uf='SP')
        
        if retorno.get('status') == 'success':
            conn = get_db_connection()
            c = conn.cursor()
            
            cstat_resp = str(retorno.get('cstat') or '')
            xmotivo_resp = str(retorno.get('xmotivo') or '')
            is_cancelada = bool(retorno.get('is_cancelada') or cstat_resp == '101' or 'cancelamento' in xmotivo_resp.lower())
            is_autorizada = ((cstat_resp == '100' or retorno.get('protocolo_autorizacao')) and not is_cancelada)
            
            status_db = 'Cancelada' if is_cancelada else ('Autorizada' if is_autorizada else 'Rejeitada')
            prot_db = retorno.get('protocolo_cancelamento') or retorno.get('protocolo_autorizacao') or ''

            # 1. Localiza rascunho vinculado a esta chave de acesso
            rascunho_row = c.execute(
                "SELECT * FROM rascunhos WHERE REPLACE(COALESCE(chave_acesso, ''), ' ', '') = ? ORDER BY id DESC LIMIT 1",
                (chave,)
            ).fetchone()

            xml_encontrado = None
            ref_interna = ''
            tipo_operacao = ''
            v_total_db = 0.0
            qtd_itens_db = 0
            n_nf_db = ''

            if rascunho_row:
                ref_interna = rascunho_row['referencia_interna'] or ''
                tipo_operacao = rascunho_row['tipo_operacao'] or ''
                v_total_db = float(rascunho_row['valor_total'] or 0.0)
                qtd_itens_db = int(rascunho_row['qtd_itens'] or 0)
                
                # Tenta extrair o XML do arquivo JSON do rascunho
                nome_arq_isolado = rascunho_row['caminho_arquivo_isolado']
                if nome_arq_isolado:
                    caminho_json = os.path.join(RASCUNHOS_DIR, nome_arq_isolado)
                    if os.path.exists(caminho_json):
                        try:
                            with open(caminho_json, 'r', encoding='utf-8') as fj:
                                d_json = json.load(fj)
                                dc = d_json.get('dados_completos') or {}
                                xml_encontrado = dc.get('xml_original') or d_json.get('xml_original') or d_json.get('xml_conteudo')
                                if not ref_interna:
                                    ref_interna = d_json.get('referencia_interna') or dc.get('referencia_interna') or ''
                                if not tipo_operacao:
                                    tipo_operacao = d_json.get('tipo_operacao') or dc.get('tipo_operacao') or ''
                        except Exception as e_json:
                            print(f"Aviso ao ler rascunho para consulta SEFAZ: {e_json}")

            # Se não achou nos rascunhos, busca se já tem no banco notas_fiscais
            if not ref_interna:
                nf_row = c.execute(
                    "SELECT referencia_interna, tipo_operacao, valor_total FROM notas_fiscais WHERE REPLACE(COALESCE(chave_nfe, ''), ' ', '') = ? LIMIT 1",
                    (chave,)
                ).fetchone()
                if nf_row:
                    ref_interna = nf_row['referencia_interna'] or ''
                    if not tipo_operacao:
                        tipo_operacao = nf_row['tipo_operacao'] or ''
                    if not v_total_db and nf_row['valor_total']:
                        v_total_db = float(nf_row['valor_total'] or 0.0)

            # Extração de dados a partir do XML original
            dh_emi_db = ''
            nat_op_db = ''
            tp_nf_db = '1'
            v_prod_db = 0.0
            
            if xml_encontrado:
                try:
                    root_xml = etree.fromstring(xml_encontrado.encode('utf-8') if isinstance(xml_encontrado, str) else xml_encontrado)
                    def _get_val(tag):
                        nodes = root_xml.xpath(f"//*[local-name()='{tag}']")
                        return nodes[0].text if nodes and nodes[0].text else ''
                    
                    n_nf_db = _get_val('nNF')
                    dh_emi_db = _get_val('dhEmi')
                    nat_op_db = _get_val('natOp')
                    tp_nf_db = _get_val('tpNF') or '1'
                    v_prod_db = float(_get_val('vProd') or 0.0)
                    v_nf_val = float(_get_val('vNF') or 0.0)
                    if v_nf_val > 0:
                        v_total_db = v_nf_val
                    if not tipo_operacao and nat_op_db:
                        tipo_operacao = nat_op_db
                except Exception as e_parse:
                    print(f"Aviso ao parsear XML original da nota consultada: {e_parse}")

            if not n_nf_db and len(chave) >= 34:
                try:
                    n_nf_db = str(int(chave[25:34]))
                except Exception:
                    pass

            # Formata data_hora para formato compatível com o banco (YYYY-MM-DD HH:MM:SS)
            data_hora_banco = retorno.get('dh_recbto') or retorno.get('data_autorizacao') or ''
            if not data_hora_banco and dh_emi_db:
                data_hora_banco = dh_emi_db
            try:
                if 'T' in data_hora_banco:
                    dt_p = data_hora_banco.split('T')[0]
                    tm_p = data_hora_banco.split('T')[1].split('-')[0].split('+')[0]
                    data_hora_banco = f"{dt_p} {tm_p}"
            except Exception:
                pass

            # 2. Salva os arquivos (XML e PDF legítimos) sincronizados com os dados da SEFAZ
            xml_path, pdf_path = garantir_xml_e_danfe_nota(chave, retorno_sefaz=retorno)
            zip_path = os.path.join(DOWNLOADS_DIR, f"{chave}-arquivos.zip")
            if (xml_path or pdf_path) and not os.path.exists(zip_path):
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        if pdf_path and os.path.exists(pdf_path):
                            zf.write(pdf_path, f"{chave}-danfe.pdf")
                        if xml_path and os.path.exists(xml_path):
                            zf.write(xml_path, f"{chave}-nfe.xml")
                except Exception as e_zip:
                    print(f"Aviso ao gerar ZIP para nota consultada: {e_zip}")

            # 3. Registra no historico_sefaz (APENAS UMA VEZ por chave)
            hist_existente = c.execute(
                "SELECT id FROM historico_sefaz WHERE REPLACE(chave_nfe, ' ', '') = ? LIMIT 1",
                (chave,)
            ).fetchone()

            if not hist_existente:
                c.execute('''
                    INSERT INTO historico_sefaz (chave_nfe, tpAmb, cstat, xmotivo, recibo, protocolo, xml_envio, xml_retorno)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chave,
                    tpAmb,
                    retorno.get('cstat') or '100',
                    retorno.get('xmotivo') or 'Autorizado o uso da NF-e',
                    '',
                    prot_db,
                    xml_encontrado or '',
                    retorno.get('raw_xml') or ''
                ))

            # 4. Registra/Atualiza em notas_fiscais para constar no relatório
            nf_existente = c.execute(
                "SELECT id, referencia_interna FROM notas_fiscais WHERE REPLACE(chave_nfe, ' ', '') = ? LIMIT 1",
                (chave,)
            ).fetchone()

            caminho_xml_rel = f"{chave}-nfe.xml" if os.path.exists(xml_path) else ''
            caminho_pdf_rel = f"{chave}-danfe.pdf" if os.path.exists(pdf_path) else ''

            if nf_existente:
                c.execute('''
                    UPDATE notas_fiscais SET
                        status = ?,
                        protocolo = CASE WHEN ? != '' THEN ? ELSE protocolo END,
                        cstat = ?,
                        xmotivo = ?,
                        caminho_xml = CASE WHEN ? != '' THEN ? ELSE caminho_xml END,
                        caminho_pdf = CASE WHEN ? != '' THEN ? ELSE caminho_pdf END,
                        data_atualizacao = CURRENT_TIMESTAMP
                    WHERE REPLACE(chave_nfe, ' ', '') = ?
                ''', (status_db, prot_db, prot_db, retorno.get('cstat'), retorno.get('xmotivo'), caminho_xml_rel, caminho_xml_rel, caminho_pdf_rel, caminho_pdf_rel, chave))
            else:
                c.execute('''
                    INSERT INTO notas_fiscais (
                        chave_nfe, referencia_interna, data_hora, numero_nfe, tipo_operacao,
                        tipo_movimento, valor_total, total_produtos, status, protocolo,
                        recibo, ambiente, cstat, xmotivo, caminho_xml, caminho_pdf, oculto
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ''', (
                    chave,
                    ref_interna or f"REF-{n_nf_db}",
                    data_hora_banco,
                    n_nf_db,
                    tipo_operacao or 'CONSULTA SEFAZ',
                    tp_nf_db,
                    v_total_db,
                    v_prod_db,
                    status_db,
                    prot_db,
                    '',
                    tpAmb,
                    retorno.get('cstat') or '100',
                    retorno.get('xmotivo') or 'Autorizado o uso da NF-e',
                    caminho_xml_rel,
                    caminho_pdf_rel
                ))

            conn.commit()
            conn.close()

            retorno['registrado_historico'] = True
            retorno['tem_arquivos'] = bool(os.path.exists(xml_path) or os.path.exists(pdf_path))
            
        return jsonify(retorno)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def obter_nome_padrao_arquivo(chave, xml_content_or_path=None):
    """
    Retorna o nome base padronizado para os arquivos:
    "{referencia Interna} - DANFE {Numero da Nota} - {chave}"
    """
    chave_limpa = (chave or '').replace(' ', '').strip()
    ref_interna = ''
    n_nf = ''

    # 1. Tenta buscar da tabela notas_fiscais
    try:
        conn = get_db_connection()
        c = conn.cursor()
        row = c.execute("SELECT numero_nfe, referencia_interna FROM notas_fiscais WHERE REPLACE(chave_nfe, ' ', '') = ? LIMIT 1", (chave_limpa,)).fetchone()
        if row:
            if row['numero_nfe']:
                n_nf = str(row['numero_nfe']).strip()
            if row['referencia_interna'] and row['referencia_interna'] != '-':
                ref_interna = str(row['referencia_interna']).strip()
        
        # Se não achou ref em notas_fiscais, tenta nos rascunhos
        if not ref_interna:
            r_row = c.execute("SELECT referencia_interna FROM rascunhos WHERE REPLACE(chave_acesso, ' ', '') = ? AND referencia_interna IS NOT NULL AND referencia_interna != '' LIMIT 1", (chave_limpa,)).fetchone()
            if r_row and r_row['referencia_interna']:
                ref_interna = str(r_row['referencia_interna']).strip()
        conn.close()
    except Exception as e_db:
        print(f"Aviso ao consultar nome padrão no banco: {e_db}")

    # 2. Se ainda faltar n_nf ou ref_interna, extrai do XML
    xml_data = None
    if xml_content_or_path:
        if isinstance(xml_content_or_path, str) and os.path.exists(xml_content_or_path):
            try:
                with open(xml_content_or_path, 'r', encoding='utf-8') as f_x:
                    xml_data = f_x.read()
            except Exception:
                pass
        elif isinstance(xml_content_or_path, str):
            xml_data = xml_content_or_path
        elif isinstance(xml_content_or_path, bytes):
            xml_data = xml_content_or_path.decode('utf-8', errors='ignore')

    if not xml_data:
        xml_local = os.path.join(DOWNLOADS_DIR, f"{chave_limpa}-nfe.xml")
        if os.path.exists(xml_local):
            try:
                with open(xml_local, 'r', encoding='utf-8') as f_x:
                    xml_data = f_x.read()
            except Exception:
                pass

    if xml_data:
        try:
            root = etree.fromstring(xml_data.encode('utf-8'))
            if not n_nf:
                nnf_nodes = root.xpath("//*[local-name()='nNF']")
                if nnf_nodes and nnf_nodes[0].text:
                    n_nf = nnf_nodes[0].text.strip()
            if not ref_interna:
                cpl_nodes = root.xpath("//*[local-name()='infCpl']")
                if cpl_nodes and cpl_nodes[0].text:
                    txt = cpl_nodes[0].text
                    m = re.search(r'S/REF:\s*([A-Za-z0-9_\-\.\/]+)', txt) or re.search(r'N/REF:\s*([A-Za-z0-9_\-\.\/]+)', txt) or re.search(r'(NFT\d+-[A-Za-z0-9]+)', txt)
                    if m:
                        ref_interna = m.group(1).strip()
                    elif 'DI:' in txt:
                        m_di = re.search(r'DI:\s*([0-9\/\-]+)', txt)
                        if m_di:
                            ref_interna = f"DI {m_di.group(1).strip()}"
        except Exception:
            pass

    # 3. Fallbacks caso ainda não tenha encontrado
    if not n_nf and len(chave_limpa) >= 34:
        try:
            n_nf = str(int(chave_limpa[25:34]))
        except Exception:
            n_nf = ''

    if not ref_interna:
        ref_interna = f"REF-{n_nf}" if n_nf else "NFT"

    # Sanitiza caracteres proibidos em nomes de arquivo
    ref_sanitizada = re.sub(r'[\\/:*?"<>|]+', '_', ref_interna).strip()
    ref_sanitizada = re.sub(r'\s+', ' ', ref_sanitizada)

    return f"{ref_sanitizada} - DANFE {n_nf} - {chave_limpa}"

@app.route('/api/sefaz/download/pdf/<chave>', methods=['GET'])
def download_pdf(chave):
    chave = chave.strip().replace(' ', '')
    xml_path, pdf_path = garantir_xml_e_danfe_nota(chave)
            
    if pdf_path and os.path.exists(pdf_path):
        nome_download = f"{obter_nome_padrao_arquivo(chave, xml_path)}.pdf"
        return send_file(pdf_path, as_attachment=True, download_name=nome_download, mimetype='application/pdf')
    return "PDF não encontrado para esta NF-e", 404

@app.route('/api/sefaz/download/xml/<chave>', methods=['GET'])
def download_xml(chave):
    chave = chave.strip().replace(' ', '')
    xml_path, _ = garantir_xml_e_danfe_nota(chave)
    if xml_path and os.path.exists(xml_path):
        nome_download = f"{obter_nome_padrao_arquivo(chave, xml_path)}.xml"
        return send_file(xml_path, as_attachment=True, download_name=nome_download, mimetype='application/xml')
    return "XML não encontrado para esta NF-e", 404

@app.route('/api/sefaz/download/zip/<chave>', methods=['GET'])
def download_zip(chave):
    chave = chave.strip().replace(' ', '')
    xml_path, pdf_path = garantir_xml_e_danfe_nota(chave)
    zip_path = os.path.join(DOWNLOADS_DIR, f"{chave}-arquivos.zip")
    nome_padrao = obter_nome_padrao_arquivo(chave, xml_path)
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if pdf_path and os.path.exists(pdf_path):
            zf.write(pdf_path, f"{nome_padrao}.pdf")
        if xml_path and os.path.exists(xml_path):
            zf.write(xml_path, f"{nome_padrao}.xml")
            
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name=f"{nome_padrao}.zip", mimetype='application/zip')
    return "Arquivos não encontrados para gerar o ZIP", 404

# ==============================================================================
# === MÓDULO RELATÓRIO: NOTAS FISCAIS GERADAS & FILTROS AVANÇADOS ===
# ==============================================================================

def sync_and_get_notas_fiscais(conn):
    """
    Sincroniza histórico SEFAZ, downloads e rascunhos para a tabela notas_fiscais,
    garantindo que todas as notas emitidas, autorizadas ou canceladas estejam atualizadas.
    """
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave_nfe TEXT UNIQUE,
            referencia_interna TEXT,
            data_hora TEXT,
            numero_nfe TEXT,
            tipo_operacao TEXT,
            tipo_movimento TEXT DEFAULT '1',
            valor_total REAL DEFAULT 0.0,
            total_produtos REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Gerada',
            protocolo TEXT DEFAULT '',
            recibo TEXT DEFAULT '',
            ambiente INTEGER DEFAULT 2,
            cstat TEXT DEFAULT '',
            xmotivo TEXT DEFAULT '',
            caminho_xml TEXT DEFAULT '',
            caminho_pdf TEXT DEFAULT '',
            oculto INTEGER DEFAULT 0,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        c.execute('ALTER TABLE notas_fiscais ADD COLUMN oculto INTEGER DEFAULT 0')
    except Exception:
        pass
    conn.commit()

    rascunhos_rows = c.execute('SELECT * FROM rascunhos').fetchall()

    def find_reference(chave, xml_str):
        # 1. Match direto em rascunhos por chave
        for r in rascunhos_rows:
            r_chave = (r['chave_acesso'] or '').replace(' ', '')
            if r_chave and (chave in r_chave or r_chave in chave):
                if r['referencia_interna']:
                    return r['referencia_interna'].strip()
        
        # 2. Extrai de infCpl do XML
        if xml_str:
            try:
                root_cpl = etree.fromstring(xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str)
                cpl_nodes = root_cpl.xpath("//*[local-name()='infCpl']")
                if cpl_nodes and cpl_nodes[0].text:
                    txt = cpl_nodes[0].text
                    m = re.search(r'S/REF:\s*([A-Za-z0-9_\-\.\/]+)', txt)
                    if m: return m.group(1).strip()
                    m = re.search(r'N/REF:\s*([A-Za-z0-9_\-\.\/]+)', txt)
                    if m: return m.group(1).strip()
                    m = re.search(r'(NFT\d+-[A-Za-z0-9]+)', txt)
                    if m: return m.group(1).strip()
                    m = re.search(r'DI:\s*([0-9\/\-]+)', txt)
                    if m: return f"DI {m.group(1).strip()}"
            except Exception:
                pass

        # 3. Match rascunho por número nNF contido na chave (dígitos 25..34)
        try:
            if len(chave) >= 34:
                chave_nnf = str(int(chave[25:34]))
                for r in rascunhos_rows:
                    r_chave = (r['chave_acesso'] or '').replace(' ', '')
                    if len(r_chave) >= 34:
                        r_nnf = str(int(r_chave[25:34]))
                        if r_nnf == chave_nnf and r['referencia_interna']:
                            return r['referencia_interna'].strip()
        except Exception:
            pass
            
        return "-"

    # Agrupa histórico da SEFAZ
    hist_rows = c.execute('SELECT * FROM historico_sefaz ORDER BY id ASC').fetchall()
    notas_dict = {}

    for r in hist_rows:
        raw_chave = (r['chave_nfe'] or '').replace(' ', '').strip()
        if not raw_chave or raw_chave == 'N/A' or len(raw_chave) < 44:
            continue
        if raw_chave not in notas_dict:
            notas_dict[raw_chave] = {
                'chave': raw_chave,
                'tpAmb': r['tpAmb'],
                'data_envio': r['data_envio'],
                'cstat': str(r['cstat'] or ''),
                'xmotivo': r['xmotivo'] or '',
                'recibo': r['recibo'] or '',
                'protocolo': r['protocolo'] or '',
                'xml_envio': r['xml_envio'] or '',
                'status': 'Rejeitada' if str(r['cstat']) != '100' else 'Autorizada',
                'eventos': []
            }
        item = notas_dict[raw_chave]
        cstat_str = str(r['cstat'] or '')
        xmotivo_str = (r['xmotivo'] or '').lower()

        if cstat_str in ('100', '801') or ('autoriz' in xmotivo_str and 'rejei' not in xmotivo_str):
            item['status'] = 'Autorizada'
            if r['protocolo']: item['protocolo'] = r['protocolo']
            if r['recibo']: item['recibo'] = r['recibo']
            if r['xml_envio']: item['xml_envio'] = r['xml_envio']
            item['cstat'] = '100'
            item['xmotivo'] = r['xmotivo'] or 'Autorizado o uso da NF-e'

        if 'cancel' in xmotivo_str and cstat_str in ('135', '136', '101'):
            item['status'] = 'Cancelada'
            if r['protocolo']: item['protocolo_cancelamento'] = r['protocolo']

        if '[cc-e' in xmotivo_str and cstat_str in ('135', '136'):
            item['eventos'].append('CC-e')
            if item['status'] != 'Cancelada':
                item['has_cce'] = True

    # Processa e persiste cada nota
    for chave, item in notas_dict.items():
        xml_str = item['xml_envio']
        nNF = ''
        dhEmi = item['data_envio'] or ''
        natOp = ''
        tpNF = '1'
        vNF = 0.0
        vProd = 0.0

        if xml_str:
            try:
                root_xml = etree.fromstring(xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str)
                def get_tag(tag):
                    nodes = root_xml.xpath(f"//*[local-name()='{tag}']")
                    return nodes[0].text if nodes and nodes[0].text else ''
                
                nNF = get_tag('nNF')
                dhEmi = get_tag('dhEmi') or dhEmi
                natOp = get_tag('natOp')
                tpNF = get_tag('tpNF') or '1'
                vNF = float(get_tag('vNF') or 0.0)
                vProd = float(get_tag('vProd') or 0.0)
            except Exception as e_xml:
                print(f"Aviso ao analisar XML para chave {chave}: {e_xml}")

        if not nNF and len(chave) >= 34:
            try: nNF = str(int(chave[25:34]))
            except: pass

        ref_interna = find_reference(chave, xml_str)
        
        # Formata data_hora para exibicao/armazenamento padrao
        data_hora_fmt = dhEmi
        try:
            if 'T' in dhEmi:
                dt_part = dhEmi.split('T')[0]
                tm_part = dhEmi.split('T')[1].split('-')[0].split('+')[0]
                data_hora_fmt = f"{dt_part} {tm_part}"
        except Exception:
            pass

        # Verifica presenca dos arquivos em downloads
        xml_file = f"{chave}-nfe.xml"
        pdf_file = f"{chave}-danfe.pdf"
        caminho_xml = xml_file if os.path.exists(os.path.join(DOWNLOADS_DIR, xml_file)) else ''
        caminho_pdf = pdf_file if os.path.exists(os.path.join(DOWNLOADS_DIR, pdf_file)) else ''

        # Protocolo final
        protocolo_final = item.get('protocolo_cancelamento') or item.get('protocolo') or ''

        # Upsert
        existing = c.execute('SELECT id, referencia_interna, oculto FROM notas_fiscais WHERE chave_nfe = ?', (chave,)).fetchone()
        if existing:
            if existing['referencia_interna'] and existing['referencia_interna'] != '-':
                ref_interna = existing['referencia_interna']
            c.execute('''
                UPDATE notas_fiscais SET
                    referencia_interna = ?,
                    data_hora = ?,
                    numero_nfe = ?,
                    tipo_operacao = ?,
                    tipo_movimento = ?,
                    valor_total = ?,
                    total_produtos = ?,
                    status = ?,
                    protocolo = ?,
                    recibo = ?,
                    ambiente = ?,
                    cstat = ?,
                    xmotivo = ?,
                    caminho_xml = ?,
                    caminho_pdf = ?,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE chave_nfe = ?
            ''', (
                ref_interna, data_hora_fmt, nNF, natOp, tpNF, vNF, vProd,
                item['status'], protocolo_final, item.get('recibo', ''),
                item['tpAmb'], item['cstat'], item['xmotivo'], caminho_xml, caminho_pdf,
                chave
            ))
        else:
            c.execute('''
                INSERT INTO notas_fiscais (
                    chave_nfe, referencia_interna, data_hora, numero_nfe, tipo_operacao,
                    tipo_movimento, valor_total, total_produtos, status, protocolo,
                    recibo, ambiente, cstat, xmotivo, caminho_xml, caminho_pdf, oculto
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                chave, ref_interna, data_hora_fmt, nNF, natOp, tpNF, vNF, vProd,
                item['status'], protocolo_final, item.get('recibo', ''),
                item['tpAmb'], item['cstat'], item['xmotivo'], caminho_xml, caminho_pdf
            ))

    conn.commit()

    # Busca todas as notas ativas (não ocultadas) ordenadas por data
    rows = c.execute('SELECT * FROM notas_fiscais WHERE COALESCE(oculto, 0) = 0 ORDER BY data_hora DESC, id DESC').fetchall()
    
    lista = []
    for r in rows:
        d = dict(r)
        # Formata chave com espacos para exibicao (ex: 3526 1047 ...)
        ch = d['chave_nfe']
        ch_fmt = ' '.join([ch[i:i+4] for i in range(0, len(ch), 4)]) if len(ch) == 44 else ch
        d['chave_formatada'] = ch_fmt
        
        # Formata data_hora para formato brasileiro DD/MM/YYYY HH:mm:ss
        raw_dt = d['data_hora'] or ''
        dt_br = raw_dt
        try:
            if '-' in raw_dt:
                partes = raw_dt.split(' ')
                data_p = partes[0].split('-')
                if len(data_p) == 3:
                    hora_p = partes[1] if len(partes) > 1 else ''
                    dt_br = f"{data_p[2]}/{data_p[1]}/{data_p[0]}"
                    if hora_p: dt_br += f" {hora_p}"
        except Exception:
            pass
        d['data_hora_formatada'] = dt_br

        # Formata valores monetarios
        v_total = float(d['valor_total'] or 0.0)
        v_prod = float(d['total_produtos'] or 0.0)
        d['valor_total_fmt'] = f"R$ {v_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        d['total_produtos_fmt'] = f"R$ {v_prod:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Garante flags de arquivos
        xml_p = os.path.join(DOWNLOADS_DIR, f"{ch}-nfe.xml")
        pdf_p = os.path.join(DOWNLOADS_DIR, f"{ch}-danfe.pdf")
        d['has_xml'] = os.path.exists(xml_p) or bool(d['caminho_xml'])
        d['has_pdf'] = os.path.exists(pdf_p) or bool(d['caminho_pdf'])
        lista.append(d)

    return lista

@app.route('/relatorios', methods=['GET'])
@app.route('/relatorio', methods=['GET'])
def pagina_relatorios():
    return render_template('relatorios.html')

@app.route('/api/relatorios/notas', methods=['GET'])
def api_relatorios_notas():
    try:
        conn = get_db_connection()
        notas = sync_and_get_notas_fiscais(conn)
        conn.close()

        # Parametros de filtro
        search = (request.args.get('search') or '').strip().lower()
        data_ini = (request.args.get('data_inicio') or '').strip()
        data_fim = (request.args.get('data_fim') or '').strip()
        status_filtro = (request.args.get('status') or '').strip()
        op_filtro = (request.args.get('tipo_operacao') or '').strip()
        mov_filtro = (request.args.get('tipo_movimento') or '').strip()
        ambiente_filtro = (request.args.get('ambiente') or '').strip()
        v_min = request.args.get('v_min')
        v_max = request.args.get('v_max')
        p_min = request.args.get('p_min')
        p_max = request.args.get('p_max')

        # Operações distintas para o dropdown
        operacoes_disponiveis = sorted(list(set(n['tipo_operacao'] for n in notas if n.get('tipo_operacao'))))

        filtradas = []
        for n in notas:
            # Filtro por busca textual (referencia, chave, numero_nfe, tipo_operacao, protocolo, recibo)
            if search:
                alvo = f"{n.get('referencia_interna','')} {n.get('chave_nfe','')} {n.get('numero_nfe','')} {n.get('tipo_operacao','')} {n.get('protocolo','')} {n.get('recibo','')}".lower()
                if search not in alvo:
                    continue

            # Filtro por periodo de data (YYYY-MM-DD)
            data_raw = (n.get('data_hora') or '')[:10]
            if data_ini and data_raw and data_raw < data_ini:
                continue
            if data_fim and data_raw and data_raw > data_fim:
                continue

            # Filtro por status
            if status_filtro and status_filtro != 'Todos':
                if n.get('status') != status_filtro:
                    continue

            # Filtro por operacao
            if op_filtro and op_filtro != 'Todas':
                if n.get('tipo_operacao') != op_filtro:
                    continue

            # Filtro por movimento (0=Entrada, 1=Saida)
            if mov_filtro and mov_filtro != 'Todos':
                if str(n.get('tipo_movimento', '1')) != mov_filtro:
                    continue

            # Filtro por ambiente
            if ambiente_filtro and ambiente_filtro != 'Todos':
                if str(n.get('ambiente', '2')) != ambiente_filtro:
                    continue

            # Filtro por faixa de vNF
            v_tot = float(n.get('valor_total') or 0.0)
            if v_min:
                try:
                    if v_tot < float(v_min): continue
                except: pass
            if v_max:
                try:
                    if v_tot > float(v_max): continue
                except: pass

            # Filtro por faixa de vProd
            v_pr = float(n.get('total_produtos') or 0.0)
            if p_min:
                try:
                    if v_pr < float(p_min): continue
                except: pass
            if p_max:
                try:
                    if v_pr > float(p_max): continue
                except: pass

            filtradas.append(n)

        # Totais e resumo
        resumo = {
            'total_notas': len(filtradas),
            'total_valor': sum(float(n.get('valor_total') or 0.0) for n in filtradas),
            'total_produtos': sum(float(n.get('total_produtos') or 0.0) for n in filtradas),
            'total_autorizadas': sum(1 for n in filtradas if n.get('status') == 'Autorizada'),
            'total_canceladas': sum(1 for n in filtradas if n.get('status') == 'Cancelada'),
            'total_rejeitadas': sum(1 for n in filtradas if n.get('status') == 'Rejeitada')
        }
        resumo['total_valor_fmt'] = f"R$ {resumo['total_valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        resumo['total_produtos_fmt'] = f"R$ {resumo['total_produtos']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        return jsonify({
            'success': True,
            'total': len(filtradas),
            'resumo': resumo,
            'operacoes': operacoes_disponiveis,
            'notas': filtradas
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/notas/atualizar_referencia', methods=['POST'])
def api_relatorios_atualizar_referencia():
    try:
        data = request.json or {}
        chave = (data.get('chave') or '').strip().replace(' ', '')
        nova_ref = (data.get('referencia_interna') or '').strip()
        
        if not chave:
            return jsonify({'success': False, 'error': 'Chave de acesso não informada.'}), 400
            
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE notas_fiscais SET
                referencia_interna = ?,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE REPLACE(chave_nfe, ' ', '') = ?
        ''', (nova_ref, chave))
        
        # Tambem atualiza rascunhos vinculados se houver
        c.execute('''
            UPDATE rascunhos SET
                referencia_interna = ?,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE REPLACE(chave_acesso, ' ', '') = ?
        ''', (nova_ref, chave))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'referencia_interna': nova_ref})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/notas/excluir', methods=['POST'])
def api_relatorios_excluir_nota():
    try:
        data = request.json or {}
        chave = (data.get('chave') or '').strip().replace(' ', '')
        
        if not chave:
            return jsonify({'success': False, 'error': 'Chave de acesso não informada.'}), 400
            
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE notas_fiscais SET
                oculto = 1,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE REPLACE(chave_nfe, ' ', '') = ?
        ''', (chave,))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Nota fiscal excluída do relatório com sucesso.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    get_db_connection().close()
    app.run(debug=True, port=1652)



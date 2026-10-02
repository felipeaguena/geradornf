import os
import sqlite3
import json
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify, send_file, redirect
import tempfile
import pandas as pd
import io
import re
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta

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
        if 'tabela_csts' not in tables:
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
        'nAdicao': g(adi, 'nfe:nAdicao'),
        'nSeqAdic': g(adi, 'nfe:nSeqAdic'),
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

def limpar_decimal_nfe(v):
    if v is None:
        return v
    s = str(v).strip()
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    return s

def atualizar_icms_node(imposto, item_data, ns):
    NFE_URI = '{http://www.portalfiscal.inf.br/nfe}'
    icms = imposto.find('nfe:ICMS', ns)
    if icms is None:
        icms = ET.Element(NFE_URI + 'ICMS')
        imposto.insert(0, icms)
    
    orig = str(item_data.get('orig') if item_data.get('orig') is not None else '1').strip()
    if orig == '':
        orig = '1'
        
    csosn_or_cst = limpar_cst(item_data.get('CSOSN') or '')
    if not csosn_or_cst:
        if len(list(icms)) > 0:
            c = list(icms)[0]
            el_orig = c.find('nfe:orig', ns)
            if el_orig is not None:
                el_orig.text = orig
        return

    # Limpa filhos anteriores de ICMS para recriar com a tag correta do Schema SEFAZ
    for child in list(icms):
        icms.remove(child)

    if len(csosn_or_cst) == 3:
        # Simples Nacional (CSOSN)
        if csosn_or_cst in ['102', '103', '300', '400']:
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN102')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = csosn_or_cst
        elif csosn_or_cst == '101':
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN101')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = '101'
            ET.SubElement(node, NFE_URI + 'pCredSN').text = limpar_decimal_nfe(item_data.get('pCredSN') or '0.00')
            ET.SubElement(node, NFE_URI + 'vCredICMSSN').text = limpar_decimal_nfe(item_data.get('vCredICMSSN') or '0.00')
        elif csosn_or_cst == '201':
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN201')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = '201'
            ET.SubElement(node, NFE_URI + 'modBCST').text = '4'
            ET.SubElement(node, NFE_URI + 'vBCST').text = limpar_decimal_nfe(item_data.get('vBCST') or '0.00')
            ET.SubElement(node, NFE_URI + 'pICMSST').text = limpar_decimal_nfe(item_data.get('pICMSST') or '0.00')
            ET.SubElement(node, NFE_URI + 'vICMSST').text = limpar_decimal_nfe(item_data.get('vICMSST') or '0.00')
            ET.SubElement(node, NFE_URI + 'pCredSN').text = limpar_decimal_nfe(item_data.get('pCredSN') or '0.00')
            ET.SubElement(node, NFE_URI + 'vCredICMSSN').text = limpar_decimal_nfe(item_data.get('vCredICMSSN') or '0.00')
        elif csosn_or_cst in ['202', '203']:
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN202')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = csosn_or_cst
            ET.SubElement(node, NFE_URI + 'modBCST').text = '4'
            ET.SubElement(node, NFE_URI + 'vBCST').text = limpar_decimal_nfe(item_data.get('vBCST') or '0.00')
            ET.SubElement(node, NFE_URI + 'pICMSST').text = limpar_decimal_nfe(item_data.get('pICMSST') or '0.00')
            ET.SubElement(node, NFE_URI + 'vICMSST').text = limpar_decimal_nfe(item_data.get('vICMSST') or '0.00')
        elif csosn_or_cst == '500':
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN500')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = '500'
        elif csosn_or_cst == '900':
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN900')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = '900'
            p_icms = item_data.get('pICMS')
            v_icms = item_data.get('vICMS')
            if (p_icms and not is_zero(p_icms)) or (v_icms and not is_zero(v_icms)):
                ET.SubElement(node, NFE_URI + 'modBC').text = '3'
                ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_ICMS') or item_data.get('vProd') or '0.00')
                ET.SubElement(node, NFE_URI + 'pICMS').text = limpar_decimal_nfe(p_icms or '0.00')
                ET.SubElement(node, NFE_URI + 'vICMS').text = limpar_decimal_nfe(v_icms or '0.00')
        else:
            node = ET.SubElement(icms, NFE_URI + 'ICMSSN102')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CSOSN').text = csosn_or_cst
    else:
        # Regime Normal (CST 2 dígitos)
        cst = csosn_or_cst.zfill(2)
        if cst == '00':
            node = ET.SubElement(icms, NFE_URI + 'ICMS00')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CST').text = '00'
            ET.SubElement(node, NFE_URI + 'modBC').text = '3'
            ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_ICMS') or item_data.get('vBC') or item_data.get('vProd') or '0.00')
            ET.SubElement(node, NFE_URI + 'pICMS').text = limpar_decimal_nfe(item_data.get('pICMS') or '0.00')
            ET.SubElement(node, NFE_URI + 'vICMS').text = limpar_decimal_nfe(item_data.get('vICMS') or '0.00')
        elif cst in ['40', '41', '50']:
            node = ET.SubElement(icms, NFE_URI + 'ICMS40')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CST').text = cst
        elif cst == '90':
            node = ET.SubElement(icms, NFE_URI + 'ICMS90')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CST').text = '90'
            ET.SubElement(node, NFE_URI + 'modBC').text = '3'
            ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_ICMS') or item_data.get('vProd') or '0.00')
            ET.SubElement(node, NFE_URI + 'pICMS').text = limpar_decimal_nfe(item_data.get('pICMS') or '0.00')
            ET.SubElement(node, NFE_URI + 'vICMS').text = limpar_decimal_nfe(item_data.get('vICMS') or '0.00')
        elif cst in ['10', '20', '30', '51', '60', '70']:
            node = ET.SubElement(icms, NFE_URI + 'ICMS' + cst)
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CST').text = cst
            if cst in ['10', '20', '51', '70']:
                ET.SubElement(node, NFE_URI + 'modBC').text = '3'
                ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_ICMS') or item_data.get('vProd') or '0.00')
                ET.SubElement(node, NFE_URI + 'pICMS').text = limpar_decimal_nfe(item_data.get('pICMS') or '0.00')
                ET.SubElement(node, NFE_URI + 'vICMS').text = limpar_decimal_nfe(item_data.get('vICMS') or '0.00')
        else:
            node = ET.SubElement(icms, NFE_URI + 'ICMS00')
            ET.SubElement(node, NFE_URI + 'orig').text = orig
            ET.SubElement(node, NFE_URI + 'CST').text = cst

def atualizar_ipi_node(imposto, item_data, ns):
    NFE_URI = '{http://www.portalfiscal.inf.br/nfe}'
    cst_ipi = limpar_cst(item_data.get('CST_IPI') or '')
    c_enq = str(item_data.get('cEnq') or '999').strip()
    if not c_enq:
        c_enq = '999'

    ipi = imposto.find('nfe:IPI', ns)
    if not cst_ipi and ipi is None:
        return

    if ipi is None:
        ipi = ET.Element(NFE_URI + 'IPI')
        ref = imposto.find('nfe:II', ns) or imposto.find('nfe:ISSQN', ns) or imposto.find('nfe:PIS', ns) or imposto.find('nfe:COFINS', ns)
        if ref is not None:
            idx = list(imposto).index(ref)
            imposto.insert(idx, ipi)
        else:
            imposto.append(ipi)

    el_cenq = ipi.find('nfe:cEnq', ns)
    if el_cenq is not None:
        el_cenq.text = c_enq
    else:
        el_cenq = ET.Element(NFE_URI + 'cEnq')
        el_cenq.text = c_enq
        ipi.insert(0, el_cenq)

    if not cst_ipi:
        return

    for el in list(ipi):
        if el.tag.endswith('IPITrib') or el.tag.endswith('IPINT'):
            ipi.remove(el)

    cst_norm = cst_ipi.zfill(2)
    # CSTs não tributados do IPI: 01, 02, 03, 04, 05, 51, 52, 53, 54, 55
    if cst_norm in ['01', '02', '03', '04', '05', '51', '52', '53', '54', '55']:
        ipint = ET.SubElement(ipi, NFE_URI + 'IPINT')
        ET.SubElement(ipint, NFE_URI + 'CST').text = cst_norm
    else:
        # CSTs tributados do IPI: 00, 49, 50, 99
        ipitrib = ET.SubElement(ipi, NFE_URI + 'IPITrib')
        ET.SubElement(ipitrib, NFE_URI + 'CST').text = cst_norm
        vbc = limpar_decimal_nfe(item_data.get('vBC_IPI') or item_data.get('vProd') or '0.00')
        pipi = limpar_decimal_nfe(item_data.get('pIPI') or '0.00')
        vipi = limpar_decimal_nfe(item_data.get('vIPI') or '0.00')
        ET.SubElement(ipitrib, NFE_URI + 'vBC').text = vbc
        ET.SubElement(ipitrib, NFE_URI + 'pIPI').text = pipi
        ET.SubElement(ipitrib, NFE_URI + 'vIPI').text = vipi

def atualizar_pis_node(imposto, item_data, ns):
    NFE_URI = '{http://www.portalfiscal.inf.br/nfe}'
    cst_pis = limpar_cst(item_data.get('CST_PIS') or '')
    
    pis = imposto.find('nfe:PIS', ns)
    if not cst_pis and pis is None:
        return

    if pis is None:
        pis = ET.Element(NFE_URI + 'PIS')
        ref = imposto.find('nfe:PISST', ns) or imposto.find('nfe:COFINS', ns)
        if ref is not None:
            idx = list(imposto).index(ref)
            imposto.insert(idx, pis)
        else:
            imposto.append(pis)

    if not cst_pis:
        return

    for child in list(pis):
        pis.remove(child)

    cst_norm = cst_pis.zfill(2)
    if cst_norm in ['01', '02']:
        node = ET.SubElement(pis, NFE_URI + 'PISAliq')
        ET.SubElement(node, NFE_URI + 'CST').text = cst_norm
        ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_PIS') or item_data.get('vProd') or '0.00')
        ET.SubElement(node, NFE_URI + 'pPIS').text = limpar_decimal_nfe(item_data.get('pPIS') or '0.00')
        ET.SubElement(node, NFE_URI + 'vPIS').text = limpar_decimal_nfe(item_data.get('vPIS') or '0.00')
    elif cst_norm in ['04', '05', '06', '07', '08', '09']:
        node = ET.SubElement(pis, NFE_URI + 'PISNT')
        ET.SubElement(node, NFE_URI + 'CST').text = cst_norm
    elif cst_norm == '03':
        node = ET.SubElement(pis, NFE_URI + 'PISQtde')
        ET.SubElement(node, NFE_URI + 'CST').text = '03'
        ET.SubElement(node, NFE_URI + 'qBCProd').text = limpar_decimal_nfe(item_data.get('qBCProd') or item_data.get('qCom') or '0.0000')
        ET.SubElement(node, NFE_URI + 'vAliqProd').text = limpar_decimal_nfe(item_data.get('vAliqProd') or '0.0000')
        ET.SubElement(node, NFE_URI + 'vPIS').text = limpar_decimal_nfe(item_data.get('vPIS') or '0.00')
    else:
        node = ET.SubElement(pis, NFE_URI + 'PISOutr')
        ET.SubElement(node, NFE_URI + 'CST').text = cst_norm
        ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_PIS') or item_data.get('vProd') or '0.00')
        ET.SubElement(node, NFE_URI + 'pPIS').text = limpar_decimal_nfe(item_data.get('pPIS') or '0.00')
        ET.SubElement(node, NFE_URI + 'vPIS').text = limpar_decimal_nfe(item_data.get('vPIS') or '0.00')

def atualizar_cofins_node(imposto, item_data, ns):
    NFE_URI = '{http://www.portalfiscal.inf.br/nfe}'
    cst_cofins = limpar_cst(item_data.get('CST_COFINS') or '')
    
    cofins = imposto.find('nfe:COFINS', ns)
    if not cst_cofins and cofins is None:
        return

    if cofins is None:
        cofins = ET.Element(NFE_URI + 'COFINS')
        ref = imposto.find('nfe:COFINSST', ns) or imposto.find('nfe:ICMSUFDest', ns)
        if ref is not None:
            idx = list(imposto).index(ref)
            imposto.insert(idx, cofins)
        else:
            imposto.append(cofins)

    if not cst_cofins:
        return

    for child in list(cofins):
        cofins.remove(child)

    cst_norm = cst_cofins.zfill(2)
    if cst_norm in ['01', '02']:
        node = ET.SubElement(cofins, NFE_URI + 'COFINSAliq')
        ET.SubElement(node, NFE_URI + 'CST').text = cst_norm
        ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_COFINS') or item_data.get('vProd') or '0.00')
        ET.SubElement(node, NFE_URI + 'pCOFINS').text = limpar_decimal_nfe(item_data.get('pCOFINS') or '0.00')
        ET.SubElement(node, NFE_URI + 'vCOFINS').text = limpar_decimal_nfe(item_data.get('vCOFINS') or '0.00')
    elif cst_norm in ['04', '05', '06', '07', '08', '09']:
        node = ET.SubElement(cofins, NFE_URI + 'COFINSNT')
        ET.SubElement(node, NFE_URI + 'CST').text = cst_norm
    elif cst_norm == '03':
        node = ET.SubElement(cofins, NFE_URI + 'COFINSQtde')
        ET.SubElement(node, NFE_URI + 'CST').text = '03'
        ET.SubElement(node, NFE_URI + 'qBCProd').text = limpar_decimal_nfe(item_data.get('qBCProd') or item_data.get('qCom') or '0.0000')
        ET.SubElement(node, NFE_URI + 'vAliqProd').text = limpar_decimal_nfe(item_data.get('vAliqProd') or '0.0000')
        ET.SubElement(node, NFE_URI + 'vCOFINS').text = limpar_decimal_nfe(item_data.get('vCOFINS') or '0.00')
    else:
        node = ET.SubElement(cofins, NFE_URI + 'COFINSOutr')
        ET.SubElement(node, NFE_URI + 'CST').text = cst_norm
        ET.SubElement(node, NFE_URI + 'vBC').text = limpar_decimal_nfe(item_data.get('vBC_COFINS') or item_data.get('vProd') or '0.00')
        ET.SubElement(node, NFE_URI + 'pCOFINS').text = limpar_decimal_nfe(item_data.get('pCOFINS') or '0.00')
        ET.SubElement(node, NFE_URI + 'vCOFINS').text = limpar_decimal_nfe(item_data.get('vCOFINS') or '0.00')

def atualizar_det(det, item_data, cfop_padrao, ns):
    def s(parent, path, val, tag_name=None):
        if parent is not None and val is not None:
            el = parent.find(path, ns)
            if el is not None:
                if tag_name and tag_name in CAMPOS_DECIMAIS_NFE:
                    el.text = limpar_decimal_nfe(val)
                else:
                    el.text = str(val)

    prod = det.find('nfe:prod', ns)
    if prod is not None:
        for k in ['cProd', 'cEAN', 'xProd', 'NCM', 'uCom', 'qCom', 'vUnCom', 'vProd', 'cEANTrib', 'uTrib', 'qTrib', 'vUnTrib', 'nItemPed']:
            if k in item_data and item_data[k] is not None:
                s(prod, 'nfe:' + k, item_data[k], k)

        # Campos de despesas em prod (vFrete, vSeg, vDesc, vOutro)
        for k in ['vFrete', 'vSeg', 'vDesc', 'vOutro']:
            val_k = item_data.get(k)
            el_k = prod.find('nfe:' + k, ns)
            if k in ['vFrete', 'vSeg', 'vOutro'] and is_zero(val_k):
                if el_k is not None:
                    prod.remove(el_k)
            elif val_k is not None and str(val_k).strip() != '':
                if el_k is not None:
                    el_k.text = limpar_decimal_nfe(val_k)
                else:
                    novo_el = ET.Element('{http://www.portalfiscal.inf.br/nfe}' + k)
                    novo_el.text = limpar_decimal_nfe(val_k)
                    ref = prod.find('nfe:indTot', ns) or prod.find('nfe:DI', ns)
                    if ref is not None:
                        idx_ref = list(prod).index(ref)
                        prod.insert(idx_ref, novo_el)
                    else:
                        prod.append(novo_el)
        
        if 'indTot' in item_data and item_data['indTot'] is not None:
            s(prod, 'nfe:indTot', item_data['indTot'])

        cfop_val = cfop_padrao if (cfop_padrao and cfop_padrao.strip()) else item_data.get('CFOP', '')
        if cfop_val:
            s(prod, 'nfe:CFOP', cfop_val)

        di = prod.find('nfe:DI', ns)
        if str(cfop_val).startswith('7'):
            # Reexportação / Exportação não permite grupo DI no schema da SEFAZ
            if di is not None:
                prod.remove(di)
        else:
            if di is not None:
                for k in ['nDI', 'dDI', 'xLocDesemb', 'UFDesemb', 'dDesemb', 'tpViaTransp', 'tpIntermedio', 'cExportador']:
                    if k in item_data and item_data[k] is not None:
                        s(di, 'nfe:' + k, item_data[k], k)

                # vAFRMM: Valor Adicional ao Frete para Renovação da Marinha Mercante
                if 'vAFRMM' in item_data and item_data['vAFRMM'] is not None and str(item_data['vAFRMM']).strip() != '':
                    el_afrmm = di.find('nfe:vAFRMM', ns)
                    if el_afrmm is not None:
                        el_afrmm.text = limpar_decimal_nfe(item_data['vAFRMM'])
                    else:
                        novo_afrmm = ET.Element('{http://www.portalfiscal.inf.br/nfe}vAFRMM')
                        novo_afrmm.text = limpar_decimal_nfe(item_data['vAFRMM'])
                        ref = di.find('nfe:tpIntermedio', ns) or di.find('nfe:cExportador', ns) or di.find('nfe:adi', ns)
                        if ref is not None:
                            idx_ref = list(di).index(ref)
                            di.insert(idx_ref, novo_afrmm)
                        else:
                            di.append(novo_afrmm)

                adi = di.find('nfe:adi', ns)
                if adi is not None:
                    for k in ['nAdicao', 'nSeqAdic', 'cFabricante']:
                        if k in item_data and item_data[k] is not None:
                            s(adi, 'nfe:' + k, item_data[k], k)

    imposto = det.find('nfe:imposto', ns)
    if imposto is None:
        imposto = ET.Element('{http://www.portalfiscal.inf.br/nfe}imposto')
        det.append(imposto)

    # 1. ICMS (Adequação da tag correta conforme CSOSN ou CST)
    atualizar_icms_node(imposto, item_data, ns)

    # 2. IPI (IPINT para CSTs não tributados como 55/05, IPITrib para tributados como 50/00)
    atualizar_ipi_node(imposto, item_data, ns)

    # 3. II (Imposto de Importação)
    if str(cfop_val).startswith('7'):
        # Reexportação / Exportação não possui II
        ii_el = imposto.find('nfe:II', ns)
        if ii_el is not None:
            imposto.remove(ii_el)
    else:
        has_ii_data = any(
            item_data.get(k) is not None and str(item_data.get(k)).strip() != '' and not (k == 'vDespAdu' and is_zero(item_data.get(k)))
            for k in ['vBC_II', 'vDespAdu', 'vII', 'vIOF']
        )
        ii = imposto.find('nfe:II', ns)
        if ii is None and has_ii_data:
            ii = ET.Element('{http://www.portalfiscal.inf.br/nfe}II')
            ref_ii = imposto.find('nfe:ISSQN', ns) or imposto.find('nfe:PIS', ns) or imposto.find('nfe:COFINS', ns)
            if ref_ii is not None:
                idx_ref = list(imposto).index(ref_ii)
                imposto.insert(idx_ref, ii)
            else:
                imposto.append(ii)

        if ii is not None:
            if 'vBC_II' in item_data and item_data['vBC_II'] is not None: s(ii, 'nfe:vBC', item_data['vBC_II'], 'vBC_II')
            
            # vDespAdu: Despesas Aduaneiras / Taxa Siscomex
            val_desp = item_data.get('vDespAdu')
            el_desp = ii.find('nfe:vDespAdu', ns)
            if is_zero(val_desp):
                if el_desp is not None:
                    ii.remove(el_desp)
            elif val_desp is not None and str(val_desp).strip() != '':
                if el_desp is not None:
                    el_desp.text = limpar_decimal_nfe(val_desp)
                else:
                    novo_desp = ET.Element('{http://www.portalfiscal.inf.br/nfe}vDespAdu')
                    novo_desp.text = limpar_decimal_nfe(val_desp)
                    ref = ii.find('nfe:vII', ns) or ii.find('nfe:vIOF', ns)
                    if ref is not None:
                        idx_ref = list(ii).index(ref)
                        ii.insert(idx_ref, novo_desp)
                    else:
                        ii.append(novo_desp)

            if 'vII' in item_data and item_data['vII'] is not None: s(ii, 'nfe:vII', item_data['vII'], 'vII')
            if 'vIOF' in item_data and item_data['vIOF'] is not None: s(ii, 'nfe:vIOF', item_data['vIOF'], 'vIOF')

            if len(list(ii)) == 0:
                imposto.remove(ii)

    # 4. PIS (PISNT para 04..09, PISAliq para 01/02, PISOutr para 49..99)
    atualizar_pis_node(imposto, item_data, ns)

    # 5. COFINS (COFINSNT para 04..09, COFINSAliq para 01/02, COFINSOutr para 49..99)
    atualizar_cofins_node(imposto, item_data, ns)

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

# === SERVIÇO & ROTAS: CÂMBIO PTAX BOLETIM (BANCO CENTRAL DO BRASIL - OLINDA) ===
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
            "emit_cMun": get_text(emit, 'cMun'),
            "emit_xMun": get_text(emit, 'xMun'),
            "emit_UF": get_text(emit, 'UF'),
            "emit_CEP": get_text(emit, 'CEP'),
            
            # Destinatario
            "dest_xNome": get_text(dest, 'xNome'),
            "dest_CNPJ_CPF": get_text(dest, 'CNPJ') or get_text(dest, 'CPF') or get_text(dest, 'idEstrangeiro'),
            "dest_indIEDest": get_text(dest, 'indIEDest') or "9",
            "dest_IE": get_text(dest, 'IE') or "",
            "dest_xLgr": get_text(dest, 'xLgr'),
            "dest_nro": get_text(dest, 'nro'),
            "dest_xBairro": get_text(dest, 'xBairro'),
            "dest_cMun": get_text(dest, 'cMun'),
            "dest_xMun": get_text(dest, 'xMun'),
            "dest_UF": get_text(dest, 'UF'),
            "dest_CEP": get_text(dest, 'CEP')
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
    data = request.json
    xml_string = data.get('xml_original')
    cabecalho = data.get('cabecalho', {})
    itens = data.get('itens', [])
    rodape = data.get('rodape', {})

    ET.register_namespace('', 'http://www.portalfiscal.inf.br/nfe')
    root = ET.fromstring(xml_string)
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    inf_nfe = root.find('nfe:infNFe', ns)
    if inf_nfe is None:
        inf_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

    def set_text(parent, tag, text_val):
        if parent is not None and text_val is not None:
            el = parent.find(f'.//{{http://www.portalfiscal.inf.br/nfe}}{tag}')
            if el is None:
                el = parent.find(f'{{http://www.portalfiscal.inf.br/nfe}}{tag}')
            if el is None:
                el = ET.SubElement(parent, f'{{http://www.portalfiscal.inf.br/nfe}}{tag}')
            el.text = str(text_val)

    # Cabecalho
    ide = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}ide')
    set_text(ide, 'nNF', cabecalho.get('nNF'))
    set_text(ide, 'serie', cabecalho.get('serie'))
    set_text(ide, 'natOp', cabecalho.get('natOp'))
    if cabecalho.get('tpNF') is not None and str(cabecalho.get('tpNF')).strip() != '':
        set_text(ide, 'tpNF', cabecalho.get('tpNF'))
    if cabecalho.get('idDest') is not None and str(cabecalho.get('idDest')).strip() != '':
        set_text(ide, 'idDest', cabecalho.get('idDest'))

    # Atualizacao da Chave de Acesso e cDV
    chave_acesso = str(cabecalho.get('chaveAcesso', '')).replace(' ', '').replace('NFe', '').strip()
    if len(chave_acesso) == 44:
        if inf_nfe is not None:
            inf_nfe.attrib['Id'] = f"NFe{chave_acesso}"
        set_text(ide, 'cDV', chave_acesso[-1])
        cNF_val = cabecalho.get('cNF')
        if not cNF_val and len(chave_acesso) == 44:
            cNF_val = chave_acesso[35:43]
        if cNF_val:
            set_text(ide, 'cNF', str(cNF_val).zfill(8))

    # Emitente
    emit = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}emit')
    set_text(emit, 'xNome', cabecalho.get('emit_xNome'))
    set_text(emit, 'CNPJ', cabecalho.get('emit_CNPJ'))
    set_text(emit, 'xLgr', cabecalho.get('emit_xLgr'))
    set_text(emit, 'nro', cabecalho.get('emit_nro'))
    set_text(emit, 'xBairro', cabecalho.get('emit_xBairro'))
    set_text(emit, 'cMun', cabecalho.get('emit_cMun'))
    set_text(emit, 'xMun', cabecalho.get('emit_xMun'))
    set_text(emit, 'UF', cabecalho.get('emit_UF'))
    set_text(emit, 'CEP', cabecalho.get('emit_CEP'))

    # Destinatario
    dest = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}dest')
    set_text(dest, 'xNome', cabecalho.get('dest_xNome'))
    if dest is not None and cabecalho.get('dest_CNPJ_CPF'):
        if dest.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ') is not None:
            dest.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ').text = str(cabecalho.get('dest_CNPJ_CPF'))
        elif dest.find('.//{http://www.portalfiscal.inf.br/nfe}CPF') is not None:
            dest.find('.//{http://www.portalfiscal.inf.br/nfe}CPF').text = str(cabecalho.get('dest_CNPJ_CPF'))
            
    set_text(dest, 'xLgr', cabecalho.get('dest_xLgr'))
    set_text(dest, 'nro', cabecalho.get('dest_nro'))
    set_text(dest, 'xBairro', cabecalho.get('dest_xBairro'))
    set_text(dest, 'cMun', cabecalho.get('dest_cMun'))
    set_text(dest, 'xMun', cabecalho.get('dest_xMun'))
    set_text(dest, 'UF', cabecalho.get('dest_UF'))
    set_text(dest, 'CEP', cabecalho.get('dest_CEP'))

    # indIEDest e IE
    ind_ie = str(cabecalho.get('dest_indIEDest') or '').strip()
    if ind_ie:
        set_text(dest, 'indIEDest', ind_ie)
    
    ie_val = str(cabecalho.get('dest_IE') or '').strip()
    if ind_ie == '1' and ie_val:
        set_text(dest, 'IE', ie_val)
    elif ind_ie in ['2', '9']:
        el_ie = dest.find('.//{http://www.portalfiscal.inf.br/nfe}IE') if dest is not None else None
        if el_ie is not None:
            if not ie_val or ie_val.upper() in ['ISENTO', '']:
                try:
                    for p in dest.iter():
                        if el_ie in list(p):
                            p.remove(el_ie)
                            break
                except Exception:
                    el_ie.text = ''
            else:
                el_ie.text = ie_val

    # Atualiza cada det correspondente em sequencia
    dets = inf_nfe.findall('.//{http://www.portalfiscal.inf.br/nfe}det')
    cfop_padrao = cabecalho.get('cfop_padrao')
    for idx, det in enumerate(dets):
        nItem = det.get('nItem')
        item_data = next((i for i in itens if str(i.get('nItem')) == str(nItem)), None)
        if item_data is None and idx < len(itens):
            item_data = itens[idx]
        
        if item_data:
            atualizar_det(det, item_data, cfop_padrao, ns)

        # Remove tags de despesas zeradas do prod e imposto/II caso tenham restado do XML original
        p = det.find('nfe:prod', ns)
        if p is not None:
            for k in ['vFrete', 'vSeg', 'vOutro']:
                el_k = p.find('nfe:' + k, ns)
                if el_k is not None and is_zero(el_k.text):
                    p.remove(el_k)
        imposto_el = det.find('nfe:imposto', ns)
        if imposto_el is not None:
            ii_el = imposto_el.find('nfe:II', ns)
            if ii_el is not None:
                el_desp = ii_el.find('nfe:vDespAdu', ns)
                if el_desp is not None and is_zero(el_desp.text):
                    ii_el.remove(el_desp)
                if len(list(ii_el)) == 0:
                    imposto_el.remove(ii_el)

    # Transporte e Volumes
    transporte_data = rodape.get('transporte', {})
    if transporte_data:
        transp = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}transp')
        if transp is not None:
            mod_frete = transporte_data.get('modFrete')
            if mod_frete is not None and str(mod_frete).strip() != '':
                set_text(transp, 'modFrete', mod_frete)
            
            # transporta
            tem_dados_transp = any(transporte_data.get(k) for k in ['CNPJ_CPF', 'xNome', 'IE', 'xEnder', 'xMun', 'UF'])
            transporta = transp.find('.//{http://www.portalfiscal.inf.br/nfe}transporta')
            if tem_dados_transp:
                if transporta is None:
                    vol_el = transp.find('.//{http://www.portalfiscal.inf.br/nfe}vol')
                    if vol_el is not None:
                        idx_vol = list(transp).index(vol_el)
                        transporta = ET.Element('{http://www.portalfiscal.inf.br/nfe}transporta')
                        transp.insert(idx_vol, transporta)
                    else:
                        transporta = ET.SubElement(transp, '{http://www.portalfiscal.inf.br/nfe}transporta')
                
                doc = str(transporte_data.get('CNPJ_CPF', '')).strip().replace('.', '').replace('-', '').replace('/', '')
                if len(doc) > 11:
                    set_text(transporta, 'CNPJ', doc)
                elif len(doc) > 0:
                    set_text(transporta, 'CPF', doc)
                if transporte_data.get('xNome') is not None: set_text(transporta, 'xNome', transporte_data.get('xNome'))
                if transporte_data.get('IE') is not None: set_text(transporta, 'IE', transporte_data.get('IE'))
                if transporte_data.get('xEnder') is not None: set_text(transporta, 'xEnder', transporte_data.get('xEnder'))
                if transporte_data.get('xMun') is not None: set_text(transporta, 'xMun', transporte_data.get('xMun'))
                if transporte_data.get('UF') is not None: set_text(transporta, 'UF', transporte_data.get('UF'))

            # vol (marca e nVol não devem ser preenchidos e não devem constar no XML)
            tem_dados_vol = any(transporte_data.get(k) for k in ['qVol', 'esp', 'pesoL', 'pesoB'])
            vol = transp.find('.//{http://www.portalfiscal.inf.br/nfe}vol')
            if tem_dados_vol:
                if vol is None:
                    vol = ET.SubElement(transp, '{http://www.portalfiscal.inf.br/nfe}vol')
                if transporte_data.get('qVol') is not None and str(transporte_data.get('qVol')).strip() != '':
                    set_text(vol, 'qVol', transporte_data.get('qVol'))
                if transporte_data.get('esp') is not None and str(transporte_data.get('esp')).strip() != '':
                    set_text(vol, 'esp', transporte_data.get('esp'))
                if transporte_data.get('pesoL') is not None and str(transporte_data.get('pesoL')).strip() != '':
                    set_text(vol, 'pesoL', limpar_decimal_nfe(transporte_data.get('pesoL')))
                if transporte_data.get('pesoB') is not None and str(transporte_data.get('pesoB')).strip() != '':
                    set_text(vol, 'pesoB', limpar_decimal_nfe(transporte_data.get('pesoB')))

            # Remover expressamente 'marca' e 'nVol' se existirem no vol original do XML
            if vol is not None:
                for tag_remover in ['marca', 'nVol']:
                    for el_rem in list(vol.findall(f'{{http://www.portalfiscal.inf.br/nfe}}{tag_remover}')):
                        vol.remove(el_rem)

    # Totais da Nota Fiscal (ICMSTot)
    totais_data = rodape.get('totais', {})
    if totais_data:
        icms_tot = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}total/{http://www.portalfiscal.inf.br/nfe}ICMSTot')
        if icms_tot is not None:
            for k in [
                'vBC', 'vICMS', 'vICMSDeson', 'vFCP', 'vBCST', 'vST', 'vFCPST', 'vFCPSTRet',
                'vProd', 'vFrete', 'vSeg', 'vDesc', 'vII', 'vIPI', 'vIPIDevol', 'vPIS', 'vCOFINS', 'vOutro', 'vNF'
            ]:
                if k in totais_data and totais_data[k] is not None and str(totais_data[k]).strip() != '':
                    set_text(icms_tot, k, limpar_decimal_nfe(totais_data[k]))

    # Rodape
    infAdic = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}infAdic')
    if infAdic is not None:
        if 'infCpl' in rodape and infAdic.find('.//{http://www.portalfiscal.inf.br/nfe}infCpl') is not None:
            infAdic.find('.//{http://www.portalfiscal.inf.br/nfe}infCpl').text = str(rodape['infCpl'])

    fd, temp_path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, 'wb') as f:
        tree = ET.ElementTree(root)
        tree.write(f, encoding='UTF-8', xml_declaration=True)

    return send_file(temp_path, as_attachment=True, download_name=f"NFe_{cabecalho.get('nNF', 'nova')}.xml")

# === ROTAS: EXCEL ===
@app.route('/export_excel', methods=['POST'])
def export_excel():
    data = request.json
    itens = data.get('itens', [])
    if not itens:
        return jsonify({"error": "Nenhum item para exportar"}), 400
    
    df = pd.DataFrame(itens)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Itens')
    
    output.seek(0)
    return send_file(output, download_name="Itens_NFe.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/import_excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna("")
        itens = df.to_dict(orient='records')
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

if __name__ == '__main__':
    get_db_connection().close()
    app.run(debug=True, port=5000)

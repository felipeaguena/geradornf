import os
import sqlite3
import json
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify, send_file
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
    except Exception:
        pass

    return conn

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
            if k in item_data and item_data[k] is not None and str(item_data[k]).strip() != '':
                el_k = prod.find('nfe:' + k, ns)
                if el_k is not None:
                    el_k.text = limpar_decimal_nfe(item_data[k])
                else:
                    novo_el = ET.Element('{http://www.portalfiscal.inf.br/nfe}' + k)
                    novo_el.text = limpar_decimal_nfe(item_data[k])
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
    if imposto is not None:
        icms = imposto.find('nfe:ICMS', ns)
        if icms is not None and len(list(icms)) > 0:
            c = list(icms)[0]
            if 'orig' in item_data and item_data['orig'] is not None:
                s(c, 'nfe:orig', item_data['orig'])
            if 'CSOSN' in item_data and item_data['CSOSN'] is not None:
                s(c, 'nfe:CSOSN', item_data['CSOSN'])
                s(c, 'nfe:CST', item_data['CSOSN'])
        
        ipi = imposto.find('nfe:IPI', ns)
        if ipi is not None:
            if 'cEnq' in item_data and item_data['cEnq'] is not None:
                s(ipi, 'nfe:cEnq', item_data['cEnq'])
            ipi_trib = ipi.find('nfe:IPITrib', ns)
            ipi_nt = ipi.find('nfe:IPINT', ns)
            cst_ipi = item_data.get('CST_IPI')
            if ipi_trib is not None:
                if cst_ipi is not None: s(ipi_trib, 'nfe:CST', cst_ipi)
                if 'vBC_IPI' in item_data and item_data['vBC_IPI'] is not None: s(ipi_trib, 'nfe:vBC', item_data['vBC_IPI'], 'vBC_IPI')
                if 'pIPI' in item_data and item_data['pIPI'] is not None: s(ipi_trib, 'nfe:pIPI', item_data['pIPI'], 'pIPI')
                if 'vIPI' in item_data and item_data['vIPI'] is not None: s(ipi_trib, 'nfe:vIPI', item_data['vIPI'], 'vIPI')
            elif ipi_nt is not None:
                if cst_ipi is not None: s(ipi_nt, 'nfe:CST', cst_ipi)

        ii = imposto.find('nfe:II', ns)
        if ii is not None:
            if 'vBC_II' in item_data and item_data['vBC_II'] is not None: s(ii, 'nfe:vBC', item_data['vBC_II'], 'vBC_II')
            
            # vDespAdu: Despesas Aduaneiras / Taxa Siscomex
            if 'vDespAdu' in item_data and item_data['vDespAdu'] is not None and str(item_data['vDespAdu']).strip() != '':
                el_desp = ii.find('nfe:vDespAdu', ns)
                if el_desp is not None:
                    el_desp.text = limpar_decimal_nfe(item_data['vDespAdu'])
                else:
                    novo_desp = ET.Element('{http://www.portalfiscal.inf.br/nfe}vDespAdu')
                    novo_desp.text = limpar_decimal_nfe(item_data['vDespAdu'])
                    ref = ii.find('nfe:vII', ns) or ii.find('nfe:vIOF', ns)
                    if ref is not None:
                        idx_ref = list(ii).index(ref)
                        ii.insert(idx_ref, novo_desp)
                    else:
                        ii.append(novo_desp)

            if 'vII' in item_data and item_data['vII'] is not None: s(ii, 'nfe:vII', item_data['vII'], 'vII')
            if 'vIOF' in item_data and item_data['vIOF'] is not None: s(ii, 'nfe:vIOF', item_data['vIOF'], 'vIOF')

        pis = imposto.find('nfe:PIS', ns)
        if pis is not None and len(list(pis)) > 0:
            c = list(pis)[0]
            if 'CST_PIS' in item_data and item_data['CST_PIS'] is not None: s(c, 'nfe:CST', item_data['CST_PIS'])
            if 'vBC_PIS' in item_data and item_data['vBC_PIS'] is not None: s(c, 'nfe:vBC', item_data['vBC_PIS'], 'vBC_PIS')
            if 'pPIS' in item_data and item_data['pPIS'] is not None: s(c, 'nfe:pPIS', item_data['pPIS'], 'pPIS')
            if 'vPIS' in item_data and item_data['vPIS'] is not None: s(c, 'nfe:vPIS', item_data['vPIS'], 'vPIS')

        cofins = imposto.find('nfe:COFINS', ns)
        if cofins is not None and len(list(cofins)) > 0:
            c = list(cofins)[0]
            if 'CST_COFINS' in item_data and item_data['CST_COFINS'] is not None: s(c, 'nfe:CST', item_data['CST_COFINS'])
            if 'vBC_COFINS' in item_data and item_data['vBC_COFINS'] is not None: s(c, 'nfe:vBC', item_data['vBC_COFINS'], 'vBC_COFINS')
            if 'pCOFINS' in item_data and item_data['pCOFINS'] is not None: s(c, 'nfe:pCOFINS', item_data['pCOFINS'], 'pCOFINS')
            if 'vCOFINS' in item_data and item_data['vCOFINS'] is not None: s(c, 'nfe:vCOFINS', item_data['vCOFINS'], 'vCOFINS')

@app.route('/')
def index():
    return render_template('index.html')

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
            data.get('csosn_icms', '102'),
            data.get('c_enq_ipi', '102'),
            data.get('cst_ipi', '05'),
            float(data.get('p_ipi', 0) or 0),
            float(data.get('aliquota_ii', 0) or 0),
            data.get('cst_pis', '07'),
            float(data.get('p_pis', 0) or 0),
            data.get('cst_cofins', '07'),
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
            data.get('csosn_icms', '102'),
            data.get('c_enq_ipi', '102'),
            data.get('cst_ipi', '05'),
            float(data.get('p_ipi', 0) or 0),
            float(data.get('aliquota_ii', 0) or 0),
            data.get('cst_pis', '07'),
            float(data.get('p_pis', 0) or 0),
            data.get('cst_cofins', '07'),
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
    c.execute('DELETE FROM tipos_operacao WHERE id = ?', (op_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

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
            "marca": get_text(vol, 'marca') if vol is not None else "",
            "nVol": get_text(vol, 'nVol') if vol is not None else "",
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

            # vol
            tem_dados_vol = any(transporte_data.get(k) for k in ['qVol', 'esp', 'marca', 'nVol', 'pesoL', 'pesoB'])
            vol = transp.find('.//{http://www.portalfiscal.inf.br/nfe}vol')
            if tem_dados_vol:
                if vol is None:
                    vol = ET.SubElement(transp, '{http://www.portalfiscal.inf.br/nfe}vol')
                if transporte_data.get('qVol') is not None: set_text(vol, 'qVol', transporte_data.get('qVol'))
                if transporte_data.get('esp') is not None: set_text(vol, 'esp', transporte_data.get('esp'))
                if transporte_data.get('marca') is not None: set_text(vol, 'marca', transporte_data.get('marca'))
                if transporte_data.get('nVol') is not None: set_text(vol, 'nVol', transporte_data.get('nVol'))
                if transporte_data.get('pesoL') is not None and str(transporte_data.get('pesoL')).strip() != '':
                    set_text(vol, 'pesoL', limpar_decimal_nfe(transporte_data.get('pesoL')))
                if transporte_data.get('pesoB') is not None and str(transporte_data.get('pesoB')).strip() != '':
                    set_text(vol, 'pesoB', limpar_decimal_nfe(transporte_data.get('pesoB')))

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

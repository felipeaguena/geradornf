import os
import sys
import json
import time
import re
import tempfile
import requests
import subprocess
from datetime import datetime
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(__file__)
CERT_DIR = os.path.join(BASE_DIR, 'certificado')
SESSION_CACHE_FILE = os.path.join(BASE_DIR, 'siscomex_session.json')
DUIMP_IMPORTADA_DIR = os.path.join(BASE_DIR, 'DUIMP Importada')
DUIMP_IMPORTADA_ROOT_DIR = os.path.join(os.path.dirname(BASE_DIR), 'DUIMP Importada')

os.makedirs(CERT_DIR, exist_ok=True)
os.makedirs(DUIMP_IMPORTADA_DIR, exist_ok=True)
os.makedirs(DUIMP_IMPORTADA_ROOT_DIR, exist_ok=True)

PUCOMEX_AUTH_URL = "https://portalunico.siscomex.gov.br/portal/api/autenticar"
PUCOMEX_DUIMP_BASE = "https://portalunico.siscomex.gov.br/duimp-api/api/ext"
PUCOMEX_CATP_BASE = "https://portalunico.siscomex.gov.br/catp/api/ext"

# Arquivo temporário de certificado PEM em cache de processo
_cached_cert_pem_path = None
_cached_key_pem_path = None


def obter_caminho_certificado_ecpf():
    r"""
    Localiza o certificado e-CPF para autenticação no Portal Único Siscomex.
    1. Verifica se já existe em gerador/certificado/felipe_ecpf.pfx
    2. Se não existir, tenta exportar do repositório de certificados do Windows (Cert:\CurrentUser\My)
    3. Fallback para outros certificados pfx em gerador/certificado/
    """
    ecpf_pfx = os.path.join(CERT_DIR, 'felipe_ecpf.pfx')
    if os.path.exists(ecpf_pfx) and os.path.getsize(ecpf_pfx) > 0:
        return ecpf_pfx, b'senha123'
    
    # Tentativa de exportar automaticamente do Windows Certificate Store
    try:
        ps_script = """
        $cert = Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object { $_.Subject -like '*AGUENA*' -or $_.Subject -like '*e-CPF*' } | Select-Object -First 1
        if ($cert -and $cert.HasPrivateKey) {
            $bytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pkcs12, 'senha123')
            [System.IO.File]::WriteAllBytes('""" + ecpf_pfx.replace('\\', '\\\\') + """', $bytes)
            Write-Output "OK"
        }
        """
        res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_script], capture_output=True, text=True, timeout=10)
        if os.path.exists(ecpf_pfx) and os.path.getsize(ecpf_pfx) > 0:
            return ecpf_pfx, b'senha123'
    except Exception as e:
        print(f"[PUCOMEX] Aviso ao exportar cert do Windows: {e}")

    # Fallback para o certificado padrão da pasta (e-CNPJ)
    for f in os.listdir(CERT_DIR):
        if f.endswith('.pfx'):
            full_p = os.path.join(CERT_DIR, f)
            return full_p, b'nftecnpj'
            
    return None, None


def get_mtls_pem_files():
    """
    Converte o PFX ativo para arquivos PEM temporários compatíveis com o requests.
    """
    global _cached_cert_pem_path, _cached_key_pem_path
    if _cached_cert_pem_path and _cached_key_pem_path:
        if os.path.exists(_cached_cert_pem_path) and os.path.exists(_cached_key_pem_path):
            return _cached_cert_pem_path, _cached_key_pem_path

    pfx_path, pfx_pass = obter_caminho_certificado_ecpf()
    if not pfx_path or not os.path.exists(pfx_path):
        raise FileNotFoundError("Certificado Digital para acesso ao Siscomex não encontrado.")

    with open(pfx_path, 'rb') as f:
        pfx_data = f.read()

    private_key, cert, add_certs = pkcs12.load_key_and_certificates(pfx_data, pfx_pass)

    c_file = tempfile.NamedTemporaryFile(suffix='_cert.pem', delete=False)
    k_file = tempfile.NamedTemporaryFile(suffix='_key.pem', delete=False)

    cert_pem = cert.public_bytes(Encoding.PEM)
    if add_certs:
        for ac in add_certs:
            cert_pem += ac.public_bytes(Encoding.PEM)
    c_file.write(cert_pem)
    c_file.flush()
    c_file.close()

    key_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    )
    k_file.write(key_pem)
    k_file.flush()
    k_file.close()

    _cached_cert_pem_path = c_file.name
    _cached_key_pem_path = k_file.name
    return _cached_cert_pem_path, _cached_key_pem_path


def carregar_sessao_cache():
    if os.path.exists(SESSION_CACHE_FILE):
        try:
            with open(SESSION_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return {}


def salvar_sessao_cache(data):
    try:
        with open(SESSION_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[PUCOMEX] Erro ao salvar sessão cache: {e}")


def autenticar_portal_unico(forcar=False):
    """
    Obtém tokens de autenticação mTLS (X-CSRF-Token e Set-Token).
    Respeita a regra de segurança do Siscomex (token válido por até 60 min, mínimo 60s entre novos logins).
    """
    sess = carregar_sessao_cache()
    agora = time.time()
    
    csrf_token = sess.get('csrf_token')
    jwt_token = sess.get('jwt_token')
    expira_em = sess.get('expira_em', 0)
    ultimo_login = sess.get('ultimo_login', 0)

    # Se já temos token válido e ainda faltam mais de 2 minutos para expirar
    if not forcar and csrf_token and jwt_token and (expira_em - agora > 120):
        return csrf_token, jwt_token

    # Se precisamos fazer um novo login mas o último login foi há menos de 65 segundos:
    tempo_desde_ultimo = agora - ultimo_login
    if tempo_desde_ultimo < 65:
        espera = int(66 - tempo_desde_ultimo)
        print(f"[PUCOMEX] Respeitando limite de 60s do Siscomex. Aguardando {espera}s...")
        time.sleep(espera)

    cert_pem, key_pem = get_mtls_pem_files()
    s = requests.Session()
    s.cert = (cert_pem, key_pem)

    headers = {
        'Role-Type': 'IMPEXP',
        'Accept': 'application/json'
    }

    resp = s.post(PUCOMEX_AUTH_URL, headers=headers, timeout=20)
    if resp.status_code == 200:
        csrf_token = resp.headers.get('X-CSRF-Token')
        jwt_token = resp.headers.get('Set-Token')
        # Siscomex expira em 3600 segundos (60 minutos)
        novo_cache = {
            'csrf_token': csrf_token,
            'jwt_token': jwt_token,
            'ultimo_login': time.time(),
            'expira_em': time.time() + 3500
        }
        salvar_sessao_cache(novo_cache)
        return csrf_token, jwt_token
    else:
        err_msg = f"Falha na autenticação do Siscomex ({resp.status_code}): {resp.text}"
        try:
            err_json = resp.json()
            if 'message' in err_json:
                err_msg = f"Siscomex: {err_json['message']}"
        except Exception:
            pass
        raise RuntimeError(err_msg)


def atualizar_csrf_se_necessario(response):
    novo_csrf = response.headers.get('X-CSRF-Token')
    if novo_csrf:
        sess = carregar_sessao_cache()
        sess['csrf_token'] = novo_csrf
        sess['expira_em'] = time.time() + 3500
        salvar_sessao_cache(sess)


def consultar_duimp_portal_unico(numero_duimp_raw):
    """
    Consulta a DUIMP completa diretamente no Portal Único Siscomex via API oficial.
    Retorna os dados oficiais e busca as descrições dos produtos no Catálogo de Produtos.
    """
    # 1. Sanitizar número da DUIMP:
    # Formato oficial da URL: 15 dígitos sem hífen (ex: 25BR00001785577)
    numero_duimp_limpo = re.sub(r'[^A-Z0-9]', '', str(numero_duimp_raw).upper())
    
    # Se o usuário digitou com o hífen final (ex 25BR0000178557-7), limpo fica 25BR00001785577
    if len(numero_duimp_limpo) == 16 and numero_duimp_limpo.endswith('7') and '-7' in numero_duimp_raw:
        pass

    # Garante tokens válidos
    csrf_token, jwt_token = autenticar_portal_unico()
    cert_pem, key_pem = get_mtls_pem_files()

    s = requests.Session()
    s.cert = (cert_pem, key_pem)

    def _headers():
        sess = carregar_sessao_cache()
        return {
            'X-CSRF-Token': sess.get('csrf_token') or csrf_token,
            'Authorization': sess.get('jwt_token') or jwt_token,
            'Accept': 'application/json'
        }

    # 2. Consultar versões da DUIMP
    url_versoes = f"{PUCOMEX_DUIMP_BASE}/duimp/{numero_duimp_limpo}/versoes"
    r_ver = s.get(url_versoes, headers=_headers(), timeout=15)
    atualizar_csrf_se_necessario(r_ver)

    if r_ver.status_code == 401:
        # Tenta renovar login uma vez
        csrf_token, jwt_token = autenticar_portal_unico(forcar=True)
        r_ver = s.get(url_versoes, headers=_headers(), timeout=15)
        atualizar_csrf_se_necessario(r_ver)

    if r_ver.status_code != 200:
        raise RuntimeError(f"Erro ao consultar versões da DUIMP ({r_ver.status_code}): {r_ver.text}")

    dados_versoes = r_ver.json()
    versao_vigente = str(dados_versoes.get('versao', 1))

    # 3. Consultar dados completos da versão vigente
    url_dados = f"{PUCOMEX_DUIMP_BASE}/duimp/{numero_duimp_limpo}/{versao_vigente}"
    r_dados = s.get(url_dados, headers=_headers(), timeout=20)
    atualizar_csrf_se_necessario(r_dados)

    if r_dados.status_code != 200:
        raise RuntimeError(f"Erro ao consultar dados da DUIMP ({r_dados.status_code}): {r_dados.text}")

    duimp_completa = r_dados.json()

    # 4. Consultar itens completos da DUIMP
    url_itens = f"{PUCOMEX_DUIMP_BASE}/duimp/{numero_duimp_limpo}/{versao_vigente}/itens"
    r_itens = s.get(url_itens, headers=_headers(), timeout=20)
    atualizar_csrf_se_necessario(r_itens)

    itens_brutos = []
    if r_itens.status_code == 200:
        itens_brutos = r_itens.json()
    else:
        # Tenta buscar itens individualmente caso a lista em bloco falhe
        indices = duimp_completa.get('itens', [])
        for ind in indices:
            idx = ind.get('indice')
            if idx:
                u_item = f"{PUCOMEX_DUIMP_BASE}/duimp/{numero_duimp_limpo}/{versao_vigente}/itens/{idx}"
                r_item = s.get(u_item, headers=_headers(), timeout=10)
                atualizar_csrf_se_necessario(r_item)
                if r_item.status_code == 200:
                    itens_brutos.append(r_item.json())

    duimp_completa['itens'] = itens_brutos

    # 5. Enriquecer produtos com Catálogo de Produtos (CATP)
    catalogo_cache = {}
    for it in itens_brutos:
        prod = it.get('produto', {})
        codigo = prod.get('codigo')
        versao_p = prod.get('versao')
        ni = prod.get('niResponsavel')
        
        if codigo and versao_p and ni:
            chave_catp = f"{ni}_{codigo}_{versao_p}"
            if chave_catp not in catalogo_cache:
                url_catp = f"{PUCOMEX_CATP_BASE}/produto/{ni}/{codigo}/{versao_p}"
                try:
                    r_catp = s.get(url_catp, headers=_headers(), timeout=10)
                    atualizar_csrf_se_necessario(r_catp)
                    if r_catp.status_code == 200:
                        catalogo_cache[chave_catp] = r_catp.json()
                    else:
                        catalogo_cache[chave_catp] = None
                except Exception as e:
                    print(f"[PUCOMEX] Aviso ao consultar CATP {chave_catp}: {e}")
                    catalogo_cache[chave_catp] = None

            dados_catp = catalogo_cache.get(chave_catp)
            if dados_catp:
                it['catp_detalhes'] = dados_catp

    return duimp_completa


def processar_dados_duimp_para_nfe(duimp_completa, numero_duimp_original, conn=None):
    """
    Converte a estrutura oficial da DUIMP do Siscomex na estrutura de dados padrão
    da NF-e de Importação utilizada no gerador (cabeçalho, 4 itens ou N itens reais, rodapé, etc.).
    """
    ident = duimp_completa.get('identificacao', {})
    numero_duimp_oficial = ident.get('numero', numero_duimp_original)
    versao = str(ident.get('versao', 1))
    
    # Data do registro
    data_reg_raw = ident.get('dataRegistro', '')
    data_duimp = ""
    if data_reg_raw and len(data_reg_raw) >= 10:
        data_duimp = data_reg_raw[:10]
    else:
        data_duimp = datetime.now().strftime('%Y-%m-%d')
        
    dh_emi_iso = f"{data_duimp}T12:00:00-03:00"

    # Local de desembaraço e UF
    carga = duimp_completa.get('carga', {}) or {}
    unid_dec = carga.get('unidadeDeclarada', {}).get('codigo', '') if isinstance(carga.get('unidadeDeclarada'), dict) else ''
    
    desemb_nome = "ALFANDEGA DO PORTO DE SANTOS" if unid_dec == "0817900" else "MULTILOG BARUERI"
    desemb_uf = "SP"

    # -------------------------------------------------------------
    # Recuperação da Referência Interna:
    # PADRÃO PRIORITÁRIO: Código Siscomex 49 (Fatura Comercial / Documento de Referência)
    # Mesmo que o valor não comece com "NFT".
    # -------------------------------------------------------------
    referencia_interna = ""
    documentos = (
        duimp_completa.get('documentos', {})
        or duimp_completa.get('duimp_original', {}).get('documentos', {})
        or {}
    )
    docs_instrucao = (
        documentos.get('documentosInstrucao')
        or duimp_completa.get('documentosInstrucao')
        or duimp_completa.get('duimp_original', {}).get('documentosInstrucao')
        or []
    )
    
    # 1. Prioridade Absoluta: Documento Siscomex código 49 (Fatura Comercial)
    # Pega o valor exatamente como está, sem exigir que comece ou contenha 'NFT'
    for doc in docs_instrucao:
        tipo_info = doc.get('tipo', {}) or {}
        cod_tipo = str(tipo_info.get('codigo') or doc.get('codigoTipoDocumento') or doc.get('codigo') or '').strip()
        if cod_tipo == '49':
            pcs = doc.get('palavrasChave', []) or []
            if isinstance(pcs, list):
                # Prioriza palavra-chave código 1 (Número do Documento)
                for pc in pcs:
                    if str(pc.get('codigo', '')).strip() == '1':
                        val = str(pc.get('valor') or '').strip()
                        if val:
                            referencia_interna = val
                            break
                # Se não achou na código 1, pega a primeira com valor
                if not referencia_interna:
                    for pc in pcs:
                        val = str(pc.get('valor') or '').strip()
                        if val:
                            referencia_interna = val
                            break
            # Fallback direto em propriedades do documento se não veio como palavrasChave
            if not referencia_interna:
                val_direto = str(doc.get('numero') or doc.get('numeroDocumento') or doc.get('valor') or '').strip()
                if val_direto:
                    referencia_interna = val_direto
            if referencia_interna:
                break

    # 2. Fallback Secundário: Varredura por qualquer outro documento de instrução que contenha 'NFT'
    if not referencia_interna:
        for doc in docs_instrucao:
            for pc in (doc.get('palavrasChave', []) or []):
                val = str(pc.get('valor') or '').strip()
                if 'NFT' in val.upper():
                    referencia_interna = val
                    break
            if referencia_interna:
                break

    # 3. Fallback Terciário: Varredura no campo informacaoComplementar por padrões NFT, REF ou FATURA
    if not referencia_interna:
        info_cpl = ident.get('informacaoComplementar', '') or ''
        m_nft = re.search(r'(NFT\d{4,}[A-Za-z0-9\-_]*)', info_cpl, re.IGNORECASE)
        if m_nft:
            referencia_interna = m_nft.group(1).upper()
        else:
            m_ref = re.search(r'(?:REF(?:ER[EÊ]NCIA)?|PROC(?:ESSO)?|FATURA(?:\s+COMERCIAL)?)\s*[:=.]*\s*([A-Za-z0-9\-_/]+)', info_cpl, re.IGNORECASE)
            if m_ref:
                referencia_interna = m_ref.group(1).strip()

    # 4. Fallback final: se não houver referência explícita, usa o número da DUIMP
    if not referencia_interna:
        referencia_interna = numero_duimp_original

    # Consulta cadastros do banco
    emit_nome = "NFT LOGISTICS LTDA"
    emit_cnpj = "47998441000198"
    emit_ie = "138843326117"
    emit_logr = "AV. DR. GASTAO VIDIGAL"
    emit_nro = "1132"
    emit_bairro = "VILA LEOPOLDINA"
    emit_mun = "SAO PAULO"
    emit_uf = "SP"
    emit_cep = "05314000"

    exp_nome = "SHENZHEN MAXSPEED LOGISTICS CO., LTD"
    exp_logr = "JIABIN ROAD"
    exp_nro = "4028"
    exp_bairro = "LUOHU DISTRICT"
    exp_mun = "EXTERIOR"
    exp_uf = "EX"
    exp_cep = "99999-999"
    exp_pais_cod = "1600"
    exp_pais_nome = "CHINA, REPUBLICA POPULAR"

    if conn:
        try:
            c = conn.cursor()
            row_emit = c.execute("SELECT * FROM cadastros WHERE tipo = 'Emitente' LIMIT 1").fetchone()
            if row_emit:
                emit_nome = row_emit['nome'] or emit_nome
                emit_cnpj = re.sub(r'\D', '', row_emit['cnpj_cpf'] or '') or emit_cnpj
                emit_ie = re.sub(r'\D', '', row_emit['ie'] or '') or emit_ie
                emit_logr = row_emit['logradouro'] or emit_logr
                emit_nro = row_emit['numero'] or emit_nro
                emit_bairro = row_emit['bairro'] or emit_bairro
                emit_mun = row_emit['municipio'] or emit_mun
                emit_uf = row_emit['uf'] or emit_uf
                emit_cep = re.sub(r'\D', '', row_emit['cep'] or '') or emit_cep

            row_desemb = c.execute("SELECT * FROM cadastros WHERE tipo = 'Local de Desembaraço' LIMIT 1").fetchone()
            if row_desemb:
                desemb_nome = row_desemb['nome'] or desemb_nome
                desemb_uf = row_desemb['uf'] or desemb_uf

            row_exp = c.execute("SELECT * FROM cadastros WHERE tipo = 'Cliente' AND (uf = 'EX' OR apelido LIKE '%EXPO%' OR apelido LIKE '%LOGISTICS%') LIMIT 1").fetchone()
            if row_exp:
                exp_nome = row_exp['nome'] or exp_nome
                exp_logr = row_exp['logradouro'] or exp_logr
                exp_nro = row_exp['numero'] or exp_nro
                exp_bairro = row_exp['bairro'] or exp_bairro
                exp_mun = row_exp['municipio'] or exp_mun
                exp_cep = row_exp['cep'] or exp_cep
                exp_pais_cod = str(row_exp['cpais'] or '1600')
                exp_pais_nome = row_exp['xpais'] or exp_pais_nome
        except Exception as e:
            print(f"[PUCOMEX] Aviso ao ler cadastros: {e}")

    # Mapa de Adições
    adicoes_raw = duimp_completa.get('adicoes', []) or []
    adic_map = {}
    for ad in adicoes_raw:
        n_ad = str(ad.get('numero', 1))
        itens_adic = ad.get('itens', [])
        for seq, n_it in enumerate(itens_adic, 1):
            adic_map[n_it] = (n_ad, str(seq))

    # -------------------------------------------------------------
    # Taxa Cambial e Moeda da DUIMP
    # -------------------------------------------------------------
    info_cpl_texto = ident.get('informacaoComplementar', '') or ''
    taxa_fiscal_global = 0.0
    m_taxa_global = re.search(r'(?:TAXA FISCAL|MOEDA VMLE|TAXA CAMBIAL)[^0-9]*?(?:US\$|R\$|USD|\$)?\s*([0-9]+[.,][0-9]+)', info_cpl_texto, re.IGNORECASE)
    if m_taxa_global:
        try:
            taxa_fiscal_global = float(m_taxa_global.group(1).replace(',', '.'))
        except Exception:
            taxa_fiscal_global = 0.0

    # Mapear Itens
    itens_brutos = duimp_completa.get('itens', []) or []
    itens = []
    
    for it in itens_brutos:
        num_item = it.get('identificacao', {}).get('numeroItem', len(itens) + 1)
        prod = it.get('produto', {}) or {}
        ncm = str(prod.get('ncm', '')).replace('.', '').strip()
        cod_prod = str(prod.get('codigo', num_item))
        
        # Descrição do Produto (CATP ou NCM)
        x_prod = ""
        catp_info = it.get('catp_detalhes', {})
        if catp_info:
            x_prod = catp_info.get('descricao') or catp_info.get('denominacao') or ""
        
        if not x_prod:
            x_prod = it.get('mercadoria', {}).get('descricao') or f"MERCADORIA IMPORTADA DUIMP {numero_duimp_original} - ITEM {num_item}"

        mercadoria = it.get('mercadoria', {}) or {}
        cond_venda = it.get('condicaoVenda', {}) or {}
        tributos = it.get('tributos', {}) or {}
        
        u_com = str(mercadoria.get('unidadeComercial') or 'UN').upper().strip()
        q_com = float(mercadoria.get('quantidadeComercial', 1.0) or 1.0)
        
        v_prod = float(cond_venda.get('valorBRL', 0.0) or 0.0)
        v_un_com = (v_prod / q_com) if q_com > 0 else v_prod

        # Moeda e Câmbio do Item
        moeda_item = str(
            mercadoria.get('moedaNegociada', {}).get('codigo')
            or cond_venda.get('moeda', {}).get('codigo')
            or 'USD'
        ).upper().strip()
        v_moeda_neg = float(cond_venda.get('valorMoedaNegociada', 0.0) or 0.0)
        v_un_moeda_neg = float(mercadoria.get('valorUnitarioMoedaNegociada', 0.0) or 0.0)

        taxa_item = 0.0
        if v_moeda_neg > 0 and v_prod > 0:
            taxa_item = v_prod / v_moeda_neg
        elif taxa_fiscal_global > 0:
            taxa_item = taxa_fiscal_global
        else:
            taxa_item = 1.0

        if v_moeda_neg <= 0 and taxa_item > 0:
            v_moeda_neg = v_prod / taxa_item
        if v_un_moeda_neg <= 0 and taxa_item > 0:
            v_un_moeda_neg = v_un_com / taxa_item

        frete_it = float(cond_venda.get('frete', {}).get('valorBRL', 0.0) or 0.0)
        seguro_it = float(cond_venda.get('seguro', {}).get('valorBRL', 0.0) or 0.0)
        taxa_siscomex_it = float(tributos.get('mercadoria', {}).get('taxaUtilizacao', 0.0) or 0.0)

        # Tributos calculados
        trib_calc_list = tributos.get('tributosCalculados', []) or []
        trib_dict = {}
        for tc in trib_calc_list:
            t_tipo = tc.get('tipo')
            if t_tipo:
                trib_dict[t_tipo] = tc

        # II
        ii_tc = trib_dict.get('II', {})
        p_ii = float(ii_tc.get('memoriaCalculo', {}).get('valorAliquota', 0.0) or 0.0)
        v_bc_ii = float(ii_tc.get('memoriaCalculo', {}).get('baseCalculoBRL', 0.0) or 0.0)
        v_ii = float(ii_tc.get('valoresBRL', {}).get('devido', 0.0) or ii_tc.get('valoresBRL', {}).get('calculado', 0.0) or 0.0)

        # IPI
        ipi_tc = trib_dict.get('IPI', {})
        p_ipi = float(ipi_tc.get('memoriaCalculo', {}).get('valorAliquota', 0.0) or 0.0)
        v_bc_ipi = float(ipi_tc.get('memoriaCalculo', {}).get('baseCalculoBRL', 0.0) or 0.0)
        v_ipi = float(ipi_tc.get('valoresBRL', {}).get('devido', 0.0) or ipi_tc.get('valoresBRL', {}).get('calculado', 0.0) or 0.0)

        # PIS
        pis_tc = trib_dict.get('PIS', {})
        p_pis = float(pis_tc.get('memoriaCalculo', {}).get('valorAliquota', 0.0) or 0.0)
        v_bc_pis = float(pis_tc.get('memoriaCalculo', {}).get('baseCalculoBRL', 0.0) or 0.0)
        v_pis = float(pis_tc.get('valoresBRL', {}).get('devido', 0.0) or pis_tc.get('valoresBRL', {}).get('calculado', 0.0) or 0.0)

        # COFINS
        cofins_tc = trib_dict.get('COFINS', {})
        p_cofins = float(cofins_tc.get('memoriaCalculo', {}).get('valorAliquota', 0.0) or 0.0)
        v_bc_cofins = float(cofins_tc.get('memoriaCalculo', {}).get('baseCalculoBRL', 0.0) or 0.0)
        v_cofins = float(cofins_tc.get('valoresBRL', {}).get('devido', 0.0) or cofins_tc.get('valoresBRL', {}).get('calculado', 0.0) or 0.0)

        # Adição e Sequencial
        n_adic, n_seq_adic = adic_map.get(num_item, (str(num_item), '1'))

        item_obj = {
            "nItem": str(num_item),
            "cProd": f"{numero_duimp_original}-{num_item}",
            "cEAN": "SEM GTIN",
            "xProd": x_prod,
            "NCM": ncm,
            "CEST": "",
            "CFOP": "3101",
            "uCom": u_com,
            "qCom": f"{q_com:.4f}",
            "vUnCom": f"{v_un_com:.4f}",
            "uTrib": u_com,
            "qTrib": f"{q_com:.4f}",
            "vUnTrib": f"{v_un_com:.4f}",
            "vProd": f"{v_prod:.2f}",
            "moeda_conversao": moeda_item,
            "taxa_conversao": f"{taxa_item:.4f}",
            "vProd_moeda_origem": f"{v_moeda_neg:.2f}",
            "vUnCom_moeda_origem": f"{v_un_moeda_neg:.4f}",
            "vUnTrib_moeda_origem": f"{v_un_moeda_neg:.4f}",
            "orig": "1",
            "cEnq": "999",
            "CST_IPI": "49",
            "CST_PIS": "98",
            "CST_COFINS": "98",
            "vFrete": f"{frete_it:.2f}",
            "vSeg": f"{seguro_it:.2f}",
            "vDesc": "0.00",
            "vOutro": f"{taxa_siscomex_it:.2f}",
            "vDespAdu": "0.00",
            "vAFRMM": "0.00",
            "pII": f"{p_ii:.2f}",
            "vBC_II": f"{v_bc_ii:.2f}",
            "vII": f"{v_ii:.2f}",
            "pIPI": f"{p_ipi:.2f}",
            "vBC_IPI": f"{v_bc_ipi:.2f}",
            "vIPI": f"{v_ipi:.2f}",
            "pPIS": f"{p_pis:.2f}",
            "vBC_PIS": f"{v_bc_pis:.2f}",
            "vPIS": f"{v_pis:.2f}",
            "pCOFINS": f"{p_cofins:.2f}",
            "vBC_COFINS": f"{v_bc_cofins:.2f}",
            "vCOFINS": f"{v_cofins:.2f}",
            "nDI": numero_duimp_original,
            "dDI": data_duimp,
            "xLocDesemb": desemb_nome,
            "UFDesemb": desemb_uf,
            "dDesemb": data_duimp,
            "tpViaTransp": "1",
            "vAFRMM_import": "0.00",
            "tpIntermedio": "1",
            "CNPJ_adquirente": "",
            "UFTerceiro": "",
            "cExportador": exp_nome,
            "cFabricante": exp_nome,
            "nAdicao": str(n_adic),
            "nSeqAdic": str(n_seq_adic)
        }
        itens.append(item_obj)

    # Totais consolidados
    total_produtos = sum(float(it['vProd']) for it in itens)
    total_frete = sum(float(it['vFrete']) for it in itens)
    total_seguro = sum(float(it['vSeg']) for it in itens)
    total_outro = sum(float(it['vOutro']) for it in itens)
    total_ii = sum(float(it['vII']) for it in itens)
    total_ipi = sum(float(it['vIPI']) for it in itens)
    total_pis = sum(float(it['vPIS']) for it in itens)
    total_cofins = sum(float(it['vCOFINS']) for it in itens)
    valor_total_nf = total_produtos + total_frete + total_seguro + total_outro

    # Peso líquido
    peso_l_total = 0.0
    for it_raw in itens_brutos:
        pl = it_raw.get('mercadoria', {}).get('pesoLiquido')
        if pl:
            try:
                peso_l_total += float(pl)
            except Exception:
                pass
    peso_b_total = peso_l_total * 1.05 if peso_l_total > 0 else 0.0

    hoje = datetime.now()
    moeda_op_global = itens[0]['moeda_conversao'] if itens else "USD"
    taxa_op_global = float(itens[0]['taxa_conversao']) if itens else (taxa_fiscal_global if taxa_fiscal_global > 0 else 1.0)
    taxa_op_global_str = f"{taxa_op_global:.4f}".replace('.', ',')

    cabecalho = {
        "referencia_interna": referencia_interna,
        "nNF": "", "serie": "1", "indFinal": "1",
        "natOp": "COMPRA PARA INDUSTRIALIZAÇÃO (IMPORTAÇÃO)",
        "cfop_padrao": "3101",
        "select_operacao": "COMPRA PARA INDUSTRIALIZAÇÃO (IMPORTAÇÃO)",
        "tpNF": "0", "idDest": "3", "chaveAcesso": "", "cUF": "35",
        "cNF": "", "dhEmi": dh_emi_iso, "mod": "55", "tpEmis": "1", "cDV": "",
        "emit_xNome": emit_nome,
        "emit_CNPJ": emit_cnpj,
        "emit_IE": emit_ie,
        "emit_CRT": "1",
        "emit_xLgr": emit_logr,
        "emit_nro": emit_nro,
        "emit_xCpl": "SALA 910 TORRE B",
        "emit_xBairro": emit_bairro,
        "emit_cMun": "3550308",
        "emit_xMun": emit_mun,
        "emit_UF": emit_uf,
        "emit_CEP": emit_cep,
        "dest_xNome": exp_nome,
        "dest_tpDoc": "Estrangeiro",
        "dest_CNPJ_CPF": "",
        "dest_indIEDest": "9",
        "dest_IE": "",
        "dest_xLgr": exp_logr,
        "dest_nro": exp_nro,
        "dest_xCpl": "",
        "dest_xBairro": exp_bairro,
        "dest_cMun": "9999999",
        "dest_xMun": "EXTERIOR",
        "dest_UF": "EX",
        "dest_CEP": exp_cep,
        "dest_cPais": exp_pais_cod,
        "dest_xPais": exp_pais_nome,
        "import_nDI": numero_duimp_original,
        "import_dDI": data_duimp,
        "import_cExportador": exp_nome,
        "import_tpViaTransp": "1",
        "import_tpIntermedio": "1",
        "import_UFDesemb": desemb_uf,
        "import_xLocDesemb": desemb_nome,
        "import_dDesemb": data_duimp,
        "modFrete": "1",
        "transp_modFrete": "1",
        "transp_xNome": "TRANSFERRARI TRANSPORTE E LOGISTICA LTDA",
        "transp_CNPJ_CPF": "04.601.873/0001-00",
        "transp_IE": "298263390116",
        "transp_xEnder": "Rua Doutor Paulo de Oliveira, 245",
        "transp_xMun": "Embu das Artes",
        "transp_UF": "SP",
        "transp_qVol": str(len(itens)),
        "transp_esp": "VOLUMES",
        "transp_pesoL": f"{peso_l_total:.3f}".replace('.', ','),
        "transp_pesoB": f"{peso_b_total:.3f}".replace('.', ','),
        "tot_vProd": f"{total_produtos:.2f}".replace('.', ','),
        "tot_vFrete": f"{total_frete:.2f}".replace('.', ','),
        "tot_vSeg": f"{total_seguro:.2f}".replace('.', ','),
        "tot_vOutro": f"{total_outro:.2f}".replace('.', ','),
        "tot_vDesc": "0,00",
        "tot_vNF": f"{valor_total_nf:.2f}".replace('.', ','),
        "vNF": f"{valor_total_nf:.2f}".replace('.', ','),
        "tot_vBC": "0,00", "tot_vICMS": "0,00", "tot_vBCST": "0,00", "tot_vST": "0,00",
        "tot_vII": f"{total_ii:.2f}".replace('.', ','),
        "tot_vIPI": f"{total_ipi:.2f}".replace('.', ','),
        "tot_vPIS": f"{total_pis:.2f}".replace('.', ','),
        "tot_vCOFINS": f"{total_cofins:.2f}".replace('.', ','),
        "rateio_vAFRMM": "0,00",
        "rateio_vSiscomex": f"{total_outro:.2f}".replace('.', ','),
        "rateio_vFrete": f"{total_frete:.2f}".replace('.', ','),
        "rateio_vSeg": f"{total_seguro:.2f}".replace('.', ','),
        "rateio_vOutro": "0,00",
        "ptax_data": data_duimp,
        "ptax_moeda": moeda_op_global,
        "ptax_cotacao_venda": taxa_op_global_str,
        "ptax_cotacao_compra": taxa_op_global_str,
        "infCpl": f"DECLARACAO UNICA DE IMPORTACAO - DUIMP: {numero_duimp_original}  DATA: {datetime.strptime(data_duimp, '%Y-%m-%d').strftime('%d/%m/%Y') if data_duimp else hoje.strftime('%d/%m/%Y')}  LOCAL DESEMBARACO: {desemb_nome} - {desemb_uf}  CANAL: VERDE  IMPORTADOR: {emit_nome} ({emit_cnpj})  EXPORTADOR: {exp_nome}"
    }

    rodape = {
        "vNF": f"{valor_total_nf:.2f}",
        "infCpl": cabecalho["infCpl"],
        "transporte": {
            "modFrete": "1",
            "CNPJ_CPF": "04.601.873/0001-00",
            "xNome": "TRANSFERRARI TRANSPORTE E LOGISTICA LTDA",
            "IE": "298263390116",
            "xEnder": "Rua Doutor Paulo de Oliveira, 245",
            "xMun": "Embu das Artes",
            "UF": "SP",
            "qVol": str(len(itens)),
            "esp": "VOLUMES",
            "marca": "",
            "nVol": "",
            "pesoL": f"{peso_l_total:.3f}",
            "pesoB": f"{peso_b_total:.3f}"
        },
        "totais": {
            "vBC": "0.00", "vICMS": "0.00", "vICMSDeson": "0.00", "vFCP": "0.00",
            "vBCST": "0.00", "vST": "0.00", "vFCPST": "0.00", "vFCPSTRet": "0.00",
            "vProd": f"{total_produtos:.2f}",
            "vFrete": f"{total_frete:.2f}",
            "vSeg": f"{total_seguro:.2f}",
            "vDesc": "0.00",
            "vII": f"{total_ii:.2f}",
            "vIPI": f"{total_ipi:.2f}",
            "vIPIDevol": "0.00",
            "vPIS": f"{total_pis:.2f}",
            "vCOFINS": f"{total_cofins:.2f}",
            "vOutro": f"{total_outro:.2f}",
            "vNF": f"{valor_total_nf:.2f}"
        }
    }

    imposto_modelo = {
        "cfop_padrao": "3101", "tp_nf": "0", "id_dest": "3", "orig_padrao": "1",
        "csosn_icms": "102", "c_enq_ipi": "999", "cst_ipi": "49", "p_ipi": 0,
        "aliquota_ii": 0, "cst_pis": "98", "p_pis": 0, "cst_cofins": "98", "p_cofins": 0
    }

    resumo_rateio = {
        "vAFRMM": "0.00", "vDespAdu": f"{total_outro:.2f}", "vOutro": f"{total_outro:.2f}",
        "vFrete": f"{total_frete:.2f}", "vSeg": f"{total_seguro:.2f}", "data_di": data_duimp,
        "ptax_moeda": moeda_op_global,
        "ptax_cotacao_venda": taxa_op_global_str
    }

    return {
        "numero": numero_duimp_original,
        "versao": versao,
        "data_registro": data_duimp,
        "referencia_interna": referencia_interna,
        "itens": itens,
        "cabecalho": cabecalho,
        "rodape": rodape,
        "imposto_modelo": imposto_modelo,
        "resumo_rateio": resumo_rateio,
        "totais": {
            "total_produtos": total_produtos,
            "total_frete": total_frete,
            "total_seguro": total_seguro,
            "total_outro": total_outro,
            "total_ii": total_ii,
            "total_ipi": total_ipi,
            "total_pis": total_pis,
            "total_cofins": total_cofins,
            "valor_total_nf": valor_total_nf
        }
    }


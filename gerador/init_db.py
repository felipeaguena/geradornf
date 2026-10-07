import sqlite3
import os

def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Tabela de NCMs e tributacao
    c.execute('''
        CREATE TABLE IF NOT EXISTS ncm_tributacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ncm TEXT UNIQUE,
            descricao TEXT,
            uTrib TEXT,
            aliquota_ii REAL,
            aliquota_ipi REAL,
            aliquota_pis REAL,
            aliquota_cofins REAL,
            aliquota_icms REAL
        )
    ''')

    # 1.1 Tabela Geral de NCM Unificada
    c.execute('''
        CREATE TABLE IF NOT EXISTS ncm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            codigo_limpo TEXT,
            descricao TEXT,
            utrib TEXT,
            descricao_utrib TEXT,
            aliquota_ii REAL,
            aliquota_ipi TEXT,
            aliquota_pis REAL,
            aliquota_cofins REAL,
            regime_pis_cofins TEXT,
            data_inicio TEXT,
            data_fim TEXT,
            tipo_ato TEXT,
            numero_ato TEXT,
            ano_ato TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ncm_codigo_limpo ON ncm(codigo_limpo)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ncm_codigo ON ncm(codigo)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ncm_utrib ON ncm(utrib)')

    ncms = [
        ('42022220', 'BOLSAS, MALAS, ETC', 'PC', 0.0, 6.5, 2.1, 9.65, 0.0),
        ('49111010', 'IMPRESSOS PROMOCIONAIS', 'PC', 0.0, 0.0, 2.1, 9.65, 0.0),
        ('90189099', 'SISTEMA CIRURGICO ENDOSCOPICO', 'KI', 0.0, 0.0, 0.0, 0.0, 0.0)
    ]
    
    for ncm in ncms:
        try:
            c.execute('''
                INSERT INTO ncm_tributacao (ncm, descricao, uTrib, aliquota_ii, aliquota_ipi, aliquota_pis, aliquota_cofins, aliquota_icms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ncm)
        except sqlite3.IntegrityError:
            pass

    # 2. Tabela de Tipos de Nota / Operacoes
    c.execute('''
        CREATE TABLE IF NOT EXISTS tipos_operacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_operacao TEXT UNIQUE,
            cfop_padrao TEXT,
            tp_nf TEXT DEFAULT '0',
            id_dest TEXT DEFAULT '3',
            orig_padrao TEXT,
            csosn_icms TEXT,
            c_enq_ipi TEXT,
            cst_ipi TEXT,
            p_ipi REAL,
            aliquota_ii REAL,
            cst_pis TEXT,
            p_pis REAL,
            cst_cofins TEXT,
            p_cofins REAL,
            inf_cpl_padrao TEXT
        )
    ''')

    # 2.1 Tabela de Configurações e Preferências do Sistema
    c.execute('''
        CREATE TABLE IF NOT EXISTS sistema_config (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Verifica se as operacoes iniciais ja foram populadas alguma vez no sistema
    op_init_row = c.execute("SELECT valor FROM sistema_config WHERE chave = 'operacoes_iniciais_carregadas'").fetchone()
    qtd_ops_existentes = c.execute("SELECT COUNT(*) FROM tipos_operacao").fetchone()[0]

    operacoes_iniciais = [
        (
            'ADMISSAO TEMPORARIA',
            '3930', '0', '3', '1', '102', '102', '05', 0.0, 0.0, '07', 0.0, '07', 0.0,
            'ADMISSAO TEMPORARIA DE CARGAS. SUSPENSAO DE TRIBUTOS CONFORME LEGISLACAO ADUANEIRA.'
        ),
        (
            'REEXPORTAÇÃO FICTA',
            '7930', '1', '3', '1', '300', '102', '05', 0.0, 0.0, '07', 0.0, '07', 0.0,
            'REEXPORTAÇÃO FICTA DE CARGAS QUE PARTICIPARAM DE EVENTO NO BRASIL E RETORNARAO A ORIGEM.'
        ),
        (
            'REMESSA PARA FEIRA',
            '5914', '1', '1', '1', '102', '102', '05', 0.0, 0.0, '07', 0.0, '07', 0.0,
            'REMESSA DE MERCADORIA OU BEM PARA EXPOSICAO OU FEIRA.'
        ),
        (
            'OUTRAS ENTRADAS DE MERCADORIA',
            '3930', '0', '3', '1', '102', '999', '00', 6.5, 0.0, '01', 2.10, '01', 9.65,
            'ENTRADA DE IMPORTACAO COM TRIBUTACAO REGULAR.'
        )
    ]

    # Só insere as operações padrão se o sistema for totalmente virgem (sem operações e flag não gravada)
    # Se o usuário já utiliza o banco ou já deletou operações, respeita a decisão e não re-insere!
    if not op_init_row:
        if qtd_ops_existentes == 0:
            for op in operacoes_iniciais:
                try:
                    c.execute('''
                        INSERT INTO tipos_operacao (
                            nome_operacao, cfop_padrao, tp_nf, id_dest, orig_padrao, csosn_icms, c_enq_ipi,
                            cst_ipi, p_ipi, aliquota_ii, cst_pis, p_pis, cst_cofins, p_cofins, inf_cpl_padrao
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', op)
                except sqlite3.IntegrityError:
                    pass
        c.execute("INSERT OR REPLACE INTO sistema_config (chave, valor) VALUES ('operacoes_iniciais_carregadas', '1')")

    # 3. Tabela de CSTs Oficiais (ICMS/CSOSN, IPI, PIS, COFINS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabela_csts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_imposto TEXT,
            codigo TEXT,
            descricao TEXT,
            codigo_descricao TEXT,
            aplicacao TEXT
        )
    ''')
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_cst_tipo_cod ON tabela_csts(tipo_imposto, codigo)')

    csts_oficiais = [
        # ICMS Normal
        ('ICMS', '00', 'Tributada integralmente', '00 - Tributada integralmente', 'GERAL'),
        ('ICMS', '10', 'Tributada e com cobrança do ICMS por substituição tributária', '10 - Tributada e com cobrança do ICMS por substituição tributária', 'GERAL'),
        ('ICMS', '20', 'Com redução de base de cálculo', '20 - Com redução de base de cálculo', 'GERAL'),
        ('ICMS', '30', 'Isenta ou não tributada e com cobrança do ICMS por substituição tributária', '30 - Isenta ou não tributada e com cobrança do ICMS por substituição tributária', 'GERAL'),
        ('ICMS', '40', 'Isenta', '40 - Isenta', 'GERAL'),
        ('ICMS', '41', 'Não tributada (Exportação / Imunidade)', '41 - Não tributada (Exportação / Imunidade)', 'EXPORTACAO'),
        ('ICMS', '50', 'Suspensão', '50 - Suspensão', 'IMPORTACAO'),
        ('ICMS', '51', 'Diferimento', '51 - Diferimento', 'IMPORTACAO'),
        ('ICMS', '60', 'ICMS cobrado anteriormente por substituição tributária', '60 - ICMS cobrado anteriormente por substituição tributária', 'GERAL'),
        ('ICMS', '70', 'Com redução de base de cálculo e cobrança do ICMS por substituição tributária', '70 - Com redução de base de cálculo e cobrança do ICMS por substituição tributária', 'GERAL'),
        ('ICMS', '90', 'Outras', '90 - Outras', 'GERAL'),

        # CSOSN - Simples Nacional
        ('CSOSN', '101', 'Tributada pelo Simples Nacional com permissão de crédito', '101 - Tributada pelo Simples Nacional com permissão de crédito', 'GERAL'),
        ('CSOSN', '102', 'Tributada pelo Simples Nacional sem permissão de crédito', '102 - Tributada pelo Simples Nacional sem permissão de crédito', 'GERAL'),
        ('CSOSN', '103', 'Isenção do ICMS no Simples Nacional para faixa de receita bruta', '103 - Isenção do ICMS no Simples Nacional para faixa de receita bruta', 'GERAL'),
        ('CSOSN', '201', 'Tributada pelo Simples Nacional com permissão de crédito e cobrança do ICMS por ST', '201 - Tributada pelo Simples Nacional com permissão de crédito e cobrança do ICMS por ST', 'GERAL'),
        ('CSOSN', '202', 'Tributada pelo Simples Nacional sem permissão de crédito e cobrança do ICMS por ST', '202 - Tributada pelo Simples Nacional sem permissão de crédito e cobrança do ICMS por ST', 'GERAL'),
        ('CSOSN', '203', 'Isenção do ICMS no Simples Nacional para faixa de receita bruta e cobrança do ICMS por ST', '203 - Isenção do ICMS no Simples Nacional para faixa de receita bruta e cobrança do ICMS por ST', 'GERAL'),
        ('CSOSN', '300', 'Imune (Exportação)', '300 - Imune (Exportação)', 'EXPORTACAO'),
        ('CSOSN', '400', 'Não tributada pelo Simples Nacional', '400 - Não tributada pelo Simples Nacional', 'GERAL'),
        ('CSOSN', '500', 'ICMS cobrado anteriormente por substituição tributária (substituído) ou por antecipação', '500 - ICMS cobrado anteriormente por substituição tributária (substituído) ou por antecipação', 'GERAL'),
        ('CSOSN', '900', 'Outros (Importação / Exportação / Outros)', '900 - Outros (Importação / Exportação / Outros)', 'IMPORTACAO'),

        # IPI
        ('IPI', '00', 'Entrada com recuperação de crédito', '00 - Entrada com recuperação de crédito', 'ENTRADA'),
        ('IPI', '01', 'Entrada tributada com alíquota zero', '01 - Entrada tributada com alíquota zero', 'ENTRADA'),
        ('IPI', '02', 'Entrada isenta', '02 - Entrada isenta', 'ENTRADA'),
        ('IPI', '03', 'Entrada não-tributada', '03 - Entrada não-tributada', 'ENTRADA'),
        ('IPI', '04', 'Entrada imune', '04 - Entrada imune', 'ENTRADA'),
        ('IPI', '05', 'Entrada com suspensão (Admissão Temporária)', '05 - Entrada com suspensão (Admissão Temporária)', 'IMPORTACAO'),
        ('IPI', '49', 'Outras entradas', '49 - Outras entradas', 'ENTRADA'),
        ('IPI', '50', 'Saída tributada', '50 - Saída tributada', 'SAIDA'),
        ('IPI', '51', 'Saída tributável com alíquota zero', '51 - Saída tributável com alíquota zero', 'SAIDA'),
        ('IPI', '52', 'Saída isenta', '52 - Saída isenta', 'SAIDA'),
        ('IPI', '53', 'Saída não-tributada', '53 - Saída não-tributada', 'SAIDA'),
        ('IPI', '54', 'Saída imune (Exportação)', '54 - Saída imune (Exportação)', 'EXPORTACAO'),
        ('IPI', '55', 'Saída com suspensão', '55 - Saída com suspensão', 'SAIDA'),
        ('IPI', '99', 'Outras saídas', '99 - Outras saídas', 'SAIDA'),

        # PIS e COFINS (Saídas e Entradas)
        ('PIS_COFINS', '01', 'Operação tributável com alíquota básica', '01 - Operação tributável com alíquota básica', 'SAIDA'),
        ('PIS_COFINS', '02', 'Operação tributável com alíquota diferenciada', '02 - Operação tributável com alíquota diferenciada', 'SAIDA'),
        ('PIS_COFINS', '03', 'Operação tributável com alíquota por unidade de medida de produto', '03 - Operação tributável com alíquota por unidade de medida de produto', 'SAIDA'),
        ('PIS_COFINS', '04', 'Operação tributável monofásica - Revenda a alíquota zero', '04 - Operação tributável monofásica - Revenda a alíquota zero', 'SAIDA'),
        ('PIS_COFINS', '05', 'Operação tributável por substituição tributária', '05 - Operação tributável por substituição tributária', 'SAIDA'),
        ('PIS_COFINS', '06', 'Operação tributável a alíquota zero', '06 - Operação tributável a alíquota zero', 'SAIDA'),
        ('PIS_COFINS', '07', 'Operação isenta da contribuição', '07 - Operação isenta da contribuição', 'SAIDA'),
        ('PIS_COFINS', '08', 'Operação sem incidência da contribuição (Exportação)', '08 - Operação sem incidência da contribuição (Exportação)', 'EXPORTACAO'),
        ('PIS_COFINS', '09', 'Operação com suspensão da contribuição', '09 - Operação com suspensão da contribuição', 'SAIDA'),
        ('PIS_COFINS', '49', 'Outras operações de saída', '49 - Outras operações de saída', 'SAIDA'),
        ('PIS_COFINS', '50', 'Operação com direito a crédito - Vinculada a receita tributada no mercado interno', '50 - Operação com direito a crédito - Vinculada a receita tributada no mercado interno', 'ENTRADA'),
        ('PIS_COFINS', '51', 'Operação com direito a crédito - Vinculada a receita não-tributada no mercado interno', '51 - Operação com direito a crédito - Vinculada a receita não-tributada no mercado interno', 'ENTRADA'),
        ('PIS_COFINS', '52', 'Operação com direito a crédito - Vinculada a receita de exportação', '52 - Operação com direito a crédito - Vinculada a receita de exportação', 'ENTRADA'),
        ('PIS_COFINS', '53', 'Operação com direito a crédito - Vinculada a receitas tributadas e não-tributadas no mercado interno', '53 - Operação com direito a crédito - Vinculada a receitas tributadas e não-tributadas no mercado interno', 'ENTRADA'),
        ('PIS_COFINS', '54', 'Operação com direito a crédito - Vinculada a receitas tributadas e de exportação', '54 - Operação com direito a crédito - Vinculada a receitas tributadas e de exportação', 'ENTRADA'),
        ('PIS_COFINS', '55', 'Operação com direito a crédito - Vinculada a receitas não-tributadas e de exportação', '55 - Operação com direito a crédito - Vinculada a receitas não-tributadas e de exportação', 'ENTRADA'),
        ('PIS_COFINS', '56', 'Operação com direito a crédito - Vinculada a múltiplos tipos de receita', '56 - Operação com direito a crédito - Vinculada a múltiplos tipos de receita', 'ENTRADA'),
        ('PIS_COFINS', '60', 'Crédito presumido - Vinculada a receita tributada no mercado interno', '60 - Crédito presumido - Vinculada a receita tributada no mercado interno', 'ENTRADA'),
        ('PIS_COFINS', '61', 'Crédito presumido - Vinculada a receita não-tributada no mercado interno', '61 - Crédito presumido - Vinculada a receita não-tributada no mercado interno', 'ENTRADA'),
        ('PIS_COFINS', '62', 'Crédito presumido - Vinculada a receita de exportação', '62 - Crédito presumido - Vinculada a receita de exportação', 'ENTRADA'),
        ('PIS_COFINS', '63', 'Crédito presumido - Vinculada a receitas tributadas e não-tributadas no mercado interno', '63 - Crédito presumido - Vinculada a receitas tributadas e não-tributadas no mercado interno', 'ENTRADA'),
        ('PIS_COFINS', '64', 'Crédito presumido - Vinculada a receitas tributadas e de exportação', '64 - Crédito presumido - Vinculada a receitas tributadas e de exportação', 'ENTRADA'),
        ('PIS_COFINS', '65', 'Crédito presumido - Vinculada a receitas não-tributadas e de exportação', '65 - Crédito presumido - Vinculada a receitas não-tributadas e de exportação', 'ENTRADA'),
        ('PIS_COFINS', '66', 'Crédito presumido - Vinculada a receitas tributadas, não-tributadas e de exportação', '66 - Crédito presumido - Vinculada a receitas tributadas, não-tributadas e de exportação', 'ENTRADA'),
        ('PIS_COFINS', '67', 'Crédito presumido - Outras operações', '67 - Crédito presumido - Outras operações', 'ENTRADA'),
        ('PIS_COFINS', '70', 'Operação de aquisição sem direito a crédito', '70 - Operação de aquisição sem direito a crédito', 'ENTRADA'),
        ('PIS_COFINS', '71', 'Operação de aquisição com isenção', '71 - Operação de aquisição com isenção', 'ENTRADA'),
        ('PIS_COFINS', '72', 'Operação de aquisição com suspensão (Admissão Temporária / Drawback)', '72 - Operação de aquisição com suspensão (Admissão Temporária / Drawback)', 'IMPORTACAO'),
        ('PIS_COFINS', '73', 'Operação de aquisição a alíquota zero', '73 - Operação de aquisição a alíquota zero', 'ENTRADA'),
        ('PIS_COFINS', '74', 'Operação de aquisição sem incidência da contribuição', '74 - Operação de aquisição sem incidência da contribuição', 'ENTRADA'),
        ('PIS_COFINS', '75', 'Operação de aquisição por substituição tributária', '75 - Operação de aquisição por substituição tributária', 'ENTRADA'),
        ('PIS_COFINS', '98', 'Outras operações de entrada', '98 - Outras operações de entrada', 'ENTRADA'),
        ('PIS_COFINS', '99', 'Outras operações', '99 - Outras operações', 'AMBOS')
    ]

    for cst in csts_oficiais:
        try:
            c.execute('''
                INSERT INTO tabela_csts (tipo_imposto, codigo, descricao, codigo_descricao, aplicacao)
                VALUES (?, ?, ?, ?, ?)
            ''', cst)
        except sqlite3.IntegrityError:
            pass

    # 4. Tabela de Rascunhos Salvos
    c.execute('''
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
    rascunhos_dir = os.path.join(os.path.dirname(__file__), 'rascunhos')
    os.makedirs(rascunhos_dir, exist_ok=True)

    # 5. Tabelas de Localidades (Paises BACEN, Municipios IBGE e Cache de CEPs)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabela_paises (
            codigo TEXT PRIMARY KEY,
            nome TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_paises_nome ON tabela_paises(nome)')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tabela_municipios (
            codigo_ibge TEXT PRIMARY KEY,
            nome TEXT,
            uf TEXT,
            c_uf TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_mun_uf ON tabela_municipios(uf)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_mun_nome ON tabela_municipios(nome)')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tabela_ceps (
            cep TEXT PRIMARY KEY,
            logradouro TEXT,
            bairro TEXT,
            municipio TEXT,
            codigo_ibge TEXT,
            uf TEXT,
            data_consulta DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed de dados_localidades.json se as tabelas estiverem vazias
    count_p = c.execute("SELECT COUNT(*) FROM tabela_paises").fetchone()[0]
    count_m = c.execute("SELECT COUNT(*) FROM tabela_municipios").fetchone()[0]
    if count_p == 0 or count_m == 0:
        json_loc_path = os.path.join(os.path.dirname(__file__), 'dados_localidades.json')
        if os.path.exists(json_loc_path):
            import json, unicodedata, re
            def clean_loc(txt):
                if not txt: return ''
                s = unicodedata.normalize('NFKD', str(txt))
                s = ''.join(c for c in s if not unicodedata.combining(c))
                s = re.sub(r'[^a-zA-Z0-9\s\-]', ' ', s)
                return re.sub(r'\s+', ' ', s).strip()

            with open(json_loc_path, 'r', encoding='utf-8') as f_loc:
                dados_loc = json.load(f_loc)
                if count_p == 0 and 'paises' in dados_loc:
                    p_rows = [(p['codigo'], clean_loc(p['nome'])) for p in dados_loc['paises']]
                    c.executemany('INSERT OR REPLACE INTO tabela_paises (codigo, nome) VALUES (?, ?)', p_rows)
                if count_m == 0 and 'municipios' in dados_loc:
                    m_rows = [(m['codigo_ibge'], clean_loc(m['nome']), m['uf'], m['c_uf']) for m in dados_loc['municipios']]
                    c.executemany('INSERT OR REPLACE INTO tabela_municipios (codigo_ibge, nome, uf, c_uf) VALUES (?, ?, ?, ?)', m_rows)

    # 6. Tabela de Feiras do Ano (Descrição da Feira)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabela_feiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_feira TEXT,
            deadline TEXT,
            local TEXT,
            organizador TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    count_feiras = c.execute("SELECT COUNT(*) FROM tabela_feiras").fetchone()[0]
    if count_feiras == 0:
        feiras_iniciais = [
            ("AES APPLIANCES & ELECTRONICS SHOW", "16 A 18 DE SETEMBRO DE 2026", "2026-08-16", "SÃO PAULO EXPO", "APPLIANCE & ELETRONICS EXPO"),
            ("AGRISHOW", "27 DE ABRIL A 01 DE MAIO DE 2026", "2026-03-28", "AGRISHOW", "INFORMA MARKETS"),
            ("AIDS", "26 A 31 DE JULHO DE 2026", "2026-06-26", "RIO DE JANEIRO", "INTERNATIONAL AIDS SOCIETY"),
            ("ANALÍTICA LATIN AMERICA", "28 A 30 DE SETEMBRO DE 2027", "2027", "SÃO PAULO EXPO", "NÜRNBERG MESSE"),
            ("AUTOCOM", "01 A 02 DE ABRIL DE 2026", "2026-03-01", "EXPO CENTER NORTE", "FRANCAL FEIRAS"),
            ("AUTOMEC", "20 A 24 DE ABRIL DE 2027", "2027-03-20", "SÃO PAULO EXPO", "RX GLOBAL"),
            ("BEAUTY FAIR", "05 A 08 DE SETEMBRO DE 2026", "2026-08-05", "EXPO CENTER NORTE", ""),
            ("BETT BRASIL", "05 A 08 DE MAIO DE 2026", "2026-04-05", "EXPO CENTER NORTE", "HYVE GROUP"),
            ("BIS SIGMA AMERICAS", "06 A 09 DE ABRIL DE 2026", "2026-03-06", "TRANSAMERICA EXPO CENTER", "GRUPO SIGMA"),
            ("BRASIL BRAU", "09 A 11 DE JUNHO DE 2026", "2026-05-09", "SÃO PAULO EXPO", "GL EXHIBITIONS"),
            ("BRASIL TRADING FITNESS FAIR", "17 A 18 OUTUBRO 2026", "2026-09-17", "EXPO CENTER NORTE", "ITALIAN EXHIBITION GROUP BRASIL EVENTOS"),
            ("BRAZIL WIND POWER", "27 A 29 DE OUTUBRO DE 2026", "2026-09-27", "SÃO PAULO EXPO", "INFORMA"),
            ("CHINA HOMELIFE BRAZIL", "16 A 18 DE SETEMBRO DE 2026", "2026-08-16", "SÃO PAULO EXPO", "CHINA HOMELIFE"),
            ("CINECOLOR", "RADAR CINECOLOR", "", "", ""),
            ("CIOSP", "28 A 31 DE JANEIRO DE 2026", "2025-12-28", "EXPO CENTER NORTE", "APCD"),
            ("CONCRETE SHOW", "25 A 27 DE AGOSTO DE 2026", "2026-07-25", "SÃO PAULO EXPO", "INFORMA"),
            ("DVS", "", "", "", ""),
            ("ELETROCAR SHOW", "21 A 24 DE JUNHO DE 2027", "2027-05-21", "DISTRITO ANHEMBI", "GRUPO ELETROLAR"),
            ("ELETROLAR SHOW", "21 A 24 DE JUNHO DE 2027", "2027-05-21", "DISTRITO ANHEMBI", "GRUPO ELETROLAR"),
            ("EQUIPOTEL", "15 A 18 DE SETEMBRO DE 2026", "2026-07-15", "EXPO CENTER NORTE", "RX GLOBAL"),
            ("ESCOLAR OFFICE BRASIL", "02 A 05 DE AGOSTO DE 2026", "2026-07-02", "EXPO CENTER NORTE", "FRANCAL FEIRAS"),
            ("EVENTO PRIVADO MAGNETTI MARELLI", "-", "-", "", ""),
            ("EXPO ELEVADOR", "01 A 03 DE JUNHO DE 2027", "2027", "PRO MAGNO", "CARDOSO ALMEIDA EVENTOS"),
            ("EXPO LAZER", "11 A 14 DE AGOSTO DE 2026", "2026-07-11", "DISTRITO ANHEMBI", "FRANCAL FEIRAS"),
            ("EXPO PRINT", "24 a 28 DE MARÇO DE 2026", "2026-02-24", "EXPO CENTER NORTE", "AFEIGRAF"),
            ("EXPO REVESTIR", "09 A 13 DE MARÇO DE 2026", "2026-02-09", "SÃO PAULO EXPO", "NÜRNBERG MESSE"),
            ("EXPOLUX", "15 A 18 DE SETEMBRO DE 2026", "2026-08-15", "EXPO CENTER NORTE", "RX GLOBAL"),
            ("EXPOMAFE", "04 A 08 DE MAIO DE 2027", "2027", "SÃO PAULO EXPO", "INFORMA MARKETS"),
            ("EXPOPOSTOS", "08 A 10 DE SETEMBRO DE 2026", "2026-08-08", "SÃO PAULO EXPO", "FECOMBUSTÍVEIS"),
            ("EXPOSEC", "01 A 03 JUNHO DE 2026", "2026-05-01", "SÃO PAULO EXPO", "FIERA MILANO"),
            ("FCE PHARMA", "01 A 03 DE JUNHO DE 2026", "2026-05-01", "SÃO PAULO EXPO", "NURNBERG MESSE"),
            ("FEBRATEX", "18 A 21 DE AGOSTO DE 2026", "2026-07-18", "AMPE BLUMENAU", "FEBRATEX GROUP"),
            ("FEBRAVA", "06 A 08 DE OUTUBRO DE 2026", "2026-09-06", "RIO CENTRO", "REED EXHIBITIONS"),
            ("FEICON", "07 A 10 DE ABRIL DE 2026", "2026-03-07", "SÃO PAULO EXPO", "RX GLOBAL"),
            ("FEIMEC", "05 A 09 DE MAIO DE 2026", "2026-04-05", "SÃO PAULO EXPO", "INFORMA MARKETS"),
            ("FENAF/CONAF", "21 A 24 DE JULHO DE 2026", "2026-06-21", "SÃO PAULO EXPO", "ABIFA"),
            ("FENASAN", "20 A 22 DE OUTUBRO DE 2026", "2026-09-20", "EXPO CENTER NORTE", "AESABESP"),
            ("FESPA", "24 A 28 DE MARÇO DE 2026", "2026-02-24", "EXPO CENTER NORTE", "APS FEIRAS"),
            ("FESTIVAL MOTO BRASIL", "16 A 18 DE OUTUBRO DE 2026", "2026-09-16", "RIO CENTRO", "Q4 EVENTOS"),
            ("FIEE", "14 A 17 DE SETEMBRO DE 2027", "2027-08-14", "SÃO PAULO EXPO", "RX GLOBAL"),
            ("FIPAN", "21 A 24 DE JULHO DE 2026", "2026-06-21", "EXPO CENTER NORTE", "SEVEN - SINDIPAN"),
            ("FISP", "06 A 08 DE OUTUBRO DE 2026", "2026-09-06", "SÃO PAULO EXPO", "FIERA MILANO"),
            ("FISPAL FOOD SERVICE", "26 A 29 DE MAIO DE 2026", "2026-04-26", "DISTRITO ANHEMBI", "INFORMA MARKETS"),
            ("FISPAL TECNOLOGIA", "26 A 29 DE MAIO DE 2026", "2026-04-26", "DISTRITO ANHEMBI", "INFORMA MARKETS"),
            ("FORMÓBILE", "30 DE JUNHO A 03 DE JULHO DE 2026", "2026-05-30", "SÃO PAULO EXPO", "INFORMA EXHIBITIONS"),
            ("FUTURE PRINT", "14 A 17 DE JULHO DE 2026", "2026-06-14", "DISTRITO ANHEMBI", "INFORMA MARKETS"),
            ("FUTURECOM", "06 a 08 DE OUTUBRO DE 2026", "2026-09-06", "SÃO PAULO EXPO", "INFORMA"),
            ("GOTEX SHOW", "23 A 25 DE SETEMBRO DE 2026", "2026-08-23", "EXPO CENTER NORTE", "OITOCOM"),
            ("GSC - GLOBAL SPINE CONGRESS", "", "", "WINDSOR EXPO CONVENTION CENTER - WECC", "GSC - GLOBAL SPINE CONGRESS"),
            ("HOME SHOW BRAZIL", "03 A 05 DE AGOSTO DE 2027", "2027-07-03", "DISTRITO ANHEMBI", "PROPÓRTIO PROMOÇÕES E EVENTOS"),
            ("HOSPITALAR", "19 A 22 DE MAIO DE 2026", "2026-04-19", "SÃO PAULO EXPO", "INFORMA MARKETS"),
            ("IFAT BRASIL", "23 A 25 DE JUNHO DE 2027", "2027", "SÃO PAULO EXPO", "MESSE MÜNCHEN"),
            ("IN-COSMETICS LATIN AMERICA", "23 A 24 DE SETEMBRO DE 2026", "2026-08-23", "EXPO CENTER NORTE", "REED"),
            ("INTERPLAST", "25 A 28 DE AGOSTO DE 2026", "2026-07-25", "EXPOVILLE", "MESSE BRAZIL"),
            ("INTERSOLAR SOUTH AMERICA", "25 A 27 DE AGOSTO DE 2026", "2026-07-25", "EXPO CENTER NORTE", "INTERSOLAR SOUTH AMERICA"),
            ("INTRA-LOG", "15 A 17 DE SETEMBRO DE 2026", "2026-08-15", "EXPO CENTER NORTE", "INTERLINK EXHIBITIONS"),
            ("JPR - JORNADA PAULISTA DE RADIOLOGIA", "30 DE ABRIL A 03 DE MAIO DE 2026", "2026-03-30", "TRANSAMERICA EXPO CENTER", "SPR - SOCIEDADE PAULISTA DE RADIOLOGIA E DIAGNÓSTICO POR IMAGEM"),
            ("M&T EXPO", "16 A 19 DE NOVEMBRO DE 2027", "2027", "SÃO PAULO EXPO", "MESSE MÜNCHEN"),
            ("MACKENZIE", "", "", "", "EVENTO INTERNO"),
            ("MERCOPAR", "20 A 23 DE OUTUBRO DE 2026", "2026-09-20", "CENTRO DE FEIRAS E EVENTOS FESTA DA UVA", "SEBRAE RS"),
            ("MOVIMAT", "09 A 13 NOVEMBRO DE 2026", "2026-10-09", "SÃO PAULO EXPO", "RX GLOBAL"),
            ("NT EXPO", "19 A 21 DE OUTUBRO DE 2027", "2027", "DISTRITO ANHEMBI", "INFORMA MARKETS"),
            ("OTC BRASIL - OFFSHORE TECHNOLOGY CONFERENCE", "-", "-", "EXPORIO", "IBP - INSTITUTO BRASILEIRO DE PETRÓLEO E GÁS"),
            ("PLÁSTICO BRASIL", "15 A 19 DE MARÇO DE 2027", "2027", "SÃO PAULO EXPO", "INFORMA MARKETS"),
            ("PUERI EXPO", "26 A 28 DE ABRIL DE 2026", "2026-03-26", "EXPO CENTER NORTE", "KOELNMESSE LTDA"),
            ("RIOPARTS", "29 A 02 DE OUTUBRO DE 2027", "2027", "EXPO MAG", "DIRETRIZ FEIRAS E EVENTOS"),
            ("SET EXPO", "17 A 20 DE AGOSTO DE 2026", "2026-08-01", "DISTRITO ANHEMBI", "SET COMUNICAÇÃO"),
            ("THE SMARTER E SOUTH AMERICA", "25 A 27 DE AGOSTO DE 2026", "2026-07-25", "EXPO CENTER NORTE", "SOLAR PROMOTION INTERNATIONAL GMBH"),
            ("TUBOTECH", "27 A 29 DE OUTUBRO DE 2027", "2027-09-29", "SÃO PAULO EXPO", "FIERA MILANO"),
            ("UFC RIO", "-", "-", "FARMASI ARENA", "UFC"),
            ("WINE TRADE FAIR", "26 A 28 DE MAIO DE 2026", "2026-04-26", "EXPO CENTER NORTE", "MARKETPRESS"),
            ("WIRE BRASIL", "27 A 29 DE OUTUBRO DE 2027", "2027", "SÃO PAULO EXPO", "FIERA MILANO"),
            ("IMCAS Americas", "13 A 15 DE MARÇO DE 2026", "2026-02-13", "", "IMCAS"),
            ("MACAÉ Energy", "17 A 19 DE MARÇO DE 2026", "2026-02-17", "Centro de Convenções Jornalista Roberto Marinho", "FIRJAN"),
            ("Febratex", "18 A 21 DE AGOSTO DE 2026", "2026-09-18", "", "Fcem"),
            ("SIAVS", "04 A 06 DE AGOSTO DE 2026", "2026-07-04", "DISTRITO ANHEMBI", "ABPA"),
            ("Lat.Bus", "11 A 13 DE AGOSTO DE 2026", "2026-07-11", "SÃO PAULO EXPO", "OTM Editora"),
            ("Movelsul", "17 A 20 DE AGOSTO DE 2026", "2026-07-17", "Parque de Eventos de Bento Gonçalves", "Sindmóveis"),
            ("Rog.E", "21 A 24 DE SETEMBRO DE 2026", "2026-08-21", "RIO CENTRO", "IBP - INSTITUTO BRASILEIRO DE PETRÓLEO E GÁS"),
            ("PNEU SHOW", "23 A 25 DE JUNHO DE 2026", "2026-05-23", "EXPO CENTER NORTE", "FRANCAL FEIRAS"),
            ("PAVING EXPO", "22 A 24 DE SETEMBRO DE 2026", "2026-09-22", "DISTRITO ANHEMBI", "STO Feiras e Eventos"),
            ("FESQUA", "09 A 12 DE SETEMBRO DE 2026", "2026-09-09", "SÃO PAULO EXPO", "IEG EXPO BRASIL"),
            ("PET SOUTH AMERICA", "12 A 14 DE AGOSTO DE 2026", "2026-07-09", "DISTRITO ANHEMBI", "NURNBERG MESSE"),
            ("SBPC - Congresso Brasileiro de Patologia Clínica e Medicina Laboratorial", "15 A 18 DE SETEMBRO DE 2026", "2026-08-15", "CentroSul - Centro de Convenções de Florianópolis", "SBPC ML"),
            ("Data Center World Brasil", "06 A 08 DE OUTUBRO DE 2026", "2026-09-06", "SÃO PAULO EXPO", "INFORMA"),
            ("YIWU FAIR", "04 A 06 DE NOVEMBRO DE 2026", "2026-10-04", "EXPO CENTER NORTE", "Yiwu Fair"),
            ("FENATRAN", "09 A 13 DE NOVEMBRO DE 2026.", "2026-10-09", "SÃO PAULO EXPO", "RX GLOBAL"),
            ("WORLD CONFERENCE ON LUNG HEALTH", "17 A 20 DE NOVEMBRO DE 2026", "2026-10-17", "WINDSOR EXPO CONVENTION CENTER - WECC", "THE UNION")
        ]
        c.executemany('''
            INSERT INTO tabela_feiras (nome, data_feira, deadline, local, organizador)
            VALUES (?, ?, ?, ?, ?)
        ''', feiras_iniciais)

    # 7. Tabela de Locais de Entrega / Centros de Exposições
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabela_locais_entrega (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            endereco TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    count_locais = c.execute("SELECT COUNT(*) FROM tabela_locais_entrega").fetchone()[0]
    if count_locais == 0:
        locais_iniciais = [
            ("NFT LOGISTICS LTDA", "AV. DR. GASTAO VIDIGAL, 1132 SALA 910 TORRE B - VILA LEOPOLDINA CEP: 05314-000 - SÃO PAULO-SP"),
            ("MULTILOG BARUERI", "AV. TAMBORÉ,1476 - ALPHAVILLE CEP: 04329-900 - BARUERI - SP"),
            ("SÃO PAULO EXPO", "RODOVIA DOS IMIGRANTES KM 1,5, SN - VILA AGUA FUNDA CEP: 04329-900 - SÃO PAULO-SP"),
            ("TRANSAMERICA EXPO CENTER", "AV. DR. MÁRIO VILAS BOAS RODRIGUES, 387 - SANTO AMARO CEP: 04757-020 - SÃO PAULO-SP"),
            ("DISTRITO ANHEMBI", "AV. OLAVO FONTOURA, 1209 - SANTANA CEP: 02012-021 - SÃO PAULO-SP"),
            ("RIO CENTRO", "R. PEDRO CALMON, SN - JACAREPAGUA CEP: 22780-160 - RIO DE JANEIRO-RJ"),
            ("EXPO CENTER NORTE", "R. JOSÉ BERNARDO PINTO, 333 - VILA GUILHERME CEP 0255-000 - SÃO PAULO-SP"),
            ("PRO MAGNO", "R. SAMARITÁ, 230 - CASA VERDE CEP 02518-080 - SÃO PAULO-SP"),
            ("CENTRO DE CONVENÇÕES FREI CANECA", "R. FREI CANECA, 569 - CONSOLAÇÃO CEP: 01307-001 - SÃO PAULO-SP"),
            ("AGRISHOW", "RODOVIA PREFEIRO ANTÔNIO DUARTE NOGUEIRA KM 321 - RIBEIRÃO PRETO CEP 14032-800 - RIBEIRÃO PRETO-SP"),
            ("EXPO MAG", "R. BEATRIZ LARRAGOITI LUCAS, S/N - CIDADE NOVA CEP: 20211-175 - RIO DE JANEIRO-RJ"),
            ("WINDSOR EXPO CONVENTION CENTER - WECC", "AV. LÚCIO COSTA, 2630 - BARRA DA TIJUCA CEP 20031-204 - RIO DE JANEIRO-RJ"),
            ("CENTRO DE FEIRAS E EVENTOS FESTA DA UVA", "R. LUDOVICO CAVINATO, 1431 - B. N. SRA. DA SAUDE CEP: 95032-620 CAXIAS DO SUL-RS"),
            ("EXPOVILLE", "R. XV DE NOVEMBRO, 4315 - GLORIA CEP: 89216-201 - JOINVILLE-SC"),
            ("AMPE BLUMENAU", "R. HUMBERTO DE CAMPOS, 245 - SALA 01 - BAIRRO VELHA CEP: 89036-050 - BLUMENAU-SC"),
            ("MEMORIAL DA AMERICA LATINA", "AV. MÁRIO DE ANDRADE, 664 - BARRA FUNDA CEP: 01156-001 SÃO PAULO-SP"),
            ("EXPORIO", "R. BEATRIZ LARRAGOITI LUCAS, S/N - CIDADE NOVA CEP: 20211-175 - RIO DE JANEIRO-RJ"),
            ("FARMASI ARENA", "AV. EMBAIXADOR ABELARDO BUENO, 3401 - BARRA OLÍMPICA, RIO DE JANEIRO - RJ, 22775-040"),
            ("RIO DE JANEIRO", "RIO DE JANEIRO-RJ"),
            ("CENTRO DE CONVENÇÕES JORNALISTA ROBERTO MARINHO", "RJ-106 - SÃO JOSÉ DO BARRETO, MACAÉ - RJ"),
            ("Parque de Eventos de Bento Gonçalves", "Alameda Fenavinho, 481"),
            ("CentroSul - Centro de Convenções de Florianópolis", "Av. Gustavo Richard, 850 - Centro, Florianópolis - SC, 88010-290")
        ]
        c.executemany('''
            INSERT OR IGNORE INTO tabela_locais_entrega (nome, endereco)
            VALUES (?, ?)
        ''', locais_iniciais)

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()

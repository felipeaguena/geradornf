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

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()

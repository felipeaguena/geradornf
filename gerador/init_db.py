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

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()

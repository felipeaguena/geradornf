import sqlite3
import json
import os
import shutil

def atualizar_banco_e_arquivos():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'database.db')
    bak_path = os.path.join(base_dir, 'database.db.bak')
    json_path = os.path.join(base_dir, 'Tabela_NCM_Unificada.json')

    print("1. Criando backup de segurança do banco de dados...")
    shutil.copy2(db_path, bak_path)
    print(f"Backup criado em: {bak_path}")

    print("2. Atualizando alíquotas PIS/COFINS de Importação no SQLite...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Atualizar ncm
    c.execute("""
        UPDATE ncm
        SET aliquota_pis = 2.1,
            aliquota_cofins = 9.65,
            regime_pis_cofins = 'Regime Geral de Importação (Lei 10.865/2004, Art. 8º)'
        WHERE aliquota_pis = 1.65 AND aliquota_cofins = 7.6
    """)
    ncm_alterados = c.rowcount
    print(f"Total de registros NCM atualizados para PIS 2.1% e COFINS 9.65%: {ncm_alterados}")

    # Atualizar operação padrão de Entrada por Importação Tributada (OUTRAS ENTRADAS DE MERCADORIA - CFOP 3949)
    c.execute("""
        UPDATE tipos_operacao
        SET p_pis = 2.10, p_cofins = 9.65
        WHERE nome_operacao LIKE '%OUTRAS ENTRADAS%' OR cfop_padrao = '3949'
    """)
    op_alteradas = c.rowcount
    print(f"Operações tributadas atualizadas em tipos_operacao: {op_alteradas}")

    conn.commit()
    conn.close()

    print("3. Atualizando Tabela_NCM_Unificada.json...")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        itens_json_alterados = 0
        for item in data.get('Nomenclaturas', []):
            if item.get('Aliquota_PIS') == 1.65 and item.get('Aliquota_COFINS') == 7.6:
                item['Aliquota_PIS'] = 2.1
                item['Aliquota_COFINS'] = 9.65
                item['Regime_PIS_COFINS'] = 'Regime Geral de Importação (Lei 10.865/2004, Art. 8º)'
                itens_json_alterados += 1

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Total de registros alterados no JSON: {itens_json_alterados}")

    print("4. Regenerando Tabela_NCM_Completa_Backup.xlsx com as novas alíquotas...")
    import exportar_ncm_excel
    exportar_ncm_excel.exportar_ncm_excel()

    print("\nAtualizacao completa concluida com sucesso!")

if __name__ == '__main__':
    atualizar_banco_e_arquivos()

import xml.etree.ElementTree as ET
import random
import sys
import os

def calcular_cdv(chave_43):
    """Calcula o digito verificador (cDV) da Chave de Acesso usando Modulo 11 SEFAZ."""
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    idx_peso = 0
    for digito in reversed(chave_43):
        soma += int(digito) * pesos[idx_peso]
        idx_peso = (idx_peso + 1) % len(pesos)
    resto = soma % 11
    if resto == 0 or resto == 1:
        return 0
    else:
        return 11 - resto

def atualizar_numero_nfe(xml_origem, xml_destino, novo_numero, nova_serie=1):
    """
    Atualiza o nNF, serie, cNF, cDV e Id na tag infNFe para permitir importar no Sebrae
    sem conflito de numeracao.
    """
    if not os.path.exists(xml_origem):
        print(f"ERRO: Arquivo de origem '{xml_origem}' nao foi encontrado.")
        return False

    ET.register_namespace('', 'http://www.portalfiscal.inf.br/nfe')
    tree = ET.parse(xml_origem)
    root = tree.getroot()
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    inf_nfe = root.find('nfe:infNFe', ns)
    if inf_nfe is None:
        inf_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
    
    if inf_nfe is None:
        print("ERRO: Nao foi possivel encontrar a tag <infNFe> no XML.")
        return False

    ide = inf_nfe.find('nfe:ide', ns) or inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}ide')
    emit = inf_nfe.find('nfe:emit', ns) or inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}emit')
    
    # Extrai dados necessarios para montar a Chave de Acesso de 44 digitos
    c_uf = ide.find('{http://www.portalfiscal.inf.br/nfe}cUF').text.strip().zfill(2)
    dh_emi = ide.find('{http://www.portalfiscal.inf.br/nfe}dhEmi').text.strip()
    aamm = dh_emi[2:4] + dh_emi[5:7] # AAMM a partir da data de emissao
    
    cnpj_elem = emit.find('{http://www.portalfiscal.inf.br/nfe}CNPJ')
    cpf_elem = emit.find('{http://www.portalfiscal.inf.br/nfe}CPF')
    doc_emit = (cnpj_elem.text if cnpj_elem is not None else cpf_elem.text).strip().zfill(14)
    
    mod = ide.find('{http://www.portalfiscal.inf.br/nfe}mod').text.strip().zfill(2)
    
    # Atualiza Serie e nNF
    ide.find('{http://www.portalfiscal.inf.br/nfe}serie').text = str(nova_serie)
    ide.find('{http://www.portalfiscal.inf.br/nfe}nNF').text = str(novo_numero)
    serie_fmt = str(nova_serie).zfill(3)
    nnf_fmt = str(novo_numero).zfill(9)
    
    # Gera novo cNF aleatorio de 8 digitos
    novo_cnf = str(random.randint(10000000, 99999999))
    ide.find('{http://www.portalfiscal.inf.br/nfe}cNF').text = novo_cnf
    
    tp_emis = ide.find('{http://www.portalfiscal.inf.br/nfe}tpEmis').text.strip()
    
    # Monta os 43 digitos e calcula o DV
    chave_43 = f"{c_uf}{aamm}{doc_emit}{mod}{serie_fmt}{nnf_fmt}{tp_emis}{novo_cnf}"
    cdv = calcular_cdv(chave_43)
    ide.find('{http://www.portalfiscal.inf.br/nfe}cDV').text = str(cdv)
    
    # Atualiza o atributo Id
    inf_nfe.set('Id', f"NFe{chave_43}{cdv}")
    
    tree.write(xml_destino, encoding='UTF-8', xml_declaration=True)
    print("=" * 60)
    print(f" SUCESSO: NF-e Numero {novo_numero} gerada com sucesso!")
    print(f" Arquivo de saida : {xml_destino}")
    print(f" Nova Chave SEFAZ : NFe{chave_43}{cdv}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        arquivo_origem = sys.argv[1]
        numero_nf = int(sys.argv[2])
        arquivo_destino = sys.argv[3] if len(sys.argv) >= 4 else f"nfe_numero_{numero_nf}.xml"
    else:
        print("--- GERADOR DE CHAVE E NUMERACAO NF-E SEBRAE ---")
        arquivo_origem = input("Digite o nome do seu arquivo XML de origem: ").strip()
        numero_nf = int(input("Digite o numero da NF-e que deseja gerar: ").strip())
        arquivo_destino = input("Digite o nome do arquivo de saida (Enter para padrao): ").strip()
        if not arquivo_destino:
            arquivo_destino = f"nfe_numero_{numero_nf}.xml"

    atualizar_numero_nfe(arquivo_origem, arquivo_destino, numero_nf)

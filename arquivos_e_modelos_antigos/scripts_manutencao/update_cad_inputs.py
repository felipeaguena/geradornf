def update_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()
        
    c = c.replace('id="cad_fone" placeholder="Ex: 11999999999"', 'id="cad_fone" class="form-control form-control-sm mask-telefone" placeholder="(00) 00000-0000"')
    c = c.replace('id="cad_cnpj_cpf"', 'id="cad_cnpj_cpf" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00"')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

update_file('templates/empresas.html')

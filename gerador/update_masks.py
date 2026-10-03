import re

def update_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()
        
    c = c.replace('id="emit_CNPJ"', 'id="emit_CNPJ" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00"')
    c = c.replace('id="dest_CNPJ_CPF"', 'id="dest_CNPJ_CPF" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00"')
    c = c.replace('id="transp_CNPJ_CPF"', 'id="transp_CNPJ_CPF" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00"')
    
    # fix duplicate classes if any
    c = c.replace('class="form-control form-control-sm" class="form-control form-control-sm mask-cnpj-cpf"', 'class="form-control form-control-sm mask-cnpj-cpf"')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

update_file('templates/index.html')
update_file('templates/di_duimp.html')

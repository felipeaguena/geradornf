import re

def fix_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()

    # Fix duplicate classes on dest_CNPJ_CPF
    c = c.replace('<input type="text" class="form-control form-control-sm" id="dest_CNPJ_CPF" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00">',
                  '<input type="text" class="form-control form-control-sm mask-cnpj-cpf" id="dest_CNPJ_CPF" placeholder="00.000.000/0000-00">')
    
    # Fix duplicate classes on transp_CNPJ_CPF
    c = c.replace('<input type="text" class="form-control form-control-sm" id="transp_CNPJ_CPF" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00">',
                  '<input type="text" class="form-control form-control-sm mask-cnpj-cpf" id="transp_CNPJ_CPF" placeholder="00.000.000/0000-00">')
                  
    # Fix indIEDest options
    c = c.replace('<option value="1">1 - Contribuinte ICMS</option>', '<option value="1">Contribuinte</option>')
    c = c.replace('<option value="2">2 - Contribuinte ISENTO</option>', '<option value="2">Isento de Contribuição</option>')
    c = c.replace('<option value="9" selected>9 - Não Contribuinte</option>', '<option value="9" selected>Não Contribuinte</option>')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

fix_file('templates/index.html')
fix_file('templates/di_duimp.html')

import re

def update_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()
        
    c = c.replace('id="emit_fone"', 'id="emit_fone" class="form-control form-control-sm mask-telefone" placeholder="(00) 00000-0000"')
    c = c.replace('id="dest_fone"', 'id="dest_fone" class="form-control form-control-sm mask-telefone" placeholder="(00) 00000-0000"')
    c = c.replace('id="transp_fone"', 'id="transp_fone" class="form-control form-control-sm mask-telefone" placeholder="(00) 00000-0000"')
    
    # In index.html/di_duimp, the phone might be dest_fone / emit_fone but let's check what IDs they have.
    # Actually, the user asked for CNPJ/CPF everywhere, but for phone: "o telefone em todos os campos do site que precisam dele, tenham o mesmo padrão tanto de placeholder quando de pattern"
    # Wait, does index.html have phone fields?
    
    # fix duplicate classes if any
    c = c.replace('class="form-control form-control-sm" class="form-control form-control-sm mask-', 'class="form-control form-control-sm mask-')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

update_file('templates/index.html')
update_file('templates/di_duimp.html')

import re

def update_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()
        
    c = c.replace(
        '<input type="text" class="form-control form-control-sm" id="cad_cnpj_cpf" class="form-control form-control-sm mask-cnpj-cpf" placeholder="00.000.000/0000-00">',
        '<input type="text" class="form-control form-control-sm mask-cnpj-cpf" id="cad_cnpj_cpf" placeholder="00.000.000/0000-00">'
    )
    c = c.replace(
        '<input type="text" class="form-control form-control-sm" id="cad_fone" class="form-control form-control-sm mask-telefone" placeholder="(00) 00000-0000">',
        '<input type="text" class="form-control form-control-sm mask-telefone" id="cad_fone" placeholder="(00) 00000-0000">'
    )
    
    # Insert cad_apelido
    c = c.replace(
        '<div class="col-md-5">\n                                        <label class="form-label small fw-bold">Nome / Razão Social</label>\n                                        <input type="text" class="form-control form-control-sm" id="cad_nome" required>\n                                    </div>',
        '<div class="col-md-5">\n                                        <label class="form-label small fw-bold">Nome / Razão Social</label>\n                                        <input type="text" class="form-control form-control-sm" id="cad_nome" required>\n                                    </div>\n                                    <div class="col-md-4">\n                                        <label class="form-label small fw-bold">Apelido</label>\n                                        <input type="text" class="form-control form-control-sm" id="cad_apelido" placeholder="Nome Fantasia / Apelido">\n                                    </div>'
    )
    
    # Insert cad_ind_ie
    c = c.replace(
        '<div class="col-md-4">\n                                        <label class="form-label small fw-bold">Inscrição Estadual</label>\n                                        <input type="text" class="form-control form-control-sm" id="cad_ie">\n                                    </div>',
        '<div class="col-md-4">\n                                        <label class="form-label small fw-bold">Inscrição Estadual</label>\n                                        <input type="text" class="form-control form-control-sm" id="cad_ie">\n                                    </div>\n                                    <div class="col-md-4">\n                                        <label class="form-label small fw-bold">Ind. IE</label>\n                                        <select class="form-select form-select-sm" id="cad_ind_ie">\n                                            <option value="1">Contribuinte</option>\n                                            <option value="2">Isento de Contribuição</option>\n                                            <option value="9">Não Contribuinte</option>\n                                        </select>\n                                    </div>'
    )
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

update_file('templates/empresas.html')

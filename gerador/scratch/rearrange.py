import re

def reformat_html(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()
        
    # --- 1. Rename tab "Cabeçalho & Operação" to "Operação" ---
    html = html.replace('1. Cabeçalho &amp; Operação', '1. Operação')
    
    # --- 2. Create the "Identificação" tab in the nav menu ---
    # Find the position of the cabecalho tab item to insert the new one after it
    tab_itens_idx = html.find('<li class="nav-item" role="presentation">\n                    <button class="nav-link" id="itens-tab"')
    
    tab_identificacao_html = '''<li class="nav-item" role="presentation">
                    <button class="nav-link" id="identificacao-tab" data-bs-toggle="tab" data-bs-target="#identificacao" type="button" role="tab">
                        <i data-lucide="contact"></i> Identificação
                    </button>
                </li>
                '''
    html = html[:tab_itens_idx] + tab_identificacao_html + html[tab_itens_idx:]
    
    # --- 3. Extract blocks ---
    
    def extract_block(html, start_marker, end_marker_count, tag='<div'):
        """Extracts a block from html starting with start_marker."""
        start_idx = html.find(start_marker)
        if start_idx == -1: return "", html
        
        # We need to find the matching closing tag
        idx = start_idx
        open_tags = 0
        started = False
        
        while idx < len(html):
            if html.startswith(tag, idx):
                open_tags += 1
                started = True
            elif html.startswith('</div', idx):
                open_tags -= 1
                
            if started and open_tags == 0:
                end_idx = html.find('>', idx) + 1
                block = html[start_idx:end_idx]
                html = html[:start_idx] + html[end_idx:]
                return block, html
            
            idx += 1
        return "", html
        
    # Extract EMITENTE
    emitente_start = '<!-- EMITENTE -->'
    emitente_block, html = extract_block(html, emitente_start, 0)
    
    # Extract DESTINATÁRIO
    destinatario_start = '<!-- DESTINATÁRIO -->'
    destinatario_block, html = extract_block(html, destinatario_start, 0)
    
    # Extract TRANSPORTE
    transporte_start = '<!-- TRANSPORTE E VOLUMES -->'
    transporte_block, html = extract_block(html, transporte_start, 0)
    
    # Extract TOTAIS DA NOTA FISCAL
    totais_start = '<!-- TOTAIS DA NOTA FISCAL (CÁLCULO DINÂMICO) -->'
    totais_block, html = extract_block(html, totais_start, 0)

    # --- 4. Split TRANSPORTE into Transporte (Identificação) and Volumes (Operação) ---
    # The volumes inputs are: transp_qVol, transp_esp, transp_pesoL, transp_pesoB
    # We will slice the transporte_block to extract the row containing these.
    # We can use regex to find the volume cols and move them out.
    
    # In index.html, these are typically cols like <div class="col-md-2"> ... transp_qVol ... </div>
    # Let's extract the HTML for the 4 volume inputs. 
    vol_pattern = r'(<div class="col-md-[0-3]">\s*<label[^>]*>Qtd\. Volumes \(qVol\).*?</label>\s*<input[^>]*id="transp_qVol"[^>]*>\s*</div>)'
    esp_pattern = r'(<div class="col-md-[0-3]">\s*<label[^>]*>Espécie.*?</label>\s*<input[^>]*id="transp_esp"[^>]*>\s*</div>)'
    pesoL_pattern = r'(<div class="col-md-[0-3]">\s*<label[^>]*>Peso Líq.*?</label>\s*<input[^>]*id="transp_pesoL"[^>]*>\s*</div>)'
    pesoB_pattern = r'(<div class="col-md-[0-3]">\s*<label[^>]*>Peso Bruto.*?</label>\s*<input[^>]*id="transp_pesoB"[^>]*>\s*</div>)'
    
    qVol = re.search(vol_pattern, transporte_block, re.DOTALL)
    esp = re.search(esp_pattern, transporte_block, re.DOTALL)
    pesoL = re.search(pesoL_pattern, transporte_block, re.DOTALL)
    pesoB = re.search(pesoB_pattern, transporte_block, re.DOTALL)
    
    volumes_html = ""
    if qVol:
        volumes_html += qVol.group(1) + "\n"
        transporte_block = transporte_block.replace(qVol.group(1), '')
    if esp:
        volumes_html += esp.group(1) + "\n"
        transporte_block = transporte_block.replace(esp.group(1), '')
    if pesoL:
        volumes_html += pesoL.group(1) + "\n"
        transporte_block = transporte_block.replace(pesoL.group(1), '')
    if pesoB:
        volumes_html += pesoB.group(1) + "\n"
        transporte_block = transporte_block.replace(pesoB.group(1), '')

    volumes_section = f'''
    <!-- VOLUMES E PESOS -->
    <div class="col-12 mt-3">
        <div class="card shadow-sm border">
            <div class="card-header bg-light py-2 fw-bold text-secondary">
                <i data-lucide="package"></i> Volumes e Pesos
            </div>
            <div class="card-body py-2">
                <div class="row g-2">
                    {volumes_html}
                </div>
            </div>
        </div>
    </div>
    '''
    
    # Insert select components inside Emitente, Destinatario and Transportadora
    emitente_select = '''
    <div class="col-12 mb-3 border-bottom pb-2">
        <label class="form-label small fw-bold text-primary">Preencher Dados do Emitente a partir do Cadastro</label>
        <select class="form-select form-select-sm" id="select_emitente" onchange="preencherDadosDeCadastro(this, 'emit')">
            <option value="">Selecione uma empresa (Emitente)...</option>
        </select>
    </div>
    '''
    emitente_block = emitente_block.replace('<div class="row g-2">', '<div class="row g-2">\n' + emitente_select)
    
    destinatario_select = '''
    <div class="col-12 mb-3 border-bottom pb-2">
        <label class="form-label small fw-bold text-primary">Preencher Dados do Destinatário a partir do Cadastro</label>
        <select class="form-select form-select-sm" id="select_destinatario" onchange="preencherDadosDeCadastro(this, 'dest')">
            <option value="">Selecione uma empresa (Cliente)...</option>
        </select>
    </div>
    '''
    destinatario_block = destinatario_block.replace('<div class="row g-2">', '<div class="row g-2">\n' + destinatario_select)

    transporte_select = '''
    <div class="col-12 mb-3 border-bottom pb-2">
        <label class="form-label small fw-bold text-primary">Preencher Dados da Transportadora a partir do Cadastro</label>
        <select class="form-select form-select-sm" id="select_transportadora" onchange="preencherDadosDeCadastro(this, 'transp')">
            <option value="">Selecione uma transportadora...</option>
        </select>
    </div>
    '''
    transporte_block = transporte_block.replace('<div class="row g-2">', '<div class="row g-2">\n' + transporte_select)


    # --- 5. Assemble Identificação Tab ---
    identificacao_tab_content = f'''
    <div class="tab-pane fade" id="identificacao" role="tabpanel">
        <div class="row">
            {emitente_block}
            {destinatario_block}
        </div>
        <div class="row mt-3">
            {transporte_block}
        </div>
    </div>
    '''
    
    # Insert the new Identificacao tab right after Operacao tab closes.
    # Operacao tab ends before `<div class="tab-pane fade" id="itens" role="tabpanel">`
    itens_pane_idx = html.find('<div class="tab-pane fade" id="itens" role="tabpanel">')
    html = html[:itens_pane_idx] + identificacao_tab_content + "\n" + html[itens_pane_idx:]
    
    # Move volumes to Cabecalho (Operação)
    # The cabecalho tab is `<div class="tab-pane fade show active" id="cabecalho" role="tabpanel">`
    # Let's just append it to the end of Operação, before the end of its div.
    # Or find where INFCPL is and put it before INFCPL.
    infcpl_idx = html.find('<!-- INFORMAÇÕES COMPLEMENTARES -->')
    if infcpl_idx != -1:
        html = html[:infcpl_idx] + volumes_section + "\n" + html[infcpl_idx:]
    
    # Totais da Nota to Itens da Nota
    # Insert it right after the itens pane opening.
    itens_body_idx = html.find('<div class="tab-pane fade" id="itens" role="tabpanel">')
    if itens_body_idx != -1:
        insert_idx = html.find('>', itens_body_idx) + 1
        html = html[:insert_idx] + "\n" + totais_block + "\n" + html[insert_idx:]

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
        
reformat_html('templates/index.html')
reformat_html('templates/di_duimp.html')

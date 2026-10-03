import sys
import re

def reformat_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Rename tab "1. Cabeçalho & Operação" to "1. Operação"
    html = html.replace('1. Cabeçalho &amp; Operação', '1. Operação')
    
    # 2. Add "Identificação" tab
    tab_itens_pattern = r'(<li class="nav-item" role="presentation">\s*<button class="nav-link" id="itens-tab")'
    identificacao_tab_html = '''<li class="nav-item" role="presentation">
                    <button class="nav-link" id="identificacao-tab" data-bs-toggle="tab" data-bs-target="#identificacao" type="button" role="tab">
                        <i data-lucide="contact"></i> 2. Identificação
                    </button>
                </li>
                '''
    html = re.sub(tab_itens_pattern, identificacao_tab_html + r'\1', html)
    
    # Also rename "2. Itens da Nota" to "3. Itens da Nota"
    html = html.replace('2. Itens da Nota', '3. Itens da Nota')
    html = html.replace('3. Rodapé &amp; Totais', '4. Rodapé &amp; Totais')
    html = html.replace('4. Tipo de Nota (Impostos)', '5. Tipo de Nota (Impostos)')
    
    # Function to extract a block based on its starting signature
    def extract_div(html, signature):
        start_idx = html.find(signature)
        if start_idx == -1: return "", html
        
        div_start = html.rfind('<div', 0, html.find('>', start_idx))
        if div_start == -1 or html.find('>', start_idx) - div_start > 500:
            div_start = html.find('<div', start_idx)
            
        open_tags = 0
        idx = div_start
        started = False
        
        while idx < len(html):
            if html.startswith('<div', idx):
                open_tags += 1
                started = True
                idx += 4
            elif html.startswith('</div', idx):
                open_tags -= 1
                idx += 5
            else:
                idx += 1
                
            if started and open_tags == 0:
                end_idx = html.find('>', idx) + 1
                block = html[div_start:end_idx]
                return block, html[:div_start] + html[end_idx:]
                
        return "", html

    # Extract Emitente
    emit_sig = '<span>Dados do Emitente</span>'
    emitente_block, html = extract_div(html, emit_sig)

    # Extract Destinatário
    dest_sig = '<span>Dados do Destinatário</span>'
    destinatario_block, html = extract_div(html, dest_sig)
    
    # Extract Transporte
    transp_sig = '<span>Dados do Transporte e Volumes</span>'
    transporte_block, html = extract_div(html, transp_sig)
    
    # Extract Informações Complementares
    infcpl_sig = '<span>Informações Complementares / Observações da Nota (infCpl)</span>'
    infcpl_block, html = extract_div(html, infcpl_sig)
    
    # Extract Totais
    totais_sig = '<span>Totais da Nota Fiscal'
    totais_block, html = extract_div(html, totais_sig)

    def extract_col(name, block):
        pattern = r'(<div class="col-md-[0-9]+">\s*<label[^>]*>.*?</label>\s*<input[^>]*id="' + name + r'"[^>]*>\s*</div>)'
        m = re.search(pattern, block, re.DOTALL)
        if m:
            col_html = m.group(1)
            return col_html, block.replace(col_html, '')
        return "", block
    
    qvol_html, transporte_block = extract_col('transp_qVol', transporte_block)
    esp_html, transporte_block = extract_col('transp_esp', transporte_block)
    pesol_html, transporte_block = extract_col('transp_pesoL', transporte_block)
    pesob_html, transporte_block = extract_col('transp_pesoB', transporte_block)

    volumes_html = f'''
    <div class="col-12 mt-3">
        <div class="card border">
            <div class="card-header bg-light py-2">
                <i data-lucide="package"></i>
                <span class="fw-bold">Volumes e Pesos</span>
            </div>
            <div class="card-body py-2">
                <div class="row g-2">
                    {qvol_html}
                    {esp_html}
                    {pesol_html}
                    {pesob_html}
                </div>
            </div>
        </div>
    </div>
    '''

    def add_select(block, label, id_name, prefix):
        sel_html = f'''
        <div class="col-12 mb-3 border-bottom pb-2">
            <label class="form-label small fw-bold text-primary">{label}</label>
            <select class="form-select form-select-sm" id="{id_name}" onchange="preencherDadosDeCadastro(this, '{prefix}')">
                <option value="">Selecione para preencher automaticamente...</option>
            </select>
        </div>
        '''
        return block.replace('<div class="row g-2">', '<div class="row g-2">\n' + sel_html)
        
    if emitente_block:
        emitente_block = add_select(emitente_block, 'Preencher Dados do Emitente a partir do Cadastro de Empresas', 'select_emitente', 'emit')
    if destinatario_block:
        destinatario_block = add_select(destinatario_block, 'Preencher Dados do Destinatário a partir do Cadastro', 'select_destinatario', 'dest')
    if transporte_block:
        transporte_block = add_select(transporte_block, 'Preencher Dados da Transportadora a partir do Cadastro', 'select_transportadora', 'transp')
    
    identificacao_tab = f'''
        <!-- ABA: IDENTIFICAÇÃO -->
        <div class="tab-pane fade" id="identificacao" role="tabpanel">
            <form id="form-identificacao">
                <div class="row">
                    <div class="col-md-6 mt-3">
                    {emitente_block}
                    </div>
                    <div class="col-md-6 mt-3">
                    {destinatario_block}
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-12">
                        {transporte_block}
                    </div>
                </div>
            </form>
        </div>
    '''
    
    # Place Identificacao Tab before "itens" tab content
    itens_pane_idx = html.find('<div class="tab-pane fade" id="itens" role="tabpanel">')
    html = html[:itens_pane_idx] + identificacao_tab + "\n" + html[itens_pane_idx:]
    
    form_cab_end = html.find('</form>', html.find('id="form-cabecalho"'))
    if form_cab_end != -1:
        html = html[:form_cab_end] + volumes_html + "\n" + infcpl_block + "\n" + html[form_cab_end:]

    planilha_sig = '<span>Planilha de Itens da NF-e (det nItem)</span>'
    planilha_idx = html.rfind('<div class="card', 0, html.find(planilha_sig))
    if planilha_idx != -1:
        html = html[:planilha_idx] + totais_block + "\n<br>\n" + html[planilha_idx:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

reformat_file('templates/index.html')
reformat_file('templates/di_duimp.html')

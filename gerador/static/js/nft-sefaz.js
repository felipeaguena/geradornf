// nft-sefaz.js
// Funcionalidades de comunicação com o SEFAZ (Certificado, Assinatura e Envio)

async function verificarStatusCertificado() {
    try {
        const response = await fetch('/api/certificado/status');
        const data = await response.json();
        const container = document.getElementById('cert-info-container');
        
        if (data.status === 'success') {
            container.innerHTML = `
                <div class="col-md-6">
                    <div class="small text-muted mb-1">Titular / Assunto</div>
                    <div class="fw-bold font-monospace" style="font-size: 11px;">${data.assunto}</div>
                </div>
                <div class="col-md-6">
                    <div class="small text-muted mb-1">Emissor</div>
                    <div class="fw-bold font-monospace" style="font-size: 11px;">${data.emissor}</div>
                </div>
                <div class="col-md-4 mt-2">
                    <div class="small text-muted mb-1">CNPJ</div>
                    <div class="fw-bold text-success">${data.cnpj || 'N/A'}</div>
                </div>
                <div class="col-md-4 mt-2">
                    <div class="small text-muted mb-1">Validade Inicial</div>
                    <div class="fw-bold">${data.inicio}</div>
                </div>
                <div class="col-md-4 mt-2">
                    <div class="small text-muted mb-1">Validade Final</div>
                    <div class="fw-bold">${data.fim}</div>
                </div>
                <div class="col-12 mt-2">
                    <span class="badge bg-info-subtle text-info fw-bold"><i data-lucide="check-circle" class="me-1"></i> Certificado Válido e Pronto para Uso</span>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger py-2 px-3 mb-0 d-flex align-items-center gap-2">
                        <i data-lucide="alert-triangle"></i>
                        <span>Erro ao carregar certificado: ${data.message}</span>
                    </div>
                </div>
            `;
        }
        lucide.createIcons();
    } catch (e) {
        console.error('Erro na verificação do certificado:', e);
        alert('Ocorreu um erro ao verificar o certificado digital.');
    }
}

async function enviarNfeSefaz(ambiente = 2) {
    // Pegar o XML atual. Pode vir do modal de visualização ou da geração normal.
    if (typeof window.obterXMLFinal === 'function') {
        try {
            // Mostra o loading
            const btnH = document.getElementById('btn-enviar-sefaz');
            const btnP = document.getElementById('btn-enviar-sefaz-prod');
            const originalH = btnH ? btnH.innerHTML : '';
            const originalP = btnP ? btnP.innerHTML : '';
            
            if (btnH && ambiente === 2) {
                btnH.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...`;
                btnH.disabled = true;
            }
            if (btnP && ambiente === 1) {
                btnP.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...`;
                btnP.disabled = true;
            }

            let xmlString = await window.obterXMLFinal();
            if (!xmlString) {
                alert('Erro: Não foi possível obter o XML gerado.');
                return;
            }

            // Força a tag <tpAmb> no XML para o ambiente clicado
            xmlString = xmlString.replace(/<tpAmb>\d+<\/tpAmb>/g, `<tpAmb>${ambiente}</tpAmb>`);

            const chave = document.getElementById('chaveAcessoDisplay')?.value || 'N/A';

            const response = await fetch('/api/sefaz/enviar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    xml: xmlString,
                    chave: chave,
                    tpAmb: ambiente
                })
            });

            const retorno = await response.json();
            
            // Atualizar o histórico
            atualizarTabelaHistorico(retorno, chave, ambiente);

            if (retorno.status === 'success') {
                const isAutorizado = retorno.cstat == '100' || retorno.cstat == '104';
                const msg = isAutorizado ? 'NF-e Autorizada com sucesso!' : `Retorno SEFAZ: ${retorno.cstat} - ${retorno.xmotivo}`;
                const icon = isAutorizado ? 'success' : 'warning';
                
                // Usar Swal se disponivel
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: isAutorizado ? 'Sucesso!' : 'Atenção!',
                        text: msg,
                        icon: icon
                    });
                } else {
                    alert(msg);
                }
            } else {
                alert(`Erro ao comunicar com a SEFAZ: ${retorno.message || retorno.error || 'Erro desconhecido'}`);
            }

        } catch(e) {
            console.error('Erro no envio', e);
            const msg = e.message || 'Falha interna ao tentar enviar a nota para a SEFAZ.';
            atualizarTabelaHistorico({ cstat: 'ERRO', error: msg }, getVal('chaveAcesso') || '-', ambiente);
            alert(msg);
        } finally {
            // Restaura o botao
            const btnH = document.getElementById('btn-enviar-sefaz');
            const btnP = document.getElementById('btn-enviar-sefaz-prod');
            if (btnH) {
                btnH.innerHTML = `<i data-lucide="send"></i><span>Assinar e Enviar NF-e para SEFAZ (Homologação)</span>`;
                btnH.disabled = false;
            }
            if (btnP) {
                btnP.innerHTML = `<i data-lucide="send"></i><span>Assinar e Enviar NF-e para SEFAZ (Produção)</span>`;
                btnP.disabled = false;
            }
            lucide.createIcons();
        }
    } else {
        const msg = 'A função de geração de XML não está disponível ou a nota não está completa.';
        atualizarTabelaHistorico({ cstat: 'ERRO', error: msg }, getVal('chaveAcesso') || '-', ambiente);
        alert(msg);
    }
}

function renderArquivosIcons(chave, isAutorizado) {
    if (!chave || chave === 'N/A' || chave === '-' || chave.trim() === '') {
        return `<span class="text-muted" style="font-size: 11px;">-</span>`;
    }
    
    const chaveLimpa = chave.trim();
    if (isAutorizado) {
        return `
            <div class="d-inline-flex align-items-center justify-content-center gap-1">
                <a href="/api/sefaz/download/pdf/${chaveLimpa}" target="_blank" download="${chaveLimpa}-danfe.pdf" class="btn btn-sm btn-outline-danger p-1 d-inline-flex align-items-center justify-content-center" title="Baixar DANFE (PDF)" style="width: 26px; height: 26px; border-radius: 4px;" onclick="event.stopPropagation();">
                    <i data-lucide="file-text" style="width: 14px; height: 14px;"></i>
                </a>
                <a href="/api/sefaz/download/xml/${chaveLimpa}" target="_blank" download="${chaveLimpa}-nfe.xml" class="btn btn-sm btn-outline-primary p-1 d-inline-flex align-items-center justify-content-center" title="Baixar XML Autorizado" style="width: 26px; height: 26px; border-radius: 4px;" onclick="event.stopPropagation();">
                    <i data-lucide="file-code" style="width: 14px; height: 14px;"></i>
                </a>
                <a href="/api/sefaz/download/zip/${chaveLimpa}" target="_blank" download="${chaveLimpa}-arquivos.zip" class="btn btn-sm btn-outline-warning p-1 d-inline-flex align-items-center justify-content-center" title="Baixar Pacote Completo (ZIP)" style="width: 26px; height: 26px; border-radius: 4px;" onclick="event.stopPropagation();">
                    <i data-lucide="archive" style="width: 14px; height: 14px;"></i>
                </a>
            </div>
        `;
    } else {
        return `
            <div class="d-inline-flex align-items-center justify-content-center gap-1 opacity-50" title="Disponível após autorização da NF-e na SEFAZ">
                <span class="btn btn-sm btn-outline-secondary p-1 d-inline-flex align-items-center justify-content-center disabled" style="width: 26px; height: 26px; border-radius: 4px; cursor: not-allowed; pointer-events: none;">
                    <i data-lucide="file-text" style="width: 14px; height: 14px;"></i>
                </span>
                <span class="btn btn-sm btn-outline-secondary p-1 d-inline-flex align-items-center justify-content-center disabled" style="width: 26px; height: 26px; border-radius: 4px; cursor: not-allowed; pointer-events: none;">
                    <i data-lucide="file-code" style="width: 14px; height: 14px;"></i>
                </span>
                <span class="btn btn-sm btn-outline-secondary p-1 d-inline-flex align-items-center justify-content-center disabled" style="width: 26px; height: 26px; border-radius: 4px; cursor: not-allowed; pointer-events: none;">
                    <i data-lucide="archive" style="width: 14px; height: 14px;"></i>
                </span>
            </div>
        `;
    }
}
window.renderArquivosIcons = renderArquivosIcons;

function atualizarTabelaHistorico(retorno, chave, ambiente = 2) {
    const tbody = document.getElementById('tbody-historico-sefaz');
    if(tbody.querySelector('td[colspan="6"]') || tbody.querySelector('td[colspan="7"]')) {
        tbody.innerHTML = '';
    }

    const tr = document.createElement('tr');
    
    // Cor do cstat e autorização
    const isAutorizado = (retorno.cstat == '100' || retorno.cstat == '104' || retorno.autorizado === true);
    let cstatBadge = 'bg-secondary';
    if(isAutorizado) cstatBadge = 'bg-success';
    else if(retorno.cstat) cstatBadge = 'bg-warning text-dark';

    const now = new Date().toLocaleString('pt-BR');
    const ambienteText = ambiente === 1 ? 'Produção' : 'Homologação';
    const ambienteClass = ambiente === 1 ? 'bg-danger' : 'bg-secondary';
    
    tr.innerHTML = `
        <td>${now}</td>
        <td><span class="badge ${ambienteClass}">${ambienteText}</span></td>
        <td class="text-center align-middle">${renderArquivosIcons(chave, isAutorizado)}</td>
        <td class="text-start" style="font-size: 11px;">${chave}</td>
        <td><span class="badge ${cstatBadge}">${retorno.cstat || 'ERRO'}</span></td>
        <td class="text-start" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${retorno.xmotivo || retorno.message || retorno.error || ''}">
            ${retorno.xmotivo || retorno.message || retorno.error || ''}
        </td>
        <td style="font-size: 11px;">
            ${retorno.recibo ? 'R: '+retorno.recibo+'<br>' : ''}
            ${retorno.protocolo ? 'P: '+retorno.protocolo : ''}
        </td>
    `;
    
    tbody.prepend(tr);
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }

    // Salva o histórico de envios no rascunho ativo imediatamente
    if (typeof window.triggerAutoSave === 'function') {
        window.triggerAutoSave();
    }
    // Salva no banco de dados silenciosamente (se for um rascunho já existente)
    if (window.idRascunhoAtual && typeof window.confirmarSalvarRascunho === 'function') {
        window.confirmarSalvarRascunho(true);
    }
}

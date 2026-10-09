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
            
            const chaveRetorno = (retorno.chave || chave).trim();
            if (retorno.chave) {
                const disp = document.getElementById('chaveAcessoDisplay');
                if (disp) disp.value = retorno.chave;
                const chaveInput = document.getElementById('chaveAcesso');
                if (chaveInput) chaveInput.value = retorno.chave;
            }

            // Atualizar o histórico
            atualizarTabelaHistorico(retorno, chaveRetorno, ambiente);

            if (retorno.status === 'success') {
                const isAutorizado = retorno.autorizado === true || retorno.cstat == '100';
                const msg = isAutorizado ? (retorno.protocolo ? `NF-e Autorizada com sucesso! Protocolo: ${retorno.protocolo}` : 'NF-e Autorizada com sucesso!') : `Retorno SEFAZ: ${retorno.cstat} - ${retorno.xmotivo}`;
                const icon = isAutorizado ? 'success' : 'warning';
                
                // Usar Swal se disponivel
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: isAutorizado ? 'NF-e Autorizada com Sucesso!' : 'Retorno da SEFAZ',
                        html: isAutorizado ? `
                            <div class="text-start py-2">
                                <div class="alert alert-success d-flex align-items-center mb-3">
                                    <div><strong>Status 100:</strong> ${retorno.xmotivo || 'Autorizado o uso da NF-e'}</div>
                                </div>
                                <div class="mb-2"><strong>Protocolo de Autorização:</strong> <span class="badge bg-success font-monospace fs-6">${retorno.protocolo || '-'}</span></div>
                                <div class="mb-3"><strong>Chave de Acesso:</strong><br><small class="font-monospace text-break text-muted">${chaveRetorno}</small></div>
                                <div class="d-flex justify-content-center gap-2 pt-2 border-top">
                                    <a href="/api/sefaz/download/pdf/${chaveRetorno}" target="_blank" class="btn btn-sm btn-danger d-inline-flex align-items-center gap-1"><i data-lucide="file-text" style="width: 14px; height: 14px;"></i> Baixar DANFE (PDF)</a>
                                    <a href="/api/sefaz/download/xml/${chaveRetorno}" target="_blank" class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1"><i data-lucide="file-code" style="width: 14px; height: 14px;"></i> Baixar XML Autorizado</a>
                                    <a href="/api/sefaz/download/zip/${chaveRetorno}" target="_blank" class="btn btn-sm btn-warning d-inline-flex align-items-center gap-1"><i data-lucide="archive" style="width: 14px; height: 14px;"></i> Pacote ZIP</a>
                                </div>
                            </div>
                        ` : `
                            <div class="text-start py-2">
                                <div class="alert alert-warning mb-2"><strong>cStat ${retorno.cstat || 'ERRO'}:</strong> ${retorno.xmotivo || 'Rejeição'}</div>
                            </div>
                        `,
                        icon: icon,
                        confirmButtonText: 'Fechar',
                        didOpen: () => {
                            if (typeof lucide !== 'undefined') lucide.createIcons();
                        }
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

function limparCodigoCStat(valor) {
    if (!valor) return '';
    let str = String(valor).trim();
    if (str.includes('<')) {
        // Tenta achar código numérico de 3 dígitos (ex: 100, 290, 135)
        const matchDig = str.match(/\b\d{3}\b/);
        if (matchDig) return matchDig[0];
        if (str.toUpperCase().includes('ERRO')) return 'ERRO';
        str = str.replace(/<[^>]*>?/gm, '').trim();
    }
    return str;
}
window.limparCodigoCStat = limparCodigoCStat;

function limparAmbiente(valor) {
    if (!valor) return 2;
    const str = String(valor).toLowerCase();
    if (str.includes('prod') || str === '1') return 1;
    return 2; // Homologação
}
window.limparAmbiente = limparAmbiente;

function obterTagCStat(cstat, retorno = {}) {
    const cs = limparCodigoCStat(cstat);
    const xmotivo = String(retorno.xmotivo || retorno.message || retorno.error || '').toLowerCase();
    const num = Number(cs);

    // 1. Erro de comunicação ou técnico (Vermelho)
    const isErro = cs === 'ERRO' || cs.startsWith('ERR') || xmotivo.includes('falha interna') || xmotivo.includes('erro de comunica');
    if (isErro) {
        return `<span class="sefaz-tag sefaz-cstat-erro"><i data-lucide="alert-octagon" style="width: 12px; height: 12px;"></i>${cs || 'ERRO'}</span>`;
    }

    // 2. Autorizado o uso (100) ou Lote Processado com sucesso (104) (Verde)
    const isAutorizado = (cs === '100' || (cs === '104' && retorno.autorizado === true && !xmotivo.includes('rejei')));
    // 3. Evento vinculado / registrado (135, 136, 101) (Verde)
    const isEventoSucesso = (cs === '135' || cs === '136' || cs === '101' || (retorno.is_evento && retorno.autorizado));
    if (isAutorizado || isEventoSucesso) {
        return `<span class="sefaz-tag sefaz-cstat-autorizado"><i data-lucide="check-circle" style="width: 12px; height: 12px;"></i>${cs || '100'}</span>`;
    }

    // 4. Aguardando processamento (103, 105, 106) (Amarelo)
    const isAguardando = (cs === '103' || cs === '105' || cs === '106');
    if (isAguardando) {
        return `<span class="sefaz-tag sefaz-cstat-aguardando"><i data-lucide="clock" style="width: 12px; height: 12px;"></i>${cs}</span>`;
    }

    // 5. Denegada (110, 205, 301, 302, 303) (Laranja)
    const isDenegada = (cs === '110' || cs === '205' || cs === '301' || cs === '302' || cs === '303' || xmotivo.includes('denegad'));
    if (isDenegada) {
        return `<span class="sefaz-tag sefaz-cstat-denegada"><i data-lucide="alert-triangle" style="width: 12px; height: 12px;"></i>${cs}</span>`;
    }

    // 6. Rejeição Fiscal (códigos >= 200 ou motivo contendo rejeição) (Vermelho)
    const isRejeicao = (!isNaN(num) && num >= 200) || xmotivo.includes('rejei') || (cs === '104' && !retorno.autorizado);
    if (isRejeicao || cs) {
        return `<span class="sefaz-tag sefaz-cstat-rejeicao"><i data-lucide="x-circle" style="width: 12px; height: 12px;"></i>${cs || 'REJEIÇÃO'}</span>`;
    }

    // 7. Fallback Erro (Vermelho)
    return `<span class="sefaz-tag sefaz-cstat-erro"><i data-lucide="alert-octagon" style="width: 12px; height: 12px;"></i>ERRO</span>`;
}
function obterBadgeCStat(cstat, retorno = {}) {
    return obterTagCStat(cstat, retorno);
}
window.obterTagCStat = obterTagCStat;
window.obterBadgeCStat = obterTagCStat;

function obterTagAmbiente(ambiente) {
    const amb = limparAmbiente(ambiente);
    if (amb === 1) {
        // Produção: verde
        return '<span class="sefaz-tag sefaz-amb-producao"><i data-lucide="shield-check" style="width: 12px; height: 12px;"></i>Produção</span>';
    } else {
        // Homologação: cinza
        return '<span class="sefaz-tag sefaz-amb-homologacao"><i data-lucide="test-tube-2" style="width: 12px; height: 12px;"></i>Homologação</span>';
    }
}
function obterBadgeAmbiente(ambiente) {
    return obterTagAmbiente(ambiente);
}
window.obterTagAmbiente = obterTagAmbiente;
window.obterBadgeAmbiente = obterTagAmbiente;

function normalizarItemHistoricoSefaz(item) {
    if (!item) return null;
    let data = item.data || '';
    let ambiente = item.ambiente || 'Homologação';
    let arquivos = item.arquivos || '';
    let chave = item.chave || '';
    let status = item.status || '';
    let motivo = item.motivo || '';
    let motivoTitle = item.motivoTitle || motivo || '';
    let protocolo = item.protocolo || '';

    // Detecta se houve deslocamento de colunas legado (onde chave tinha html de arquivos ou status tinha chave de 44 dígitos)
    const chaveDigitos = String(chave || '').replace(/\D/g, '');
    const statusDigitos = String(status || '').replace(/\D/g, '');
    
    if (statusDigitos.length === 44) {
        arquivos = chave;
        chave = statusDigitos;
        status = motivo;
        motivo = protocolo;
        protocolo = '';
    } else if (String(chave).includes('<div') || String(chave).includes('<a ') || String(chave).includes('disabled')) {
        arquivos = chave;
        chave = statusDigitos.length === 44 ? statusDigitos : '';
    }

    // Limpa chave se tiver HTML residual
    chave = String(chave || '').replace(/<[^>]*>?/gm, '').trim();

    // Limpa status (cStat) de tags HTML ou badge antigos
    const cstatLimpo = limparCodigoCStat(status);
    const ambLimpo = limparAmbiente(ambiente);

    // Renderiza tags padronizadas com as novas classes (sem badge)
    const tagAmbiente = obterTagAmbiente(ambLimpo);
    const tagCStat = obterTagCStat(cstatLimpo, { xmotivo: motivo });

    const isAut = (cstatLimpo === '100' || cstatLimpo === '104' || cstatLimpo === '135' || cstatLimpo === '136');
    if ((!arquivos || arquivos === '-') && typeof window.renderArquivosIcons === 'function' && chave) {
        arquivos = window.renderArquivosIcons(chave, isAut);
    }

    return {
        data: String(data || '').replace(/<[^>]*>?/gm, '').trim() || new Date().toLocaleString('pt-BR'),
        ambienteHtml: tagAmbiente,
        arquivosHtml: arquivos || '-',
        chave: chave,
        cstatHtml: tagCStat,
        motivo: String(motivo || '').replace(/<[^>]*>?/gm, '').trim(),
        motivoTitle: String(motivoTitle || motivo || '').replace(/<[^>]*>?/gm, '').trim(),
        protocolo: String(protocolo || '').replace(/<[^>]*>?/gm, '').trim()
    };
}
window.normalizarItemHistoricoSefaz = normalizarItemHistoricoSefaz;


function atualizarTabelaHistorico(retorno, chave, ambiente = 2) {
    const tbody = document.getElementById('tbody-historico-sefaz');
    if(tbody.querySelector('td[colspan="6"]') || tbody.querySelector('td[colspan="7"]')) {
        tbody.innerHTML = '';
    }

    const tr = document.createElement('tr');
    
    const cs = String(retorno.cstat || '').trim();
    const isRejeicao = (cs && Number(cs) >= 200) || String(retorno.xmotivo || '').toLowerCase().includes('rejei');
    const isAutorizado = ((cs === '100' || cs === '135' || cs === '136' || cs === '101' || retorno.autorizado === true) && !isRejeicao);

    const now = new Date().toLocaleString('pt-BR');
    
    tr.innerHTML = `
        <td class="align-middle">${now}</td>
        <td class="align-middle">${obterTagAmbiente(ambiente)}</td>
        <td class="text-center align-middle">${renderArquivosIcons(chave, isAutorizado)}</td>
        <td class="text-start align-middle font-monospace" style="font-size: 11px;">${chave}</td>
        <td class="align-middle">${obterTagCStat(retorno.cstat, retorno)}</td>
        <td class="text-start align-middle" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${retorno.xmotivo || retorno.message || retorno.error || ''}">
            ${retorno.xmotivo || retorno.message || retorno.error || ''}
        </td>
        <td class="align-middle" style="font-size: 11px;">
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

async function solicitarCartaCorrecao(ambiente = 2) {
    const isHomolog = (Number(ambiente) === 2);
    const ambNome = isHomolog ? 'Homologação' : 'Produção';
    const btnId = isHomolog ? 'btn-cce-sefaz-homolog' : 'btn-cce-sefaz-prod';

    let chave = (document.getElementById('chaveAcessoDisplay')?.value || getVal('chaveAcesso') || '').replace(/\D/g, '').trim();
    if (!chave || chave.length !== 44) {
        chave = prompt(`Informe a Chave de Acesso (44 dígitos) da NF-e para emitir a Carta de Correção (${ambNome}):`, chave);
        if (chave) chave = chave.replace(/\D/g, '').trim();
    }
    
    if (!chave || chave.length !== 44) {
        alert('A Chave de Acesso válida (44 dígitos) é obrigatória para emitir a Carta de Correção.');
        return;
    }
    
    let textoCorrecao = prompt(`Digite o texto da Carta de Correção (${ambNome}) - mínimo 15 caracteres:\n\nObservação: Não é permitido alterar valores, alíquotas, dados cadastrais de remetente/destinatário ou datas.`);
    if (!textoCorrecao) return;
    textoCorrecao = textoCorrecao.trim();
    if (textoCorrecao.length < 15) {
        alert('O texto da correção deve conter no mínimo 15 caracteres (exigência SEFAZ).');
        return;
    }
    
    const confirma = confirm(`Confirmar transmissão de CARTA DE CORREÇÃO em ${ambNome.toUpperCase()} na SEFAZ?\n\nChave: ${chave}\nTexto: "${textoCorrecao}"`);
    if (!confirma) return;
    
    const btnCCe = document.getElementById(btnId);
    const originalHtml = btnCCe ? btnCCe.innerHTML : '';
    if (btnCCe) {
        btnCCe.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Transmitindo CC-e...`;
        btnCCe.disabled = true;
    }
    
    try {
        const response = await fetch('/api/sefaz/carta_correcao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chave: chave,
                texto_correcao: textoCorrecao,
                nSeqEvento: 1,
                tpAmb: ambiente
            })
        });
        
        const retorno = await response.json();
        atualizarTabelaHistorico(retorno, chave, ambiente);
        
        if (retorno.status === 'success') {
            const isVinculado = (retorno.cstat == '135' || retorno.cstat == '136' || retorno.autorizado === true);
            const msg = isVinculado ? `Carta de Correção (CC-e) registrada e vinculada com sucesso na SEFAZ (${ambNome})!` : `Retorno SEFAZ: ${retorno.cstat} - ${retorno.xmotivo}`;
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: isVinculado ? 'CC-e Registrada!' : 'Retorno SEFAZ',
                    html: `<div class="text-start py-1">
                        <div class="alert ${isVinculado ? 'alert-success' : 'alert-warning'} mb-2"><strong>cStat ${retorno.cstat || '-'}:</strong> ${retorno.xmotivo || '-'}</div>
                        ${retorno.protocolo ? `<p class="mb-1"><strong>Protocolo do Evento:</strong> <span class="badge bg-success font-monospace">${retorno.protocolo}</span></p>` : ''}
                        <p class="mb-0 text-muted"><small>Ambiente: ${ambNome}</small></p>
                    </div>`,
                    icon: isVinculado ? 'success' : 'warning'
                });
            } else {
                alert(msg);
            }
        } else {
            alert(`Erro SEFAZ: ${retorno.error || retorno.message || 'Falha ao registrar CC-e'}`);
        }
    } catch (e) {
        console.error('Erro ao enviar CC-e:', e);
        alert('Erro ao comunicar evento de Carta de Correção: ' + e.message);
    } finally {
        if (btnCCe) {
            btnCCe.innerHTML = originalHtml;
            btnCCe.disabled = false;
        }
        if (typeof lucide !== 'undefined' && lucide.createIcons) lucide.createIcons();
    }
}

function solicitarCartaCorrecaoHomolog() {
    return solicitarCartaCorrecao(2);
}

function solicitarCartaCorrecaoProd() {
    return solicitarCartaCorrecao(1);
}

window.solicitarCartaCorrecao = solicitarCartaCorrecao;
window.solicitarCartaCorrecaoHomolog = solicitarCartaCorrecaoHomolog;
window.solicitarCartaCorrecaoProd = solicitarCartaCorrecaoProd;

async function solicitarCancelarNfe(ambiente = 2) {
    const isHomolog = (Number(ambiente) === 2);
    const ambNome = isHomolog ? 'Homologação' : 'Produção';
    const btnId = isHomolog ? 'btn-cancelar-sefaz-homolog' : 'btn-cancelar-sefaz-prod';

    let chave = (document.getElementById('chaveAcessoDisplay')?.value || getVal('chaveAcesso') || '').replace(/\D/g, '').trim();
    if (!chave || chave.length !== 44) {
        chave = prompt(`Informe a Chave de Acesso (44 dígitos) da NF-e que deseja cancelar (${ambNome}):`, chave);
        if (chave) chave = chave.replace(/\D/g, '').trim();
    }
    
    if (!chave || chave.length !== 44) {
        alert('A Chave de Acesso válida (44 dígitos) é obrigatória para cancelar a NF-e.');
        return;
    }
    
    let protocoloSugerido = '';
    const linhas = document.querySelectorAll('#tbody-historico-sefaz tr');
    linhas.forEach(l => {
        const txt = l.innerText || '';
        const m = txt.match(/P:\s*(\d{10,20})/);
        if (m) protocoloSugerido = m[1];
    });
    
    let protocolo = prompt(`Informe o número do Protocolo de Autorização da NF-e (15 dígitos) em ${ambNome}:`, protocoloSugerido);
    if (!protocolo) return;
    protocolo = protocolo.replace(/\D/g, '').trim();
    if (!protocolo) {
        alert('O número de Protocolo de Autorização é obrigatório para cancelamento.');
        return;
    }
    
    let justificativa = prompt(`Informe a justificativa do Cancelamento (${ambNome}) - mínimo 15 caracteres:`);
    if (!justificativa) return;
    justificativa = justificativa.trim();
    if (justificativa.length < 15) {
        alert('A justificativa de cancelamento deve ter no mínimo 15 caracteres (exigência SEFAZ).');
        return;
    }
    
    const confirma = confirm(`ATENÇÃO: Deseja realmente CANCELAR a NF-e em ${ambNome.toUpperCase()}?\n\nChave: ${chave}\nProtocolo: ${protocolo}\nJustificativa: "${justificativa}"\n\nEsta operação é irreversível.`);
    if (!confirma) return;
    
    const btnCanc = document.getElementById(btnId);
    const originalHtml = btnCanc ? btnCanc.innerHTML : '';
    if (btnCanc) {
        btnCanc.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Transmitindo Cancelamento...`;
        btnCanc.disabled = true;
    }
    
    try {
        const response = await fetch('/api/sefaz/cancelar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chave: chave,
                protocolo: protocolo,
                justificativa: justificativa,
                tpAmb: ambiente
            })
        });
        
        const retorno = await response.json();
        atualizarTabelaHistorico(retorno, chave, ambiente);
        
        if (retorno.status === 'success') {
            const isCancelado = (retorno.cstat == '135' || retorno.cstat == '136' || retorno.cstat == '101' || retorno.autorizado === true);
            const msg = isCancelado ? `NF-e Cancelada com sucesso na SEFAZ (${ambNome})!` : `Retorno SEFAZ: ${retorno.cstat} - ${retorno.xmotivo}`;
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: isCancelado ? 'NF-e Cancelada!' : 'Retorno SEFAZ',
                    html: `<div class="text-start py-1">
                        <div class="alert ${isCancelado ? 'alert-success' : 'alert-warning'} mb-2"><strong>cStat ${retorno.cstat || '-'}:</strong> ${retorno.xmotivo || '-'}</div>
                        ${retorno.protocolo ? `<p class="mb-1"><strong>Protocolo do Evento:</strong> <span class="badge bg-success font-monospace">${retorno.protocolo}</span></p>` : ''}
                        <p class="mb-0 text-muted"><small>Ambiente: ${ambNome}</small></p>
                    </div>`,
                    icon: isCancelado ? 'success' : 'warning'
                });
            } else {
                alert(msg);
            }
        } else {
            alert(`Erro SEFAZ: ${retorno.error || retorno.message || 'Falha ao cancelar NF-e'}`);
        }
    } catch (e) {
        console.error('Erro ao cancelar NF-e:', e);
        alert('Erro ao comunicar evento de Cancelamento: ' + e.message);
    } finally {
        if (btnCanc) {
            btnCanc.innerHTML = originalHtml;
            btnCanc.disabled = false;
        }
        if (typeof lucide !== 'undefined' && lucide.createIcons) lucide.createIcons();
    }
}

function solicitarCancelarNfeHomolog() {
    return solicitarCancelarNfe(2);
}

function solicitarCancelarNfeProd() {
    return solicitarCancelarNfe(1);
}

window.solicitarCancelarNfe = solicitarCancelarNfe;
window.solicitarCancelarNfeHomolog = solicitarCancelarNfeHomolog;
window.solicitarCancelarNfeProd = solicitarCancelarNfeProd;

function sanitizarTabelaHistoricoSefaz() {
    const tbody = document.getElementById('tbody-historico-sefaz');
    if (!tbody) return;
    
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(tr => {
        const cells = tr.querySelectorAll('td');
        if (cells.length === 1 && (cells[0].getAttribute('colspan') === '6' || cells[0].getAttribute('colspan') === '7')) {
            return;
        }

        if (cells.length >= 6) {
            // Coluna 1: Ambiente (Homologação ou Produção)
            const cellAmb = cells[1];
            if (cellAmb && (!cellAmb.querySelector('.sefaz-tag') || cellAmb.querySelector('.badge') || cellAmb.innerText.trim())) {
                const ambText = cellAmb.innerText || cellAmb.innerHTML;
                cellAmb.innerHTML = obterTagAmbiente(ambText);
                cellAmb.className = "align-middle";
            }

            // Colunas: Arquivos, Chave, cStat, Motivo
            let cellArq = cells.length >= 7 ? cells[2] : null;
            let cellChave = cells.length >= 7 ? cells[3] : cells[2];
            let cellStatus = cells.length >= 7 ? cells[4] : cells[3];
            let cellMotivo = cells.length >= 7 ? cells[5] : cells[4];

            // Verifica se a chave e status estavam deslocados
            const statusTxt = (cellStatus ? cellStatus.innerText.trim() : '');
            if (statusTxt.replace(/\D/g, '').length === 44 && cells.length >= 7) {
                const realChave = statusTxt;
                const realStatus = cellMotivo ? cellMotivo.innerText.trim() : '';
                cellStatus.innerHTML = obterTagCStat(realStatus);
                cellStatus.className = "align-middle";
                if (cellChave) cellChave.innerText = realChave;
            } else if (cellStatus && (!cellStatus.querySelector('.sefaz-tag') || cellStatus.querySelector('.badge') || cellStatus.innerText.trim())) {
                const motivoText = cellMotivo ? (cellMotivo.getAttribute('title') || cellMotivo.innerText || '') : '';
                const rawStatus = cellStatus.innerText || cellStatus.innerHTML;
                cellStatus.innerHTML = obterTagCStat(rawStatus, { xmotivo: motivoText });
                cellStatus.className = "align-middle";
            }
        }
    });

    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }
}
window.sanitizarTabelaHistoricoSefaz = sanitizarTabelaHistoricoSefaz;

function iniciarObservadorHistoricoSefaz() {
    const tbody = document.getElementById('tbody-historico-sefaz');
    if (!tbody || tbody._sefazObserverIniciado) return;
    
    tbody._sefazObserverIniciado = true;
    const observer = new MutationObserver((mutations) => {
        let precisaSanitizar = false;
        mutations.forEach(m => {
            if (m.addedNodes.length > 0) {
                m.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        if (node.querySelector?.('.badge') || node.classList?.contains('badge') || (node.tagName === 'TR' && !node.querySelector('.sefaz-tag'))) {
                            precisaSanitizar = true;
                        }
                    }
                });
            }
        });
        if (precisaSanitizar) {
            observer.disconnect();
            sanitizarTabelaHistoricoSefaz();
            observer.observe(tbody, { childList: true, subtree: true });
        }
    });

    observer.observe(tbody, { childList: true, subtree: true });
}

// Inicializa no carregamento do DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        sanitizarTabelaHistoricoSefaz();
        iniciarObservadorHistoricoSefaz();
    });
} else {
    sanitizarTabelaHistoricoSefaz();
    iniciarObservadorHistoricoSefaz();
}



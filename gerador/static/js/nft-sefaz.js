// nft-sefaz.js
// Funcionalidades de comunicação com o SEFAZ (Certificado, Assinatura e Envio)

async function verificarStatusCertificado() {
    try {
        const response = await fetch('/api/certificado/status');
        const data = await response.json();
        const container = document.getElementById('cert-info-container');
        if (!container) return;
        
        if (data.status === 'success') {
            const arquivoNome = data.arquivo ? `<div class="small text-muted font-monospace mt-1"><i data-lucide="file-key" style="width: 12px; height: 12px;"></i> Arquivo: ${data.arquivo}</div>` : '';
            container.innerHTML = `
                <div class="col-md-6">
                    <div class="small text-muted mb-1">Titular / Assunto</div>
                    <div class="fw-bold font-monospace" style="font-size: 11px;">${data.assunto}</div>
                    ${arquivoNome}
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
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error('Erro na verificação do certificado:', e);
        if (window.nftAlert) {
            await window.nftAlert('Ocorreu um erro ao verificar o certificado digital.', { type: 'danger', title: 'Erro de Certificado' });
        }
    }
}

// === IMPORTAÇÃO E INSTALAÇÃO DE CERTIFICADO DIGITAL A1 (PFX / P12) ===
let arquivoPfxSelecionado = null;

function abrirModalImportarCertificado() {
    arquivoPfxSelecionado = null;
    const inputPfx = document.getElementById('inputArquivoPfx');
    if (inputPfx) inputPfx.value = '';
    
    const displayEl = document.getElementById('pfx-file-name-display');
    if (displayEl) displayEl.classList.add('d-none');
    
    const textEl = document.getElementById('pfx-file-name-text');
    if (textEl) textEl.innerText = '';
    
    const dropzone = document.getElementById('dropzone-certificado');
    if (dropzone) dropzone.classList.remove('dragover');
    
    const senhaInput = document.getElementById('inputSenhaCertificado');
    if (senhaInput && !senhaInput.value) {
        senhaInput.value = 'nftecnpj';
    }
    
    const modalEl = document.getElementById('modalImportarCertificado');
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
        configurarDropzonePfx();
        setTimeout(() => {
            if (window.lucide) lucide.createIcons();
        }, 150);
    }
}

function configurarDropzonePfx() {
    const dropzone = document.getElementById('dropzone-certificado');
    if (!dropzone || dropzone.dataset.configured === 'true') return;
    dropzone.dataset.configured = 'true';

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            definirArquivoPfx(files[0]);
        }
    }, false);
}

function aoSelecionarArquivoPfx(input) {
    if (input.files && input.files[0]) {
        definirArquivoPfx(input.files[0]);
    }
}

function definirArquivoPfx(file) {
    const nome = file.name.toLowerCase();
    if (!nome.endsWith('.pfx') && !nome.endsWith('.p12')) {
        if (window.nftAlert) {
            window.nftAlert('Por favor, selecione um arquivo de certificado digital válido (.pfx ou .p12).', {
                title: 'Formato Não Suportado',
                type: 'warning'
            });
        } else {
            alert('Por favor, selecione um arquivo de certificado digital válido (.pfx ou .p12).');
        }
        return;
    }

    arquivoPfxSelecionado = file;
    const displayEl = document.getElementById('pfx-file-name-display');
    const textEl = document.getElementById('pfx-file-name-text');
    const sizeKB = (file.size / 1024).toFixed(1);
    
    if (textEl) {
        textEl.innerText = `${file.name} (${sizeKB} KB)`;
    }
    if (displayEl) {
        displayEl.classList.remove('d-none');
    }
    if (window.lucide) lucide.createIcons();
}

function alternarVisibilidadeSenhaCertificado() {
    const input = document.getElementById('inputSenhaCertificado');
    const icone = document.getElementById('icone-olho-senha-cert');
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        if (icone) icone.setAttribute('data-lucide', 'eye-off');
    } else {
        input.type = 'password';
        if (icone) icone.setAttribute('data-lucide', 'eye');
    }
    if (window.lucide) lucide.createIcons();
}

async function submeterImportarCertificado() {
    if (!arquivoPfxSelecionado) {
        const input = document.getElementById('inputArquivoPfx');
        if (input && input.files && input.files[0]) {
            definirArquivoPfx(input.files[0]);
        }
    }

    if (!arquivoPfxSelecionado) {
        if (window.nftAlert) {
            await window.nftAlert('Por favor, selecione ou arraste um arquivo de certificado (.pfx ou .p12) antes de continuar.', {
                title: 'Arquivo Necessário',
                type: 'warning'
            });
        } else {
            alert('Por favor, selecione ou arraste um arquivo de certificado (.pfx ou .p12) antes de continuar.');
        }
        return;
    }

    const senha = (document.getElementById('inputSenhaCertificado')?.value || '').trim();
    if (!senha) {
        if (window.nftAlert) {
            await window.nftAlert('Por favor, informe a senha do certificado digital.', {
                title: 'Senha Obrigatória',
                type: 'warning'
            });
        } else {
            alert('Por favor, informe a senha do certificado digital.');
        }
        document.getElementById('inputSenhaCertificado')?.focus();
        return;
    }

    const btnInstalar = document.getElementById('btnInstalarCertificadoModal');
    const originalHtml = btnInstalar ? btnInstalar.innerHTML : '';
    if (btnInstalar) {
        btnInstalar.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Validando e Instalando...`;
        btnInstalar.disabled = true;
    }

    try {
        const formData = new FormData();
        formData.append('file', arquivoPfxSelecionado);
        formData.append('senha', senha);

        const resp = await fetch('/api/certificado/importar', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();

        if (!resp.ok || data.status === 'error') {
            throw new Error(data.message || 'Falha ao importar certificado digital.');
        }

        // Fecha modal
        const modalEl = document.getElementById('modalImportarCertificado');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        // Atualiza painel do certificado na tela
        await verificarStatusCertificado();

        const msgSucesso = 
            `Certificado digital instalado e pronto para uso no sistema!\n\n` +
            `• Arquivo: ${data.arquivo}\n` +
            `• Titular: ${data.assunto}\n` +
            `• CNPJ: ${data.cnpj || 'Identificado'}\n` +
            `• Validade: até ${data.fim}`;

        if (window.nftAlert) {
            await window.nftAlert(msgSucesso, {
                title: 'Certificado Ativado!',
                type: 'success',
                icon: 'shield-check'
            });
        } else {
            alert('✅ ' + msgSucesso);
        }

    } catch (err) {
        console.error('Erro ao importar certificado:', err);
        if (window.nftAlert) {
            await window.nftAlert(err.message, {
                title: 'Falha na Instalação do Certificado',
                type: 'danger'
            });
        } else {
            alert('❌ Erro: ' + err.message);
        }
    } finally {
        if (btnInstalar) {
            btnInstalar.innerHTML = originalHtml;
            btnInstalar.disabled = false;
        }
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
                await window.nftAlert('Erro: Não foi possível obter o XML gerado.', { type: 'danger', title: 'XML Não Encontrado' });
                return;
            }

            // Força a tag <tpAmb> no XML para o ambiente clicado
            xmlString = xmlString.replace(/<tpAmb>\d+<\/tpAmb>/g, `<tpAmb>${ambiente}</tpAmb>`);

            const chave = (document.getElementById('chaveAcesso')?.value || 
                           document.getElementById('chaveAcessoDisplay')?.value || 
                           'N/A').replace(/\s+/g, '');
            const refInterna = document.getElementById('referenciaInterna')?.value || 
                               document.getElementById('inputReferenciaInterna')?.value || 
                               document.getElementById('referencia_interna')?.value || 
                               document.getElementById('input_referencia_interna')?.value || 
                               (typeof obterReferenciaInterna === 'function' ? obterReferenciaInterna() : '') || '';

            const response = await fetch('/api/sefaz/enviar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    xml: xmlString,
                    chave: chave,
                    tpAmb: ambiente,
                    referencia_interna: refInterna
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
                    await window.nftAlert(msg, {
                        type: isAutorizado ? 'success' : 'warning',
                        title: isAutorizado ? 'NF-e Autorizada com Sucesso!' : 'Retorno da SEFAZ'
                    });
                }
            } else {
                await window.nftAlert(`Erro ao comunicar com a SEFAZ: ${retorno.message || retorno.error || 'Erro desconhecido'}`, {
                    type: 'danger',
                    title: 'Falha na Comunicação SEFAZ'
                });
            }

        } catch(e) {
            console.error('Erro no envio', e);
            const msg = e.message || 'Falha interna ao tentar enviar a nota para a SEFAZ.';
            atualizarTabelaHistorico({ cstat: 'ERRO', error: msg }, getVal('chaveAcesso') || '-', ambiente);
            await window.nftAlert(msg, { type: 'danger', title: 'Erro de Envio' });
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
        await window.nftAlert(msg, { type: 'warning', title: 'Nota Incompleta' });
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
                <a href="/api/sefaz/download/pdf/${chaveLimpa}" target="_blank" class="btn btn-sm btn-outline-danger p-1 d-inline-flex align-items-center justify-content-center" title="Baixar DANFE (PDF)" style="width: 26px; height: 26px; border-radius: 4px;" onclick="event.stopPropagation();">
                    <i data-lucide="file-text" style="width: 14px; height: 14px;"></i>
                </a>
                <a href="/api/sefaz/download/xml/${chaveLimpa}" target="_blank" class="btn btn-sm btn-outline-primary p-1 d-inline-flex align-items-center justify-content-center" title="Baixar XML Autorizado" style="width: 26px; height: 26px; border-radius: 4px;" onclick="event.stopPropagation();">
                    <i data-lucide="file-code" style="width: 14px; height: 14px;"></i>
                </a>
                <a href="/api/sefaz/download/zip/${chaveLimpa}" target="_blank" class="btn btn-sm btn-outline-warning p-1 d-inline-flex align-items-center justify-content-center" title="Baixar Pacote Completo (ZIP)" style="width: 26px; height: 26px; border-radius: 4px;" onclick="event.stopPropagation();">
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
    let cs = limparCodigoCStat(cstat);
    const xmotivo = String(retorno.xmotivo || retorno.message || retorno.error || '').toLowerCase();
    
    // Normalização: se constar 801 ou se o retorno/motivo indicar autorização, corrige para o código oficial 100
    if (cs === '801' || retorno.autorizado === true || xmotivo.includes('autoriz')) {
        cs = '100';
    }
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
    let cstatLimpo = limparCodigoCStat(status);
    const ambLimpo = limparAmbiente(ambiente);
    const motivoLower = String(motivo || '').toLowerCase();

    // Normalização: se for evento (135/136/101 ou motivo de evento), preserva 135
    if (cstatLimpo === '135' || cstatLimpo === '136' || cstatLimpo === '101' || motivoLower.includes('vinculado') || motivoLower.includes('cancelamento')) {
        if (!cstatLimpo || cstatLimpo === '100' || cstatLimpo === 'EVENTO') cstatLimpo = '135';
    } else if (cstatLimpo === '801' || motivoLower.includes('autoriz') || item.status === 'Autorizada' || item.autorizado === true) {
        cstatLimpo = '100';
    }

    // Renderiza tags padronizadas com as novas classes (sem badge)
    const tagAmbiente = obterTagAmbiente(ambLimpo);
    const tagCStat = obterTagCStat(cstatLimpo, { xmotivo: motivo, autorizado: (cstatLimpo === '100') });

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
    
    let cs = String(retorno.cstat || '').trim();
    const xmotivo = String(retorno.xmotivo || '').toLowerCase();
    if (cs === '135' || cs === '136' || cs === '101' || (retorno.is_evento && retorno.autorizado)) {
        // Mantém 135/136 para eventos (Cancelamento / CC-e)
        if (!cs || cs === '100' || cs === 'EVENTO') cs = '135';
        retorno.cstat = cs;
    } else if (cs === '801' || retorno.autorizado === true || xmotivo.includes('autoriz')) {
        cs = '100';
        retorno.cstat = '100';
    }
    const isRejeicao = (cs && Number(cs) >= 200 && cs !== '801') || xmotivo.includes('rejei');
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

    // 1. Tenta obter a chave autorizada do histórico da SEFAZ na tela
    let chave = '';
    const linhasHist = document.querySelectorAll('#tbody-historico-sefaz tr');
    for (const l of linhasHist) {
        const txtStatus = (l.querySelector('td:nth-child(5)')?.innerText || l.innerText || '');
        if (txtStatus.includes('100') || txtStatus.toLowerCase().includes('autoriz')) {
            const tdChave = l.querySelector('td:nth-child(4)');
            if (tdChave) {
                const cand = tdChave.innerText.replace(/\D/g, '').trim();
                if (cand.length === 44) {
                    chave = cand;
                    break;
                }
            }
        }
    }

    // 2. Se não encontrou no histórico autorizado, pega do campo da tela
    if (!chave || chave.length !== 44) {
        chave = (document.getElementById('chaveAcessoDisplay')?.value || getVal('chaveAcesso') || '').replace(/\D/g, '').trim();
    }

    if (!chave || chave.length !== 44) {
        chave = await window.nftPrompt(
            `Informe a Chave de Acesso (44 dígitos) da NF-e para emitir a Carta de Correção (${ambNome}):`,
            chave,
            {
                title: `Chave de Acesso da NF-e (${ambNome})`,
                icon: 'key',
                type: 'primary',
                maxlength: 44,
                minlength: 44,
                placeholder: 'Digite os 44 dígitos da chave de acesso da nota',
                hint: 'A chave deve conter exatamente 44 dígitos numéricos.',
                confirmText: 'Continuar'
            }
        );
        if (chave) chave = chave.replace(/\D/g, '').trim();
    }
    
    if (!chave || chave.length !== 44) {
        await window.nftAlert('A Chave de Acesso válida (44 dígitos numéricos) é obrigatória para emitir a Carta de Correção na SEFAZ.', {
            type: 'warning',
            title: 'Chave de Acesso Inválida'
        });
        return;
    }
    
    const textoCorrecao = await window.nftPrompt(
        `Digite o texto detalhado da Carta de Correção Eletrônica (CC-e) para a SEFAZ (${ambNome}):\n\n` +
        `• Observação Fiscal: Conforme o Art. 7º do Convênio S/N de 1970, NÃO é permitido alterar valores fiscais, alíquotas, dados cadastrais de remetente/destinatário ou datas de emissão/saída.`,
        '',
        {
            title: `Carta de Correção Eletrônica - CC-e (${ambNome})`,
            icon: 'file-edit',
            type: 'warning',
            inputType: 'textarea',
            rows: 6,
            minlength: 15,
            maxlength: 1000,
            placeholder: 'Descreva aqui detalhadamente a retificação fiscal a ser registrada (mínimo 15 caracteres, até 1000 caracteres)...',
            hint: 'Mínimo de 15 caracteres exigido pela SEFAZ. Pressione Ctrl+Enter para avançar.',
            confirmText: 'Avançar com CC-e',
            cancelText: 'Cancelar'
        }
    );
    if (!textoCorrecao) return;
    const textoLimpo = textoCorrecao.trim();
    if (textoLimpo.length < 15) {
        await window.nftAlert('O texto da correção deve conter no mínimo 15 caracteres conforme exigência estrita da SEFAZ.', {
            type: 'warning',
            title: 'Texto Insuficiente'
        });
        return;
    }
    
    const confirma = await window.nftConfirm(
        `Confirmar a transmissão da CARTA DE CORREÇÃO em ${ambNome.toUpperCase()} na SEFAZ?\n\n` +
        `• Chave da NF-e: ${chave}\n` +
        `• Extensão do Texto: ${textoLimpo.length} caracteres\n` +
        `• Texto:\n"${textoLimpo}"`,
        {
            title: `Confirmar Transmissão CC-e (${ambNome})`,
            type: 'warning',
            icon: 'send',
            confirmText: 'Sim, Transmitir CC-e',
            cancelText: 'Voltar e Revisar'
        }
    );
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
                texto_correcao: textoLimpo,
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
                await window.nftAlert(msg, { type: isVinculado ? 'success' : 'warning', title: isVinculado ? 'CC-e Registrada!' : 'Retorno SEFAZ' });
            }
        } else {
            await window.nftAlert(`Erro SEFAZ: ${retorno.error || retorno.message || 'Falha ao registrar CC-e'}`, { type: 'danger', title: 'Erro de Transmissão' });
        }
    } catch (e) {
        console.error('Erro ao enviar CC-e:', e);
        await window.nftAlert('Erro ao comunicar evento de Carta de Correção: ' + e.message, { type: 'danger', title: 'Falha de Comunicação' });
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

    // 1. Tenta obter a chave autorizada do histórico da SEFAZ na tela
    let chave = '';
    const linhasHist = document.querySelectorAll('#tbody-historico-sefaz tr');
    for (const l of linhasHist) {
        const txtStatus = (l.querySelector('td:nth-child(5)')?.innerText || l.innerText || '');
        if (txtStatus.includes('100') || txtStatus.toLowerCase().includes('autoriz')) {
            const tdChave = l.querySelector('td:nth-child(4)');
            if (tdChave) {
                const cand = tdChave.innerText.replace(/\D/g, '').trim();
                if (cand.length === 44) {
                    chave = cand;
                    break;
                }
            }
        }
    }

    // 2. Se não encontrou no histórico autorizado, pega do campo da tela
    if (!chave || chave.length !== 44) {
        chave = (document.getElementById('chaveAcessoDisplay')?.value || getVal('chaveAcesso') || '').replace(/\D/g, '').trim();
    }

    if (!chave || chave.length !== 44) {
        chave = await window.nftPrompt(
            `Informe a Chave de Acesso (44 dígitos) da NF-e que deseja cancelar (${ambNome}):`,
            chave,
            {
                title: `Chave de Acesso da NF-e (${ambNome})`,
                icon: 'key',
                type: 'primary',
                maxlength: 44,
                minlength: 44,
                placeholder: 'Digite os 44 dígitos da chave de acesso da nota',
                hint: 'A chave deve conter exatamente 44 dígitos numéricos.',
                confirmText: 'Continuar'
            }
        );
        if (chave) chave = chave.replace(/\D/g, '').trim();
    }
    
    if (!chave || chave.length !== 44) {
        await window.nftAlert('A Chave de Acesso válida (44 dígitos) é obrigatória para cancelar a NF-e.', {
            type: 'warning',
            title: 'Chave Obrigatória'
        });
        return;
    }
    
    let protocoloSugerido = '';
    const linhas = document.querySelectorAll('#tbody-historico-sefaz tr');
    linhas.forEach(l => {
        const txt = l.innerText || '';
        const m = txt.match(/P:\s*(\d{10,20})/);
        if (m) protocoloSugerido = m[1];
    });
    
    let protocolo = await window.nftPrompt(
        `Informe o número do Protocolo de Autorização da NF-e (15 dígitos) em ${ambNome}:`,
        protocoloSugerido,
        {
            title: `Protocolo de Autorização (${ambNome})`,
            icon: 'file-text',
            type: 'primary',
            maxlength: 20,
            minlength: 10,
            placeholder: 'Ex: 135260009186901',
            hint: 'Informe o número do protocolo retornado pela SEFAZ no momento da autorização.',
            confirmText: 'Continuar'
        }
    );
    if (!protocolo) return;
    protocolo = protocolo.replace(/\D/g, '').trim();
    if (!protocolo) {
        await window.nftAlert('O número do Protocolo de Autorização é obrigatório para cancelamento perante o Fisco.', {
            type: 'warning',
            title: 'Protocolo Obrigatório'
        });
        return;
    }
    
    const justificativa = await window.nftPrompt(
        `Informe a justificativa do CANCELAMENTO desta NF-e na SEFAZ (${ambNome}):\n\n` +
        `• Atenção: A justificativa é gravada publicamente na SEFAZ e vinculada à nota fiscal.`,
        '',
        {
            title: `Justificativa de Cancelamento (${ambNome})`,
            icon: 'x-circle',
            type: 'danger',
            inputType: 'textarea',
            rows: 6,
            minlength: 15,
            maxlength: 1000,
            placeholder: 'Descreva detalhadamente o motivo do cancelamento (mínimo 15 caracteres, até 1000 caracteres)...',
            hint: 'Mínimo de 15 caracteres exigido pelo Fisco. Pressione Ctrl+Enter para avançar.',
            confirmText: 'Avançar para Cancelamento',
            cancelText: 'Cancelar'
        }
    );
    if (!justificativa) return;
    const justificativaLimpa = justificativa.trim();
    if (justificativaLimpa.length < 15) {
        await window.nftAlert('A justificativa de cancelamento deve conter no mínimo 15 caracteres conforme exigência legal da SEFAZ.', {
            type: 'warning',
            title: 'Justificativa Insuficiente'
        });
        return;
    }
    
    const confirma = await window.nftConfirm(
        `ATENÇÃO: Deseja realmente CANCELAR a NF-e em ${ambNome.toUpperCase()} na SEFAZ?\n\n` +
        `• Chave: ${chave}\n` +
        `• Protocolo: ${protocolo}\n` +
        `• Justificativa (${justificativaLimpa.length} caracteres):\n"${justificativaLimpa}"\n\n` +
        `Esta operação é IRREVERSÍVEL. O cancelamento será homologado perante o Fisco.`,
        {
            title: `CONFIRMAR CANCELAMENTO DE NF-E (${ambNome.toUpperCase()})`,
            type: 'danger',
            icon: 'alert-triangle',
            confirmText: 'Sim, Cancelar NF-e Definitivamente',
            cancelText: 'Desistir e Manter Nota'
        }
    );
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
                justificativa: justificativaLimpa,
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
                await window.nftAlert(msg, { type: isCancelado ? 'success' : 'warning', title: isCancelado ? 'NF-e Cancelada!' : 'Retorno SEFAZ' });
            }
        } else {
            await window.nftAlert(`Erro SEFAZ: ${retorno.error || retorno.message || 'Falha ao cancelar NF-e'}`, { type: 'danger', title: 'Erro de Cancelamento' });
        }
    } catch (e) {
        console.error('Erro ao cancelar NF-e:', e);
        await window.nftAlert('Erro ao comunicar evento de Cancelamento: ' + e.message, { type: 'danger', title: 'Falha de Comunicação' });
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

// ==============================================================================
// === CONSULTA DE SITUAÇÃO DA NF-E NA SEFAZ (POPUP COMPLETO COM DETALHES) ===
// ==============================================================================

async function consultarSituacaoNfeSefaz(ambiente = 1) {
    const isHomolog = (Number(ambiente) === 2);
    const ambNome = isHomolog ? 'Homologação' : 'Produção';

    // 1. Tenta obter a chave autorizada do histórico ou do campo de tela
    let chave = '';
    const linhasHist = document.querySelectorAll('#tbody-historico-sefaz tr');
    for (const l of linhasHist) {
        const txtStatus = (l.querySelector('td:nth-child(5)')?.innerText || l.innerText || '');
        if (txtStatus.includes('100') || txtStatus.includes('135') || txtStatus.toLowerCase().includes('autoriz') || txtStatus.toLowerCase().includes('cancel')) {
            const tdChave = l.querySelector('td:nth-child(4)');
            if (tdChave) {
                const cand = tdChave.innerText.replace(/\D/g, '').trim();
                if (cand.length === 44) {
                    chave = cand;
                    break;
                }
            }
        }
    }

    if (!chave || chave.length !== 44) {
        chave = (document.getElementById('chaveAcessoDisplay')?.value || getVal('chaveAcesso') || '').replace(/\D/g, '').trim();
    }

    if (!chave || chave.length !== 44) {
        chave = await window.nftPrompt(
            `Informe a Chave de Acesso (44 dígitos) da NF-e que deseja consultar na SEFAZ (${ambNome}):`,
            chave,
            {
                title: `Consultar Situação na SEFAZ (${ambNome})`,
                icon: 'search',
                type: 'primary',
                maxlength: 44,
                minlength: 44,
                placeholder: 'Digite os 44 dígitos da chave de acesso',
                hint: 'A chave deve conter exatamente 44 dígitos numéricos.',
                confirmText: 'Consultar SEFAZ'
            }
        );
        if (chave) chave = chave.replace(/\D/g, '').trim();
    }

    if (!chave || chave.length !== 44) {
        await window.nftAlert('Informe uma Chave de Acesso válida (44 dígitos) para consultar a SEFAZ.', {
            type: 'warning',
            title: 'Chave Obrigatória'
        });
        return;
    }

    // Modal ou Swal de Loading
    const btnConsultar = document.getElementById(isHomolog ? 'btn-consultar-sefaz-homolog' : 'btn-consultar-sefaz-prod');
    const originalHtml = btnConsultar ? btnConsultar.innerHTML : '';
    if (btnConsultar) {
        btnConsultar.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Consultando SEFAZ...`;
        btnConsultar.disabled = true;
    }

    try {
        const resp = await fetch('/api/sefaz/consultar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chave: chave, tpAmb: ambiente })
        });
        const data = await resp.json();

        if (!resp.ok || data.status === 'error') {
            throw new Error(data.xmotivo || data.error || data.message || 'Falha ao consultar WebService da SEFAZ.');
        }

        // Monta o Modal / Popup com todos os dados fiscais da nota
        exibirModalDetalhesConsultaSefaz(data);

        // Atualiza a tabela de histórico (Aba 5) caso a nota esteja autorizada ou cancelada
        const cs = String(data.cstat || '').trim();
        const isAut = (cs === '100' || Boolean(data.protocolo_autorizacao));
        
        if (data.is_cancelada || isAut) {
            // Verifica se esta chave e status já constam no histórico da tela para não duplicar
            const tbody = document.getElementById('tbody-historico-sefaz');
            let jaExisteNoHistorico = false;
            if (tbody) {
                const linhas = tbody.querySelectorAll('tr');
                linhas.forEach(tr => {
                    const txt = tr.innerText || '';
                    if (txt.includes(chave)) {
                        if (data.is_cancelada && (txt.includes('101') || txt.toLowerCase().includes('cancel'))) {
                            jaExisteNoHistorico = true;
                        } else if (isAut && !data.is_cancelada && (txt.includes('100') || txt.toLowerCase().includes('autoriz'))) {
                            jaExisteNoHistorico = true;
                        }
                    }
                });
            }

            if (!jaExisteNoHistorico) {
                if (data.is_cancelada) {
                    atualizarTabelaHistorico({
                        cstat: '101',
                        xmotivo: 'Cancelamento de NF-e homologado',
                        protocolo: data.protocolo_cancelamento || data.protocolo_autorizacao,
                        autorizado: false
                    }, chave, ambiente);
                } else if (isAut) {
                    atualizarTabelaHistorico({
                        cstat: data.cstat || '100',
                        xmotivo: data.xmotivo || 'Autorizado o uso da NF-e',
                        protocolo: data.protocolo_autorizacao,
                        autorizado: true
                    }, chave, ambiente);
                }
            }
        }

    } catch (e) {
        console.error('Erro na consulta SEFAZ:', e);
        await window.nftAlert(`Erro ao consultar SEFAZ (${ambNome}):\n\n${e.message}`, {
            type: 'danger',
            title: 'Falha na Consulta SEFAZ'
        });
    } finally {
        if (btnConsultar) {
            btnConsultar.innerHTML = originalHtml;
            btnConsultar.disabled = false;
        }
        if (typeof lucide !== 'undefined' && lucide.createIcons) lucide.createIcons();
    }
}

function exibirModalDetalhesConsultaSefaz(data) {
    let modalEl = document.getElementById('modalDetalhesConsultaSefaz');
    if (!modalEl) {
        modalEl = document.createElement('div');
        modalEl.id = 'modalDetalhesConsultaSefaz';
        modalEl.className = 'modal fade';
        modalEl.tabIndex = -1;
        modalEl.setAttribute('aria-hidden', 'true');
        document.body.appendChild(modalEl);
    }

    const chaveFmt = data.chave ? data.chave.replace(/(\d{4})/g, '$1 ').trim() : '-';
    const situacaoTexto = String(data.situacao || '').toUpperCase();
    const isCancelada = Boolean(data.is_cancelada || situacaoTexto.includes('CANCELADA') || data.cstat === '101');
    const isAutorizada = (data.cstat === '100' && !isCancelada);
    
    let statusBadgeHtml = '';
    if (isCancelada) {
        statusBadgeHtml = `<span class="badge bg-danger text-white fs-6 px-3 py-2 d-inline-flex align-items-center gap-1 shadow-sm" style="background-color: #dc2626 !important; color: #ffffff !important; border-color: #dc2626 !important;"><i data-lucide="x-circle" style="width: 16px; height: 16px; stroke: #ffffff;"></i> CANCELADA</span>`;
    } else if (isAutorizada) {
        statusBadgeHtml = `<span class="badge bg-success text-white fs-6 px-3 py-2 d-inline-flex align-items-center gap-1 shadow-sm" style="color: #ffffff !important;"><i data-lucide="check-circle" style="width: 16px; height: 16px; stroke: #ffffff;"></i> AUTORIZADA (EM USO)</span>`;
    } else {
        statusBadgeHtml = `<span class="badge bg-secondary text-white fs-6 px-3 py-2 d-inline-flex align-items-center gap-1 shadow-sm" style="color: #ffffff !important;">${data.cstat} - ${data.xmotivo}</span>`;
    }

    // Renderiza lista de eventos (se houver)
    let eventosHtml = '';
    if (data.eventos && data.eventos.length > 0) {
        eventosHtml = `
            <div class="mt-3">
                <h6 class="fw-bold d-flex align-items-center gap-2 mb-2 text-secondary">
                    <i data-lucide="calendar-check" style="width: 16px; height: 16px;"></i>
                    Eventos Fiscais Vinculados (${data.eventos.length})
                </h6>
                <div class="table-responsive border rounded bg-white">
                    <table class="table table-sm table-striped mb-0" style="font-size: 12px;">
                        <thead class="table-light">
                            <tr>
                                <th>Tipo / Evento</th>
                                <th>Seq</th>
                                <th>Data/Hora Registro</th>
                                <th>Protocolo</th>
                                <th>Status SEFAZ</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.eventos.map(ev => `
                                <tr>
                                    <td><strong class="text-primary">${ev.descricao}</strong></td>
                                    <td>${ev.sequencia || '1'}</td>
                                    <td class="text-nowrap">${ev.data || '-'}</td>
                                    <td class="font-monospace fw-bold">${ev.protocolo || '-'}</td>
                                    <td><span class="badge bg-success-subtle text-success">${ev.cstat || '135'} - ${ev.motivo || 'Vinculado'}</span></td>
                                </tr>
                                ${ev.detalhe ? `
                                <tr>
                                    <td colspan="5" class="bg-light ps-4 small text-muted">
                                        <em>Detalhe / Justificativa:</em> ${ev.detalhe}
                                    </td>
                                </tr>` : ''}
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    modalEl.innerHTML = `
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content shadow-lg border-0" style="border-radius: 16px; overflow: hidden;">
                <div class="modal-header ${isCancelada ? 'bg-danger text-white' : (isAutorizada ? 'bg-success-subtle text-success' : 'bg-body-secondary')} py-3 border-bottom" style="${isCancelada ? 'background-color: #dc2626 !important; color: #fff !important;' : ''}">
                    <h5 class="modal-title fw-bold d-flex align-items-center gap-2">
                        <i data-lucide="${isCancelada ? 'alert-triangle' : 'shield-check'}" style="width: 22px; height: 22px;"></i>
                        Situação da NF-e na SEFAZ (${data.ambiente_nome})
                    </h5>
                    <button type="button" class="btn-close ${isCancelada ? 'btn-close-white' : ''}" data-bs-dismiss="modal" aria-label="Fechar"></button>
                </div>
                <div class="modal-body p-4" style="background-color: var(--surface, #f8fafc);">
                    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 p-3 bg-white border rounded shadow-sm mb-3">
                        <div>
                            <span class="text-muted small text-uppercase fw-bold d-block mb-1">Status Oficial SEFAZ</span>
                            <div class="d-flex align-items-center gap-2">
                                ${statusBadgeHtml}
                                <span class="badge bg-light text-dark border font-monospace">cStat: ${data.cstat}</span>
                            </div>
                        </div>
                        <div class="text-end">
                            <span class="text-muted small text-uppercase fw-bold d-block mb-1">Data / Hora Consulta</span>
                            <span class="small font-monospace text-secondary">${data.dh_recbto || new Date().toLocaleString('pt-BR')}</span>
                        </div>
                    </div>

                    <!-- Dados da Nota -->
                    <div class="p-3 bg-white border rounded shadow-sm mb-3">
                        <div class="mb-2">
                            <span class="text-muted small text-uppercase fw-bold d-block">Chave de Acesso (44 Dígitos)</span>
                            <span class="font-monospace fw-bold text-dark text-break fs-6">${chaveFmt}</span>
                        </div>
                        <div class="mb-2">
                            <span class="text-muted small text-uppercase fw-bold d-block">Mensagem da SEFAZ</span>
                            <span class="fw-semibold text-secondary">${data.xmotivo || 'Processamento concluído'}</span>
                        </div>
                        <hr class="my-2">
                        <div class="row g-2 pt-1">
                            <div class="col-sm-6">
                                <span class="text-muted small text-uppercase fw-bold d-block">Protocolo de Autorização</span>
                                <span class="font-monospace fw-bold text-success">${data.protocolo_autorizacao || '-'}</span>
                                ${data.data_autorizacao ? `<small class="text-muted d-block font-monospace">${data.data_autorizacao}</small>` : ''}
                            </div>
                            <div class="col-sm-6">
                                <span class="text-muted small text-uppercase fw-bold d-block">Protocolo do Evento de Cancelamento</span>
                                <span class="font-monospace fw-bold text-danger">${data.protocolo_cancelamento || (isCancelada ? 'Homologado na SEFAZ' : 'Não se aplica')}</span>
                                ${data.data_cancelamento ? `<small class="text-muted d-block font-monospace">${data.data_cancelamento}</small>` : ''}
                            </div>
                        </div>
                    </div>

                    ${eventosHtml}

                    <!-- Links Rápidos -->
                    <div class="d-flex justify-content-center gap-2 pt-2 mt-3 border-top">
                        <a href="/api/sefaz/download/pdf/${data.chave}" target="_blank" class="btn btn-sm btn-outline-danger d-inline-flex align-items-center gap-1 shadow-sm">
                            <i data-lucide="file-text" style="width: 14px; height: 14px;"></i> Baixar DANFE (PDF)
                        </a>
                        <a href="/api/sefaz/download/xml/${data.chave}" target="_blank" class="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1 shadow-sm">
                            <i data-lucide="file-code" style="width: 14px; height: 14px;"></i> Baixar XML
                        </a>
                        <a href="/api/sefaz/download/zip/${data.chave}" target="_blank" class="btn btn-sm btn-outline-warning d-inline-flex align-items-center gap-1 shadow-sm">
                            <i data-lucide="archive" style="width: 14px; height: 14px;"></i> Pacote ZIP
                        </a>
                    </div>
                </div>
                <div class="modal-footer bg-light py-2">
                    <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Fechar</button>
                </div>
            </div>
        </div>
    `;

    const bsModal = new bootstrap.Modal(modalEl);
    modalEl.addEventListener('hidden.bs.modal', () => {
        modalEl.remove();
    }, { once: true });
    bsModal.show();
    if (typeof lucide !== 'undefined' && lucide.createIcons) lucide.createIcons();
}

window.consultarSituacaoNfeSefaz = consultarSituacaoNfeSefaz;
window.consultarSituacaoNfeSefazHomolog = () => consultarSituacaoNfeSefaz(2);
window.consultarSituacaoNfeSefazProd = () => consultarSituacaoNfeSefaz(1);


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



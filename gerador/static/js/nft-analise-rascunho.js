/**
 * NFT Logistics - Módulo de Análise e Validação Completa de Rascunho XML
 * Valida o rascunho atual contra as regras de esquema do MOC SEFAZ (NF-e v4.00)
 */

(function () {
    let modalElement = null;

    function getOrCreateModal() {
        if (modalElement && document.body.contains(modalElement)) {
            return modalElement;
        }

        const modalDiv = document.createElement('div');
        modalDiv.id = 'modalResultadoAnalise';
        modalDiv.className = 'modal fade';
        modalDiv.tabIndex = -1;
        modalDiv.setAttribute('aria-labelledby', 'modalResultadoAnaliseLabel');
        modalDiv.setAttribute('aria-hidden', 'true');

        modalDiv.innerHTML = `
            <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
                <div class="modal-content shadow-lg border-0" style="border-radius: 12px; overflow: hidden;">
                    <div class="modal-header py-3 px-4" id="modalAnaliseHeader" style="border-bottom: 1px solid var(--border);">
                        <div class="d-flex align-items-center gap-2">
                            <span id="modalAnaliseIcon" class="d-inline-flex align-items-center justify-content-center" style="width: 32px; height: 32px; border-radius: 50%;"></span>
                            <div>
                                <h5 class="modal-title fw-bold mb-0" id="modalResultadoAnaliseLabel">Resultado da Análise do Rascunho</h5>
                                <small class="text-muted" id="modalAnaliseSubtitulo">Auditoria de conformidade com o Esquema XML da NF-e v4.00</small>
                            </div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                    </div>
                    <div class="modal-body p-4" id="modalAnaliseCorpo" style="background-color: var(--surface);">
                        <!-- Conteúdo dinâmico -->
                    </div>
                    <div class="modal-footer py-2 px-4 d-flex justify-content-between" style="border-top: 1px solid var(--border); background-color: var(--surface-secondary);">
                        <span class="text-muted small" id="modalAnaliseFooterInfo">NFT Logistics XML Validator</span>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn-nft px-3" data-bs-dismiss="modal">Fechar e Revisar</button>
                            <button type="button" class="btn-nft px-3 fw-bold d-flex align-items-center gap-1 shadow-sm" id="btnGerarXMLModal" onclick="fecharModalEGerarXML()">
                                <i data-lucide="download" style="width: 15px; height: 15px;"></i>
                                <span>Gerar Novo XML</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalDiv);
        modalElement = modalDiv;
        return modalElement;
    }

    function coletarDadosRascunho() {
        const getVal = (id) => {
            const el = document.getElementById(id);
            return el ? el.value : '';
        };

        const mutatorLimparNumero = (val) => {
            if (!val) return '0.00';
            let s = String(val).trim();
            if (s.includes(',') && s.includes('.')) {
                s = s.replace(/\./g, '').replace(',', '.');
            } else if (s.includes(',')) {
                s = s.replace(',', '.');
            }
            return s;
        };

        let itensLimpos = [];
        if (window.itensTable && typeof window.itensTable.getData === 'function') {
            itensLimpos = window.itensTable.getData();
        } else if (window.itensCache && Array.isArray(window.itensCache)) {
            itensLimpos = window.itensCache;
        }

        itensLimpos = itensLimpos.map(item => {
            const novo = { ...item };
            const camposNum = [
                'qCom', 'vUnCom', 'vProd', 'qTrib', 'vUnTrib', 'vFrete', 'vSeg', 'vDesc', 'vOutro',
                'vAFRMM', 'vBC_IPI', 'pIPI', 'vIPI', 'vBC_II', 'vDespAdu', 'vII', 'vIOF',
                'vBC_PIS', 'pPIS', 'vPIS', 'vBC_COFINS', 'pCOFINS', 'vCOFINS'
            ];
            camposNum.forEach(k => {
                if (novo[k] !== undefined && novo[k] !== null && novo[k] !== '') {
                    let v = String(novo[k]).trim();
                    if (v.includes(',') && v.includes('.')) {
                        v = v.replace(/\./g, '').replace(',', '.');
                    } else if (v.includes(',')) {
                        v = v.replace(',', '.');
                    }
                    novo[k] = v;
                }
            });
            return novo;
        });

        return {
            cabecalho: {
                nNF: getVal('nNF'),
                serie: getVal('serie'),
                refNFe: (getVal('refNFe') || '').replace(/\D/g, '').slice(0, 44),
                natOp: getVal('natOp') || getVal('select_operacao'),
                cfop_padrao: getVal('cfop_padrao'),
                tpNF: getVal('tpNF'),
                idDest: getVal('idDest'),
                chaveAcesso: getVal('chaveAcesso'),
                cNF: getVal('cNF'),
                cUF: getVal('cUF'),
                dhEmi: getVal('dhEmi'),
                mod: getVal('mod'),
                tpEmis: getVal('tpEmis'),
                cDV: getVal('cDV'),
                emit_xNome: getVal('emit_xNome'),
                emit_CNPJ: getVal('emit_CNPJ'),
                emit_xLgr: getVal('emit_xLgr'),
                emit_nro: getVal('emit_nro'),
                emit_xBairro: getVal('emit_xBairro'),
                emit_cMun: getVal('emit_cMun'),
                emit_xMun: getVal('emit_xMun'),
                emit_UF: getVal('emit_UF'),
                emit_CEP: getVal('emit_CEP'),
                emit_IE: getVal('emit_IE') || (window.currentCabecalho && window.currentCabecalho.emit_IE) || '',
                emit_CRT: getVal('emit_CRT') || (window.currentCabecalho && window.currentCabecalho.emit_CRT) || '1',
                dest_xNome: getVal('dest_xNome'),
                dest_CNPJ_CPF: getVal('dest_CNPJ_CPF'),
                dest_idEstrangeiro: getVal('dest_idEstrangeiro') || (window.currentCabecalho && window.currentCabecalho.dest_idEstrangeiro) || '',
                dest_indIEDest: getVal('dest_indIEDest') || '9',
                dest_IE: getVal('dest_IE') || '',
                dest_xLgr: getVal('dest_xLgr'),
                dest_nro: getVal('dest_nro'),
                dest_xBairro: getVal('dest_xBairro'),
                dest_cMun: getVal('dest_cMun'),
                dest_xMun: getVal('dest_xMun'),
                dest_UF: getVal('dest_UF'),
                dest_CEP: getVal('dest_CEP'),
                dest_cPais: getVal('dest_cPais') || (window.currentCabecalho && window.currentCabecalho.dest_cPais) || '1058',
                dest_xPais: getVal('dest_xPais') || (window.currentCabecalho && window.currentCabecalho.dest_xPais) || 'Brasil',
                verProc: getVal('verProc') || '4.01_sebrae_b057',
                exporta_UFSaidaPais: getVal('exporta_UFSaidaPais'),
                exporta_xLocExporta: getVal('exporta_xLocExporta'),
                exporta_xLocDespacho: getVal('exporta_xLocDespacho')
            },
            referencia_interna: (typeof window.obterReferenciaInterna === 'function' ? window.obterReferenciaInterna() : (getVal('referenciaInterna') || getVal('referencia_interna') || '')).trim(),
            itens: itensLimpos,
            rodape: {
                infCpl: getVal('infCpl'),
                transporte: {
                    modFrete: getVal('transp_modFrete'),
                    CNPJ_CPF: getVal('transp_CNPJ_CPF'),
                    xNome: getVal('transp_xNome'),
                    IE: getVal('transp_IE'),
                    xEnder: getVal('transp_xEnder'),
                    xMun: getVal('transp_xMun'),
                    UF: getVal('transp_UF'),
                    CEP: getVal('transp_CEP'),
                    qVol: getVal('transp_qVol'),
                    esp: getVal('transp_esp'),
                    pesoL: mutatorLimparNumero(getVal('transp_pesoL')),
                    pesoB: mutatorLimparNumero(getVal('transp_pesoB'))
                },
                exportacao: {
                    UFSaidaPais: getVal('exporta_UFSaidaPais'),
                    xLocExporta: getVal('exporta_xLocExporta'),
                    xLocDespacho: getVal('exporta_xLocDespacho')
                },
                totais: {
                    vProd: mutatorLimparNumero(getVal('tot_vProd')),
                    vFrete: mutatorLimparNumero(getVal('tot_vFrete')),
                    vSeg: mutatorLimparNumero(getVal('tot_vSeg')),
                    vOutro: mutatorLimparNumero(getVal('tot_vOutro')),
                    vDesc: mutatorLimparNumero(getVal('tot_vDesc')),
                    vNF: mutatorLimparNumero(getVal('tot_vNF') || getVal('vNF')),
                    vBC: mutatorLimparNumero(getVal('tot_vBC')),
                    vICMS: mutatorLimparNumero(getVal('tot_vICMS')),
                    vBCST: mutatorLimparNumero(getVal('tot_vBCST')),
                    vST: mutatorLimparNumero(getVal('tot_vST')),
                    vII: mutatorLimparNumero(getVal('tot_vII')),
                    vIPI: mutatorLimparNumero(getVal('tot_vIPI')),
                    vPIS: mutatorLimparNumero(getVal('tot_vPIS')),
                    vCOFINS: mutatorLimparNumero(getVal('tot_vCOFINS'))
                }
            }
        };
    }

    function navegarParaAba(abaNome) {
        if (typeof window.sidebarSwitchTab !== 'function') return;
        const nome = String(abaNome).toLowerCase();
        if (nome.includes('item') || nome.includes('itens') || nome.includes('3')) {
            window.sidebarSwitchTab('itens');
        } else if (nome.includes('emitente') || nome.includes('destinatario') || nome.includes('identifica') || nome.includes('1') || nome.includes('2')) {
            window.sidebarSwitchTab('cabecalho');
        } else if (nome.includes('total') || nome.includes('transporte') || nome.includes('4')) {
            window.sidebarSwitchTab('rodape');
        } else if (nome.includes('tipo') || nome.includes('imposto')) {
            window.sidebarSwitchTab('tipo-nota');
        }
        
        // Fecha o modal após navegar
        if (modalElement && window.bootstrap && bootstrap.Modal) {
            const inst = bootstrap.Modal.getInstance(modalElement);
            if (inst) inst.hide();
        }
    }

    window.irParaAbaAnalise = function(abaNome) {
        navegarParaAba(abaNome);
    };

    window.fecharModalEGerarXML = function() {
        if (modalElement && window.bootstrap && bootstrap.Modal) {
            const inst = bootstrap.Modal.getInstance(modalElement);
            if (inst) inst.hide();
        }
        if (typeof window.generateXML === 'function') {
            window.generateXML();
        }
    };

    function renderizarResultadoAnalise(data) {
        const modal = getOrCreateModal();
        const headerEl = modal.querySelector('#modalAnaliseHeader');
        const iconWrap = modal.querySelector('#modalAnaliseIcon');
        const corpoEl = modal.querySelector('#modalAnaliseCorpo');
        const footerInfo = modal.querySelector('#modalAnaliseFooterInfo');
        const btnGerarXML = modal.querySelector('#btnGerarXMLModal');

        const totalErros = data.total_erros || 0;
        const totalAlertas = data.total_alertas || 0;
        const valido = data.valido === true;
        const resumo = data.resumo || {};

        footerInfo.innerText = `${resumo.total_itens || 0} itens analisados • NF nº ${resumo.n_nf || '-'} • Destinatário: ${resumo.destinatario || '-'}`;

        let statusBannerHtml = '';

        if (valido && totalAlertas === 0) {
            iconWrap.className = 'd-inline-flex align-items-center justify-content-center bg-success text-white shadow-sm';
            iconWrap.innerHTML = '<i data-lucide="check" style="width: 18px; height: 18px;"></i>';
            statusBannerHtml = `
                <div class="alert alert-success d-flex align-items-center gap-3 p-3 rounded-3 shadow-sm border-0 mb-3" style="background-color: rgba(16, 185, 129, 0.12); color: #065f46;">
                    <i data-lucide="check-circle-2" style="width: 28px; height: 28px; flex-shrink: 0;"></i>
                    <div>
                        <div class="fw-bold fs-6">Rascunho 100% Válido!</div>
                        <div class="small">Todos os campos obrigatórios e regras do esquema da NF-e 4.00 estão em total conformidade. Você já pode gerar o arquivo XML com segurança.</div>
                    </div>
                </div>
            `;
        } else if (valido && totalAlertas > 0) {
            iconWrap.className = 'd-inline-flex align-items-center justify-content-center bg-warning text-dark shadow-sm';
            iconWrap.innerHTML = '<i data-lucide="alert-triangle" style="width: 18px; height: 18px;"></i>';
            statusBannerHtml = `
                <div class="alert alert-warning d-flex align-items-center gap-3 p-3 rounded-3 shadow-sm border-0 mb-3" style="background-color: rgba(245, 158, 11, 0.15); color: #92400e;">
                    <i data-lucide="alert-circle" style="width: 28px; height: 28px; flex-shrink: 0;"></i>
                    <div>
                        <div class="fw-bold fs-6">Rascunho Apto com ${totalAlertas} Alerta(s) / Recomendações</div>
                        <div class="small">A estrutura do XML é válida, mas há avisos ou campos opcionais que merecem sua atenção antes da transmissão final à SEFAZ.</div>
                    </div>
                </div>
            `;
        } else {
            iconWrap.className = 'd-inline-flex align-items-center justify-content-center bg-danger text-white shadow-sm';
            iconWrap.innerHTML = '<i data-lucide="x" style="width: 18px; height: 18px;"></i>';
            statusBannerHtml = `
                <div class="alert alert-danger d-flex align-items-center gap-3 p-3 rounded-3 shadow-sm border-0 mb-3" style="background-color: rgba(239, 68, 68, 0.12); color: #991b1b;">
                    <i data-lucide="alert-octagon" style="width: 28px; height: 28px; flex-shrink: 0;"></i>
                    <div>
                        <div class="fw-bold fs-6">Rascunho com ${totalErros} Pendência(s) Obrigatória(s)</div>
                        <div class="small">Foram detectados campos sem preencher ou inconsistências que violam o esquema da NF-e e resultarão em rejeição imediata na SEFAZ.</div>
                    </div>
                </div>
            `;
        }

        // Cards de Resumo Rápido
        const formatMoeda = (val) => {
            return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        };

        const cardsResumoHtml = `
            <div class="row g-2 mb-3">
                <div class="col-6 col-md-3">
                    <div class="p-2 px-3 rounded-3 border bg-light text-center h-100">
                        <small class="text-muted d-block" style="font-size: 11px;">Itens na Nota</small>
                        <strong class="fs-6 text-dark font-monospace">${resumo.total_itens || 0}</strong>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="p-2 px-3 rounded-3 border bg-light text-center h-100">
                        <small class="text-muted d-block" style="font-size: 11px;">Total Produtos</small>
                        <strong class="fs-6 text-primary font-monospace">${formatMoeda(resumo.valor_total_produtos)}</strong>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="p-2 px-3 rounded-3 border bg-light text-center h-100">
                        <small class="text-muted d-block" style="font-size: 11px;">NF-e / Série</small>
                        <strong class="fs-6 text-dark font-monospace">${resumo.n_nf || '-'} / ${resumo.serie || '-'}</strong>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="p-2 px-3 rounded-3 border bg-light text-center h-100">
                        <small class="text-muted d-block" style="font-size: 11px;">Montagem XML</small>
                        <span class="badge py-1 px-2 bg-info-subtle text-info fw-bold" style="font-size: 11px;">
                            ${resumo.xml_construido ? '100% Ok' : 'Incompleto'}
                        </span>
                    </div>
                </div>
            </div>
        `;

        // Lista de Erros
        let errosHtml = '';
        if (totalErros > 0) {
            const itensErros = data.erros.map(e => `
                <li class="list-group-item d-flex justify-content-between align-items-start gap-2 py-2 px-3 border-danger-subtle" style="background-color: rgba(239, 68, 68, 0.03);">
                    <div class="ms-1 me-auto">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-info-subtle text-info fw-bold" style="font-size: 10.5px;">${e.categoria || 'Erro'}</span>
                            <strong class="text-dark" style="font-size: 13px;">${e.campo || ''}</strong>
                        </div>
                        <div class="text-secondary small">${e.mensagem || ''}</div>
                    </div>
                    <button type="button" class="btn-nft py-0 px-2 mt-1 shadow-none" onclick="irParaAbaAnalise('${e.aba}')" title="Ir para a aba para corrigir este campo" style="font-size: 11px; border-radius: 4px; white-space: nowrap;">
                        Corrigir na ${e.aba || 'Aba'} &rarr;
                    </button>
                </li>
            `).join('');

            errosHtml = `
                <div class="card border border-danger mb-3 shadow-sm rounded-3 overflow-hidden">
                    <div class="card-header py-2 px-3 d-flex justify-content-between align-items-center text-secondary">
                        <span class="fw-bold d-flex align-items-center gap-2" style="font-size: 13px;">
                            <i data-lucide="alert-octagon" style="width: 16px; height: 16px;"></i>
                            O que precisa ser corrigido (${totalErros}):
                        </span>
                    </div>
                    <ul class="list-group list-group-flush">
                        ${itensErros}
                    </ul>
                </div>
            `;
        }

        // Lista de Alertas
        let alertasHtml = '';
        if (totalAlertas > 0) {
            const itensAlertas = data.alertas.map(a => `
                <li class="list-group-item d-flex justify-content-between align-items-start gap-2 py-2 px-3 border-warning-subtle" style="background-color: rgba(245, 158, 11, 0.03);">
                    <div class="ms-1 me-auto">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-info-subtle text-info fw-bold" style="font-size: 10.5px;">${a.categoria || 'Aviso'}</span>
                            <strong class="text-dark" style="font-size: 13px;">${a.campo || ''}</strong>
                        </div>
                        <div class="text-secondary small">${a.mensagem || ''}</div>
                    </div>
                    <button type="button" class="btn-nft text-dark py-0 px-2 mt-1 shadow-none" onclick="irParaAbaAnalise('${a.aba}')" title="Ir para a aba para revisar este campo" style="font-size: 11px; border-radius: 4px; white-space: nowrap;">
                        Revisar na ${a.aba || 'Aba'} &rarr;
                    </button>
                </li>
            `).join('');

            alertasHtml = `
                <div class="card border border-warning mb-3 shadow-sm rounded-3 overflow-hidden">
                    <div class="card-header py-2 px-3 d-flex justify-content-between align-items-center text-secondary">
                        <span class="fw-bold d-flex align-items-center gap-2" style="font-size: 13px;">
                            <i data-lucide="alert-triangle" style="width: 16px; height: 16px;"></i>
                            Alertas e Recomendações (${totalAlertas}):
                        </span>
                    </div>
                    <ul class="list-group list-group-flush">
                        ${itensAlertas}
                    </ul>
                </div>
            `;
        }

        corpoEl.innerHTML = `
            ${statusBannerHtml}
            ${cardsResumoHtml}
            ${errosHtml}
            ${alertasHtml}
        `;

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }

        if (window.bootstrap && bootstrap.Modal) {
            const modalInstance = bootstrap.Modal.getOrCreateInstance(modal);
            modalInstance.show();
        }
    }

    // Função Principal Exposta Globalmente
    window.analisarRascunho = async function () {
        // Feedback visual no botão
        const btn = document.querySelector('.sidebar-footer-btn-analisar');
        let oldHtml = '';
        if (btn) {
            oldHtml = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span><span>Analisando...</span>';
            btn.disabled = true;
        }

        try {
            // Garante chave de acesso recalculada
            if (typeof window.calcularChaveAcessoDinamica === 'function') {
                window.calcularChaveAcessoDinamica();
            }

            const payload = coletarDadosRascunho();
            const res = await fetch('/api/analisar_rascunho', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || `Erro HTTP ${res.status}`);
            }

            const data = await res.json();
            renderizarResultadoAnalise(data);
        } catch (err) {
            console.error("Erro ao analisar rascunho:", err);
            if (window.nftAlert) {
                window.nftAlert(`Não foi possível concluir a análise do rascunho:\n${err.message}`, {
                    title: 'Falha na Análise',
                    type: 'danger'
                });
            } else {
                alert(`Erro ao analisar rascunho: ${err.message}`);
            }
        } finally {
            if (btn) {
                btn.innerHTML = oldHtml;
                btn.disabled = false;
                if (window.lucide && typeof window.lucide.createIcons === 'function') {
                    window.lucide.createIcons();
                }
            }
        }
    };
})();

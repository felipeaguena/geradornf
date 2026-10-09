/**
 * NFT Logistics - Gerenciador Avançado de Operações & Enquadramentos Fiscais
 * Módulo para reordenação Drag-and-Drop, busca/filtro e configuração de Regimes Tributários.
 */

(function () {
    'use strict';

    // Cache local das configurações de regimes tributários
    let regimesConfigCache = null;
    let dragSrcElement = null;

    // Regimes padrões de fallback
    const REGIMES_FALLBACK = {
        SUSPENSAO: {
            codigo: 'SUSPENSAO',
            nome: 'Suspensão de Impostos',
            icone: '🛡️',
            descricao: 'Admissão Temporária de mercadorias e Remessas/Retornos de Feiras e Exposições.',
            cfop_padrao: '3930',
            tp_nf: '0',
            id_dest: '3',
            csosn_icms: '400',
            c_enq_ipi: '108',
            cst_ipi: '55',
            p_ipi: 0.00,
            aliquota_ii: 0.00,
            cst_pis: '08',
            p_pis: 0.00,
            cst_cofins: '08',
            p_cofins: 0.00,
            t_pag: '90',
            inf_cpl_padrao: 'ADMISSAO TEMPORARIA DE CARGAS AO AMPARO DA IN RFB 1600/2016. SUSPENSAO DE TRIBUTOS FEDERAIS E ESTADUAIS (ICMS, IPI, PIS E COFINS). IPI SUSPENSO CONFORME ART. 43, INCISO I DO DECRETO 7.212/2010 (RIPI).'
        },
        ISENCAO: {
            codigo: 'ISENCAO',
            nome: 'Isenção Fiscal',
            icone: '🌱',
            descricao: 'Importação ou circulação de mercadorias com benefício de isenção legal de tributos.',
            cfop_padrao: '3949',
            tp_nf: '0',
            id_dest: '3',
            csosn_icms: '400',
            c_enq_ipi: '301',
            cst_ipi: '52',
            p_ipi: 0.00,
            aliquota_ii: 0.00,
            cst_pis: '07',
            p_pis: 0.00,
            cst_cofins: '07',
            p_cofins: 0.00,
            t_pag: '90',
            inf_cpl_padrao: 'ENTRADA DE IMPORTACAO COM BENEFICIO FISCAL DE ISENCAO DE TRIBUTOS FEDERAIS E ESTADUAIS CONFORME LEGISLACAO VIGENTE.'
        },
        RECOLHIMENTO: {
            codigo: 'RECOLHIMENTO',
            nome: 'Recolhimento Integral',
            icone: '💰',
            descricao: 'Operações tributadas regularmente com recolhimento integral (II, IPI, PIS, COFINS e ICMS).',
            cfop_padrao: '3949',
            tp_nf: '0',
            id_dest: '3',
            csosn_icms: '900',
            c_enq_ipi: '999',
            cst_ipi: '49',
            p_ipi: 0.00,
            aliquota_ii: 0.00,
            cst_pis: '01',
            p_pis: 1.65,
            cst_cofins: '01',
            p_cofins: 7.60,
            t_pag: '90',
            inf_cpl_padrao: 'ENTRADA DE IMPORTACAO COM TRIBUTACAO REGULAR E RECOLHIMENTO INTEGRAL DE TRIBUTOS (II, IPI, PIS, COFINS E ICMS).'
        },
        IMUNIDADE: {
            codigo: 'IMUNIDADE',
            nome: 'Imunidade Tributária',
            icone: '✈️',
            descricao: 'Reexportação de admissão temporária e exportações com imunidade tributária constitucional.',
            cfop_padrao: '7930',
            tp_nf: '1',
            id_dest: '3',
            csosn_icms: '400',
            c_enq_ipi: '999',
            cst_ipi: '55',
            p_ipi: 0.00,
            aliquota_ii: 0.00,
            cst_pis: '08',
            p_pis: 0.00,
            cst_cofins: '08',
            p_cofins: 0.00,
            t_pag: '90',
            inf_cpl_padrao: 'REEXPORTACAO DE MERCADORIA SOB REGIME ADUANEIRO ESPECIAL DE ADMISSAO TEMPORARIA. IMUNIDADE TRIBUTARIA CONSTITUCIONAL DE EXPORTACAO (ART. 153, PAR. 3, III DA CF/88).'
        }
    };

    // =========================================================================
    // 1. CARREGAMENTO E MANIPULAÇÃO DE CONFIGURAÇÕES DE REGIMES
    // =========================================================================

    async function carregarConfigRegimes(forcar = false) {
        if (regimesConfigCache && !forcar) {
            return regimesConfigCache;
        }
        try {
            const resp = await fetch('/api/config/regimes_tributarios');
            const data = await resp.json();
            if (data && data.status === 'success' && data.regimes) {
                regimesConfigCache = data.regimes;
            } else {
                regimesConfigCache = REGIMES_FALLBACK;
            }
        } catch (e) {
            console.warn('Erro ao carregar configurações de regimes fiscais:', e);
            regimesConfigCache = REGIMES_FALLBACK;
        }
        return regimesConfigCache;
    }

    // Aplica as regras do regime tributário selecionado aos campos do formulário da operação
    window.aplicarPresetDoRegimeAoFormOperacao = async function () {
        const regimeEl = document.getElementById('op_regime');
        if (!regimeEl) return;
        const regime = regimeEl.value || 'SUSPENSAO';

        const configs = await carregarConfigRegimes();
        const conf = configs[regime] || REGIMES_FALLBACK[regime];
        if (!conf) return;

        // Preenche campos do formulário de operação se existirem
        if (typeof setVal === 'function') {
            if (conf.cfop_padrao && !document.getElementById('op_cfop').value) setVal('op_cfop', conf.cfop_padrao);
            if (conf.tp_nf !== undefined) setVal('op_tp_nf', conf.tp_nf);
            if (conf.id_dest !== undefined) setVal('op_id_dest', conf.id_dest);
            if (conf.csosn_icms) setVal('op_csosn', conf.csosn_icms);
            if (conf.c_enq_ipi) setVal('op_c_enq', conf.c_enq_ipi);
            if (conf.cst_ipi) setVal('op_cst_ipi', conf.cst_ipi);
            if (conf.p_ipi !== undefined) setVal('op_p_ipi', Number(conf.p_ipi || 0).toFixed(2));
            if (conf.aliquota_ii !== undefined) setVal('op_aliquota_ii', Number(conf.aliquota_ii || 0).toFixed(2));
            if (conf.cst_pis) setVal('op_cst_pis', conf.cst_pis);
            if (conf.p_pis !== undefined) setVal('op_p_pis', Number(conf.p_pis || 0).toFixed(2));
            if (conf.cst_cofins) setVal('op_cst_cofins', conf.cst_cofins);
            if (conf.p_cofins !== undefined) setVal('op_p_cofins', Number(conf.p_cofins || 0).toFixed(2));
            if (conf.t_pag) setVal('op_t_pag', conf.t_pag);
            if (conf.inf_cpl_padrao && !document.getElementById('op_inf_cpl').value) {
                setVal('op_inf_cpl', conf.inf_cpl_padrao);
            }
        }

        window.atualizarResumoRegimeForm(regime);

        if (window.nftToast) {
            window.nftToast(`Parâmetros fiscais do regime "${conf.nome}" aplicados ao formulário!`, { type: 'success' });
        } else {
            console.log(`Parâmetros do regime ${conf.nome} aplicados.`);
        }
    };

    // Atualiza o resumo visual logo abaixo do select de regime na operação
    window.atualizarResumoRegimeForm = async function (regime) {
        const resumoEl = document.getElementById('op_regime_info');
        if (!resumoEl) return;
        const configs = await carregarConfigRegimes();
        const conf = configs[regime] || REGIMES_FALLBACK[regime];
        if (!conf) {
            resumoEl.innerText = '';
            return;
        }

        let resumoTxt = `${conf.icone} ${conf.nome}: `;
        if (regime === 'SUSPENSAO') {
            resumoTxt += `cEnq ${conf.c_enq_ipi} | CST IPI ${conf.cst_ipi} | PIS/COFINS ${conf.cst_pis} | Pagamento ${conf.t_pag} (Sem Pagamento) | Impostos Zerados`;
        } else if (regime === 'ISENCAO') {
            resumoTxt += `cEnq ${conf.c_enq_ipi} | CST IPI ${conf.cst_ipi} | PIS/COFINS ${conf.cst_pis} | Pagamento ${conf.t_pag} | Isenção Legal de Tributos`;
        } else if (regime === 'RECOLHIMENTO') {
            resumoTxt += `cEnq ${conf.c_enq_ipi} | CST IPI ${conf.cst_ipi} | PIS ${conf.cst_pis} (${conf.p_pis}%) | COFINS ${conf.cst_cofins} (${conf.p_cofins}%) | Tributação Regular`;
        } else if (regime === 'IMUNIDADE') {
            resumoTxt += `cEnq ${conf.c_enq_ipi} | CST IPI ${conf.cst_ipi} | PIS/COFINS ${conf.cst_pis} | Pagamento ${conf.t_pag} | Imunidade Aduaneira de Reexportação`;
        }
        resumoEl.innerText = resumoTxt;
    };

    // =========================================================================
    // 2. MODAL DE CONFIGURAÇÃO DE ENQUADRAMENTOS FISCAIS
    // =========================================================================

    function injetarModalConfigRegimesHTML() {
        if (document.getElementById('modal-config-regimes')) return;

        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modal-config-regimes';
        modalDiv.tabIndex = -1;
        modalDiv.setAttribute('aria-hidden', 'true');
        modalDiv.setAttribute('data-bs-backdrop', 'static');

        modalDiv.innerHTML = `
        <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content border-0 shadow-lg">
                <div class="modal-header bg-dark text-white py-3">
                    <div class="d-flex align-items-center gap-2">
                        <i data-lucide="sliders" class="text-primary"></i>
                        <div>
                            <h5 class="modal-title fw-bold mb-0 text-white">Configurações dos Enquadramentos Fiscais</h5>
                            <small class="text-white-50" style="font-size: 11px;">
                                Padronize regras padrão de cEnq, CSTs, Meio de Pagamento e Fundamentação Legal para cada regime.
                            </small>
                        </div>
                    </div>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-3 p-md-4">
                    <!-- Nav Tabs para os 4 Regimes -->
                    <ul class="nav nav-pills nav-fill mb-3 p-1 bg-body-tertiary rounded border" id="pills-regimes-tab" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active fw-bold py-2" id="pill-suspensao-tab" data-bs-toggle="pill" data-bs-target="#pill-suspensao" type="button" role="tab">
                                🛡️ Suspensão
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link fw-bold py-2" id="pill-isencao-tab" data-bs-toggle="pill" data-bs-target="#pill-isencao" type="button" role="tab">
                                🌱 Isenção
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link fw-bold py-2" id="pill-recolhimento-tab" data-bs-toggle="pill" data-bs-target="#pill-recolhimento" type="button" role="tab">
                                💰 Recolhimento
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link fw-bold py-2" id="pill-imunidade-tab" data-bs-toggle="pill" data-bs-target="#pill-imunidade" type="button" role="tab">
                                ✈️ Imunidade
                            </button>
                        </li>
                    </ul>

                    <!-- Conteúdo das Abas dos Regimes -->
                    <div class="tab-content" id="pills-regimes-tabContent">
                        ${renderizarFormRegimeHTML('SUSPENSAO', '🛡️ Suspensão de Impostos', 'Admissão Temporária (3930), Remessas/Retornos de Feira (5914, 6914, 1914, 2914)')}
                        ${renderizarFormRegimeHTML('ISENCAO', '🌱 Isenção Fiscal', 'Outras Entradas de Mercadoria com Isenção Legal de Tributos (3949)')}
                        ${renderizarFormRegimeHTML('RECOLHIMENTO', '💰 Recolhimento Integral', 'Entrada com Tributação Regular e Recolhimento Integral de Impostos (3949)')}
                        ${renderizarFormRegimeHTML('IMUNIDADE', '✈️ Imunidade Tributária', 'Reexportação de Admissão Temporária ao Exterior (7930, 7949)')}
                    </div>
                </div>
                <div class="modal-footer d-flex justify-content-between py-2 bg-body-tertiary">
                    <button type="button" class="btn btn-outline-danger btn-sm d-flex align-items-center gap-1" onclick="restaurarConfigRegimesPadrao()">
                        <i data-lucide="rotate-ccw"></i>
                        <span>Restaurar Padrões Fiscais</span>
                    </button>
                    <div class="d-flex align-items-center gap-2">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-primary btn-sm fw-bold d-flex align-items-center gap-1 shadow-sm" onclick="salvarConfigRegimesTributarios()">
                            <i data-lucide="save"></i>
                            <span>Salvar Configurações</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;

        document.body.appendChild(modalDiv);
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    function renderizarFormRegimeHTML(prefix, titulo, desc) {
        return `
        <div class="tab-pane fade ${prefix === 'SUSPENSAO' ? 'show active' : ''}" id="pill-${prefix.toLowerCase()}" role="tabpanel">
            <div class="alert alert-light border d-flex align-items-center gap-2 py-2 mb-3">
                <i data-lucide="info" class="text-primary"></i>
                <div class="small">
                    <strong>${titulo}</strong>: ${desc}
                </div>
            </div>
            <div class="row g-3">
                <div class="col-md-3">
                    <label class="form-label small fw-bold">CFOP Sugerido</label>
                    <input type="text" class="form-control form-control-sm font-monospace fw-bold" id="cfg_${prefix}_cfop" placeholder="Ex: 3930, 3949">
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold">Tipo da NF (tpNF)</label>
                    <select class="form-select form-select-sm" id="cfg_${prefix}_tp_nf">
                        <option value="0">0 - Entrada</option>
                        <option value="1">1 - Saída</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold">Destino (idDest)</label>
                    <select class="form-select form-select-sm" id="cfg_${prefix}_id_dest">
                        <option value="1">1 - Interna</option>
                        <option value="2">2 - Interestadual</option>
                        <option value="3" selected>3 - Exterior</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold">Meio de Pagamento (tPag)</label>
                    <select class="form-select form-select-sm fw-bold" id="cfg_${prefix}_t_pag">
                        <option value="90">90 - Sem Pagamento (SEFAZ vPag=0)</option>
                        <option value="99">99 - Outros (Câmbio / Exterior)</option>
                        <option value="01">01 - Dinheiro</option>
                        <option value="15">15 - Boleto Bancário</option>
                        <option value="17">17 - PIX</option>
                    </select>
                </div>

                <!-- ICMS & IPI -->
                <div class="col-12"><h6 class="border-bottom pb-1 mb-1 mt-2 fw-bold text-heading">Tributos Federais e Estaduais Padrão</h6></div>
                <div class="col-md-4">
                    <label class="form-label small">CSOSN / CST ICMS</label>
                    <input type="text" class="form-control form-control-sm font-monospace" id="cfg_${prefix}_csosn" placeholder="Ex: 400, 900, 102">
                </div>
                <div class="col-md-4">
                    <label class="form-label small">Código de Enquadramento IPI (cEnq)</label>
                    <input type="text" class="form-control form-control-sm font-monospace fw-bold" id="cfg_${prefix}_c_enq" placeholder="Ex: 108, 107, 301, 999">
                </div>
                <div class="col-md-2">
                    <label class="form-label small">CST IPI</label>
                    <input type="text" class="form-control form-control-sm font-monospace" id="cfg_${prefix}_cst_ipi" placeholder="Ex: 55, 05, 52, 49">
                </div>
                <div class="col-md-2">
                    <label class="form-label small">Alíquota IPI (%)</label>
                    <input type="number" step="0.01" class="form-control form-control-sm" id="cfg_${prefix}_p_ipi" value="0.00">
                </div>

                <!-- PIS & COFINS -->
                <div class="col-md-3">
                    <label class="form-label small">CST PIS</label>
                    <input type="text" class="form-control form-control-sm font-monospace" id="cfg_${prefix}_cst_pis" placeholder="Ex: 08, 07, 01">
                </div>
                <div class="col-md-3">
                    <label class="form-label small">Alíquota PIS (%)</label>
                    <input type="number" step="0.01" class="form-control form-control-sm" id="cfg_${prefix}_p_pis" value="0.00">
                </div>
                <div class="col-md-3">
                    <label class="form-label small">CST COFINS</label>
                    <input type="text" class="form-control form-control-sm font-monospace" id="cfg_${prefix}_cst_cofins" placeholder="Ex: 08, 07, 01">
                </div>
                <div class="col-md-3">
                    <label class="form-label small">Alíquota COFINS (%)</label>
                    <input type="number" step="0.01" class="form-control form-control-sm" id="cfg_${prefix}_p_cofins" value="0.00">
                </div>

                <!-- Fundamentação Legal infCpl -->
                <div class="col-12">
                    <label class="form-label small fw-bold">Texto Padrão de Fundamentação Legal (infCpl sugerido no rodapé)</label>
                    <textarea class="form-control form-control-sm" id="cfg_${prefix}_inf_cpl" rows="2" placeholder="Fundamentação legal sugerida para esta nota..."></textarea>
                </div>
            </div>
        </div>
        `;
    }

    // Abre a modal e preenche os campos com os valores atuais
    window.abrirModalConfigRegimes = async function () {
        injetarModalConfigRegimesHTML();
        const configs = await carregarConfigRegimes();

        ['SUSPENSAO', 'ISENCAO', 'RECOLHIMENTO', 'IMUNIDADE'].forEach(prefix => {
            const conf = configs[prefix] || REGIMES_FALLBACK[prefix];
            if (!conf) return;

            const elCfop = document.getElementById(`cfg_${prefix}_cfop`);
            if (elCfop) elCfop.value = conf.cfop_padrao || '';
            const elTpNf = document.getElementById(`cfg_${prefix}_tp_nf`);
            if (elTpNf) elTpNf.value = conf.tp_nf || '0';
            const elIdDest = document.getElementById(`cfg_${prefix}_id_dest`);
            if (elIdDest) elIdDest.value = conf.id_dest || '3';
            const elTPag = document.getElementById(`cfg_${prefix}_t_pag`);
            if (elTPag) elTPag.value = conf.t_pag || '90';
            const elCsosn = document.getElementById(`cfg_${prefix}_csosn`);
            if (elCsosn) elCsosn.value = conf.csosn_icms || '';
            const elCEnq = document.getElementById(`cfg_${prefix}_c_enq`);
            if (elCEnq) elCEnq.value = conf.c_enq_ipi || '';
            const elCstIpi = document.getElementById(`cfg_${prefix}_cst_ipi`);
            if (elCstIpi) elCstIpi.value = conf.cst_ipi || '';
            const elPIpi = document.getElementById(`cfg_${prefix}_p_ipi`);
            if (elPIpi) elPIpi.value = Number(conf.p_ipi || 0).toFixed(2);
            const elCstPis = document.getElementById(`cfg_${prefix}_cst_pis`);
            if (elCstPis) elCstPis.value = conf.cst_pis || '';
            const elPPis = document.getElementById(`cfg_${prefix}_p_pis`);
            if (elPPis) elPPis.value = Number(conf.p_pis || 0).toFixed(2);
            const elCstCofins = document.getElementById(`cfg_${prefix}_cst_cofins`);
            if (elCstCofins) elCstCofins.value = conf.cst_cofins || '';
            const elPCofins = document.getElementById(`cfg_${prefix}_p_cofins`);
            if (elPCofins) elPCofins.value = Number(conf.p_cofins || 0).toFixed(2);
            const elInfCpl = document.getElementById(`cfg_${prefix}_inf_cpl`);
            if (elInfCpl) elInfCpl.value = conf.inf_cpl_padrao || '';
        });

        const modalEl = document.getElementById('modal-config-regimes');
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            const m = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            m.show();
        }
    };

    // Salva as configurações editadas no backend
    window.salvarConfigRegimesTributarios = async function () {
        const payload = { regimes: {} };

        ['SUSPENSAO', 'ISENCAO', 'RECOLHIMENTO', 'IMUNIDADE'].forEach(prefix => {
            const base = REGIMES_FALLBACK[prefix];
            payload.regimes[prefix] = {
                codigo: prefix,
                nome: base.nome,
                icone: base.icone,
                descricao: base.descricao,
                cfop_padrao: (document.getElementById(`cfg_${prefix}_cfop`)?.value || base.cfop_padrao).trim(),
                tp_nf: document.getElementById(`cfg_${prefix}_tp_nf`)?.value || base.tp_nf,
                id_dest: document.getElementById(`cfg_${prefix}_id_dest`)?.value || base.id_dest,
                t_pag: document.getElementById(`cfg_${prefix}_t_pag`)?.value || base.t_pag,
                csosn_icms: (document.getElementById(`cfg_${prefix}_csosn`)?.value || base.csosn_icms).trim(),
                c_enq_ipi: (document.getElementById(`cfg_${prefix}_c_enq`)?.value || base.c_enq_ipi).trim(),
                cst_ipi: (document.getElementById(`cfg_${prefix}_cst_ipi`)?.value || base.cst_ipi).trim(),
                p_ipi: parseFloat(document.getElementById(`cfg_${prefix}_p_ipi`)?.value || 0),
                aliquota_ii: 0.00,
                cst_pis: (document.getElementById(`cfg_${prefix}_cst_pis`)?.value || base.cst_pis).trim(),
                p_pis: parseFloat(document.getElementById(`cfg_${prefix}_p_pis`)?.value || 0),
                cst_cofins: (document.getElementById(`cfg_${prefix}_cst_cofins`)?.value || base.cst_cofins).trim(),
                p_cofins: parseFloat(document.getElementById(`cfg_${prefix}_p_cofins`)?.value || 0),
                inf_cpl_padrao: (document.getElementById(`cfg_${prefix}_inf_cpl`)?.value || base.inf_cpl_padrao).trim()
            };
        });

        try {
            const resp = await fetch('/api/config/regimes_tributarios', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (data.status === 'success') {
                regimesConfigCache = data.regimes;

                // Atualiza resumo no formulário se estiver visível
                const opRegimeEl = document.getElementById('op_regime');
                if (opRegimeEl) {
                    window.atualizarResumoRegimeForm(opRegimeEl.value);
                }

                // Fecha modal
                const modalEl = document.getElementById('modal-config-regimes');
                if (modalEl && window.bootstrap && window.bootstrap.Modal) {
                    const m = bootstrap.Modal.getInstance(modalEl);
                    if (m) m.hide();
                }

                if (window.nftToast) {
                    window.nftToast('Configurações dos Enquadramentos Fiscais salvas com sucesso!', { type: 'success' });
                } else {
                    alert('Configurações dos Enquadramentos Fiscais salvas com sucesso!');
                }
            } else {
                alert('Erro ao salvar configurações: ' + (data.message || 'Erro desconhecido'));
            }
        } catch (e) {
            console.error('Falha ao salvar regimes tributarios:', e);
            alert('Falha na comunicação com o servidor para salvar configurações.');
        }
    };

    // Restaura padrões fiscais
    window.restaurarConfigRegimesPadrao = async function () {
        const confirmar = confirm('Deseja restaurar todas as regras dos Enquadramentos Fiscais para os padrões fiscais oficiais (RIPI Art. 43, IN 1600, etc.)?');
        if (!confirmar) return;

        try {
            const resp = await fetch('/api/config/regimes_tributarios/reset', { method: 'POST' });
            const data = await resp.json();
            if (data.status === 'success') {
                regimesConfigCache = data.regimes;
                window.abrirModalConfigRegimes();
                if (window.nftToast) {
                    window.nftToast('Padrões fiscais restaurados com sucesso!', { type: 'info' });
                }
            }
        } catch (e) {
            console.error('Erro ao restaurar padrões:', e);
        }
    };

    // =========================================================================
    // 3. REORGANIZAÇÃO COM CLICK E ARRASTE (DRAG-AND-DROP) & FILTRO DE OPERAÇÕES
    // =========================================================================

    // Renderiza a lista de operações com suporte a drag-and-drop e filtro
    window.renderizarListaOperacoesCadastradas = function (operacoesParaExibir) {
        const lista = document.getElementById('lista-operacoes');
        if (!lista) return;

        const termoFiltro = (document.getElementById('filtro-operacoes')?.value || '').toLowerCase().trim();
        const ops = Array.isArray(operacoesParaExibir) ? operacoesParaExibir : (window.operacoesCache || []);

        lista.innerHTML = '';

        // Filtra por nome, CFOP ou regime se houver busca
        const opsFiltradas = ops.filter(op => {
            if (!termoFiltro) return true;
            const nome = (op.nome_operacao || '').toLowerCase();
            const cfop = (op.cfop_padrao || '').toLowerCase();
            const regime = (op.regime_tributario || '').toLowerCase();
            return nome.includes(termoFiltro) || cfop.includes(termoFiltro) || regime.includes(termoFiltro);
        });

        // Atualiza contador de operações
        const badgeContador = document.getElementById('badge-total-operacoes');
        if (badgeContador) {
            badgeContador.innerText = `${opsFiltradas.length} operação${opsFiltradas.length !== 1 ? 'ões' : ''}`;
        }

        if (opsFiltradas.length === 0) {
            lista.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i data-lucide="search-x" class="mb-2" style="width: 28px; height: 28px;"></i>
                    <p class="mb-0 small">Nenhuma operação localizada para "${termoFiltro}".</p>
                </div>
            `;
            if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
            return;
        }

        opsFiltradas.forEach((op, index) => {
            const item = document.createElement('div');
            item.className = 'list-group-item list-group-item-action py-2 px-3 border rounded mb-1 op-drag-item';
            item.setAttribute('draggable', termoFiltro ? 'false' : 'true'); // Desabilita drag enquanto filtra para não corromper posições
            item.setAttribute('data-id', op.id);
            item.setAttribute('data-index', index);
            item.style.cursor = 'pointer';
            item.style.transition = 'all 0.15s ease-in-out';

            // Ícones de Regime
            let regimeBadge = '';
            const reg = (op.regime_tributario || '').toUpperCase();
            if (reg === 'SUSPENSAO') {
                regimeBadge = '<span class="badge bg-secondary-subtle text-secondary" style="font-size: 10px;">🛡️ Suspensão</span>';
            } else if (reg === 'ISENCAO') {
                regimeBadge = '<span class="badge bg-success-subtle text-success" style="font-size: 10px;">🌱 Isenção</span>';
            } else if (reg === 'RECOLHIMENTO') {
                regimeBadge = '<span class="badge bg-primary-subtle text-primary" style="font-size: 10px;">💰 Recolhimento</span>';
            } else if (reg === 'IMUNIDADE') {
                regimeBadge = '<span class="badge bg-info-subtle text-info" style="font-size: 10px;">✈️ Imunidade</span>';
            }

            const tipoTxt = (op.tp_nf == '1') ? '1-Saída' : '0-Entrada';
            const destTxt = (op.id_dest == '1') ? 'Interna' : (op.id_dest == '2' ? 'Interestadual' : 'Exterior');

            item.innerHTML = `
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center gap-2" style="min-width: 0;">
                        ${!termoFiltro ? '<i data-lucide="grip-vertical" class="text-muted grip-handle cursor-grab flex-shrink-0" title="Arraste para reordenar" style="cursor: grab; width: 16px; height: 16px;"></i>' : ''}
                        <div class="text-truncate">
                            <span class="fw-bold font-monospace text-primary">(${op.cfop_padrao})</span>
                            <span class="fw-bold text-heading ms-1">${op.nome_operacao}</span>
                        </div>
                    </div>
                    <div class="flex-shrink-0 ms-2">
                        ${regimeBadge}
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2 mt-1 text-muted" style="font-size: 11px;">
                    <span>${tipoTxt}</span>
                    <span>•</span>
                    <span>Dest: ${destTxt}</span>
                    <span>•</span>
                    <span>cEnq: ${op.c_enq_ipi || '108'}</span>
                    <span>•</span>
                    <span>CST IPI: ${op.cst_ipi || '55'}</span>
                    <span>•</span>
                    <span>tPag: ${op.t_pag || '90'}</span>
                </div>
            `;

            // Clique simples para editar a operação
            item.onclick = function (e) {
                // Não dispara edição se estiver arrastando
                if (item.classList.contains('dragging')) return;
                if (typeof selecionarOperacaoParaEdicao === 'function') {
                    selecionarOperacaoParaEdicao(op);
                }
                // Destaque visual do selecionado
                document.querySelectorAll('#lista-operacoes .op-drag-item').forEach(el => el.classList.remove('active', 'border-primary', 'active-op-item', 'bg-light'));
                item.classList.add('border-primary', 'active-op-item');
            };

            // Eventos Drag and Drop (apenas quando não há filtro ativo)
            if (!termoFiltro) {
                item.addEventListener('dragstart', handleDragStart);
                item.addEventListener('dragover', handleDragOver);
                item.addEventListener('dragleave', handleDragLeave);
                item.addEventListener('drop', handleDrop);
                item.addEventListener('dragend', handleDragEnd);
            }

            lista.appendChild(item);
        });

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    };

    // =========================================================================
    // 4. HANDLERS DRAG AND DROP
    // =========================================================================

    function handleDragStart(e) {
        dragSrcElement = this;
        this.classList.add('dragging');
        this.style.opacity = '0.4';
        this.style.borderColor = '#0d6efd';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.getAttribute('data-id'));
    }

    function handleDragOver(e) {
        if (e.preventDefault) e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        if (this !== dragSrcElement) {
            this.classList.add('op-drag-target-over');
            this.style.borderTop = '2px solid #0d6efd';
        }
        return false;
    }

    function handleDragLeave() {
        this.classList.remove('op-drag-target-over');
        this.style.borderTop = '';
    }

    async function handleDrop(e) {
        if (e.stopPropagation) e.stopPropagation();
        this.classList.remove('op-drag-target-over');
        this.style.borderTop = '';

        if (dragSrcElement && dragSrcElement !== this) {
            const srcId = parseInt(dragSrcElement.getAttribute('data-id'));
            const targetId = parseInt(this.getAttribute('data-id'));

            // Reordena o array operacoesCache
            if (Array.isArray(window.operacoesCache)) {
                const srcIdx = window.operacoesCache.findIndex(o => o.id === srcId);
                const targetIdx = window.operacoesCache.findIndex(o => o.id === targetId);

                if (srcIdx >= 0 && targetIdx >= 0) {
                    const itemMovido = window.operacoesCache.splice(srcIdx, 1)[0];
                    window.operacoesCache.splice(targetIdx, 0, itemMovido);

                    // Re-renderiza a lista imediatamente
                    window.renderizarListaOperacoesCadastradas(window.operacoesCache);

                    // Atualiza o select de operações na tela
                    atualizarSelectOperacoesComNovaOrdem(window.operacoesCache);

                    // Persiste a nova ordem no backend
                    const ordemIds = window.operacoesCache.map(o => o.id);
                    try {
                        await fetch('/api/operacoes/reordenar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ordem_ids: ordemIds })
                        });
                        if (window.nftToast) {
                            window.nftToast('Ordem das operações atualizada!', { type: 'success' });
                        }
                    } catch (err) {
                        console.error('Falha ao salvar ordem de operações:', err);
                    }
                }
            }
        }
        return false;
    }

    function handleDragEnd() {
        this.classList.remove('dragging');
        this.style.opacity = '1';
        this.style.borderColor = '';
        document.querySelectorAll('#lista-operacoes .op-drag-item').forEach(el => {
            el.classList.remove('op-drag-target-over');
            el.style.borderTop = '';
        });
    }

    function atualizarSelectOperacoesComNovaOrdem(novaLista) {
        const sel = document.getElementById('select_operacao');
        if (!sel || !Array.isArray(novaLista)) return;
        const valorAtual = sel.value;

        sel.innerHTML = '<option value="">-- Selecione a Operação Fiscal --</option>';
        novaLista.forEach(op => {
            const opt = document.createElement('option');
            opt.value = op.nome_operacao;
            opt.text = `(${op.cfop_padrao}) ${op.nome_operacao}`;
            sel.appendChild(opt);
        });

        if (valorAtual) sel.value = valorAtual;
    }

    // =========================================================================
    // 5. FILTRO EM TEMPO REAL
    // =========================================================================

    window.filtrarOperacoesCadastradas = function (termo) {
        window.renderizarListaOperacoesCadastradas(window.operacoesCache);
    };

    window.limparFiltroOperacoes = function () {
        const inp = document.getElementById('filtro-operacoes');
        if (inp) {
            inp.value = '';
            window.renderizarListaOperacoesCadastradas(window.operacoesCache);
            inp.focus();
        }
    };

    // Inicialização ao carregar o DOM
    document.addEventListener('DOMContentLoaded', function () {
        injetarModalConfigRegimesHTML();
        carregarConfigRegimes();

        // Vincula evento no select de regime da operação se já existir
        const selRegimeOp = document.getElementById('op_regime');
        if (selRegimeOp) {
            selRegimeOp.addEventListener('change', function () {
                window.atualizarResumoRegimeForm(this.value);
            });
            window.atualizarResumoRegimeForm(selRegimeOp.value);
        }
    });

    if (document.body) {
        injetarModalConfigRegimesHTML();
        carregarConfigRegimes();
    }
})();

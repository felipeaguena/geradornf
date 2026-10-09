/**
 * NFT Logistics - Cadastro Rápido de Empresas & Integração Automática com a NF-e
 * Permite cadastrar uma nova empresa em popup sem sair da digitação da nota,
 * salva no banco de dados (Listagem de Empresas) e preenche os campos do Destinatário instantaneamente.
 */

(function () {
    'use strict';

    let _empresaAlvo = 'dest'; // 'dest', 'emit', 'transp'

    // =========================================================================
    // 1. INJEÇÃO DO MODAL NO DOM
    // =========================================================================
    function injetarModalNovaEmpresaRapidaHTML() {
        if (document.getElementById('modal-nova-empresa-rapida')) return;

        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modal-nova-empresa-rapida';
        modalDiv.tabIndex = -1;
        modalDiv.setAttribute('aria-hidden', 'true');
        modalDiv.setAttribute('data-bs-backdrop', 'static');

        modalDiv.innerHTML = `
        <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content border-0 shadow-lg">
                <div class="modal-header bg-dark text-white py-3">
                    <div class="d-flex align-items-center gap-2">
                        <div class="p-2 rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">
                            <i data-lucide="building-2" style="width: 20px; height: 20px;"></i>
                        </div>
                        <div>
                            <h5 class="modal-title fw-bold mb-0 text-white" id="modal-rapida-titulo">Adicionar Nova Empresa</h5>
                            <small class="text-white-50" style="font-size: 11.5px;">
                                Cadastra na Listagem de Empresas & Cadastros e preenche automaticamente na nota fiscal.
                            </small>
                        </div>
                    </div>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>

                <div class="modal-body p-3 p-md-4">
                    <form id="formNovaEmpresaRapida" onsubmit="window.salvarNovaEmpresaRapido(event)">
                        <!-- SEÇÃO 1: DADOS PRINCIPAIS -->
                        <div class="d-flex align-items-center justify-content-between border-bottom pb-2 mb-3">
                            <h6 class="fw-bold text-heading mb-0 d-flex align-items-center gap-2">
                                <i data-lucide="info" class="text-primary" style="width: 16px; height: 16px;"></i>
                                <span>Dados Principais da Empresa</span>
                            </h6>
                            <span class="badge bg-primary-subtle text-primary font-monospace" id="rap_badge_tipo">Destinatário</span>
                        </div>

                        <div class="row g-2 mb-3">
                            <div class="col-md-3">
                                <label class="form-label small fw-bold">Categoria / Tipo <span class="text-danger">*</span></label>
                                <select class="form-select form-select-sm fw-bold" id="rap_tipo" required>
                                    <option value="Cliente" selected>Cliente</option>
                                    <option value="Emitente">Emitente</option>
                                    <option value="Transportadora">Transportadora</option>
                                    <option value="Armazem">Armazém</option>
                                    <option value="Local de Desembaraço">Local de Desembaraço</option>
                                    <option value="Exportador">Exportador / Fornecedor</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small fw-bold">Localização</label>
                                <select class="form-select form-select-sm fw-bold border-primary" id="rap_localidade" onchange="window.aoMudarLocalidadeRapida()">
                                    <option value="Brasil" selected>Brasil (Nacional)</option>
                                    <option value="Exterior">Exterior</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">CNPJ / CPF / IdEstrangeiro</label>
                                <div class="input-group input-group-sm">
                                    <input type="text" class="form-control form-control-sm font-monospace fw-bold mask-cnpj-cpf" id="rap_cnpj_cpf" placeholder="00.000.000/0000-00">
                                    <button type="button" class="btn btn-outline-primary btn-sm d-flex align-items-center gap-1" id="btn-busca-cnpj-rapido" onclick="window.buscarCnpjRapido()" title="Consultar CNPJ na Receita / BrasilAPI">
                                        <i data-lucide="search" style="width: 13px; height: 13px;"></i>
                                        <span class="small fw-bold">Buscar CNPJ</span>
                                    </button>
                                </div>
                                <small class="text-muted" id="rap_cnpj_status" style="font-size: 10.5px;"></small>
                            </div>

                            <div class="col-md-7">
                                <label class="form-label small fw-bold">Razão Social / Nome Oficial (xNome) <span class="text-danger">*</span></label>
                                <input type="text" class="form-control form-control-sm fw-bold" id="rap_nome" placeholder="Nome completo ou Razão Social" required>
                            </div>
                            <div class="col-md-5">
                                <label class="form-label small fw-bold">Nome Fantasia / Apelido</label>
                                <input type="text" class="form-control form-control-sm" id="rap_apelido" placeholder="Nome Fantasia para identificação rápida">
                            </div>

                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Inscrição Estadual (IE)</label>
                                <input type="text" class="form-control form-control-sm font-monospace" id="rap_ie" placeholder="Apenas p/ Contribuinte ICMS">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Indicador de IE (indIEDest)</label>
                                <select class="form-select form-select-sm" id="rap_ind_ie" onchange="window.aoMudarIndIeRapida()">
                                    <option value="1">1 - Contribuinte ICMS</option>
                                    <option value="2">2 - Isento de Contribuição</option>
                                    <option value="9" selected>9 - Não Contribuinte</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Telefone / Contato</label>
                                <input type="text" class="form-control form-control-sm mask-telefone font-monospace" id="rap_fone" placeholder="(00) 00000-0000">
                            </div>
                        </div>

                        <!-- SEÇÃO 2: ENDEREÇO -->
                        <div class="d-flex align-items-center justify-content-between border-bottom pb-2 mb-3 mt-4">
                            <h6 class="fw-bold text-heading mb-0 d-flex align-items-center gap-2">
                                <i data-lucide="map-pin" class="text-primary" style="width: 16px; height: 16px;"></i>
                                <span>Endereço Completo</span>
                            </h6>
                            <small class="text-muted" style="font-size: 11px;">Busca automática via CEP ou preenchimento manual</small>
                        </div>

                        <div class="row g-2">
                            <div class="col-md-4">
                                <label class="form-label small fw-bold">CEP</label>
                                <div class="input-group input-group-sm">
                                    <input type="text" class="form-control form-control-sm font-monospace fw-bold" id="rap_cep" onblur="window.buscarCepRapido()" placeholder="00000-000 ou 99999-999">
                                    <button type="button" class="btn-nft py-0 px-2" onclick="window.buscarCepRapido()" title="Consultar CEP na base nacional">
                                        <i data-lucide="search" style="width: 13px; height: 13px;"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">Logradouro (xLgr)</label>
                                <input type="text" class="form-control form-control-sm" id="rap_logradouro" placeholder="Rua, Av, Alameda...">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold">Número (nro)</label>
                                <input type="text" class="form-control form-control-sm font-monospace" id="rap_numero" placeholder="123 ou S/N">
                            </div>

                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Bairro (xBairro)</label>
                                <input type="text" class="form-control form-control-sm" id="rap_bairro" placeholder="Bairro">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Município (xMun)</label>
                                <input type="text" class="form-control form-control-sm" id="rap_municipio" placeholder="Nome da Cidade">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold">UF</label>
                                <input type="text" class="form-control form-control-sm text-uppercase font-monospace fw-bold" id="rap_uf" maxlength="2" placeholder="SP">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold">Cód. IBGE (cMun)</label>
                                <input type="text" class="form-control form-control-sm font-monospace" id="rap_cmun" placeholder="3550308">
                            </div>

                            <div class="col-md-8">
                                <label class="form-label small fw-bold">País (xPais)</label>
                                <div class="input-group input-group-sm">
                                    <input type="text" class="form-control form-control-sm fw-semibold" id="rap_xpais" list="datalist-paises" onchange="window.aoMudarPaisRapido()" placeholder="Brasil" value="Brasil">
                                    <button type="button" class="btn-nft py-0 px-2" onclick="window.resetarPaisRapido()" title="Redefinir para Brasil">
                                        <i data-lucide="rotate-ccw" style="width: 12px; height: 12px;"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Cód. BACEN (cPais)</label>
                                <input type="text" class="form-control form-control-sm font-monospace fw-bold bg-light" id="rap_cpais" readonly value="1058">
                            </div>
                        </div>

                        <div class="modal-footer d-flex justify-content-between p-0 pt-4 mt-3 border-top bg-transparent">
                            <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">
                                Cancelar
                            </button>
                            <button type="submit" class="btn btn-primary btn-sm fw-bold d-inline-flex align-items-center gap-2 shadow-sm" id="btn-salvar-empresa-rapida">
                                <i data-lucide="save"></i>
                                <span>Salvar e Preencher na Nota</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        `;

        document.body.appendChild(modalDiv);
        aplicarMascarasRapidas(modalDiv);

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    // =========================================================================
    // 2. ABERTURA E PREPARAÇÃO DO MODAL
    // =========================================================================
    window.abrirModalNovaEmpresaRapido = function (alvo = 'dest') {
        _empresaAlvo = alvo;
        injetarModalNovaEmpresaRapidaHTML();

        const form = document.getElementById('formNovaEmpresaRapida');
        if (form) form.reset();

        const badgeTipo = document.getElementById('rap_badge_tipo');
        const selectTipo = document.getElementById('rap_tipo');
        const titulo = document.getElementById('modal-rapida-titulo');

        if (alvo === 'dest') {
            if (badgeTipo) badgeTipo.innerText = 'Destinatário da Nota';
            if (selectTipo) selectTipo.value = 'Cliente';
            if (titulo) titulo.innerText = 'Adicionar Nova Empresa (Destinatário)';
            
            // Se já tiver digitado algum valor nos campos da nota, aproveita no modal
            const nomeDigitado = document.getElementById('dest_xNome')?.value || '';
            const cnpjDigitado = document.getElementById('dest_CNPJ_CPF')?.value || '';
            if (nomeDigitado && document.getElementById('rap_nome')) {
                document.getElementById('rap_nome').value = nomeDigitado;
            }
            if (cnpjDigitado && document.getElementById('rap_cnpj_cpf')) {
                document.getElementById('rap_cnpj_cpf').value = cnpjDigitado;
            }
        } else if (alvo === 'transp') {
            if (badgeTipo) badgeTipo.innerText = 'Transportadora';
            if (selectTipo) selectTipo.value = 'Transportadora';
            if (titulo) titulo.innerText = 'Adicionar Nova Transportadora';
        } else if (alvo === 'emit') {
            if (badgeTipo) badgeTipo.innerText = 'Emitente';
            if (selectTipo) selectTipo.value = 'Emitente';
            if (titulo) titulo.innerText = 'Adicionar Novo Emitente';
        }

        // Reseta regras de localidade para Brasil por padrão
        window.resetarPaisRapido();
        window.aoMudarIndIeRapida();

        const modalEl = document.getElementById('modal-nova-empresa-rapida');
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            const m = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            m.show();
            setTimeout(() => {
                const foco = document.getElementById('rap_cnpj_cpf');
                if (foco) foco.focus();
            }, 300);
        }
    };

    // =========================================================================
    // 3. CONSULTA ONLINE DE CNPJ
    // =========================================================================
    window.buscarCnpjRapido = async function () {
        const inputCnpj = document.getElementById('rap_cnpj_cpf');
        const statusEl = document.getElementById('rap_cnpj_status');
        const btnBusca = document.getElementById('btn-busca-cnpj-rapido');
        if (!inputCnpj) return;

        const cnpjLimpo = inputCnpj.value.replace(/\D/g, '');
        if (cnpjLimpo.length !== 14) {
            if (statusEl) {
                statusEl.className = 'text-warning';
                statusEl.innerText = 'Informe um CNPJ válido com 14 dígitos para consultar.';
            }
            return;
        }

        if (btnBusca) {
            btnBusca.disabled = true;
            btnBusca.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Buscando...';
        }
        if (statusEl) {
            statusEl.className = 'text-muted';
            statusEl.innerText = 'Consultando base da Receita Federal / BrasilAPI...';
        }

        try {
            const resp = await fetch(`/api/empresas/consulta_cnpj/${cnpjLimpo}`);
            const data = await resp.json();

            if (resp.ok && data.status === 'success') {
                if (data.nome && document.getElementById('rap_nome')) {
                    document.getElementById('rap_nome').value = data.nome;
                }
                if (data.apelido && document.getElementById('rap_apelido')) {
                    document.getElementById('rap_apelido').value = data.apelido;
                }
                if (data.cep && document.getElementById('rap_cep')) {
                    document.getElementById('rap_cep').value = data.cep;
                }
                if (data.logradouro && document.getElementById('rap_logradouro')) {
                    document.getElementById('rap_logradouro').value = data.logradouro;
                }
                if (data.numero && document.getElementById('rap_numero')) {
                    document.getElementById('rap_numero').value = data.numero;
                }
                if (data.bairro && document.getElementById('rap_bairro')) {
                    document.getElementById('rap_bairro').value = data.bairro;
                }
                if (data.municipio && document.getElementById('rap_municipio')) {
                    document.getElementById('rap_municipio').value = data.municipio;
                }
                if (data.uf && document.getElementById('rap_uf')) {
                    document.getElementById('rap_uf').value = data.uf;
                }
                if (data.cmun && document.getElementById('rap_cmun')) {
                    document.getElementById('rap_cmun').value = data.cmun;
                }
                if (data.fone && document.getElementById('rap_fone')) {
                    document.getElementById('rap_fone').value = data.fone;
                }

                window.resetarPaisRapido();

                if (statusEl) {
                    statusEl.className = 'text-success fw-bold';
                    statusEl.innerText = '✓ Dados do CNPJ localizados e preenchidos com sucesso!';
                }
            } else {
                if (statusEl) {
                    statusEl.className = 'text-warning';
                    statusEl.innerText = data.error || 'CNPJ não encontrado na consulta online. Preencha manualmente.';
                }
            }
        } catch (e) {
            console.warn('Erro ao consultar CNPJ:', e);
            if (statusEl) {
                statusEl.className = 'text-danger';
                statusEl.innerText = 'Falha na comunicação ao consultar CNPJ online. Preencha manualmente.';
            }
        } finally {
            if (btnBusca) {
                btnBusca.disabled = false;
                btnBusca.innerHTML = '<i data-lucide="search" style="width: 13px; height: 13px;"></i> <span class="small fw-bold">Buscar CNPJ</span>';
                if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
            }
        }
    };

    // =========================================================================
    // 4. CONSULTA AUTOMÁTICA DE CEP
    // =========================================================================
    window.buscarCepRapido = async function () {
        const cepInput = document.getElementById('rap_cep');
        if (!cepInput) return;
        const cepVal = cepInput.value.trim().replace(/\D/g, '');
        if (cepVal.length !== 8 && cepVal !== '99999999') return;

        try {
            const resp = await fetch(`/api/localidades/cep/${encodeURIComponent(cepVal)}`);
            const data = await resp.json();

            if (resp.ok && data) {
                if (data.exterior) {
                    document.getElementById('rap_logradouro').value = 'EXTERIOR';
                    document.getElementById('rap_bairro').value = 'EXTERIOR';
                    document.getElementById('rap_municipio').value = 'Exterior';
                    document.getElementById('rap_uf').value = 'EX';
                    document.getElementById('rap_cmun').value = '9999999';
                    document.getElementById('rap_localidade').value = 'Exterior';
                    window.aoMudarLocalidadeRapida();
                } else {
                    if (data.logradouro) document.getElementById('rap_logradouro').value = data.logradouro;
                    if (data.bairro) document.getElementById('rap_bairro').value = data.bairro;
                    if (data.localidade) document.getElementById('rap_municipio').value = data.localidade;
                    if (data.uf) document.getElementById('rap_uf').value = data.uf;
                    if (data.ibge) document.getElementById('rap_cmun').value = data.ibge;
                    window.resetarPaisRapido();
                }
            }
        } catch (err) {
            console.warn('Erro ao consultar CEP:', err);
        }
    };

    // =========================================================================
    // 5. REGRAS DE LOCALIDADE (BRASIL / EXTERIOR)
    // =========================================================================
    window.aoMudarLocalidadeRapida = function () {
        const locSelect = document.getElementById('rap_localidade');
        const ehExterior = locSelect ? (locSelect.value === 'Exterior') : false;

        const cnpjElem = document.getElementById('rap_cnpj_cpf');
        const ieElem = document.getElementById('rap_ie');
        const indIeElem = document.getElementById('rap_ind_ie');
        const munElem = document.getElementById('rap_municipio');
        const ufElem = document.getElementById('rap_uf');
        const cmunElem = document.getElementById('rap_cmun');
        const xpaisElem = document.getElementById('rap_xpais');
        const cpaisElem = document.getElementById('rap_cpais');

        if (ehExterior) {
            if (cnpjElem) {
                cnpjElem.placeholder = 'IdEstrangeiro ou em branco';
            }
            if (ieElem) {
                ieElem.disabled = true;
                ieElem.value = '';
                ieElem.classList.add('bg-light');
            }
            if (indIeElem) {
                indIeElem.disabled = true;
                indIeElem.value = '9';
            }
            if (ufElem) {
                ufElem.value = 'EX';
                ufElem.readOnly = true;
                ufElem.classList.add('bg-light');
            }
            if (munElem && (!munElem.value || munElem.value === '')) {
                munElem.value = 'Exterior';
            }
            if (cmunElem) {
                cmunElem.value = '9999999';
            }
            if (xpaisElem && (xpaisElem.value.trim().toUpperCase() === 'BRASIL' || !xpaisElem.value.trim())) {
                xpaisElem.value = '';
                if (cpaisElem) cpaisElem.value = '';
            }
        } else {
            if (cnpjElem) {
                cnpjElem.placeholder = '00.000.000/0000-00';
            }
            if (ieElem) {
                ieElem.disabled = false;
                ieElem.classList.remove('bg-light');
            }
            if (indIeElem) {
                indIeElem.disabled = false;
            }
            if (ufElem) {
                ufElem.readOnly = false;
                ufElem.classList.remove('bg-light');
                if (ufElem.value === 'EX') ufElem.value = '';
            }
            if (munElem && munElem.value === 'Exterior') {
                munElem.value = '';
            }
            if (cmunElem && cmunElem.value === '9999999') {
                cmunElem.value = '';
            }
            if (xpaisElem && (!xpaisElem.value.trim() || xpaisElem.value.trim().toUpperCase() !== 'BRASIL')) {
                xpaisElem.value = 'Brasil';
                if (cpaisElem) cpaisElem.value = '1058';
            }
            window.aoMudarIndIeRapida();
        }
    };

    window.aoMudarIndIeRapida = function () {
        const indIe = document.getElementById('rap_ind_ie')?.value;
        const ieInput = document.getElementById('rap_ie');
        if (!ieInput) return;

        if (indIe === '1') {
            ieInput.disabled = false;
            ieInput.placeholder = 'Inscrição Estadual obrigatória';
            ieInput.classList.remove('bg-light');
        } else {
            ieInput.disabled = (indIe === '2' || indIe === '9');
            if (indIe === '2') {
                ieInput.placeholder = 'ISENTO';
            } else {
                ieInput.placeholder = 'Não Contribuinte ICMS';
            }
        }
    };

    window.aoMudarPaisRapido = function () {
        const xpais = document.getElementById('rap_xpais');
        const cpais = document.getElementById('rap_cpais');
        if (!xpais || !cpais) return;

        const val = xpais.value.trim().toUpperCase();
        if (val === 'BRASIL' || !val) {
            xpais.value = 'Brasil';
            cpais.value = '1058';
            document.getElementById('rap_localidade').value = 'Brasil';
            window.aoMudarLocalidadeRapida();
        } else {
            document.getElementById('rap_localidade').value = 'Exterior';
            window.aoMudarLocalidadeRapida();
        }
    };

    window.resetarPaisRapido = function () {
        const xpais = document.getElementById('rap_xpais');
        const cpais = document.getElementById('rap_cpais');
        const loc = document.getElementById('rap_localidade');
        if (xpais) xpais.value = 'Brasil';
        if (cpais) cpais.value = '1058';
        if (loc) loc.value = 'Brasil';
        window.aoMudarLocalidadeRapida();
    };

    // =========================================================================
    // 6. SALVAR EMPRESA & PREENCHIMENTO AUTOMÁTICO NA NOTA
    // =========================================================================
    window.salvarNovaEmpresaRapido = async function (e) {
        if (e && e.preventDefault) e.preventDefault();

        const nome = (document.getElementById('rap_nome')?.value || '').trim();
        if (!nome) {
            alert('Por favor, informe a Razão Social / Nome da empresa.');
            return;
        }

        const btnSalvar = document.getElementById('btn-salvar-empresa-rapida');
        if (btnSalvar) {
            btnSalvar.disabled = true;
            btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Salvando Empresa...';
        }

        const payload = {
            tipo: document.getElementById('rap_tipo')?.value || 'Cliente',
            nome: nome,
            apelido: (document.getElementById('rap_apelido')?.value || '').trim(),
            cnpj_cpf: (document.getElementById('rap_cnpj_cpf')?.value || '').trim(),
            ie: (document.getElementById('rap_ie')?.value || '').trim(),
            ind_ie: document.getElementById('rap_ind_ie')?.value || '9',
            fone: (document.getElementById('rap_fone')?.value || '').trim(),
            cep: (document.getElementById('rap_cep')?.value || '').trim(),
            logradouro: (document.getElementById('rap_logradouro')?.value || '').trim(),
            numero: (document.getElementById('rap_numero')?.value || '').trim(),
            bairro: (document.getElementById('rap_bairro')?.value || '').trim(),
            municipio: (document.getElementById('rap_municipio')?.value || '').trim(),
            uf: (document.getElementById('rap_uf')?.value || '').trim().toUpperCase(),
            cmun: (document.getElementById('rap_cmun')?.value || '').trim(),
            xpais: (document.getElementById('rap_xpais')?.value || 'Brasil').trim(),
            cpais: (document.getElementById('rap_cpais')?.value || '1058').trim()
        };

        try {
            const resp = await fetch('/api/empresas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            if (resp.ok && data.status === 'success') {
                const novaEmpresa = data.empresa || {
                    id: data.id,
                    ...payload
                };
                if (!novaEmpresa.id && data.id) novaEmpresa.id = data.id;

                // 1. Atualiza lista global em memória de empresas
                if (window.cadastrosDisponiveis && Array.isArray(window.cadastrosDisponiveis)) {
                    window.cadastrosDisponiveis.push(novaEmpresa);
                } else {
                    window.cadastrosDisponiveis = [novaEmpresa];
                }

                // 2. Atualiza os selects da aba Identificação
                if (typeof window.preencherOpcoesSelect === 'function') {
                    window.preencherOpcoesSelect('select_destinatario', 'Cliente');
                    window.preencherOpcoesSelect('select_emitente', 'Emitente');
                    window.preencherOpcoesSelect('select_transportadora', 'Transportadora');
                }

                // 3. SE FOR DESTINATÁRIO: Aplica e seleciona automaticamente na nota!
                if (_empresaAlvo === 'dest') {
                    const selDest = document.getElementById('select_destinatario');
                    if (selDest && novaEmpresa.id) {
                        selDest.value = String(novaEmpresa.id);
                    }

                    // Preenche diretamente todos os campos do Destinatário na tela
                    aplicarDadosEmpresaNoDestinatario(novaEmpresa);
                } else if (_empresaAlvo === 'emit') {
                    const selEmit = document.getElementById('select_emitente');
                    if (selEmit && novaEmpresa.id) selEmit.value = String(novaEmpresa.id);
                    if (typeof window.preencherDadosDeCadastro === 'function') {
                        window.preencherDadosDeCadastro(selEmit, 'emit');
                    }
                } else if (_empresaAlvo === 'transp') {
                    const selTransp = document.getElementById('select_transportadora');
                    if (selTransp && novaEmpresa.id) selTransp.value = String(novaEmpresa.id);
                    if (typeof window.preencherDadosDeCadastro === 'function') {
                        window.preencherDadosDeCadastro(selTransp, 'transp');
                    }
                }

                // 4. Fecha o modal
                const modalEl = document.getElementById('modal-nova-empresa-rapida');
                if (modalEl && window.bootstrap && window.bootstrap.Modal) {
                    const m = bootstrap.Modal.getInstance(modalEl);
                    if (m) m.hide();
                }

                // 5. Notificação de sucesso
                const msg = `Empresa "${novaEmpresa.nome}" cadastrada com sucesso e aplicada aos Dados do Destinatário!`;
                if (window.nftToast) {
                    window.nftToast(msg, { type: 'success' });
                } else if (window.nftDialog && typeof window.nftDialog.alert === 'function') {
                    window.nftDialog.alert(msg, { title: 'Empresa Cadastrada', type: 'success' });
                } else {
                    console.log(msg);
                }
            } else {
                alert('Erro ao salvar a empresa no banco de dados. Tente novamente.');
            }
        } catch (err) {
            console.error('Erro ao salvar empresa:', err);
            alert('Falha na comunicação com o servidor: ' + err.message);
        } finally {
            if (btnSalvar) {
                btnSalvar.disabled = false;
                btnSalvar.innerHTML = '<i data-lucide="save"></i> <span>Salvar e Preencher na Nota</span>';
                if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
            }
        }
    };

    // =========================================================================
    // 7. PREENCHIMENTO DIRETO NOS CAMPOS DO DESTINATÁRIO
    // =========================================================================
    function aplicarDadosEmpresaNoDestinatario(emp) {
        if (!emp) return;

        // Nome / Razão Social
        const elNome = document.getElementById('dest_xNome');
        if (elNome) elNome.value = emp.nome || '';

        // Tipo de Documento & CNPJ/CPF
        const docLimpo = String(emp.cnpj_cpf || '').replace(/\D/g, '');
        const tpDocEl = document.getElementById('dest_tpDoc');
        if (tpDocEl) {
            if (emp.uf === 'EX' || (emp.cpais && String(emp.cpais) !== '1058') || (!docLimpo && emp.tipo === 'Exportador')) {
                tpDocEl.value = 'Estrangeiro';
            } else if (docLimpo.length <= 11 && docLimpo.length > 0) {
                tpDocEl.value = 'CPF';
            } else {
                tpDocEl.value = 'CNPJ';
            }
            if (typeof window.atualizarTipoDocumentoDestinatario === 'function') {
                window.atualizarTipoDocumentoDestinatario();
            }
        }

        const elDoc = document.getElementById('dest_CNPJ_CPF');
        if (elDoc) {
            elDoc.value = emp.cnpj_cpf || '';
        }

        // Indicador de IE e Inscrição Estadual
        const elIndIe = document.getElementById('dest_indIEDest');
        if (elIndIe) {
            elIndIe.value = emp.ind_ie || '9';
            if (typeof window.atualizarEstadoInscricaoEstadual === 'function') {
                window.atualizarEstadoInscricaoEstadual();
            }
        }

        const elIe = document.getElementById('dest_IE');
        if (elIe) {
            elIe.value = emp.ie || '';
        }

        // Endereço
        if (document.getElementById('dest_xLgr')) document.getElementById('dest_xLgr').value = emp.logradouro || '';
        if (document.getElementById('dest_nro')) document.getElementById('dest_nro').value = emp.numero || '';
        if (document.getElementById('dest_xBairro')) document.getElementById('dest_xBairro').value = emp.bairro || '';
        if (document.getElementById('dest_cMun')) document.getElementById('dest_cMun').value = emp.cmun || '';
        if (document.getElementById('dest_xMun')) document.getElementById('dest_xMun').value = emp.municipio || '';
        if (document.getElementById('dest_UF')) document.getElementById('dest_UF').value = emp.uf || '';
        if (document.getElementById('dest_CEP')) document.getElementById('dest_CEP').value = emp.cep || '';
        if (document.getElementById('dest_xPais')) document.getElementById('dest_xPais').value = emp.xpais || 'Brasil';
        if (document.getElementById('dest_cPais')) document.getElementById('dest_cPais').value = emp.cpais || '1058';

        // Atualiza indicador de país no topo do card se existir
        const badgePais = document.getElementById('lbl-status-pais-dest');
        if (badgePais) {
            if (emp.uf === 'EX' || (emp.cpais && String(emp.cpais) !== '1058')) {
                badgePais.className = 'badge font-monospace bg-warning-subtle text-warning fw-bold';
                badgePais.innerText = `Exterior (${emp.xpais || 'Exterior'})`;
            } else {
                badgePais.className = 'badge font-monospace bg-info-subtle text-info fw-bold';
                badgePais.innerText = 'Nacional (Brasil)';
            }
        }

        // Sincroniza fornecedor/exportador em DI/DUIMP se existir
        const expEl = document.getElementById('import_cExportador');
        if (expEl && (!expEl.value || expEl.dataset.autoSynced === 'true')) {
            expEl.value = emp.nome || '';
            expEl.dataset.autoSynced = 'true';
        }

        // Dispara validação regex visual para deixar campos verdes
        if (window.validarCamposRegexVisual) {
            setTimeout(window.validarCamposRegexVisual, 30);
        }
    }

    // =========================================================================
    // 8. MÁSCARAS
    // =========================================================================
    function aplicarMascarasRapidas(container) {
        container.addEventListener('input', function (e) {
            if (e.target.classList.contains('mask-cnpj-cpf')) {
                let v = e.target.value.replace(/\D/g, '');
                if (v.length <= 11) {
                    v = v.replace(/(\d{3})(\d)/, '$1.$2');
                    v = v.replace(/(\d{3})(\d)/, '$1.$2');
                    v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
                } else {
                    v = v.replace(/^(\d{2})(\d)/, '$1.$2');
                    v = v.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
                    v = v.replace(/\.(\d{3})(\d)/, '.$1/$2');
                    v = v.replace(/(\d{4})(\d{1,2})$/, '$1-$2');
                    if (v.length > 18) v = v.substring(0, 18);
                }
                e.target.value = v;
            }
            if (e.target.classList.contains('mask-telefone')) {
                let v = e.target.value.replace(/\D/g, '');
                if (v.length > 11) v = v.substring(0, 11);
                if (v.length > 10) {
                    v = v.replace(/^(\d{2})(\d{5})(\d{4}).*/, '($1) $2-$3');
                } else if (v.length > 5) {
                    v = v.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
                } else if (v.length > 2) {
                    v = v.replace(/^(\d{2})(\d{0,5})/, '($1) $2');
                }
                e.target.value = v;
            }
        });
    }

    // Inicializa injeção quando o documento carregar
    document.addEventListener('DOMContentLoaded', () => {
        injetarModalNovaEmpresaRapidaHTML();
    });
})();

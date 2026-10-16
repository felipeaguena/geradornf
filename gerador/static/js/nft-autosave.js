/**
 * NFT LOGISTICS - GERENCIADOR DE SESSÃO TEMPORÁRIA E AUTOSAVE
 * 
 * Preserva o trabalho em andamento em cada tela (XML Rascunho vs XML DI/DUIMP).
 * Sobrevive a:
 *  - Troca de telas / menus laterais
 *  - Atualização de página (F5)
 *  - Fechamento acidental do navegador
 *  - Queda de energia ou desligamento do computador
 *  - Queda / reinicialização do servidor Flask
 * 
 * Armazenamento de camada dupla: LocalStorage (síncrono/imediato) + IndexedDB (capacidade ilimitada).
 */

(function () {
    const isDI = window.location.pathname.includes('di_duimp');
    const isNovaNF = window.location.pathname.includes('nova_nf');
    const STORAGE_KEY = isNovaNF ? 'nft_sessao_temp_nova_nf' : (isDI ? 'nft_sessao_temp_di_duimp' : 'nft_sessao_temp_rascunho');
    const DB_NAME = 'NFT_Logistics_DB';
    const DB_VERSION = 1;
    const STORE_NAME = 'sessoes_temporarias';

    let _debounceTimer = null;
    let _restaurandoSessao = false;

    // === 1. CAMADA INDEXEDDB (CAPACIDADE ILIMITADA) ===
    function openIDB() {
        return new Promise((resolve, reject) => {
            if (!window.indexedDB) {
                return reject(new Error('IndexedDB não suportado'));
            }
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: 'key' });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async function idbSet(key, val) {
        try {
            const db = await openIDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readwrite');
                tx.objectStore(STORE_NAME).put({ key: key, value: val, updatedAt: Date.now() });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => reject(tx.error);
            });
        } catch (e) {
            console.warn('IDB save fallback warning:', e);
        }
    }

    async function idbGet(key) {
        try {
            const db = await openIDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readonly');
                const req = tx.objectStore(STORE_NAME).get(key);
                req.onsuccess = () => resolve(req.result ? req.result.value : null);
                req.onerror = () => reject(req.error);
            });
        } catch (e) {
            return null;
        }
    }

    async function idbDelete(key) {
        try {
            const db = await openIDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readwrite');
                tx.objectStore(STORE_NAME).delete(key);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => reject(tx.error);
            });
        } catch (e) {
            console.warn('IDB delete warning:', e);
        }
    }

    // === 2. CAPTURA DE DADOS DO FORMULÁRIO E TABELA ===
    function coletarDadosSessao() {
        if (_restaurandoSessao) return null;

        const campos = {};
        const inputs = document.querySelectorAll('input[id], select[id], textarea[id]');
        inputs.forEach(el => {
            const id = el.id;
            if (!id) return;
            // Ignora campos de busca, modais e uploads de arquivo
            if (el.type === 'file' || el.type === 'button' || el.type === 'submit') return;
            if (el.closest('.modal')) return;
            if (id.startsWith('filtro_')) return;

            campos[id] = el.value !== undefined ? el.value : '';
        });

        let itens = [];
        if (window.itensTable && typeof window.itensTable.getData === 'function') {
            itens = window.itensTable.getData();
        } else if (Array.isArray(window.itensCache)) {
            itens = window.itensCache;
        }

        // Captura Histórico SEFAZ
        const sefazHistory = [];
        const rows = document.querySelectorAll('#tbody-historico-sefaz tr');
        rows.forEach(tr => {
            const cells = tr.querySelectorAll('td');
            if (cells.length >= 7) {
                sefazHistory.push({
                    data: cells[0].innerHTML,
                    ambiente: cells[1].innerHTML,
                    arquivos: cells[2].innerHTML,
                    chave: cells[3].innerHTML,
                    status: cells[4].innerHTML,
                    motivo: cells[5].innerHTML,
                    motivoTitle: cells[5].getAttribute('title') || '',
                    protocolo: cells[6].innerHTML
                });
            } else if (cells.length === 6) {
                sefazHistory.push({
                    data: cells[0].innerHTML,
                    ambiente: cells[1].innerHTML,
                    arquivos: '',
                    chave: cells[2].innerHTML,
                    status: cells[3].innerHTML,
                    motivo: cells[4].innerHTML,
                    motivoTitle: cells[4].getAttribute('title') || '',
                    protocolo: cells[5].innerHTML
                });
            }
        });

        const now = new Date();
        const dataFmt = now.toLocaleDateString('pt-BR') + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        return {
            modulo: window.NOME_MODULO_ORIGEM || (isNovaNF ? 'Nova NF' : (isDI ? 'XML da DI ou DUIMP' : 'XML Rascunho')),
            timestamp: now.getTime(),
            data_formatada: dataFmt,
            campos: campos,
            itens: itens,
            sefaz_history: sefazHistory,
            xml_original: window.xmlOriginalData || '',
            nome_arquivo_original: window.nomeArquivoOriginal || '',
            id_rascunho_atual: window.idRascunhoAtual || null,
            referencia_interna: (typeof window.obterReferenciaInterna === 'function') ? window.obterReferenciaInterna() : (document.getElementById('referenciaInterna')?.value || '')
        };
    }

    // === 3. SALVAR SESSÃO (DEBOUNCED & IMEDIATO) ===
    function salvarSessaoImediata() {
        if (window._nftDesabilitarAutosave) return;
        if (sessionStorage.getItem('nft_limpar_sessao_' + STORAGE_KEY)) return;
        const payload = coletarDadosSessao();
        if (!payload) return;

        // Se não há dados preenchidos (formulário vazio), não precisa salvar
        const temItens = payload.itens && payload.itens.length > 0;
        const temCampos = Object.keys(payload.campos).some(k => {
            const v = payload.campos[k];
            // Ignora valores padrão/fixos
            if (['cUF', 'tpEmis', 'mod', 'idDest', 'tpNF', 'dest_indIEDest'].includes(k)) return false;
            return v && String(v).trim() !== '' && String(v).trim() !== '0,00' && String(v).trim() !== '0.00';
        });

        if (!temItens && !temCampos && !payload.xml_original) {
            return;
        }

        // 1. Salva em LocalStorage (síncrono, persistência instantânea no disco)
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (e) {
            // Se o XML original exceder a cota do LocalStorage (5MB), salva sem o XML no LS
            if (e.name === 'QuotaExceededError') {
                try {
                    const fallbackPayload = { ...payload, xml_original: '' };
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(fallbackPayload));
                } catch (e2) {}
            }
        }

        // 2. Salva no IndexedDB (sem restrição de cota, suporta arquivos grandes)
        idbSet(STORAGE_KEY, payload);

        // Atualiza indicador visual sutil se existir
        const alertTimeEl = document.getElementById('nft-autosave-time');
        if (alertTimeEl && !document.getElementById('nft-autosave-alert')?.classList.contains('d-none')) {
            alertTimeEl.innerText = payload.data_formatada || '';
        }
    }

    window.triggerAutoSave = function () {
        if (_restaurandoSessao || window._nftDesabilitarAutosave) return;
        if (sessionStorage.getItem('nft_limpar_sessao_' + STORAGE_KEY)) return;
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(salvarSessaoImediata, 400);
    };

    // === 4. RESTAURAÇÃO DE SESSÃO TEMPORÁRIA ===
    async function tentarRestaurarSessao() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Se foi solicitado explicitamente iniciar uma nova nota limpa
        const isNovaNota = urlParams.get('nova_nota') || sessionStorage.getItem('nft_limpar_sessao_' + STORAGE_KEY);
        if (isNovaNota) {
            sessionStorage.removeItem('nft_limpar_sessao_' + STORAGE_KEY);
            localStorage.removeItem(STORAGE_KEY);
            await idbDelete(STORAGE_KEY);
            
            // Limpa a URL sem recarregar a página (remove ?nova_nota=1)
            if (window.history.replaceState) {
                window.history.replaceState({}, document.title, window.location.pathname);
            }

            // Garante o status inicial limpo do documento e oculta alertas
            const badgeUpload = document.getElementById('status-badge');
            if (badgeUpload) {
                badgeUpload.className = "badge py-1 px-2 bg-info-subtle text-info fw-bold";
                badgeUpload.innerText = isNovaNF ? "Aguardando Dados" : "Aguardando XML";
            }
            const infoTag = document.getElementById('rascunho-info-tag');
            if (infoTag) {
                infoTag.innerText = '';
                infoTag.classList.add('d-none');
            }
            const alertEl = document.getElementById('nft-autosave-alert');
            if (alertEl) {
                alertEl.classList.add('d-none');
                alertEl.classList.remove('d-flex');
            }
            return;
        }

        // Se a URL contém instrução para abrir um rascunho salvo, não usa autosave
        if (urlParams.get('carregar_rascunho')) {
            return;
        }

        // Tenta obter do LocalStorage primeiro (mais rápido), senão IndexedDB
        let sessionData = null;
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) sessionData = JSON.parse(raw);
        } catch (e) {}

        if (!sessionData) {
            sessionData = await idbGet(STORAGE_KEY);
        }

        if (!sessionData) return;

        const temItens = sessionData.itens && sessionData.itens.length > 0;
        const temCampos = sessionData.campos && Object.keys(sessionData.campos).some(k => {
            const v = sessionData.campos[k];
            if (['cUF', 'tpEmis', 'mod', 'idDest', 'tpNF', 'dest_indIEDest'].includes(k)) return false;
            return v && String(v).trim() !== '' && String(v).trim() !== '0,00' && String(v).trim() !== '0.00';
        });

        if (!temItens && !temCampos && !sessionData.xml_original) {
            return;
        }

        _restaurandoSessao = true;

        try {
            // 1. Restaura campos do formulário
            if (sessionData.campos) {
                Object.keys(sessionData.campos).forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        const val = sessionData.campos[id];
                        el.value = val;
                    }
                });
            }

            // 2. Restaura Referência Interna
            if (sessionData.referencia_interna && typeof window.definirReferenciaInterna === 'function') {
                window.definirReferenciaInterna(sessionData.referencia_interna);
            }

            // 3. Restaura XML original e metadados
            if (sessionData.xml_original) {
                window.xmlOriginalData = sessionData.xml_original;
            }
            if (sessionData.nome_arquivo_original) {
                window.nomeArquivoOriginal = sessionData.nome_arquivo_original;
            }
            if (sessionData.id_rascunho_atual) {
                window.idRascunhoAtual = sessionData.id_rascunho_atual;
            }

            // 4. Restaura Operação Selecionada se houver
            if (sessionData.campos && sessionData.campos.select_operacao) {
                const selOp = document.getElementById('select_operacao');
                if (selOp) {
                    selOp.value = sessionData.campos.select_operacao;
                    if (typeof window.aoSelecionarOperacao === 'function') {
                        window.aoSelecionarOperacao(sessionData.campos.select_operacao, true);
                    }
                }
            }

            // 5. Restaura Tabela de Itens com retry para garantir que Tabulator esteja montado
            if (temItens) {
                window.itensCache = sessionData.itens;
                let attempts = 0;
                const applyData = () => {
                    attempts++;
                    if (window.itensTable && typeof window.itensTable.setData === 'function') {
                        window.itensTable.setData(window.itensCache);
                        setTimeout(() => {
                            if (window.itensTable && typeof window.itensTable.redraw === 'function') {
                                window.itensTable.redraw(true);
                            }
                            if (typeof window.recalcularTotaisDosItens === 'function') {
                                window.recalcularTotaisDosItens(true);
                            }
                        }, 80);
                    } else if (attempts < 20) {
                        setTimeout(applyData, 100);
                    }
                };
                applyData();

                const badgeItens = document.getElementById('itens-badge');
                if (badgeItens) badgeItens.innerText = window.itensCache.length;
            }

            // 6. Atualiza cálculos e visuais da tela
            if (typeof window.atualizarCamposIdentificacao === 'function') {
                const tpNF = document.getElementById('tpNF')?.value || '0';
                const idDest = document.getElementById('idDest')?.value || '3';
                window.atualizarCamposIdentificacao(tpNF, idDest);
            }
            if (typeof window.atualizarEstadoInscricaoEstadual === 'function') {
                window.atualizarEstadoInscricaoEstadual();
            }
            if (typeof window.calcularChaveAcessoDinamica === 'function') {
                window.calcularChaveAcessoDinamica();
            }
            if (typeof window.atualizarBadgesRateioEItens === 'function') {
                window.atualizarBadgesRateioEItens();
            }

            // 7. Restaura Histórico SEFAZ
            if (sessionData.sefaz_history && sessionData.sefaz_history.length > 0) {
                const tbody = document.getElementById('tbody-historico-sefaz');
                if (tbody) {
                    tbody.innerHTML = '';
                    sessionData.sefaz_history.forEach(item => {
                        const tr = document.createElement('tr');
                        const norm = typeof window.normalizarItemHistoricoSefaz === 'function'
                            ? window.normalizarItemHistoricoSefaz(item)
                            : null;
                            
                        if (norm) {
                            tr.innerHTML = `
                                <td class="align-middle">${norm.data}</td>
                                <td class="align-middle">${norm.ambienteHtml}</td>
                                <td class="text-center align-middle">${norm.arquivosHtml}</td>
                                <td class="text-start align-middle font-monospace" style="font-size: 11px;">${norm.chave}</td>
                                <td class="align-middle">${norm.cstatHtml}</td>
                                <td class="text-start align-middle" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${norm.motivoTitle}">
                                    ${norm.motivo}
                                </td>
                                <td class="align-middle" style="font-size: 11px;">${norm.protocolo}</td>
                            `;
                        } else {
                            tr.innerHTML = `
                                <td>${item.data || ''}</td>
                                <td>${item.ambiente || ''}</td>
                                <td class="text-center align-middle">${item.arquivos || '-'}</td>
                                <td class="text-start" style="font-size: 11px;">${item.chave || ''}</td>
                                <td>${item.status || ''}</td>
                                <td class="text-start" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.motivoTitle || ''}">
                                    ${item.motivo || ''}
                                </td>
                                <td>${item.protocolo || ''}</td>
                            `;
                        }
                        tbody.appendChild(tr);
                    });
                    if (typeof window.sanitizarTabelaHistoricoSefaz === 'function') {
                        window.sanitizarTabelaHistoricoSefaz();
                    }
                }
            }

            // 8. Atualiza badge de status de upload
            const badgeUpload = document.getElementById('status-badge');
            if (badgeUpload) {
                badgeUpload.className = "badge bg-info py-2 px-3 w-100";
                badgeUpload.innerText = `Sessão ativa restaurada (${window.itensCache ? window.itensCache.length : 0} itens)`;
            }

            // 8. Exibe barra de notificação amigável com opção de descartar/iniciar nova nota
            const alertEl = document.getElementById('nft-autosave-alert');
            const alertTimeEl = document.getElementById('nft-autosave-time');
            if (alertEl) {
                alertEl.classList.remove('d-none');
                alertEl.classList.add('d-flex');
                if (alertTimeEl) {
                    alertTimeEl.innerText = sessionData.data_formatada || '';
                }
            }

            if (window.lucide) {
                window.lucide.createIcons();
            }
            if (window.validarCamposRegexVisual) {
                window.validarCamposRegexVisual();
            }

        } finally {
            _restaurandoSessao = false;
        }
    }

    function limparTodosCamposDom() {
        // 1. Limpa inputs, selects e textareas preservando apenas defaults estruturais
        const inputs = document.querySelectorAll('input[id], select[id], textarea[id]');
        inputs.forEach(el => {
            const id = el.id;
            if (!id || el.closest('.modal') || id.startsWith('filtro_')) return;
            if (el.type === 'file') {
                el.value = '';
                return;
            }
            if (['cUF', 'mod', 'serie', 'tpEmis'].includes(id)) return;
            if (id === 'dest_cPais') { el.value = '1058'; return; }
            if (id === 'dest_xPais') { el.value = 'Brasil'; return; }
            if (id === 'dest_tpDoc') { el.value = 'CNPJ'; return; }
            if (id === 'dest_indIEDest') { el.value = '9'; return; }
            if (id === 'tpNF') { el.value = isDI ? '0' : '1'; return; }
            if (id === 'idDest') { el.value = isDI ? '3' : '1'; return; }
            if (id.startsWith('tot_') || id.startsWith('rateio_')) {
                el.value = '0,00';
                return;
            }
            el.value = '';
        });

        // 2. Limpa tabela e cache de itens
        if (window.itensTable && typeof window.itensTable.setData === 'function') {
            window.itensTable.setData([]);
        }
        window.itensCache = [];
        const badgeItens = document.getElementById('itens-badge');
        if (badgeItens) badgeItens.innerText = '0';

        // 3. Limpa badges de status do documento e tags de rascunho
        const badgeUpload = document.getElementById('status-badge');
        if (badgeUpload) {
            badgeUpload.className = "badge py-1 px-2 bg-info-subtle text-info fw-bold";
            badgeUpload.innerText = isNovaNF ? "Aguardando Dados" : "Aguardando XML";
        }
        const infoTag = document.getElementById('rascunho-info-tag');
        if (infoTag) {
            infoTag.innerText = '';
            infoTag.classList.add('d-none');
        }
        const alertEl = document.getElementById('nft-autosave-alert');
        if (alertEl) {
            alertEl.classList.add('d-none');
            alertEl.classList.remove('d-flex');
        }
        const origIndicator = document.getElementById('rascunho-origem-indicator');
        if (origIndicator) {
            const badgeClass = isNovaNF ? 'badge-origem-nova' : (isDI ? 'badge-origem-di' : 'badge-origem-rasc');
            origIndicator.innerHTML = `Módulo Ativo: <span class="badge ${badgeClass} bg-info-subtle text-info fw-bold">${window.NOME_MODULO_ORIGEM || (isNovaNF ? 'Nova NF' : (isDI ? 'XML da DI ou DUIMP' : 'XML Rascunho'))}</span>`;
        }

        const tbodySefaz = document.getElementById('tbody-historico-sefaz');
        if (tbodySefaz) tbodySefaz.innerHTML = '';
    }

    // === 5. LIMPAR SESSÃO TEMPORÁRIA (NOVA NOTA) ===
    window.limparSessaoTemporariaComConfirmacao = async function () {
        let confirmado = false;
        if (typeof window.nftConfirm === 'function') {
            confirmado = await window.nftConfirm(
                'Deseja limpar todos os dados preenchidos desta página e iniciar uma nova nota fiscal em branco?\n\n(Os rascunhos salvos formalmente na lista de rascunhos não serão apagados).',
                {
                    title: 'Iniciar Nova Nota Fiscal',
                    type: 'warning',
                    confirmText: 'Limpar e Começar do Zero',
                    cancelText: 'Cancelar'
                }
            );
        } else {
            confirmado = confirm('Deseja limpar todos os dados preenchidos desta página e iniciar uma nova nota fiscal em branco?');
        }

        if (!confirmado) return;

        // 1. Desativa IMEDIATAMENTE o autosave para impedir qualquer gravação posterior
        window._nftDesabilitarAutosave = true;
        clearTimeout(_debounceTimer);

        // 2. Apaga chaves de autosave do LocalStorage e do IndexedDB
        localStorage.removeItem(STORAGE_KEY);
        await idbDelete(STORAGE_KEY);

        // 3. Registra flag na sessionStorage para impedir que após o reload a sessão seja reativada
        sessionStorage.setItem('nft_limpar_sessao_' + STORAGE_KEY, 'true');

        // 4. Limpa em memória todas as variáveis globais de rascunho e XML
        window.idRascunhoAtual = null;
        window.origemRascunhoAtual = null;
        window.nomeArquivoOriginal = "";
        window.xmlOriginalData = "";
        window.itensCache = [];

        // 5. Executa a limpeza física de todos os campos no DOM
        limparTodosCamposDom();

        // 6. Recarrega a página limpa com ?nova_nota=1
        window.location.replace(window.location.pathname + '?nova_nota=1');
    };

    // Fechar banner de restauração
    window.fecharBannerSessaoRestaurada = function () {
        const alertEl = document.getElementById('nft-autosave-alert');
        if (alertEl) {
            alertEl.classList.add('d-none');
            alertEl.classList.remove('d-flex');
        }
    };

    // === 6. ATIVAÇÃO DE LISTENERS GLOBAIS ===
    document.addEventListener('DOMContentLoaded', function () {
        // Escuta qualquer digitação ou alteração em qualquer campo da página
        document.body.addEventListener('input', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) {
                window.triggerAutoSave();
            }
        });

        document.body.addEventListener('change', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) {
                window.triggerAutoSave();
            }
        });

        // Salva imediatamente ao sair da tela / fechar aba (a menos que seja desligamento ou nova nota)
        window.addEventListener('beforeunload', function (e) {
            if (window._nftIsShuttingDown || window._nftDesabilitarAutosave) {
                return;
            }
            if (sessionStorage.getItem('nft_limpar_sessao_' + STORAGE_KEY)) {
                return;
            }
            salvarSessaoImediata();
        });

        // Aguarda carregar operações cadastradas antes de tentar restaurar
        setTimeout(() => {
            tentarRestaurarSessao();
        }, 450);
    });

})();

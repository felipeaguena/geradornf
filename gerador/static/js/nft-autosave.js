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
    const STORAGE_KEY = isDI ? 'nft_sessao_temp_di_duimp' : 'nft_sessao_temp_rascunho';
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

        const now = new Date();
        const dataFmt = now.toLocaleDateString('pt-BR') + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        return {
            modulo: window.NOME_MODULO_ORIGEM || (isDI ? 'XML da DI ou DUIMP' : 'XML Rascunho'),
            timestamp: now.getTime(),
            data_formatada: dataFmt,
            campos: campos,
            itens: itens,
            xml_original: window.xmlOriginalData || '',
            nome_arquivo_original: window.nomeArquivoOriginal || '',
            id_rascunho_atual: window.idRascunhoAtual || null,
            referencia_interna: (typeof window.obterReferenciaInterna === 'function') ? window.obterReferenciaInterna() : (document.getElementById('referenciaInterna')?.value || '')
        };
    }

    // === 3. SALVAR SESSÃO (DEBOUNCED & IMEDIATO) ===
    function salvarSessaoImediata() {
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
        if (_restaurandoSessao) return;
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(salvarSessaoImediata, 400);
    };

    // === 4. RESTAURAÇÃO DE SESSÃO TEMPORÁRIA ===
    async function tentarRestaurarSessao() {
        // Se a URL contém instrução para abrir um rascunho salvo explicitamente, não restaura sessão temporária
        const urlParams = new URLSearchParams(window.location.search);
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

            // 7. Atualiza badge de status de upload
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

        } finally {
            _restaurandoSessao = false;
        }
    }

    // === 5. LIMPAR SESSÃO TEMPORÁRIA (NOVA NOTA) ===
    window.limparSessaoTemporariaComConfirmacao = async function () {
        let confirmado = false;
        if (typeof window.nftConfirm === 'function') {
            confirmado = await window.nftConfirm(
                'Deseja limpar todos os dados temporários desta página e iniciar uma nota em branco?\n\n(Os rascunhos salvos formalmente na pasta Rascunhos não serão apagados).',
                {
                    title: 'Iniciar Nova Nota',
                    type: 'warning',
                    confirmText: 'Limpar e Começar do Zero',
                    cancelText: 'Continuar com Esta Nota'
                }
            );
        } else {
            confirmado = confirm('Deseja limpar todos os dados temporários desta página e iniciar uma nota em branco?');
        }

        if (confirmado) {
            localStorage.removeItem(STORAGE_KEY);
            await idbDelete(STORAGE_KEY);
            // Recarrega a página limpa
            window.location.href = window.location.pathname;
        }
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

        // Salva imediatamente ao sair da tela / fechar aba
        window.addEventListener('beforeunload', function () {
            salvarSessaoImediata();
        });

        // Aguarda carregar operações cadastradas antes de tentar restaurar
        setTimeout(() => {
            tentarRestaurarSessao();
        }, 450);
    });

})();

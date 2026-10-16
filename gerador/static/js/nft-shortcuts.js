/**
 * NFT LOGISTICS - ATALHOS GLOBAIS E HISTÓRICO DE AÇÕES (UNDO / REDO / SALVAR)
 * 
 * Suporta:
 *  - Ctrl + S (ou Cmd + S): Salvar Rascunho / Formulário
 *  - Ctrl + Z (ou Cmd + Z): Desfazer Ação (Undo)
 *  - Ctrl + Shift + Z (ou Ctrl + Y / Cmd + Shift + Z): Refazer Ação (Redo)
 */

(function () {
    // Configurações da pilha de histórico
    const MAX_HISTORY = 30;
    const undoStack = [];
    const redoStack = [];
    let isApplyingHistory = false;
    let snapshotDebounceTimer = null;

    // Toast de notificação sutil na tela
    function showShortcutToast(message, type = 'info', icon = 'info') {
        let toastContainer = document.getElementById('nft-shortcut-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'nft-shortcut-toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                z-index: 100000;
                display: flex;
                flex-direction: column;
                gap: 8px;
                pointer-events: none;
            `;
            document.body.appendChild(toastContainer);
        }

        const colors = {
            success: { bg: 'rgba(16, 185, 129, 0.95)', border: '#059669', text: '#ffffff' },
            info: { bg: 'rgba(30, 41, 59, 0.92)', border: 'rgba(59, 130, 246, 0.4)', text: '#f8fafc' },
            warning: { bg: 'rgba(245, 158, 11, 0.95)', border: '#d97706', text: '#ffffff' },
            danger: { bg: 'rgba(239, 68, 68, 0.95)', border: '#dc2626', text: '#ffffff' }
        };
        const c = colors[type] || colors.info;

        const toast = document.createElement('div');
        toast.style.cssText = `
            background: ${c.bg};
            border: 1px solid ${c.border};
            color: ${c.text};
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            gap: 10px;
            opacity: 0;
            transform: translateY(12px) scale(0.96);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: auto;
        `;

        toast.innerHTML = `<span>${message}</span>`;
        toastContainer.appendChild(toast);

        // Animação de entrada
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0) scale(1)';
        });

        // Remove após 2.2 segundos
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-8px) scale(0.95)';
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 250);
        }, 2200);
    }

    // === 1. CAPTURA E RESTAURAÇÃO DE SNAPSHOT (ESTADO) ===
    function capturarEstadoAtual(descricao = 'Modificação') {
        const campos = {};
        const inputs = document.querySelectorAll('input[id], select[id], textarea[id]');
        inputs.forEach(el => {
            if (el.type === 'file' || el.type === 'button' || el.type === 'submit') return;
            if (el.closest('.modal')) return;
            if (el.id.startsWith('filtro_')) return;
            campos[el.id] = el.value !== undefined ? el.value : '';
        });

        // Captura itens da tabela
        let itens = [];
        if (typeof window.itensTable !== 'undefined' && window.itensTable && typeof window.itensTable.getData === 'function') {
            try { itens = JSON.parse(JSON.stringify(window.itensTable.getData())); } catch(e) {}
        } else if (Array.isArray(window.itensCache)) {
            try { itens = JSON.parse(JSON.stringify(window.itensCache)); } catch(e) {}
        }

        return {
            timestamp: Date.now(),
            descricao: descricao,
            campos: campos,
            itens: itens
        };
    }

    function aplicarEstado(snapshot) {
        if (!snapshot || !snapshot.campos) return;
        isApplyingHistory = true;

        try {
            // Restaura campos
            Object.keys(snapshot.campos).forEach(id => {
                const el = document.getElementById(id);
                if (el && el.value !== snapshot.campos[id]) {
                    el.value = snapshot.campos[id];
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });

            // Restaura itens da tabela
            if (Array.isArray(snapshot.itens)) {
                const itensClone = JSON.parse(JSON.stringify(snapshot.itens));
                window.itensCache = itensClone;
                if (typeof window.itensTable !== 'undefined' && window.itensTable && typeof window.itensTable.setData === 'function') {
                    window.itensTable.setData(itensClone);
                }
                if (typeof window.recalcularTotaisDosItens === 'function') {
                    window.recalcularTotaisDosItens(true);
                }
                if (typeof window.atualizarBadgesRateioEItens === 'function') {
                    window.atualizarBadgesRateioEItens();
                }
            }

            if (typeof window.triggerAutoSave === 'function') {
                window.triggerAutoSave();
            }
        } catch (e) {
            console.warn('Erro ao restaurar snapshot:', e);
        } finally {
            setTimeout(() => {
                isApplyingHistory = false;
            }, 100);
        }
    }

    // Registra alteração para histórico
    window.nftRegistrarSnapshot = function (descricao = 'Alteração') {
        if (isApplyingHistory) return;
        const snap = capturarEstadoAtual(descricao);
        if (!snap) return;

        // Evita duplicar se o estado for idêntico ao anterior
        if (undoStack.length > 0) {
            const last = undoStack[undoStack.length - 1];
            if (JSON.stringify(last.campos) === JSON.stringify(snap.campos) &&
                JSON.stringify(last.itens) === JSON.stringify(snap.itens)) {
                return;
            }
        }

        undoStack.push(snap);
        if (undoStack.length > MAX_HISTORY) {
            undoStack.shift();
        }
        // Limpa pilha de refazer após nova modificação
        redoStack.length = 0;
    };

    function debouncedRegistrarSnapshot(descricao = 'Digitação') {
        if (isApplyingHistory) return;
        clearTimeout(snapshotDebounceTimer);
        snapshotDebounceTimer = setTimeout(() => {
            window.nftRegistrarSnapshot(descricao);
        }, 600);
    }

    // === 2. AÇÕES DE UNDO / REDO / SAVE ===
    window.nftDesfazer = function () {
        if (undoStack.length <= 1) {
            showShortcutToast('Nenhuma ação anterior para desfazer (Ctrl + Z)', 'info');
            return;
        }

        // Move o estado atual para o redoStack
        const estadoAtual = undoStack.pop();
        redoStack.push(estadoAtual);

        // Aplica o estado anterior
        const estadoAnterior = undoStack[undoStack.length - 1];
        aplicarEstado(estadoAnterior);

        showShortcutToast(`Desfeito: ${estadoAtual.descricao || 'Alteração'} (Ctrl + Z)`, 'info');
    };

    window.nftRefazer = function () {
        if (redoStack.length === 0) {
            showShortcutToast('Nenhuma ação para refazer (Ctrl + Shift + Z)', 'info');
            return;
        }

        const estadoProximo = redoStack.pop();
        undoStack.push(estadoProximo);
        aplicarEstado(estadoProximo);

        showShortcutToast(`Refeito: ${estadoProximo.descricao || 'Alteração'} (Ctrl + Shift + Z)`, 'info');
    };

    window.nftSalvarAtalho = async function () {
        // 1. Telas de Emissão com Rascunho (di_duimp, index, nova_nf)
        if (typeof window.confirmarSalvarRascunho === 'function') {
            // Se já tem ID de rascunho ou referência preenchida, salva silenciosamente com toast
            const refAtual = (typeof window.obterReferenciaInterna === 'function') ? window.obterReferenciaInterna() : (document.getElementById('referenciaInterna')?.value || '');
            
            if (window.idRascunhoAtual || refAtual) {
                // Sincroniza input do modal caso necessário
                const refInputModal = document.getElementById('rascunho_ref_input');
                if (refInputModal && !refInputModal.value) refInputModal.value = refAtual;
                
                showShortcutToast('Salvando rascunho...', 'info');
                try {
                    await window.confirmarSalvarRascunho(true);
                    showShortcutToast('✅ Rascunho salvo com sucesso! (Ctrl + S)', 'success');
                } catch(e) {
                    showShortcutToast('Erro ao salvar rascunho.', 'danger');
                }
            } else if (typeof window.abrirModalSalvarRascunho === 'function') {
                // Se nunca foi salvo nem tem referência, abre o modal para o usuário escolher o nome
                window.abrirModalSalvarRascunho();
            }
            return;
        }

        // 2. Modais ativos ou formulários de cadastro (Empresas, Feiras, Localidades)
        const modalAberto = document.querySelector('.modal.show');
        if (modalAberto) {
            const btnSalvarModal = modalAberto.querySelector('button[type="submit"], button.btn-primary, button.btn-nft:not([data-bs-dismiss])');
            if (btnSalvarModal && typeof btnSalvarModal.click === 'function') {
                btnSalvarModal.click();
                showShortcutToast('Salvando formulário... (Ctrl + S)', 'success');
                return;
            }
        }

        // 3. Fallback genérico para botão Salvar na página
        const btnSalvarGeral = document.querySelector('button#btnSalvar, button.btn-salvar, form button[type="submit"]');
        if (btnSalvarGeral && typeof btnSalvarGeral.click === 'function') {
            btnSalvarGeral.click();
            showShortcutToast('Salvando... (Ctrl + S)', 'success');
            return;
        }

        // 4. Salva sessão imediata de autosave se disponível
        if (typeof window.triggerAutoSave === 'function') {
            window.triggerAutoSave();
            showShortcutToast('Sessão salva com sucesso! (Ctrl + S)', 'success');
        }
    };

    // === 3. LISTENER GLOBAL DE TECLADO ===
    document.addEventListener('keydown', function (e) {
        const isCtrlOrCmd = e.ctrlKey || e.metaKey;
        if (!isCtrlOrCmd) return;

        const key = e.key.toLowerCase();

        // 1. CTRL + S (Salvar)
        if (key === 's') {
            e.preventDefault();
            e.stopPropagation();
            window.nftSalvarAtalho();
            return;
        }

        // 2. CTRL + SHIFT + Z OU CTRL + Y (Refazer / Redo)
        if ((key === 'z' && e.shiftKey) || (key === 'y' && !e.shiftKey)) {
            // Se o foco estiver em um input com histórico nativo de texto não esgotado, podemos respeitar ou interceptar.
            // Em formulários complexos fiscais onde se altera itens e configurações, interceptamos caso não seja input de texto ou se o usuário estiver na tabela.
            const target = e.target;
            const isTextEditable = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') && !target.readOnly;
            
            // Se não for edição de texto simples ou se foi disparado no corpo da página
            if (!isTextEditable || target.closest('.tabulator') || target.type === 'checkbox' || target.type === 'radio') {
                e.preventDefault();
                e.stopPropagation();
                window.nftRefazer();
            }
            return;
        }

        // 3. CTRL + Z (Desfazer / Undo)
        if (key === 'z' && !e.shiftKey) {
            const target = e.target;
            const isTextEditable = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') && !target.readOnly;
            
            // Permite undo de itens/tabela se não estiver ativamente digitando num input de texto, ou se o foco estiver fora de inputs
            if (!isTextEditable || target.closest('.tabulator') || target.type === 'checkbox' || target.type === 'radio') {
                e.preventDefault();
                e.stopPropagation();
                window.nftDesfazer();
            }
            return;
        }
    }, true);

    // === 4. MONITORAMENTO AUTOMÁTICO DE ESTADO PARA O UNDO STACK ===
    document.addEventListener('DOMContentLoaded', function () {
        // Salva estado inicial após carregar os dados
        setTimeout(() => {
            window.nftRegistrarSnapshot('Estado Inicial');
        }, 1200);

        // Monitora alterações em inputs e selects
        document.body.addEventListener('input', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) {
                debouncedRegistrarSnapshot('Edição de campo');
            }
        });

        document.body.addEventListener('change', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) {
                window.nftRegistrarSnapshot('Alteração de opção');
            }
        });
    });

})();

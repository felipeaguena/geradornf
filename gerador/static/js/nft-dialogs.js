/**
 * NFT Logistics - Modern Dialogs System (Alert & Confirm)
 * Substitui os popups nativos do navegador por caixas modernas centralizadas,
 * com fundo escurecido e blur, ícones em formato 'line' e suporte nativo aos temas claro/escuro.
 */

(function () {
    let activeDialogPromise = null;
    let containerEl = null;

    function getOrCreateDialogContainer() {
        if (containerEl && document.body.contains(containerEl)) {
            return containerEl;
        }

        containerEl = document.createElement('div');
        containerEl.id = 'nft-dialog-container';
        containerEl.className = 'nft-dialog-overlay';
        containerEl.setAttribute('role', 'dialog');
        containerEl.setAttribute('aria-modal', 'true');
        containerEl.style.display = 'none';

        containerEl.innerHTML = `
            <div class="nft-dialog-box" id="nft-dialog-box">
                <div class="nft-dialog-icon-wrap" id="nft-dialog-icon-wrap">
                    <i id="nft-dialog-icon" data-lucide="info"></i>
                </div>
                <div class="nft-dialog-content">
                    <h5 class="nft-dialog-title" id="nft-dialog-title">Aviso</h5>
                    <div class="nft-dialog-message" id="nft-dialog-message"></div>
                </div>
                <div class="nft-dialog-actions" id="nft-dialog-actions">
                    <button type="button" class="btn btn-outline-secondary nft-dialog-btn-cancel" id="nft-dialog-btn-cancel">Cancelar</button>
                    <button type="button" class="btn btn-primary nft-dialog-btn-confirm" id="nft-dialog-btn-confirm">OK</button>
                </div>
            </div>
        `;

        document.body.appendChild(containerEl);
        return containerEl;
    }

    function formatMessageText(msg) {
        if (msg === null || msg === undefined) return '';
        const str = String(msg).trim();
        // Remove emojis duplicados do início do texto já que o ícone do topo representa o status
        const cleanStr = str.replace(/^[✅❌⚠️ℹ️?!\s]+/, '');
        
        // Separa por quebras de linha duplas ou simples
        const paragraphs = cleanStr.split(/\n+/).filter(Boolean);
        if (paragraphs.length <= 1) {
            return `<p class="mb-0">${cleanStr.replace(/\n/g, '<br>')}</p>`;
        }

        return paragraphs.map((p, idx) => {
            const isLast = idx === paragraphs.length - 1;
            // Se parecer um item de lista (bullet)
            if (p.trim().startsWith('•') || p.trim().startsWith('-')) {
                return `<div class="text-start ps-3 ${isLast ? 'mb-0' : 'mb-1'}">${p}</div>`;
            }
            return `<p class="${isLast ? 'mb-0' : 'mb-2'}">${p}</p>`;
        }).join('');
    }

    function detectTypeFromContent(msg, explicitType) {
        if (explicitType) return explicitType;
        const lower = String(msg).toLowerCase();
        if (lower.includes('erro') || lower.includes('falha') || lower.includes('excluir') || lower.includes('remover') || String(msg).includes('❌')) {
            return 'danger';
        }
        if (lower.includes('sucesso') || lower.includes('concluíd') || lower.includes('salvo com sucesso') || String(msg).includes('✅')) {
            return 'success';
        }
        if (lower.includes('atenção') || lower.includes('cuidado') || lower.includes('em branco') || lower.includes('zerar') || lower.includes('certeza') || String(msg).includes('⚠️')) {
            return 'warning';
        }
        return 'info';
    }

    function getIconName(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'danger': return 'alert-circle';
            case 'warning': return 'alert-triangle';
            case 'info':
            default: return 'info';
        }
    }

    function getDefaultTitle(type) {
        switch (type) {
            case 'success': return 'Sucesso';
            case 'danger': return 'Atenção';
            case 'warning': return 'Confirmação';
            case 'info':
            default: return 'Informação';
        }
    }

    /**
     * Exibe um popup modal moderno do tipo Alert.
     * @param {string} message - Mensagem a ser exibida.
     * @param {object} [options] - Opções { title, type, confirmText }
     * @returns {Promise<void>}
     */
    window.nftAlert = function (message, options = {}) {
        return new Promise((resolve) => {
            const container = getOrCreateDialogContainer();
            const type = detectTypeFromContent(message, options.type);
            const title = options.title || getDefaultTitle(type);
            const iconName = options.icon || getIconName(type);
            const confirmText = options.confirmText || 'Entendido';

            const iconWrap = container.querySelector('#nft-dialog-icon-wrap');
            const titleEl = container.querySelector('#nft-dialog-title');
            const msgEl = container.querySelector('#nft-dialog-message');
            const btnCancel = container.querySelector('#nft-dialog-btn-cancel');
            const btnConfirm = container.querySelector('#nft-dialog-btn-confirm');
            const boxEl = container.querySelector('#nft-dialog-box');

            // Configurar ícone e classes de tipo
            iconWrap.className = `nft-dialog-icon-wrap type-${type}`;
            iconWrap.innerHTML = `<i data-lucide="${iconName}"></i>`;

            // Textos
            titleEl.textContent = title;
            msgEl.innerHTML = formatMessageText(message);

            // Botões: no alert, esconde Cancelar
            btnCancel.style.display = 'none';
            btnConfirm.textContent = confirmText;
            btnConfirm.className = `btn btn-${type === 'danger' ? 'danger' : 'primary'} nft-dialog-btn-confirm`;

            function close() {
                container.classList.remove('active');
                document.removeEventListener('keydown', handleKeyDown);
                container.removeEventListener('click', handleBackdropClick);
                setTimeout(() => {
                    container.style.display = 'none';
                    resolve();
                }, 200);
            }

            function handleKeyDown(e) {
                if (e.key === 'Escape' || e.key === 'Enter') {
                    e.preventDefault();
                    close();
                }
            }

            function handleBackdropClick(e) {
                if (e.target === container) {
                    close();
                }
            }

            btnConfirm.onclick = close;
            document.addEventListener('keydown', handleKeyDown);
            container.addEventListener('click', handleBackdropClick);

            container.style.display = 'flex';
            // Renderizar ícones do lucide
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                lucide.createIcons({ root: iconWrap });
            }

            // Animar entrada
            requestAnimationFrame(() => {
                container.classList.add('active');
                btnConfirm.focus();
            });
        });
    };

    /**
     * Exibe um popup modal moderno do tipo Confirm.
     * @param {string} message - Mensagem ou pergunta a ser confirmada.
     * @param {object} [options] - Opções { title, type, confirmText, cancelText, icon }
     * @returns {Promise<boolean>} - Resolve para true (confirmado) ou false (cancelado).
     */
    window.nftConfirm = function (message, options = {}) {
        return new Promise((resolve) => {
            const container = getOrCreateDialogContainer();
            const type = detectTypeFromContent(message, options.type || 'warning');
            const title = options.title || (type === 'danger' ? 'Confirmar Exclusão' : 'Confirmação');
            const iconName = options.icon || (type === 'danger' ? 'trash-2' : getIconName(type));
            const confirmText = options.confirmText || (type === 'danger' ? 'Sim, Excluir' : 'Confirmar');
            const cancelText = options.cancelText || 'Cancelar';

            const iconWrap = container.querySelector('#nft-dialog-icon-wrap');
            const titleEl = container.querySelector('#nft-dialog-title');
            const msgEl = container.querySelector('#nft-dialog-message');
            const btnCancel = container.querySelector('#nft-dialog-btn-cancel');
            const btnConfirm = container.querySelector('#nft-dialog-btn-confirm');

            // Configurar ícone e classes de tipo
            iconWrap.className = `nft-dialog-icon-wrap type-${type}`;
            iconWrap.innerHTML = `<i data-lucide="${iconName}"></i>`;

            // Textos
            titleEl.textContent = title;
            msgEl.innerHTML = formatMessageText(message);

            // Botões: mostra ambos
            btnCancel.style.display = 'inline-flex';
            btnCancel.textContent = cancelText;
            btnConfirm.textContent = confirmText;
            btnConfirm.className = `btn btn-${type === 'danger' ? 'danger' : 'primary'} nft-dialog-btn-confirm`;

            function finish(result) {
                container.classList.remove('active');
                document.removeEventListener('keydown', handleKeyDown);
                container.removeEventListener('click', handleBackdropClick);
                setTimeout(() => {
                    container.style.display = 'none';
                    resolve(result);
                }, 200);
            }

            function handleKeyDown(e) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    finish(false);
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    finish(true);
                }
            }

            function handleBackdropClick(e) {
                if (e.target === container) {
                    finish(false);
                }
            }

            btnConfirm.onclick = () => finish(true);
            btnCancel.onclick = () => finish(false);
            document.addEventListener('keydown', handleKeyDown);
            container.addEventListener('click', handleBackdropClick);

            container.style.display = 'flex';
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                lucide.createIcons({ root: iconWrap });
            }

            // Animar entrada
            requestAnimationFrame(() => {
                container.classList.add('active');
                btnConfirm.focus();
            });
        });
    };

    // Sobrescrever o window.alert tradicional para usar automaticamente o visual moderno com blur
    const _originalAlert = window.alert;
    window.alert = function (message) {
        return window.nftAlert(message);
    };

})();

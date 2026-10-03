/**
 * NFT LOGISTICS - GERENCIADOR DO MENU LATERAL (SIDEBAR)
 * Controla expansão, colapso, hover e sincronização com abas
 */

(function () {
    const STORAGE_KEY = 'nft_sidebar_collapsed';

    // 1. Inicializa Estado da Sidebar (Padrão: Aberto)
    function initSidebarState() {
        const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
        if (isCollapsed) {
            document.body.classList.add('sidebar-collapsed');
        } else {
            document.body.classList.remove('sidebar-collapsed');
        }
        updateToggleButton(isCollapsed);
    }

    // 2. Alterna Estado Aberto / Fechado
    window.toggleSidebar = function () {
        const isCurrentlyCollapsed = document.body.classList.contains('sidebar-collapsed');
        const nextState = !isCurrentlyCollapsed;

        if (nextState) {
            document.body.classList.add('sidebar-collapsed');
        } else {
            document.body.classList.remove('sidebar-collapsed');
        }

        localStorage.setItem(STORAGE_KEY, nextState ? 'true' : 'false');
        updateToggleButton(nextState);

        // Se existir tabela Handsontable ou Tabulator, redimensiona suavemente
        setTimeout(() => {
            if (window.hot && typeof window.hot.render === 'function') {
                window.hot.render();
            }
            if (window.itensTable && typeof window.itensTable.redraw === 'function') {
                window.itensTable.redraw(true);
            }
        }, 300);
    };

    function updateToggleButton(isCollapsed) {
        const btns = document.querySelectorAll('.sidebar-toggle-btn');
        btns.forEach(btn => {
            if (isCollapsed) {
                btn.innerHTML = '▶';
                btn.title = 'Fixar Menu Lateral Aberto';
                btn.setAttribute('aria-label', 'Expandir Menu');
            } else {
                btn.innerHTML = '◀';
                btn.title = 'Recolher Menu Lateral';
                btn.setAttribute('aria-label', 'Recolher Menu');
            }
        });

        const collapseTextEl = document.getElementById('sidebar-collapse-text');
        if (collapseTextEl) {
            collapseTextEl.innerText = isCollapsed ? 'Fixar Aberto' : 'Recolher Menu';
        }
    }

    // 3. Sincronização de Abas (Cabeçalho, Itens, Rodapé, Configurações)
    window.sidebarSwitchTab = function (tabKey) {
        const targetTabBtn = document.getElementById(tabKey + '-tab');
        if (targetTabBtn) {
            if (window.bootstrap && bootstrap.Tab) {
                try {
                    const tabInstance = bootstrap.Tab.getOrCreateInstance(targetTabBtn);
                    tabInstance.show();
                } catch(e) {
                    targetTabBtn.click();
                }
            } else {
                targetTabBtn.click();
            }
        }

        // Força a transição segura dos tab-panes
        const targetPane = document.getElementById(tabKey);
        if (targetPane) {
            const tabContent = targetPane.closest('.tab-content') || document.getElementById('myTabContent');
            if (tabContent) {
                tabContent.querySelectorAll('.tab-pane').forEach(p => {
                    p.classList.remove('show', 'active');
                });
                targetPane.classList.add('show', 'active');
            }
        }

        // Sincroniza abas superiores nav-tabs
        const myTab = document.getElementById('myTab');
        if (myTab) {
            myTab.querySelectorAll('.nav-link').forEach(btn => {
                btn.classList.remove('active');
            });
            if (targetTabBtn) {
                targetTabBtn.classList.add('active');
            }
        }

        setActiveSidebarItem(tabKey);
    };

    function setActiveSidebarItem(tabKey) {
        const items = document.querySelectorAll('.nft-sidebar-btn[data-tab]');
        items.forEach(item => {
            if (item.getAttribute('data-tab') === tabKey) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    // 4. Observador para manter Badge de Itens sincronizado
    function initBadgeObserver() {
        const sourceBadge = document.getElementById('itens-badge');
        const targetBadge = document.getElementById('sidebar-itens-badge');
        if (!sourceBadge || !targetBadge) return;

        const updateBadge = () => {
            const count = sourceBadge.innerText.trim();
            targetBadge.innerText = count;
            if (count === '0' || count === '') {
                targetBadge.className = 'badge bg-secondary-subtle text-muted sidebar-badge';
            } else {
                targetBadge.className = 'badge bg-primary text-white sidebar-badge';
            }
        };

        const observer = new MutationObserver(updateBadge);
        observer.observe(sourceBadge, { childList: true, characterData: true, subtree: true });
        updateBadge();
    }

    // 5. Detecta Mudança de Abas Nativas
    function initTabListeners() {
        const tabButtons = document.querySelectorAll('button[data-bs-toggle="tab"]');
        tabButtons.forEach(btn => {
            btn.addEventListener('shown.bs.tab', function (e) {
                const target = e.target.getAttribute('data-bs-target') || '';
                const tabKey = target.replace('#', '');
                if (tabKey) {
                    setActiveSidebarItem(tabKey);
                }
            });
        });
    }

    // Executa ao carregar o DOM
    document.addEventListener('DOMContentLoaded', function () {
        initSidebarState();
        initTabListeners();
        initBadgeObserver();

        // Detecta aba ativa inicial
        const activeTab = document.querySelector('.nav-tabs .nav-link.active');
        if (activeTab) {
            const target = activeTab.getAttribute('data-bs-target') || '';
            const tabKey = target.replace('#', '');
            if (tabKey) setActiveSidebarItem(tabKey);
        }
    });

    // Aplica estado antes do render final para evitar flash
    initSidebarState();
})();

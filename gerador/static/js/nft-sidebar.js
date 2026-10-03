/**
 * NFT LOGISTICS - GERENCIADOR DO MENU LATERAL (SIDEBAR) & CONTROLE DO SERVIDOR
 */

// === 1. CONTROLE DE ENCERRAMENTO DO SERVIDOR E FECHAMENTO DE JANELAS ===
(function() {
    let isShuttingDown = false;

    window.fecharJanelaCompleta = function() {
        // Tenta fechar a aba/janela por multiplas abordagens
        try { window.close(); } catch(e) {}
        try { window.open('', '_self', ''); window.close(); } catch(e) {}
        try { window.opener = null; window.open('', '_self'); window.close(); } catch(e) {}
        try { self.close(); } catch(e) {}
        try { if (window.top) window.top.close(); } catch(e) {}
        try { open(location, '_self').close(); } catch(e) {}

        // Fallback: se o navegador ainda assim bloquear o fechamento forçado, redireciona para tela em branco
        setTimeout(() => {
            try {
                window.location.replace("about:blank");
                window.close();
            } catch(e) {}
        }, 150);
    };

    window.showShutdownOverlay = function(title, msg, isSuccess) {
        let overlay = document.getElementById('nft-shutdown-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'nft-shutdown-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(15, 23, 42, 0.94);
                backdrop-filter: blur(8px);
                z-index: 999999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
                text-align: center;
                animation: fadeIn 0.25s ease-out;
            `;
            const parent = document.body || document.documentElement;
            if (parent) parent.appendChild(overlay);
        }

        const iconColor = isSuccess ? '#ef4444' : '#f59e0b';
        overlay.innerHTML = `
            <div style="background: #1e293b; border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 36px 44px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.6); max-width: 440px; margin: 16px;">
                <div style="width: 68px; height: 68px; border-radius: 50%; background: rgba(239,68,68,0.15); display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; color: ${iconColor};">
                    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path>
                        <line x1="12" y1="2" x2="12" y2="12"></line>
                    </svg>
                </div>
                <h3 style="font-size: 21px; font-weight: 800; margin-bottom: 10px; color: #f8fafc;">${title}</h3>
                <p style="color: #94a3b8; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">${msg}</p>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button onclick="fecharJanelaCompleta()" style="background: #ef4444; color: #fff; border: none; padding: 11px 24px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                        Fechar Janela
                    </button>
                </div>
            </div>
        `;
    };

    window.encerrarServidor = function() {
        if (confirm("Deseja realmente desligar o servidor do Emissor NF-e?")) {
            isShuttingDown = true;
            window.showShutdownOverlay("Encerrando Servidor...", "O backend na porta 1652 está sendo finalizado. Fechando a janela...", true);
            
            fetch('/api/shutdown', { method: 'POST' })
                .catch(() => {})
                .finally(() => {
                    setTimeout(() => {
                        window.fecharJanelaCompleta();
                    }, 400);
                });
        }
    };

    // Monitora a conexão do servidor (Heartbeat)
    let offlineCount = 0;
    setInterval(() => {
        if (isShuttingDown) return;

        fetch('/api/ping', { method: 'GET', cache: 'no-store' })
            .then(res => {
                if (res.ok) {
                    offlineCount = 0;
                } else {
                    offlineCount++;
                }
            })
            .catch(() => {
                offlineCount++;
                if (offlineCount >= 2 && !isShuttingDown) {
                    isShuttingDown = true;
                    window.showShutdownOverlay("Servidor Desligado", "O backend local foi finalizado. Fechando a janela...", true);
                    setTimeout(() => {
                        window.fecharJanelaCompleta();
                    }, 500);
                }
            });
    }, 3500);

    // Intercepta navegação interna do sistema para usar location.replace
    // Isso mantem history.length === 1 permanentemente, permitindo que window.close()
    // funcione com 100% de sucesso em qualquer tela (sem ser bloqueado pela politica de historico do Chromium).
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        if (!link) return;

        const href = link.getAttribute('href');
        if (!href) return;

        // Ignora links externos, download, abas, modals, APIs ou novas abas
        if (link.target === '_blank' || link.hasAttribute('download') || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('/api')) {
            return;
        }

        // Se for rota interna do sistema
        if (href.startsWith('/') || href.startsWith(window.location.origin)) {
            e.preventDefault();
            window.location.replace(link.href);
        }
    });
})();

// === 2. GERENCIADOR DO MENU LATERAL (SIDEBAR) ===
(function () {
    const STORAGE_KEY = 'nft_sidebar_collapsed';

    // Inicializa Estado da Sidebar (Padrão: Aberto) com proteção contra document.body nulo
    function initSidebarState() {
        if (!document.body) return;
        const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
        if (isCollapsed) {
            document.body.classList.add('sidebar-collapsed');
        } else {
            document.body.classList.remove('sidebar-collapsed');
        }
        updateToggleButton(isCollapsed);
    }

    // Alterna Estado Aberto / Fechado
    window.toggleSidebar = function () {
        if (!document.body) return;
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

    // Sincronização de Abas (Cabeçalho, Itens, Rodapé, Configurações)
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
        const items = document.querySelectorAll('.nft-sidebar-btn');
        items.forEach(item => {
            const onclickAttr = item.getAttribute('onclick') || '';
            if (onclickAttr.includes(`sidebarSwitchTab('${tabKey}')`)) {
                item.classList.add('active');
            } else if (onclickAttr.includes('sidebarSwitchTab')) {
                item.classList.remove('active');
            }
        });
    }

    // Sincronização de Badges da Sidebar com os da Página
    function initBadgeObserver() {
        const itensBadgeMain = document.getElementById('itens-badge');
        const itensBadgeSidebar = document.getElementById('sidebar-itens-badge');

        if (itensBadgeMain && itensBadgeSidebar) {
            const observer = new MutationObserver(() => {
                itensBadgeSidebar.innerText = itensBadgeMain.innerText;
            });
            observer.observe(itensBadgeMain, { childList: true, characterData: true, subtree: true });
            itensBadgeSidebar.innerText = itensBadgeMain.innerText;
        }
    }

    // Listener para quando o usuário clicar diretamente nas abas superiores
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

        // Garante renderização dos ícones Lucide na sidebar
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    });

    // Aplica estado antes do render final se body já estiver disponível
    if (document.body) {
        initSidebarState();
    }
})();

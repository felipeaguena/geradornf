// NFT Logistics Theme Manager (Light / Dark)
(function() {
    function getPreferredTheme() {
        const stored = localStorage.getItem('nft_theme');
        if (stored === 'dark' || stored === 'light') return stored;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
            root.setAttribute('data-theme', 'dark');
        } else {
            root.classList.remove('dark');
            root.setAttribute('data-theme', 'light');
        }
        updateToggleButtons(theme);
    }

    function updateToggleButtons(theme) {
        const btns = document.querySelectorAll('.theme-toggle-btn');
        btns.forEach(btn => {
            if (theme === 'dark') {
                btn.innerHTML = '<i data-lucide="sun"></i>';
                btn.title = 'Alternar para Modo Claro';
                btn.setAttribute('aria-label', 'Modo Claro');
            } else {
                btn.innerHTML = '<i data-lucide="moon"></i>';
                btn.title = 'Alternar para Modo Escuro';
                btn.setAttribute('aria-label', 'Modo Escuro');
            }
        });
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    // Apply immediately to prevent flash
    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme);

    window.toggleTheme = function() {
        const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem('nft_theme', next);
        applyTheme(next);

        // If hot table exists, re-render
        if (window.hot) {
            setTimeout(() => {
                window.hot.render();
            }, 50);
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        updateToggleButtons(getPreferredTheme());
    });
})();

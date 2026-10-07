/**
 * NFT Logistics - Módulo de Gestão da Seção de Exportação (Tag SEFAZ: <exporta>)
 * 
 * Regras do Esquema XML (MOC SEFAZ NF-e v4.00):
 * - Grupo <exporta> posicionado após <infAdic> e antes de <compra>/<cana>
 * - Aplicável exclusivamente em operações com o exterior ou CFOP 7xxx (reexportação / exportação)
 * - Preenchimento opcional. Se informado:
 *     - <UFSaidaPais>: Sigla da UF de Embarque (2 letras, da base de dados)
 *     - <xLocExporta>: Local de embarque (1 a 60 caracteres)
 *     - <xLocDespacho>: Local de despacho (1 a 60 caracteres, opcional)
 */

(function () {
    // 1. Carregar lista de UFs do banco de dados oficial
    async function carregarUfsExportacao() {
        const selectUF = document.getElementById('exporta_UFSaidaPais');
        if (!selectUF) return;

        try {
            const resp = await fetch('/api/localidades/ufs');
            if (!resp.ok) return;
            const ufs = await resp.json();
            if (Array.isArray(ufs) && ufs.length > 0) {
                const valorAtual = selectUF.value;
                // Preserva o primeiro option ("Selecione a UF...")
                selectUF.innerHTML = '<option value="">Selecione a UF de embarque...</option>';
                ufs.forEach(uf => {
                    const opt = document.createElement('option');
                    opt.value = uf;
                    opt.textContent = uf;
                    if (uf === valorAtual) opt.selected = true;
                    selectUF.appendChild(opt);
                });
            }
        } catch (err) {
            console.warn('[NFT Exportação] Não foi possível carregar UFs do banco:', err);
        }
    }

    // 2. Verificar se a operação atual é de exportação ou reexportação
    function verificarExibicaoSecaoExportacao() {
        const secao = document.getElementById('secao_exportacao');
        if (!secao) return;

        const getValSeguro = (id) => {
            const el = document.getElementById(id);
            return el ? String(el.value || '').trim() : '';
        };

        const cfopPadrao = getValSeguro('cfop_padrao');
        const natOp = (getValSeguro('natOp') || getValSeguro('select_operacao')).toUpperCase();
        const idDest = getValSeguro('idDest');
        const destUF = getValSeguro('dest_UF').toUpperCase();

        // Verifica itens da tabela
        let temItemCFOP7 = false;
        try {
            const itens = (window.itensTable && typeof window.itensTable.getData === 'function')
                ? window.itensTable.getData()
                : (window.itensCache || []);
            temItemCFOP7 = itens.some(it => String(it.CFOP || '').trim().startsWith('7'));
        } catch (e) {}

        const isExportacao = (
            cfopPadrao.startsWith('7') ||
            temItemCFOP7 ||
            idDest === '3' ||
            destUF === 'EX' ||
            natOp.includes('EXPORTA') ||
            natOp.includes('REEXPORTA')
        );

        if (isExportacao) {
            if (secao.style.display === 'none' || !secao.style.display) {
                secao.style.display = 'block';
                secao.classList.add('fade-in-secao');
            }
        } else {
            secao.style.display = 'none';
        }
    }

    // 3. Limpar campos de exportação
    function limparCamposExportacao() {
        const u = document.getElementById('exporta_UFSaidaPais');
        const l = document.getElementById('exporta_xLocExporta');
        const d = document.getElementById('exporta_xLocDespacho');
        if (u) u.value = '';
        if (l) l.value = '';
        if (d) d.value = '';
    }

    // 4. Inicialização de listeners
    function inicializarModuloExportacao() {
        carregarUfsExportacao();
        verificarExibicaoSecaoExportacao();

        const camposGatilho = ['select_operacao', 'cfop_padrao', 'idDest', 'dest_UF', 'natOp'];
        camposGatilho.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', verificarExibicaoSecaoExportacao);
                el.addEventListener('input', verificarExibicaoSecaoExportacao);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarModuloExportacao);
    } else {
        inicializarModuloExportacao();
    }

    // Expor globalmente para acesso nos fluxos de rascunho/carga
    window.carregarUfsExportacao = carregarUfsExportacao;
    window.verificarExibicaoSecaoExportacao = verificarExibicaoSecaoExportacao;
    window.limparCamposExportacao = limparCamposExportacao;
})();

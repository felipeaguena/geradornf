/**
 * NFT LOGISTICS - MODAL DEDICADO DE EDIÇÃO E CADASTRO DE ITENS DA NF-E (det nItem)
 * Permite preenchimento objetivo, rápido e validado com recálculos automáticos de totais e impostos.
 */

(function () {
    let currentModalItemIndex = -1; // -1 = Novo Item, >= 0 = Editando item existente
    let cstOptionsCache = null;

    // Converte string para número float seguro
    function parseNum(val) {
        if (!val) return 0;
        if (typeof val === 'number') return isNaN(val) ? 0 : val;
        let s = String(val).trim();
        if (s.includes(',') && s.includes('.')) {
            s = s.replace(/\./g, '').replace(',', '.');
        } else if (s.includes(',')) {
            s = s.replace(',', '.');
        }
        const n = parseFloat(s);
        return isNaN(n) ? 0 : n;
    }

    function formatNum(val, dec = 2) {
        return parseNum(val).toFixed(dec);
    }

    // Injeta a estrutura HTML da Modal caso não exista no DOM
    function injectItemModalHTML() {
        if (document.getElementById('modalItemDetalhe')) return;

        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modalItemDetalhe';
        modalDiv.tabIndex = -1;
        modalDiv.setAttribute('aria-labelledby', 'modalItemDetalheTitle');
        modalDiv.setAttribute('aria-hidden', 'true');

        modalDiv.innerHTML = `
        <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content shadow-lg border-0">
                <!-- CABEÇALHO DO POPUP -->
                <div class="modal-header border-bottom bg-body-tertiary py-2 px-3">
                    <div class="d-flex align-items-center gap-2">
                        <div class="d-flex align-items-center justify-content-center bg-primary text-white rounded-2" style="width: 32px; height: 32px;" id="modalItemHeaderIcon">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
                        </div>
                        <div>
                            <div class="d-flex align-items-center gap-2">
                                <h5 class="modal-title fw-bold mb-0 text-body" id="modalItemDetalheTitle">Item da NF-e</h5>
                                <span class="badge bg-primary-subtle text-primary border border-primary-subtle font-monospace" id="modalItemBadgeNum">#1</span>
                            </div>
                            <small class="text-muted" id="modalItemSubtitle">Preenchimento objetivo de produtos, quantidades, rateios e impostos.</small>
                        </div>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                </div>

                <!-- CORPO DO POPUP COM ABAS -->
                <div class="modal-body p-3">
                    <!-- NAVEGAÇÃO DE SUB-ABAS -->
                    <ul class="nav nav-tabs nav-fill mb-3" id="modalItemNavTabs" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active fw-semibold d-flex align-items-center justify-content-center gap-2 py-2" id="tab-item-geral-btn" data-bs-toggle="tab" data-bs-target="#tab-item-geral" type="button" role="tab">
                                <span>📦 1. Produto & Valores</span>
                                <span class="badge bg-success-subtle text-success font-monospace" id="modal-badge-resumo-vprod">R$ 0,00</span>
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link fw-semibold d-flex align-items-center justify-content-center gap-2 py-2" id="tab-item-tributos-btn" data-bs-toggle="tab" data-bs-target="#tab-item-tributos" type="button" role="tab">
                                <span>⚖️ 2. Tributação (ICMS, IPI, PIS, COFINS, II)</span>
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link fw-semibold d-flex align-items-center justify-content-center gap-2 py-2" id="tab-item-aduaneiro-btn" data-bs-toggle="tab" data-bs-target="#tab-item-aduaneiro" type="button" role="tab">
                                <span>🌐 3. Declaração Aduaneira (DI / DUIMP) & Trib.</span>
                            </button>
                        </li>
                    </ul>

                    <!-- CONTEÚDO DAS ABAS -->
                    <div class="tab-content" id="modalItemTabContent">
                        
                        <!-- ABA 1: PRODUTO & VALORES -->
                        <div class="tab-pane fade show active" id="tab-item-geral" role="tabpanel">
                            <div class="row g-2">
                                <div class="col-md-2">
                                    <label class="form-label small fw-bold mb-1">Item (nItem)</label>
                                    <input type="text" class="form-control form-control-sm font-monospace text-center bg-body-tertiary fw-bold" id="m_item_nItem" readonly value="1">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label small fw-bold mb-1">Cód. Produto (cProd) <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control form-control-sm font-monospace" id="m_item_cProd" placeholder="Ex: 0001 ou SKU">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label small fw-bold mb-1">Código EAN/GTIN (cEAN)</label>
                                    <input type="text" class="form-control form-control-sm font-monospace" id="m_item_cEAN" value="SEM GTIN">
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label small fw-bold mb-1">CFOP <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control form-control-sm font-monospace text-center fw-bold text-primary" id="m_item_CFOP" placeholder="5102" maxlength="4">
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label small fw-bold mb-1">Origem Mercad.</label>
                                    <select class="form-select form-select-sm" id="m_item_orig">
                                        <option value="0">0 - Nacional</option>
                                        <option value="1">1 - Estrang. Import. Direta</option>
                                        <option value="2">2 - Estrang. Mercado Interno</option>
                                        <option value="3">3 - Nac. Conteúdo Imp. > 40%</option>
                                        <option value="4">4 - Nac. Conf. Proc. Básicos</option>
                                        <option value="5">5 - Nac. Conteúdo Imp. <= 40%</option>
                                        <option value="6">6 - Estrang. sem similar CAMEX</option>
                                        <option value="7">7 - Estrang. Mercado s/ similar</option>
                                        <option value="8">8 - Nac. Conteúdo Imp. > 70%</option>
                                    </select>
                                </div>

                                <div class="col-md-7">
                                    <label class="form-label small fw-bold mb-1">Descrição do Produto (xProd) <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control form-control-sm" id="m_item_xProd" placeholder="Descrição comercial completa do produto...">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label small fw-bold mb-1">NCM <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control form-control-sm font-monospace" id="m_item_NCM" placeholder="Ex: 84713012" maxlength="8">
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label small fw-bold mb-1">CEST</label>
                                    <input type="text" class="form-control form-control-sm font-monospace" id="m_item_CEST" placeholder="Opcional" maxlength="7">
                                </div>

                                <!-- CARD DE QUANTIDADE E VALORES -->
                                <div class="col-12 mt-3">
                                    <div class="card border bg-body-tertiary p-3">
                                        <h6 class="fw-bold mb-2 text-primary d-flex align-items-center gap-1">
                                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                                            <span>Quantidades & Valores Comerciais</span>
                                        </h6>
                                        <div class="row g-2">
                                            <div class="col-md-2">
                                                <label class="form-label small mb-1">Un. Comercial (uCom) <span class="text-danger">*</span></label>
                                                <input type="text" class="form-control form-control-sm text-uppercase text-center font-monospace" id="m_item_uCom" value="UN" maxlength="6">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Quantidade (qCom) <span class="text-danger">*</span></label>
                                                <input type="number" step="0.0001" class="form-control form-control-sm text-end font-monospace fw-semibold" id="m_item_qCom" value="1.0000">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">V. Unitário R$ (vUnCom) <span class="text-danger">*</span></label>
                                                <input type="number" step="0.0001" class="form-control form-control-sm text-end font-monospace fw-semibold" id="m_item_vUnCom" value="0.0000">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1 fw-bold text-success">Total do Produto R$ (vProd)</label>
                                                <input type="text" class="form-control form-control-sm text-end font-monospace fw-bold bg-success-subtle text-success border-success-subtle" id="m_item_vProd" readonly value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- RATEIOS E DESCONTOS -->
                                <div class="col-12 mt-2">
                                    <div class="card border p-3">
                                        <h6 class="fw-bold mb-2 text-secondary d-flex align-items-center gap-1">
                                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg>
                                            <span>Rateio de Despesas, Frete & Descontos (R$)</span>
                                        </h6>
                                        <div class="row g-2">
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Frete (vFrete)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vFrete" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Seguro (vSeg)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vSeg" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Desconto (vDesc)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vDesc" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Outras Desp. (vOutro)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vOutro" value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- INFORMAÇÕES ADICIONAIS DO PRODUTO -->
                                <div class="col-12 mt-2">
                                    <label class="form-label small fw-bold mb-1">Informações Adicionais do Produto (infAdProd)</label>
                                    <textarea class="form-control form-control-sm" id="m_item_infAdProd" rows="2" placeholder="Informações técnicas, número de série, lote, observações específicas deste item..."></textarea>
                                </div>
                            </div>
                        </div>

                        <!-- ABA 2: TRIBUTAÇÃO -->
                        <div class="tab-pane fade" id="tab-item-tributos" role="tabpanel">
                            <div class="row g-3">
                                <!-- ICMS -->
                                <div class="col-md-6">
                                    <div class="card border p-3 h-100 shadow-sm">
                                        <h6 class="fw-bold mb-2 text-primary border-bottom pb-1">ICMS / CSOSN</h6>
                                        <div class="row g-2">
                                            <div class="col-12">
                                                <label class="form-label small mb-1">Situação Tributária (CST / CSOSN)</label>
                                                <select class="form-select form-select-sm font-monospace" id="m_item_CSOSN"></select>
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">% Red. Base</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_pRedBC" value="0.00">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Base ICMS R$</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vBC_ICMS" value="0.00">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Alíq. ICMS %</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_pICMS" value="0.00">
                                            </div>
                                            <div class="col-12">
                                                <label class="form-label small mb-1 fw-bold text-primary">Valor ICMS R$ (vICMS)</label>
                                                <input type="text" class="form-control form-control-sm text-end font-monospace fw-bold bg-body-tertiary" id="m_item_vICMS" value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- IPI -->
                                <div class="col-md-6">
                                    <div class="card border p-3 h-100 shadow-sm">
                                        <h6 class="fw-bold mb-2 text-secondary border-bottom pb-1">IPI</h6>
                                        <div class="row g-2">
                                            <div class="col-md-8">
                                                <label class="form-label small mb-1">CST IPI</label>
                                                <select class="form-select form-select-sm font-monospace" id="m_item_CST_IPI"></select>
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">cEnq IPI</label>
                                                <input type="text" class="form-control form-control-sm text-center font-monospace" id="m_item_cEnq" value="999">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Base IPI R$</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vBC_IPI" value="0.00">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Alíq. IPI %</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_pIPI" value="0.00">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1 fw-bold">Valor IPI R$</label>
                                                <input type="text" class="form-control form-control-sm text-end font-monospace fw-bold bg-body-tertiary" id="m_item_vIPI" value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- PIS -->
                                <div class="col-md-6">
                                    <div class="card border p-3 shadow-sm">
                                        <h6 class="fw-bold mb-2 text-secondary border-bottom pb-1">PIS</h6>
                                        <div class="row g-2">
                                            <div class="col-12">
                                                <label class="form-label small mb-1">CST PIS</label>
                                                <select class="form-select form-select-sm font-monospace" id="m_item_CST_PIS"></select>
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Base PIS R$</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vBC_PIS" value="0.00">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Alíq. PIS %</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_pPIS" value="1.65">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1 fw-bold">Valor PIS R$</label>
                                                <input type="text" class="form-control form-control-sm text-end font-monospace fw-bold bg-body-tertiary" id="m_item_vPIS" value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- COFINS -->
                                <div class="col-md-6">
                                    <div class="card border p-3 shadow-sm">
                                        <h6 class="fw-bold mb-2 text-secondary border-bottom pb-1">COFINS</h6>
                                        <div class="row g-2">
                                            <div class="col-12">
                                                <label class="form-label small mb-1">CST COFINS</label>
                                                <select class="form-select form-select-sm font-monospace" id="m_item_CST_COFINS"></select>
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Base COFINS R$</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vBC_COFINS" value="0.00">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Alíq. COFINS %</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_pCOFINS" value="7.60">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1 fw-bold">Valor COFINS R$</label>
                                                <input type="text" class="form-control form-control-sm text-end font-monospace fw-bold bg-body-tertiary" id="m_item_vCOFINS" value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- IMPOSTO DE IMPORTAÇÃO (II) & IOF -->
                                <div class="col-12">
                                    <div class="card border p-3 shadow-sm bg-body-tertiary">
                                        <h6 class="fw-bold mb-2 text-dark border-bottom pb-1">Imposto de Importação (II) & Despesas Aduaneiras</h6>
                                        <div class="row g-2">
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Base II (R$)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vBC_II" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Desp. Aduaneiras (vDespAdu)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vDespAdu" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Valor II (vII)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vII" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Valor IOF (vIOF)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vIOF" value="0.00">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- ABA 3: DECLARAÇÃO ADUANEIRA (DI / DUIMP) & UNIDADE TRIBUTÁVEL -->
                        <div class="tab-pane fade" id="tab-item-aduaneiro" role="tabpanel">
                            <div class="row g-3">
                                <!-- UNIDADES TRIBUTÁVEIS (uTrib) -->
                                <div class="col-12">
                                    <div class="card border p-3 bg-body-tertiary">
                                        <div class="d-flex justify-content-between align-items-center mb-2 border-bottom pb-1">
                                            <h6 class="fw-bold mb-0 text-primary">Unidade Tributável na SEFAZ (uTrib / qTrib / vUnTrib)</h6>
                                            <button type="button" class="btn btn-xs btn-outline-primary py-0 px-2" id="btn-copiar-com-para-trib">
                                                Copiar Comercial ➔ Tributável
                                            </button>
                                        </div>
                                        <div class="row g-2">
                                            <div class="col-md-2">
                                                <label class="form-label small mb-1">Un. Trib (uTrib)</label>
                                                <input type="text" class="form-control form-control-sm text-uppercase text-center font-monospace" id="m_item_uTrib" value="UN" maxlength="6">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Qtd. Trib (qTrib)</label>
                                                <input type="number" step="0.0001" class="form-control form-control-sm text-end font-monospace" id="m_item_qTrib" value="1.0000">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">V. Unit. Trib (vUnTrib)</label>
                                                <input type="number" step="0.0001" class="form-control form-control-sm text-end font-monospace" id="m_item_vUnTrib" value="0.0000">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">GTIN Tributável (cEANTrib)</label>
                                                <input type="text" class="form-control form-control-sm font-monospace" id="m_item_cEANTrib" value="SEM GTIN">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- DADOS DA DI / DUIMP -->
                                <div class="col-12">
                                    <div class="card border p-3">
                                        <h6 class="fw-bold mb-2 text-dark border-bottom pb-1">Declaração de Importação (DI / DUIMP) & Adição</h6>
                                        <div class="row g-2">
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Número DI/DUIMP (nDI)</label>
                                                <input type="text" class="form-control form-control-sm font-monospace" id="m_item_nDI" placeholder="Ex: 24/1234567-8">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Data Registro (dDI)</label>
                                                <input type="date" class="form-control form-control-sm" id="m_item_dDI">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Local Desembaraço (xLocDesemb)</label>
                                                <input type="text" class="form-control form-control-sm" id="m_item_xLocDesemb" placeholder="Ex: PORTO DE SANTOS">
                                            </div>
                                            <div class="col-md-2">
                                                <label class="form-label small mb-1">UF Desemb.</label>
                                                <input type="text" class="form-control form-control-sm text-uppercase text-center font-monospace" id="m_item_UFDesemb" maxlength="2" placeholder="SP">
                                            </div>

                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Data Desembaraço</label>
                                                <input type="date" class="form-control form-control-sm" id="m_item_dDesemb">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Via de Transporte</label>
                                                <select class="form-select form-select-sm" id="m_item_tpViaTransp">
                                                    <option value="1">1 - Marítima</option>
                                                    <option value="2">2 - Fluvial</option>
                                                    <option value="3">3 - Lacustre</option>
                                                    <option value="4">4 - Aérea</option>
                                                    <option value="5">5 - Postal</option>
                                                    <option value="6">6 - Ferroviária</option>
                                                    <option value="7">7 - Rodoviária</option>
                                                    <option value="8">8 - Conduto / Rede Transmissão</option>
                                                    <option value="9">9 - Meios Próprios</option>
                                                    <option value="10">10 - Entrada / Saída Ficta</option>
                                                </select>
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">AFRMM (vAFRMM)</label>
                                                <input type="number" step="0.01" class="form-control form-control-sm text-end font-monospace" id="m_item_vAFRMM" value="0.00">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Intermediação</label>
                                                <select class="form-select form-select-sm" id="m_item_tpIntermedio">
                                                    <option value="1">1 - Importação Conta Própria</option>
                                                    <option value="2">2 - Importação Conta e Ordem</option>
                                                    <option value="3">3 - Importação por Encomenda</option>
                                                </select>
                                            </div>

                                            <div class="col-md-2">
                                                <label class="form-label small mb-1">Nº Adição</label>
                                                <input type="text" class="form-control form-control-sm text-center font-monospace" id="m_item_nAdicao" value="1">
                                            </div>
                                            <div class="col-md-2">
                                                <label class="form-label small mb-1">Seq. Adição</label>
                                                <input type="text" class="form-control form-control-sm text-center font-monospace" id="m_item_nSeqAdic" value="1">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Cód. Fabricante (cFabricante)</label>
                                                <input type="text" class="form-control form-control-sm font-monospace" id="m_item_cFabricante" placeholder="Fabricante estrangeiro">
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label small mb-1">Cód. Exportador (cExportador)</label>
                                                <input type="text" class="form-control form-control-sm font-monospace" id="m_item_cExportador" placeholder="Exportador estrangeiro">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- CÂMBIO & CONVERSÃO -->
                                <div class="col-12">
                                    <div class="card border p-3 bg-body-tertiary">
                                        <h6 class="fw-bold mb-2 text-secondary border-bottom pb-1">Câmbio & Conversão de Moeda Estrangeira</h6>
                                        <div class="row g-2">
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Moeda Utilizada</label>
                                                <input type="text" class="form-control form-control-sm text-uppercase text-center font-monospace" id="m_item_moeda_conversao" placeholder="USD / EUR">
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label small mb-1">Taxa Câmbio (PTAX)</label>
                                                <input type="number" step="0.0001" class="form-control form-control-sm text-end font-monospace" id="m_item_taxa_conversao" placeholder="Ex: 5.4321">
                                            </div>
                                            <div class="col-md-6 d-flex align-items-end">
                                                <small class="text-muted">Esses valores são registrados como referência de conversão da DI/DUIMP para a moeda nacional.</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- RODAPÉ DO POPUP -->
                <div class="modal-footer border-top bg-body-tertiary py-2 px-3 d-flex justify-content-between">
                    <div>
                        <button type="button" class="btn btn-sm btn-outline-warning d-inline-flex align-items-center gap-1" id="btn-recalcular-impostos-modal" title="Recalcular automaticamente ICMS, IPI, PIS e COFINS com base no Total do Produto">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                            <span>Recalcular Impostos</span>
                        </button>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-success btn-sm fw-bold px-3 d-inline-flex align-items-center gap-2 shadow-sm" id="btn-salvar-item-modal">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                            <span id="btn-salvar-item-modal-texto">Salvar Item</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;

        document.body.appendChild(modalDiv);
        vincularEventosCalculosModal();
        carregarCSTsParaModal();
    }

    // Carrega CSTs oficiais nos selects da Modal
    async function carregarCSTsParaModal() {
        try {
            if (!cstOptionsCache) {
                const resp = await fetch('/api/csts');
                const data = await resp.json();
                if (data.status === 'success' && data.csts) {
                    cstOptionsCache = data.csts;
                }
            }

            if (!cstOptionsCache) return;

            // 1. ICMS / CSOSN
            const selCsosn = document.getElementById('m_item_CSOSN');
            if (selCsosn && selCsosn.options.length <= 1) {
                selCsosn.innerHTML = '';
                const grpCsosn = document.createElement('optgroup');
                grpCsosn.label = 'Simples Nacional (CSOSN)';
                const grpIcms = document.createElement('optgroup');
                grpIcms.label = 'Regime Normal (CST ICMS)';
                (cstOptionsCache.csosn || []).forEach(c => grpCsosn.appendChild(new Option(c.codigo_descricao, c.codigo)));
                (cstOptionsCache.icms || []).forEach(c => grpIcms.appendChild(new Option(c.codigo_descricao, c.codigo)));
                selCsosn.appendChild(grpCsosn);
                selCsosn.appendChild(grpIcms);
            }

            // 2. IPI
            const selIpi = document.getElementById('m_item_CST_IPI');
            if (selIpi && selIpi.options.length <= 1) {
                selIpi.innerHTML = '';
                (cstOptionsCache.ipi || []).forEach(c => selIpi.appendChild(new Option(c.codigo_descricao, c.codigo)));
            }

            // 3. PIS & COFINS
            ['m_item_CST_PIS', 'm_item_CST_COFINS'].forEach(id => {
                const sel = document.getElementById(id);
                if (sel && sel.options.length <= 1) {
                    sel.innerHTML = '';
                    (cstOptionsCache.pis_cofins || []).forEach(c => sel.appendChild(new Option(c.codigo_descricao, c.codigo)));
                }
            });
        } catch (e) {
            console.warn('Erro ao carregar CSTs para o modal:', e);
        }
    }

    // Vincula cálculos em tempo real no formulário da modal
    function vincularEventosCalculosModal() {
        const qComEl = document.getElementById('m_item_qCom');
        const vUnComEl = document.getElementById('m_item_vUnCom');
        const vProdEl = document.getElementById('m_item_vProd');
        const badgeResumo = document.getElementById('modal-badge-resumo-vprod');

        function recalcularTotalItemModal(autoAtualizarImpostos = true) {
            const q = parseNum(qComEl ? qComEl.value : 1);
            const vu = parseNum(vUnComEl ? vUnComEl.value : 0);
            const total = q * vu;
            const totalStr = total.toFixed(2);

            if (vProdEl) vProdEl.value = totalStr;
            if (badgeResumo) badgeResumo.innerText = 'R$ ' + totalStr.replace('.', ',');

            if (autoAtualizarImpostos) {
                recalcularImpostosModal(false);
            }
        }

        if (qComEl) qComEl.addEventListener('input', () => recalcularTotalItemModal(true));
        if (vUnComEl) vUnComEl.addEventListener('input', () => recalcularTotalItemModal(true));

        // Botão copiar comercial para tributável
        const btnCopiar = document.getElementById('btn-copiar-com-para-trib');
        if (btnCopiar) {
            btnCopiar.addEventListener('click', function () {
                const uCom = (document.getElementById('m_item_uCom').value || 'UN').trim();
                const qCom = document.getElementById('m_item_qCom').value || '1.0000';
                const vUnCom = document.getElementById('m_item_vUnCom').value || '0.0000';

                document.getElementById('m_item_uTrib').value = uCom;
                document.getElementById('m_item_qTrib').value = qCom;
                document.getElementById('m_item_vUnTrib').value = vUnCom;
            });
        }

        // Botão recalcular impostos
        const btnRecalcImp = document.getElementById('btn-recalcular-impostos-modal');
        if (btnRecalcImp) {
            btnRecalcImp.addEventListener('click', () => recalcularImpostosModal(true));
        }

        // Listeners de impostos individuais
        ['m_item_vBC_ICMS', 'm_item_pICMS'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', calcICMS);
        });
        ['m_item_vBC_IPI', 'm_item_pIPI'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', calcIPI);
        });
        ['m_item_vBC_PIS', 'm_item_pPIS'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', calcPIS);
        });
        ['m_item_vBC_COFINS', 'm_item_pCOFINS'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', calcCOFINS);
        });

        // Botão Salvar
        const btnSalvar = document.getElementById('btn-salvar-item-modal');
        if (btnSalvar) {
            btnSalvar.addEventListener('click', salvarModalItem);
        }
    }

    function calcICMS() {
        const bc = parseNum(document.getElementById('m_item_vBC_ICMS').value);
        const p = parseNum(document.getElementById('m_item_pICMS').value);
        document.getElementById('m_item_vICMS').value = (bc * (p / 100)).toFixed(2);
    }

    function calcIPI() {
        const bc = parseNum(document.getElementById('m_item_vBC_IPI').value);
        const p = parseNum(document.getElementById('m_item_pIPI').value);
        document.getElementById('m_item_vIPI').value = (bc * (p / 100)).toFixed(2);
    }

    function calcPIS() {
        const bc = parseNum(document.getElementById('m_item_vBC_PIS').value);
        const p = parseNum(document.getElementById('m_item_pPIS').value);
        document.getElementById('m_item_vPIS').value = (bc * (p / 100)).toFixed(2);
    }

    function calcCOFINS() {
        const bc = parseNum(document.getElementById('m_item_vBC_COFINS').value);
        const p = parseNum(document.getElementById('m_item_pCOFINS').value);
        document.getElementById('m_item_vCOFINS').value = (bc * (p / 100)).toFixed(2);
    }

    function recalcularImpostosModal(forcar = false) {
        const vProd = parseNum(document.getElementById('m_item_vProd').value);
        const vFrete = parseNum(document.getElementById('m_item_vFrete').value);
        const vSeg = parseNum(document.getElementById('m_item_vSeg').value);

        // ICMS
        const elBcIcms = document.getElementById('m_item_vBC_ICMS');
        if (forcar || parseNum(elBcIcms.value) === 0 || parseNum(elBcIcms.value) === vProd) {
            elBcIcms.value = vProd.toFixed(2);
        }
        calcICMS();

        // IPI
        const elBcIpi = document.getElementById('m_item_vBC_IPI');
        if (forcar || parseNum(elBcIpi.value) === 0) {
            elBcIpi.value = vProd.toFixed(2);
        }
        calcIPI();

        // PIS & COFINS
        const elBcPis = document.getElementById('m_item_vBC_PIS');
        if (forcar || parseNum(elBcPis.value) === 0) {
            elBcPis.value = vProd.toFixed(2);
        }
        calcPIS();

        const elBcCofins = document.getElementById('m_item_vBC_COFINS');
        if (forcar || parseNum(elBcCofins.value) === 0) {
            elBcCofins.value = vProd.toFixed(2);
        }
        calcCOFINS();

        // II
        const elBcII = document.getElementById('m_item_vBC_II');
        if (forcar || parseNum(elBcII.value) === 0) {
            elBcII.value = (vProd + vFrete + vSeg).toFixed(2);
        }
    }

    // Obtém a lista atual de itens
    function getListaItensAtual() {
        if (Array.isArray(window.itensCache)) return window.itensCache;
        if (window.itensTable && typeof window.itensTable.getData === 'function') {
            return window.itensTable.getData();
        }
        const t = window.Tabulator ? window.Tabulator.findTable('#itens-table')[0] : null;
        if (t) return t.getData();
        return [];
    }

    // Salva a lista de itens e atualiza tabela e totais
    function aplicarListaItensAtual(novaLista, scrollToIdx = -1) {
        window.itensCache = novaLista;

        let table = window.itensTable;
        if (!table && window.Tabulator) {
            const arr = window.Tabulator.findTable('#itens-table');
            if (arr && arr.length > 0) table = arr[0];
        }

        if (table) {
            table.setData(novaLista);
            if (scrollToIdx >= 0) {
                const rows = table.getRows();
                if (rows && rows[scrollToIdx]) {
                    rows[scrollToIdx].scrollTo();
                }
            }
        }

        // Atualiza contador no badge da aba
        const badge = document.getElementById('itens-badge');
        if (badge) badge.innerText = novaLista.length;

        // Recalcula totais gerais da nota
        if (typeof window.recalcularTotaisDosItens === 'function') {
            window.recalcularTotaisDosItens(true);
        }
        if (typeof window.atualizarBadgesRateioEItens === 'function') {
            window.atualizarBadgesRateioEItens();
        }
    }

    // ABRIR MODAL: NOVO ITEM
    window.abrirModalItemNovo = function () {
        injectItemModalHTML();
        carregarCSTsParaModal();

        currentModalItemIndex = -1;
        const lista = getListaItensAtual();
        const proxItemNum = lista.length + 1;

        // Recupera valores padrão da Operação selecionada se existir
        let opCfop = "5102";
        let opCsosn = "00";
        let opAliqIcms = "0.00";
        let opCstIpi = "99";
        let opAliqIpi = "0.00";
        let opCstPis = "01";
        let opAliqPis = "1.65";
        let opCstCofins = "01";
        let opAliqCofins = "7.60";

        if (window.operacoesCache && Array.isArray(window.operacoesCache)) {
            const selOp = document.getElementById('select_operacao');
            const nomeOp = selOp ? selOp.value : '';
            const op = window.operacoesCache.find(o => o.nome_operacao && o.nome_operacao.toUpperCase() === (nomeOp || '').toUpperCase());
            if (op) {
                if (op.cfop_padrao) opCfop = op.cfop_padrao;
                if (op.csosn_icms) opCsosn = op.csosn_icms;
                if (op.aliquota_icms !== undefined) opAliqIcms = String(op.aliquota_icms);
                if (op.cst_ipi) opCstIpi = op.cst_ipi;
                if (op.aliquota_ipi !== undefined) opAliqIpi = String(op.aliquota_ipi);
                if (op.cst_pis) opCstPis = op.cst_pis;
                if (op.aliquota_pis !== undefined) opAliqPis = String(op.aliquota_pis);
                if (op.cst_cofins) opCstCofins = op.cst_cofins;
                if (op.aliquota_cofins !== undefined) opAliqCofins = String(op.aliquota_cofins);
            }
        }

        // Títulos e cabeçalho
        document.getElementById('modalItemDetalheTitle').innerText = "Adicionar Novo Item da NF-e";
        document.getElementById('modalItemBadgeNum').innerText = "#" + proxItemNum;
        document.getElementById('modalItemSubtitle').innerText = "Preencha os campos abaixo e clique em Confirmar para inserir na grade da nota.";
        document.getElementById('btn-salvar-item-modal-texto').innerText = "Adicionar à Nota";

        // Preenche campos padrões
        document.getElementById('m_item_nItem').value = String(proxItemNum);
        document.getElementById('m_item_cProd').value = String(proxItemNum).padStart(4, '0');
        document.getElementById('m_item_cEAN').value = "SEM GTIN";
        document.getElementById('m_item_xProd').value = "";
        document.getElementById('m_item_NCM').value = "";
        document.getElementById('m_item_CEST').value = "";
        document.getElementById('m_item_CFOP').value = opCfop;
        document.getElementById('m_item_orig').value = "0";
        document.getElementById('m_item_uCom').value = "UN";
        document.getElementById('m_item_qCom').value = "1.0000";
        document.getElementById('m_item_vUnCom').value = "0.0000";
        document.getElementById('m_item_vProd').value = "0.00";
        document.getElementById('modal-badge-resumo-vprod').innerText = "R$ 0,00";
        document.getElementById('m_item_vFrete').value = "0.00";
        document.getElementById('m_item_vSeg').value = "0.00";
        document.getElementById('m_item_vDesc').value = "0.00";
        document.getElementById('m_item_vOutro').value = "0.00";
        document.getElementById('m_item_infAdProd').value = "";

        // Tributos padrão
        const selCsosn = document.getElementById('m_item_CSOSN');
        if (selCsosn) selCsosn.value = opCsosn;
        document.getElementById('m_item_pRedBC').value = "0.00";
        document.getElementById('m_item_vBC_ICMS').value = "0.00";
        document.getElementById('m_item_pICMS').value = opAliqIcms;
        document.getElementById('m_item_vICMS').value = "0.00";

        const selIpi = document.getElementById('m_item_CST_IPI');
        if (selIpi) selIpi.value = opCstIpi;
        document.getElementById('m_item_cEnq').value = "999";
        document.getElementById('m_item_vBC_IPI').value = "0.00";
        document.getElementById('m_item_pIPI').value = opAliqIpi;
        document.getElementById('m_item_vIPI').value = "0.00";

        const selPis = document.getElementById('m_item_CST_PIS');
        if (selPis) selPis.value = opCstPis;
        document.getElementById('m_item_vBC_PIS').value = "0.00";
        document.getElementById('m_item_pPIS').value = opAliqPis;
        document.getElementById('m_item_vPIS').value = "0.00";

        const selCofins = document.getElementById('m_item_CST_COFINS');
        if (selCofins) selCofins.value = opCstCofins;
        document.getElementById('m_item_vBC_COFINS').value = "0.00";
        document.getElementById('m_item_pCOFINS').value = opAliqCofins;
        document.getElementById('m_item_vCOFINS').value = "0.00";

        document.getElementById('m_item_vBC_II').value = "0.00";
        document.getElementById('m_item_vDespAdu').value = "0.00";
        document.getElementById('m_item_vII').value = "0.00";
        document.getElementById('m_item_vIOF').value = "0.00";

        // Unidade Tributável padrão
        document.getElementById('m_item_uTrib').value = "UN";
        document.getElementById('m_item_qTrib').value = "1.0000";
        document.getElementById('m_item_vUnTrib').value = "0.0000";
        document.getElementById('m_item_cEANTrib').value = "SEM GTIN";

        // Dados DI herdados da Identificação da Importação no cabeçalho (se preenchidos)
        const elDiGeral = document.getElementById('import_nDI') || document.getElementById('di_numero') || document.getElementById('numero_di');
        const elDdiGeral = document.getElementById('import_dDI');
        const elLocDesembGeral = document.getElementById('import_xLocDesemb');
        const elUfDesembGeral = document.getElementById('import_UFDesemb');
        const elDDesembGeral = document.getElementById('import_dDesemb');
        const elViaTranspGeral = document.getElementById('import_tpViaTransp');
        const elIntermedioGeral = document.getElementById('import_tpIntermedio');
        const elExportadorGeral = document.getElementById('import_cExportador') || document.getElementById('dest_xNome');

        document.getElementById('m_item_nDI').value = elDiGeral ? elDiGeral.value : "";
        document.getElementById('m_item_dDI').value = elDdiGeral ? elDdiGeral.value : "";
        document.getElementById('m_item_xLocDesemb').value = elLocDesembGeral ? elLocDesembGeral.value : "";
        document.getElementById('m_item_UFDesemb').value = elUfDesembGeral ? elUfDesembGeral.value : "";
        document.getElementById('m_item_dDesemb').value = elDDesembGeral ? elDDesembGeral.value : "";
        document.getElementById('m_item_tpViaTransp').value = elViaTranspGeral ? elViaTranspGeral.value : "1";
        document.getElementById('m_item_tpIntermedio').value = elIntermedioGeral ? elIntermedioGeral.value : "1";
        document.getElementById('m_item_vAFRMM').value = "0.00";
        document.getElementById('m_item_nAdicao').value = "1";
        document.getElementById('m_item_nSeqAdic').value = "1";
        document.getElementById('m_item_cFabricante').value = "";
        document.getElementById('m_item_cExportador').value = elExportadorGeral ? elExportadorGeral.value : "";
        document.getElementById('m_item_moeda_conversao').value = "";
        document.getElementById('m_item_taxa_conversao').value = "";

        // Ativa a primeira aba
        const tabBtn = document.getElementById('tab-item-geral-btn');
        if (tabBtn && window.bootstrap && bootstrap.Tab) {
            bootstrap.Tab.getOrCreateInstance(tabBtn).show();
        }

        // Abre a modal
        const modalEl = document.getElementById('modalItemDetalhe');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();

        setTimeout(() => {
            const xProd = document.getElementById('m_item_xProd');
            if (xProd) xProd.focus();
        }, 200);
    };

    // ABRIR MODAL: EDITAR ITEM EXISTENTE
    window.abrirModalItemEditar = function (rowData, optIndex = -1) {
        if (!rowData) return;
        injectItemModalHTML();
        carregarCSTsParaModal();

        const lista = getListaItensAtual();
        let idx = -1;
        if (optIndex >= 0 && optIndex < lista.length) {
            idx = optIndex;
        } else {
            idx = lista.findIndex(it => it === rowData || (it.nItem && String(it.nItem) === String(rowData.nItem)));
        }
        currentModalItemIndex = idx >= 0 ? idx : 0;

        // Títulos e cabeçalho
        document.getElementById('modalItemDetalheTitle').innerText = "Editar Item #" + (rowData.nItem || (currentModalItemIndex + 1));
        document.getElementById('modalItemBadgeNum').innerText = (rowData.cProd || "ITEM");
        document.getElementById('modalItemSubtitle').innerText = (rowData.xProd || "Edição detalhada do item");
        document.getElementById('btn-salvar-item-modal-texto').innerText = "Salvar Alterações";

        // Preenche campos a partir de rowData
        document.getElementById('m_item_nItem').value = String(rowData.nItem || (currentModalItemIndex + 1));
        document.getElementById('m_item_cProd').value = rowData.cProd || "";
        document.getElementById('m_item_cEAN').value = rowData.cEAN || "SEM GTIN";
        document.getElementById('m_item_xProd').value = rowData.xProd || "";
        document.getElementById('m_item_NCM').value = rowData.NCM || "";
        document.getElementById('m_item_CEST').value = rowData.CEST || "";
        document.getElementById('m_item_CFOP').value = rowData.CFOP || "";
        document.getElementById('m_item_orig').value = String(rowData.orig !== undefined ? rowData.orig : "0");
        document.getElementById('m_item_uCom').value = rowData.uCom || "UN";
        document.getElementById('m_item_qCom').value = formatNum(rowData.qCom, 4);
        document.getElementById('m_item_vUnCom').value = formatNum(rowData.vUnCom, 4);
        
        const vProd = formatNum(rowData.vProd, 2);
        document.getElementById('m_item_vProd').value = vProd;
        document.getElementById('modal-badge-resumo-vprod').innerText = "R$ " + vProd.replace('.', ',');

        document.getElementById('m_item_vFrete').value = formatNum(rowData.vFrete, 2);
        document.getElementById('m_item_vSeg').value = formatNum(rowData.vSeg, 2);
        document.getElementById('m_item_vDesc').value = formatNum(rowData.vDesc, 2);
        document.getElementById('m_item_vOutro').value = formatNum(rowData.vOutro, 2);
        document.getElementById('m_item_infAdProd').value = rowData.infAdProd || "";

        // Tributos
        const cstIcms = rowData.CSOSN || rowData.CST_ICMS || "00";
        const selCsosn = document.getElementById('m_item_CSOSN');
        if (selCsosn) selCsosn.value = cstIcms;
        document.getElementById('m_item_pRedBC').value = formatNum(rowData.pRedBC, 2);
        document.getElementById('m_item_vBC_ICMS').value = formatNum(rowData.vBC_ICMS, 2);
        document.getElementById('m_item_pICMS').value = formatNum(rowData.pICMS, 2);
        document.getElementById('m_item_vICMS').value = formatNum(rowData.vICMS, 2);

        const selIpi = document.getElementById('m_item_CST_IPI');
        if (selIpi) selIpi.value = rowData.CST_IPI || "99";
        document.getElementById('m_item_cEnq').value = rowData.cEnq || "999";
        document.getElementById('m_item_vBC_IPI').value = formatNum(rowData.vBC_IPI, 2);
        document.getElementById('m_item_pIPI').value = formatNum(rowData.pIPI, 2);
        document.getElementById('m_item_vIPI').value = formatNum(rowData.vIPI, 2);

        const selPis = document.getElementById('m_item_CST_PIS');
        if (selPis) selPis.value = rowData.CST_PIS || "01";
        document.getElementById('m_item_vBC_PIS').value = formatNum(rowData.vBC_PIS, 2);
        document.getElementById('m_item_pPIS').value = formatNum(rowData.pPIS, 2);
        document.getElementById('m_item_vPIS').value = formatNum(rowData.vPIS, 2);

        const selCofins = document.getElementById('m_item_CST_COFINS');
        if (selCofins) selCofins.value = rowData.CST_COFINS || "01";
        document.getElementById('m_item_vBC_COFINS').value = formatNum(rowData.vBC_COFINS, 2);
        document.getElementById('m_item_pCOFINS').value = formatNum(rowData.pCOFINS, 2);
        document.getElementById('m_item_vCOFINS').value = formatNum(rowData.vCOFINS, 2);

        document.getElementById('m_item_vBC_II').value = formatNum(rowData.vBC_II, 2);
        document.getElementById('m_item_vDespAdu').value = formatNum(rowData.vDespAdu, 2);
        document.getElementById('m_item_vII').value = formatNum(rowData.vII, 2);
        document.getElementById('m_item_vIOF').value = formatNum(rowData.vIOF, 2);

        // Unidade Tributável
        document.getElementById('m_item_uTrib').value = rowData.uTrib || rowData.uCom || "UN";
        document.getElementById('m_item_qTrib').value = formatNum(rowData.qTrib || rowData.qCom, 4);
        document.getElementById('m_item_vUnTrib').value = formatNum(rowData.vUnTrib || rowData.vUnCom, 4);
        document.getElementById('m_item_cEANTrib').value = rowData.cEANTrib || "SEM GTIN";

        // Dados DI
        document.getElementById('m_item_nDI').value = rowData.nDI || "";
        document.getElementById('m_item_dDI').value = rowData.dDI || "";
        document.getElementById('m_item_xLocDesemb').value = rowData.xLocDesemb || "";
        document.getElementById('m_item_UFDesemb').value = rowData.UFDesemb || "";
        document.getElementById('m_item_dDesemb').value = rowData.dDesemb || "";
        document.getElementById('m_item_tpViaTransp').value = String(rowData.tpViaTransp || "1");
        document.getElementById('m_item_tpIntermedio').value = String(rowData.tpIntermedio || "1");
        document.getElementById('m_item_vAFRMM').value = formatNum(rowData.vAFRMM, 2);
        document.getElementById('m_item_nAdicao').value = String(rowData.nAdicao || "1");
        document.getElementById('m_item_nSeqAdic').value = String(rowData.nSeqAdic || "1");
        document.getElementById('m_item_cFabricante').value = rowData.cFabricante || "";
        document.getElementById('m_item_cExportador').value = rowData.cExportador || "";
        document.getElementById('m_item_moeda_conversao').value = rowData.moeda_conversao || "";
        document.getElementById('m_item_taxa_conversao').value = rowData.taxa_conversao || "";

        // Ativa a primeira aba
        const tabBtn = document.getElementById('tab-item-geral-btn');
        if (tabBtn && window.bootstrap && bootstrap.Tab) {
            bootstrap.Tab.getOrCreateInstance(tabBtn).show();
        }

        // Abre a modal
        const modalEl = document.getElementById('modalItemDetalhe');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();

        setTimeout(() => {
            const xProd = document.getElementById('m_item_xProd');
            if (xProd) xProd.focus();
        }, 200);
    };

    // SALVAR ITEM (NOVO OU EDITADO)
    function salvarModalItem() {
        const xProd = (document.getElementById('m_item_xProd').value || '').trim();
        const cProd = (document.getElementById('m_item_cProd').value || '').trim();
        const cfop = (document.getElementById('m_item_CFOP').value || '').trim();
        const ncm = (document.getElementById('m_item_NCM').value || '').trim();
        const qCom = parseNum(document.getElementById('m_item_qCom').value);
        const vUnCom = parseNum(document.getElementById('m_item_vUnCom').value);

        if (!xProd) {
            alert('Por favor, informe a Descrição do Produto (xProd).');
            document.getElementById('m_item_xProd').focus();
            return;
        }

        if (!cfop || cfop.length < 4) {
            alert('Por favor, informe um CFOP válido com 4 dígitos.');
            document.getElementById('m_item_CFOP').focus();
            return;
        }

        if (qCom <= 0) {
            alert('A quantidade comercial (qCom) deve ser maior que zero.');
            document.getElementById('m_item_qCom').focus();
            return;
        }

        const vProd = (qCom * vUnCom).toFixed(2);
        const uCom = (document.getElementById('m_item_uCom').value || 'UN').trim().toUpperCase();

        const csosnVal = (document.getElementById('m_item_CSOSN').value || '00').trim();

        // Monta o objeto completo do item
        const itemObj = {
            nItem: document.getElementById('m_item_nItem').value || "1",
            cProd: cProd || String(document.getElementById('m_item_nItem').value).padStart(4, '0'),
            cEAN: document.getElementById('m_item_cEAN').value || "SEM GTIN",
            xProd: xProd,
            NCM: ncm,
            CEST: document.getElementById('m_item_CEST').value || "",
            CFOP: cfop,
            orig: document.getElementById('m_item_orig').value || "0",
            uCom: uCom,
            qCom: qCom.toFixed(4),
            vUnCom: vUnCom.toFixed(4),
            vProd: vProd,
            indTot: "1",
            vFrete: formatNum(document.getElementById('m_item_vFrete').value, 2),
            vSeg: formatNum(document.getElementById('m_item_vSeg').value, 2),
            vDesc: formatNum(document.getElementById('m_item_vDesc').value, 2),
            vOutro: formatNum(document.getElementById('m_item_vOutro').value, 2),
            infAdProd: document.getElementById('m_item_infAdProd').value || "",

            // ICMS
            CSOSN: csosnVal,
            CST_ICMS: csosnVal,
            modBC: "3",
            pRedBC: formatNum(document.getElementById('m_item_pRedBC').value, 2),
            vBC_ICMS: formatNum(document.getElementById('m_item_vBC_ICMS').value, 2),
            pICMS: formatNum(document.getElementById('m_item_pICMS').value, 2),
            vICMS: formatNum(document.getElementById('m_item_vICMS').value, 2),
            motDesICMS: "",
            vICMSDeson: "0.00",

            // IPI
            CST_IPI: document.getElementById('m_item_CST_IPI').value || "99",
            cEnq: document.getElementById('m_item_cEnq').value || "999",
            vBC_IPI: formatNum(document.getElementById('m_item_vBC_IPI').value, 2),
            pIPI: formatNum(document.getElementById('m_item_pIPI').value, 2),
            vIPI: formatNum(document.getElementById('m_item_vIPI').value, 2),

            // PIS
            CST_PIS: document.getElementById('m_item_CST_PIS').value || "01",
            vBC_PIS: formatNum(document.getElementById('m_item_vBC_PIS').value, 2),
            pPIS: formatNum(document.getElementById('m_item_pPIS').value, 2),
            vPIS: formatNum(document.getElementById('m_item_vPIS').value, 2),

            // COFINS
            CST_COFINS: document.getElementById('m_item_CST_COFINS').value || "01",
            vBC_COFINS: formatNum(document.getElementById('m_item_vBC_COFINS').value, 2),
            pCOFINS: formatNum(document.getElementById('m_item_pCOFINS').value, 2),
            vCOFINS: formatNum(document.getElementById('m_item_vCOFINS').value, 2),

            // II
            vBC_II: formatNum(document.getElementById('m_item_vBC_II').value, 2),
            vDespAdu: formatNum(document.getElementById('m_item_vDespAdu').value, 2),
            vII: formatNum(document.getElementById('m_item_vII').value, 2),
            vIOF: formatNum(document.getElementById('m_item_vIOF').value, 2),

            // Tributável
            uTrib: (document.getElementById('m_item_uTrib').value || uCom).trim().toUpperCase(),
            qTrib: formatNum(document.getElementById('m_item_qTrib').value || qCom, 4),
            vUnTrib: formatNum(document.getElementById('m_item_vUnTrib').value || vUnCom, 4),
            cEANTrib: document.getElementById('m_item_cEANTrib').value || "SEM GTIN",

            // DI / Aduaneiro
            nDI: document.getElementById('m_item_nDI').value || "",
            dDI: document.getElementById('m_item_dDI').value || "",
            xLocDesemb: document.getElementById('m_item_xLocDesemb').value || "",
            UFDesemb: (document.getElementById('m_item_UFDesemb').value || "").toUpperCase(),
            dDesemb: document.getElementById('m_item_dDesemb').value || "",
            tpViaTransp: document.getElementById('m_item_tpViaTransp').value || "1",
            vAFRMM: formatNum(document.getElementById('m_item_vAFRMM').value, 2),
            tpIntermedio: document.getElementById('m_item_tpIntermedio').value || "1",
            CNPJ: "",
            UFTerceiro: "",
            cExportador: document.getElementById('m_item_cExportador').value || "",
            nAdicao: document.getElementById('m_item_nAdicao').value || "1",
            nSeqAdic: document.getElementById('m_item_nSeqAdic').value || "1",
            cFabricante: document.getElementById('m_item_cFabricante').value || "",
            vDescDI: "0.00",
            nDraw: "",
            moeda_conversao: document.getElementById('m_item_moeda_conversao').value || "",
            taxa_conversao: document.getElementById('m_item_taxa_conversao').value || ""
        };

        const lista = getListaItensAtual();
        let targetScrollIdx = -1;

        if (currentModalItemIndex >= 0 && currentModalItemIndex < lista.length) {
            // Editando existente
            lista[currentModalItemIndex] = Object.assign({}, lista[currentModalItemIndex], itemObj);
            targetScrollIdx = currentModalItemIndex;
        } else {
            // Novo item
            lista.push(itemObj);
            targetScrollIdx = lista.length - 1;
        }

        // Re-indexa nItem sequencialmente
        lista.forEach((it, i) => {
            it.nItem = String(i + 1);
        });

        // Aplica a nova lista na grade Tabulator e nos cálculos
        aplicarListaItensAtual(lista, targetScrollIdx);

        // Fecha a modal
        const modalEl = document.getElementById('modalItemDetalhe');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        // Alerta moderno ou aviso de sucesso
        const msg = currentModalItemIndex >= 0 ? `Item #${itemObj.nItem} atualizado com sucesso!` : `Novo item #${itemObj.nItem} adicionado à nota com sucesso!`;
        if (window.nftAlert) {
            window.nftAlert(msg, { type: 'success', title: 'Itens da Nota' });
        }
    }

    // Intercepta e redefine adicionarNovoItem globalmente para abrir o pop-up
    window.adicionarNovoItem = function () {
        window.abrirModalItemNovo();
    };

    // ==========================================
    // IDENTIFICAÇÃO DA IMPORTAÇÃO & SINCRONIZAÇÃO
    // ==========================================
    window.puxarNomeDestinatarioParaExportador = function () {
        const destNome = document.getElementById('dest_xNome');
        const exp = document.getElementById('import_cExportador');
        if (exp) {
            if (destNome && destNome.value) {
                exp.value = destNome.value.trim();
                exp.dataset.autoSynced = 'true';
            } else {
                exp.value = '';
            }
        }
    };

    window.repassarImportacaoParaItens = function () {
        const nDI = (document.getElementById('import_nDI')?.value || '').trim();
        const dDI = document.getElementById('import_dDI')?.value || '';
        const cExportador = (document.getElementById('import_cExportador')?.value || '').trim();
        const tpViaTransp = document.getElementById('import_tpViaTransp')?.value || '1';
        const tpIntermedio = document.getElementById('import_tpIntermedio')?.value || '1';
        const UFDesemb = (document.getElementById('import_UFDesemb')?.value || '').trim().toUpperCase();
        const xLocDesemb = (document.getElementById('import_xLocDesemb')?.value || '').trim().toUpperCase();
        const dDesemb = document.getElementById('import_dDesemb')?.value || '';

        let lista = getListaItensAtual();

        if (!lista || lista.length === 0) {
            const msgInfo = 'ℹ️ Dados de importação gravados como padrão! Ao adicionar novos itens, esses dados serão herdados automaticamente.';
            if (typeof window.nftAlert === 'function') {
                window.nftAlert(msgInfo, 'info');
            } else {
                alert(msgInfo);
            }
            return;
        }

        lista.forEach(item => {
            item.nDI = nDI;
            item.dDI = dDI;
            item.cExportador = cExportador;
            item.tpViaTransp = tpViaTransp;
            item.tpIntermedio = tpIntermedio;
            item.UFDesemb = UFDesemb;
            item.xLocDesemb = xLocDesemb;
            item.dDesemb = dDesemb;
        });

        aplicarListaItensAtual(lista);

        const msgSucesso = `✅ Dados de importação repassados com sucesso para todos os ${lista.length} itens da nota!`;
        if (typeof window.nftAlert === 'function') {
            window.nftAlert(msgSucesso, 'success');
        } else {
            alert(msgSucesso);
        }
    };

    window.inicializarSincronizacaoImportacao = function () {
        const destNome = document.getElementById('dest_xNome');
        const exp = document.getElementById('import_cExportador');
        if (destNome && exp) {
            const aoMudarDestNome = function () {
                if (!exp.value || exp.dataset.autoSynced === 'true') {
                    exp.value = destNome.value;
                    exp.dataset.autoSynced = 'true';
                }
            };
            destNome.addEventListener('input', aoMudarDestNome);
            destNome.addEventListener('change', aoMudarDestNome);
            exp.addEventListener('input', function () {
                exp.dataset.autoSynced = 'false';
            });
            if (destNome.value && !exp.value) {
                exp.value = destNome.value.trim();
                exp.dataset.autoSynced = 'true';
            }
        }
    };

    // Inicialização ao carregar o DOM
    document.addEventListener('DOMContentLoaded', function () {
        if (document.getElementById('itens') || document.getElementById('itens-table')) {
            injectItemModalHTML();
        }
        window.inicializarSincronizacaoImportacao();
    });

    if (document.body) {
        if (document.getElementById('itens') || document.getElementById('itens-table')) {
            injectItemModalHTML();
        }
        window.inicializarSincronizacaoImportacao();
    }
})();

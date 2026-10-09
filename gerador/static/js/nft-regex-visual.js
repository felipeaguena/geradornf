/**
 * NFT Logistics - Validação Visual de Campos via Regex & Contagem de Caracteres
 * 
 * Regra fundamental: Esta validação é ESTRITAMENTE VISUAL.
 * Ela NÃO altera, trunca nem bloqueia o valor dos campos, garantindo que
 * os dados finais para geração do XML e comunicação com a SEFAZ permaneçam 100% íntegros.
 */
(function () {
    'use strict';

    const UFS_VALIDAS = new Set([
        'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA',
        'MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN',
        'RS','RO','RR','SC','SP','SE','TO','EX'
    ]);

    // Definição das regras de validação visual por ID de campo
    const REGRAS_CAMPOS = {
        // --- 1. Identificação da NF ---
        'nNF': {
            labelPadrao: '1 a 9 dígitos (> 0)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '1 a 9 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (!limpo || parseInt(limpo, 10) <= 0) return { estado: 'erro', msg: 'Deve ser > 0' };
                if (limpo.length > 9) return { estado: 'erro', msg: `${limpo.length}/9 dígitos (excedeu)` };
                return { estado: 'valido', msg: `✓ NF nº ${limpo}` };
            }
        },
        'serie': {
            labelPadrao: '1 a 3 dígitos',
            maxlength: 3,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '1 a 3 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (!limpo) return { estado: 'erro', msg: 'Apenas números' };
                if (limpo.length > 3) return { estado: 'erro', msg: `${limpo.length}/3 dígitos (excedeu)` };
                return { estado: 'valido', msg: `✓ Série ${limpo}` };
            }
        },
        'refNFe': {
            labelPadrao: '44 dígitos numéricos',
            badgeId: 'refNFe_badge',
            maxlength: 44,
            validar: function (val) {
                const limpo = String(val || '').replace(/\D/g, '');
                const qtd = limpo.length;
                if (qtd === 0) return { estado: 'neutro', msg: '0 / 44 dígitos' };
                if (qtd === 44) return { estado: 'valido', msg: '✓ 44 / 44 dígitos' };
                if (qtd < 44) return { estado: 'aviso', msg: `${qtd} / 44 dígitos (faltam ${44 - qtd})` };
                return { estado: 'erro', msg: `${qtd} / 44 dígitos (excedeu ${qtd - 44})` };
            }
        },
        'chaveAcessoDisplay': {
            labelPadrao: '44 dígitos (SEFAZ)',
            validar: function (val) {
                if (!val || String(val).includes('Aguardando')) return { estado: 'neutro', msg: '44 dígitos (Dinâmica)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 44) return { estado: 'valido', msg: '✓ 44/44 (Chave Pronta)' };
                return { estado: 'aviso', msg: `${limpo.length}/44 dígitos` };
            }
        },
        'ptax_moeda_custom': {
            labelPadrao: '3 letras (Ex: USD)',
            maxlength: 3,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '3 letras (Ex: USD)' };
                const v = String(val).trim().toUpperCase();
                if (/^[A-Z]{3}$/.test(v)) return { estado: 'valido', msg: `✓ ${v}` };
                if (v.length < 3) return { estado: 'aviso', msg: `${v.length}/3 letras` };
                return { estado: 'erro', msg: `${v.length}/3 letras (máx. 3)` };
            }
        },
        'op_cfop': {
            labelPadrao: '4 dígitos (CFOP)',
            maxlength: 4,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '4 dígitos (CFOP)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 4) {
                    if (/^[123567]/.test(limpo)) return { estado: 'valido', msg: `✓ CFOP ${limpo}` };
                    return { estado: 'erro', msg: 'Início inválido (1,2,3,5,6,7)' };
                }
                if (limpo.length < 4) return { estado: 'aviso', msg: `${limpo.length}/4 dígitos (faltam ${4 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/4 dígitos (excedeu)` };
            }
        },
        'cfop_padrao': {
            labelPadrao: '4 dígitos (CFOP)',
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '4 dígitos (CFOP)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 4 && /^[123567]/.test(limpo)) return { estado: 'valido', msg: `✓ CFOP ${limpo}` };
                return { estado: 'aviso', msg: `${limpo.length}/4 dígitos` };
            }
        },
        'op_c_enq': {
            labelPadrao: '3 dígitos (cEnq)',
            maxlength: 3,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '3 dígitos (cEnq)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 3) return { estado: 'valido', msg: `✓ cEnq ${limpo}` };
                if (limpo.length < 3) return { estado: 'aviso', msg: `${limpo.length}/3 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/3 dígitos (excedeu)` };
            }
        },

        // --- 2. Emitente ---
        'emit_CNPJ': {
            labelPadrao: '14 dígitos (CNPJ)',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '14 dígitos (CNPJ)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 14) return { estado: 'valido', msg: '✓ 14/14 (CNPJ)' };
                if (limpo.length < 14) return { estado: 'aviso', msg: `${limpo.length}/14 dígitos (faltam ${14 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/14 dígitos (excedeu)` };
            }
        },
        'emit_IE': {
            labelPadrao: '2 a 14 dígitos ou ISENTO',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2-14 dígitos ou ISENTO' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'ISENTO') return { estado: 'valido', msg: '✓ ISENTO' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 14) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos (IE)` };
                if (limpo.length < 2) return { estado: 'aviso', msg: `${limpo.length}/2 mín.` };
                return { estado: 'erro', msg: `${limpo.length}/14 máx.` };
            }
        },
        'emit_cMun': {
            labelPadrao: '7 dígitos (IBGE)',
            maxlength: 7,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '7 dígitos (IBGE)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 7) return { estado: 'valido', msg: '✓ 7/7 (IBGE)' };
                if (limpo.length < 7) return { estado: 'aviso', msg: `${limpo.length}/7 dígitos (faltam ${7 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/7 dígitos (excedeu)` };
            }
        },
        'emit_UF': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                if (v.length === 2) return { estado: 'erro', msg: `${v} (UF inválida)` };
                if (v.length < 2) return { estado: 'aviso', msg: `${v.length}/2 letras` };
                return { estado: 'erro', msg: `${v.length}/2 letras (excedeu)` };
            }
        },
        'emit_CEP': {
            labelPadrao: '8 dígitos (CEP)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos (CEP)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (CEP)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos (faltam ${8 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        },
        'emit_cPais': {
            labelPadrao: '2 a 4 dígitos (BACEN)',
            maxlength: 4,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 a 4 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 4) return { estado: 'valido', msg: `✓ ${limpo}` };
                if (limpo.length < 2) return { estado: 'aviso', msg: 'Mín. 2 dígitos' };
                return { estado: 'erro', msg: `${limpo.length}/4 máx.` };
            }
        },

        // --- 3. Destinatário ---
        'dest_CNPJ_CPF': {
            labelPadrao: '11 (CPF), 14 (CNPJ) ou 5-20 (Estrangeiro)',
            maxlength: 20,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'CNPJ, CPF ou IdEstrang.' };
                const tpDocEl = document.getElementById('dest_tpDoc');
                const isEstrangeiro = tpDocEl && tpDocEl.value === 'Estrangeiro';
                const vTrim = String(val).trim();
                if (isEstrangeiro) {
                    if (vTrim.length >= 5 && vTrim.length <= 20) return { estado: 'valido', msg: `✓ ${vTrim.length} chars (Estrang.)` };
                    if (vTrim.length < 5) return { estado: 'aviso', msg: `${vTrim.length}/5-20 chars (mín. 5)` };
                    return { estado: 'erro', msg: `${vTrim.length}/20 chars (excedeu)` };
                }
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 14) return { estado: 'valido', msg: '✓ 14/14 (CNPJ)' };
                if (limpo.length === 11) return { estado: 'valido', msg: '✓ 11/11 (CPF)' };
                if (limpo.length < 11) return { estado: 'aviso', msg: `${limpo.length}/11 ou 14 dígitos` };
                if (limpo.length > 11 && limpo.length < 14) return { estado: 'aviso', msg: `${limpo.length}/14 dígitos (faltam ${14 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/14 dígitos (excedeu)` };
            }
        },
        'dest_IE': {
            labelPadrao: '2 a 14 dígitos ou ISENTO',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2-14 dígitos ou ISENTO' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'ISENTO') return { estado: 'valido', msg: '✓ ISENTO' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 14) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos (IE)` };
                if (limpo.length < 2) return { estado: 'aviso', msg: `${limpo.length}/2 mín.` };
                return { estado: 'erro', msg: `${limpo.length}/14 máx.` };
            }
        },
        'dest_cMun': {
            labelPadrao: '7 dígitos (IBGE)',
            maxlength: 7,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '7 dígitos (IBGE)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 7) return { estado: 'valido', msg: '✓ 7/7 (IBGE)' };
                if (limpo.length < 7) return { estado: 'aviso', msg: `${limpo.length}/7 dígitos (faltam ${7 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/7 dígitos (excedeu)` };
            }
        },
        'dest_UF': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                if (v.length === 2) return { estado: 'erro', msg: `${v} (UF inválida)` };
                if (v.length < 2) return { estado: 'aviso', msg: `${v.length}/2 letras` };
                return { estado: 'erro', msg: `${v.length}/2 letras (excedeu)` };
            }
        },
        'dest_CEP': {
            labelPadrao: '8 dígitos (CEP)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos (CEP)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (CEP)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos (faltam ${8 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        },
        'dest_cPais': {
            labelPadrao: '2 a 4 dígitos (BACEN)',
            maxlength: 4,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 a 4 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 4) return { estado: 'valido', msg: `✓ ${limpo}` };
                if (limpo.length < 2) return { estado: 'aviso', msg: 'Mín. 2 dígitos' };
                return { estado: 'erro', msg: `${limpo.length}/4 máx.` };
            }
        },
        'dest_idEstrangeiro': {
            labelPadrao: '5 a 20 caracteres',
            maxlength: 20,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '5 a 20 chars' };
                const v = String(val).trim();
                if (v.length >= 5 && v.length <= 20) return { estado: 'valido', msg: `✓ ${v.length} chars` };
                if (v.length < 5) return { estado: 'aviso', msg: `${v.length}/5-20 chars (mín. 5)` };
                return { estado: 'erro', msg: `${v.length}/20 chars (excedeu)` };
            }
        },

        // --- 4. Transporte ---
        'transp_CNPJ_CPF': {
            labelPadrao: '11 (CPF) ou 14 (CNPJ)',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'CNPJ ou CPF' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 14) return { estado: 'valido', msg: '✓ 14/14 (CNPJ)' };
                if (limpo.length === 11) return { estado: 'valido', msg: '✓ 11/11 (CPF)' };
                if (limpo.length < 11) return { estado: 'aviso', msg: `${limpo.length}/11 ou 14 dígitos` };
                if (limpo.length < 14) return { estado: 'aviso', msg: `${limpo.length}/14 dígitos (faltam ${14 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/14 dígitos (excedeu)` };
            }
        },
        'transp_IE': {
            labelPadrao: '2 a 14 dígitos ou ISENTO',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2-14 dígitos ou ISENTO' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'ISENTO') return { estado: 'valido', msg: '✓ ISENTO' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 14) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos (IE)` };
                if (limpo.length < 2) return { estado: 'aviso', msg: `${limpo.length}/2 mín.` };
                return { estado: 'erro', msg: `${limpo.length}/14 máx.` };
            }
        },
        'transp_CEP': {
            labelPadrao: '8 dígitos (CEP)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (CEP)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        },
        'transp_UF': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/2 letras` };
            }
        },
        'transp_qVol': {
            labelPadrao: 'Número inteiro',
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'Número inteiro' };
                const limpo = String(val).trim();
                if (/^\d+$/.test(limpo)) return { estado: 'valido', msg: `✓ ${limpo} vol.` };
                return { estado: 'erro', msg: 'Apenas números inteiros' };
            }
        },

        // --- 5. Exportação e Importação Geral ---
        'exporta_UFSaidaPais': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/2 letras` };
            }
        },
        'import_nDI': {
            labelPadrao: 'DI ou DUIMP',
            maxlength: 16,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'DI ou DUIMP' };
                const v = String(val).trim();
                if (/^(\d{2}\/\d{7}-\d|\d{2}BR\d{8,10}(-\d)?|\d{10,16})$/i.test(v)) return { estado: 'valido', msg: '✓ DI/DUIMP válida' };
                if (v.length < 10) return { estado: 'aviso', msg: `${v.length} chars (mín. 10)` };
                return { estado: 'valido', msg: `✓ ${v.length} chars` };
            }
        },
        'import_UFDesemb': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/2 letras` };
            }
        },

        // --- 6. Modal de Itens (m_item_*) ---
        'm_item_CFOP': {
            labelPadrao: '4 dígitos (CFOP)',
            maxlength: 4,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '4 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 4) {
                    if (/^[123567]/.test(limpo)) return { estado: 'valido', msg: `✓ CFOP ${limpo}` };
                    return { estado: 'erro', msg: 'Início inválido (1,2,3,5,6,7)' };
                }
                if (limpo.length < 4) return { estado: 'aviso', msg: `${limpo.length}/4 dígitos (faltam ${4 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/4 dígitos (excedeu)` };
            }
        },
        'm_item_NCM': {
            labelPadrao: '8 dígitos (NCM)',
            maxlength: 10,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (NCM)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos (faltam ${8 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        },
        'm_item_CEST': {
            labelPadrao: '7 dígitos (CEST)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '7 dígitos (Opcional)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 7) return { estado: 'valido', msg: '✓ 7/7 (CEST)' };
                if (limpo.length < 7) return { estado: 'aviso', msg: `${limpo.length}/7 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/7 dígitos (excedeu)` };
            }
        },
        'm_item_cEAN': {
            labelPadrao: 'SEM GTIN ou 8/12/13/14',
            maxlength: 14,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'SEM GTIN ou 8/12/13/14' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'SEM GTIN') return { estado: 'valido', msg: '✓ SEM GTIN' };
                const limpo = String(val).replace(/\D/g, '');
                if ([8, 12, 13, 14].includes(limpo.length)) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos` };
                return { estado: 'aviso', msg: `${limpo.length} dígitos` };
            }
        },
        'm_item_cEANTrib': {
            labelPadrao: 'SEM GTIN ou 8/12/13/14',
            maxlength: 14,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'SEM GTIN ou 8/12/13/14' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'SEM GTIN') return { estado: 'valido', msg: '✓ SEM GTIN' };
                const limpo = String(val).replace(/\D/g, '');
                if ([8, 12, 13, 14].includes(limpo.length)) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos` };
                return { estado: 'aviso', msg: `${limpo.length} dígitos` };
            }
        },
        'm_item_uCom': {
            labelPadrao: '1 a 6 caracteres',
            maxlength: 6,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '1 a 6 chars' };
                const v = String(val).trim();
                if (v.length >= 1 && v.length <= 6) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'erro', msg: `${v.length}/6 máx.` };
            }
        },
        'm_item_uTrib': {
            labelPadrao: '1 a 6 caracteres',
            maxlength: 6,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '1 a 6 chars' };
                const v = String(val).trim();
                if (v.length >= 1 && v.length <= 6) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'erro', msg: `${v.length}/6 máx.` };
            }
        },
        'm_item_nDI': {
            labelPadrao: 'DI ou DUIMP',
            maxlength: 16,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: 'DI ou DUIMP' };
                const v = String(val).trim();
                if (/^(\d{2}\/\d{7}-\d|\d{2}BR\d{8,10}(-\d)?|\d{10,16})$/i.test(v)) return { estado: 'valido', msg: '✓ DI/DUIMP' };
                if (v.length < 10) return { estado: 'aviso', msg: `${v.length} chars (mín. 10)` };
                return { estado: 'valido', msg: `✓ ${v.length} chars` };
            }
        },
        'm_item_UFDesemb': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/2 letras` };
            }
        },
        'm_item_nAdicao': {
            labelPadrao: '1 a 3 dígitos',
            maxlength: 3,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '1 a 3 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 1 && limpo.length <= 3) return { estado: 'valido', msg: `✓ Nº ${limpo}` };
                return { estado: 'erro', msg: `${limpo.length}/3 máx.` };
            }
        },
        'm_item_nSeqAdic': {
            labelPadrao: '1 a 3 dígitos',
            maxlength: 3,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '1 a 3 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 1 && limpo.length <= 3) return { estado: 'valido', msg: `✓ Nº ${limpo}` };
                return { estado: 'erro', msg: `${limpo.length}/3 máx.` };
            }
        },
        'm_item_moeda_conversao': {
            labelPadrao: '3 letras (Ex: USD)',
            maxlength: 3,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '3 letras' };
                const v = String(val).trim().toUpperCase();
                if (/^[A-Z]{3}$/.test(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/3 letras` };
            }
        },

        // --- 7. Cadastro de Empresas (empresas.html) ---
        'cad_cnpj_cpf': {
            labelPadrao: '11 (CPF) ou 14 (CNPJ)',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '11 (CPF) ou 14 (CNPJ)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 14) return { estado: 'valido', msg: '✓ 14/14 (CNPJ)' };
                if (limpo.length === 11) return { estado: 'valido', msg: '✓ 11/11 (CPF)' };
                if (limpo.length < 11) return { estado: 'aviso', msg: `${limpo.length}/11 ou 14 dígitos` };
                if (limpo.length < 14) return { estado: 'aviso', msg: `${limpo.length}/14 dígitos (faltam ${14 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/14 dígitos (excedeu)` };
            }
        },
        'edit_cnpj_cpf': {
            labelPadrao: '11 (CPF) ou 14 (CNPJ)',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '11 (CPF) ou 14 (CNPJ)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 14) return { estado: 'valido', msg: '✓ 14/14 (CNPJ)' };
                if (limpo.length === 11) return { estado: 'valido', msg: '✓ 11/11 (CPF)' };
                if (limpo.length < 11) return { estado: 'aviso', msg: `${limpo.length}/11 ou 14 dígitos` };
                if (limpo.length < 14) return { estado: 'aviso', msg: `${limpo.length}/14 dígitos (faltam ${14 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/14 dígitos (excedeu)` };
            }
        },
        'cad_ie': {
            labelPadrao: '2 a 14 dígitos ou ISENTO',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2-14 dígitos ou ISENTO' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'ISENTO') return { estado: 'valido', msg: '✓ ISENTO' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 14) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos (IE)` };
                return { estado: 'aviso', msg: `${limpo.length}/14 máx.` };
            }
        },
        'edit_ie': {
            labelPadrao: '2 a 14 dígitos ou ISENTO',
            maxlength: 18,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2-14 dígitos ou ISENTO' };
                const vUpper = String(val).trim().toUpperCase();
                if (vUpper === 'ISENTO') return { estado: 'valido', msg: '✓ ISENTO' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 14) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos (IE)` };
                return { estado: 'aviso', msg: `${limpo.length}/14 máx.` };
            }
        },
        'cad_cep': {
            labelPadrao: '8 dígitos (CEP)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos (CEP)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (CEP)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos (faltam ${8 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        },
        'edit_cep': {
            labelPadrao: '8 dígitos (CEP)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos (CEP)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (CEP)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos (faltam ${8 - limpo.length})` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        },
        'cad_cmun': {
            labelPadrao: '7 dígitos (IBGE)',
            maxlength: 7,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '7 dígitos (IBGE)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 7) return { estado: 'valido', msg: '✓ 7/7 (IBGE)' };
                if (limpo.length < 7) return { estado: 'aviso', msg: `${limpo.length}/7 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/7 dígitos (excedeu)` };
            }
        },
        'edit_cmun': {
            labelPadrao: '7 dígitos (IBGE)',
            maxlength: 7,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '7 dígitos (IBGE)' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 7) return { estado: 'valido', msg: '✓ 7/7 (IBGE)' };
                if (limpo.length < 7) return { estado: 'aviso', msg: `${limpo.length}/7 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/7 dígitos (excedeu)` };
            }
        },
        'cad_uf': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/2 letras` };
            }
        },
        'edit_uf': {
            labelPadrao: '2 letras (UF)',
            maxlength: 2,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 letras (UF)' };
                const v = String(val).trim().toUpperCase();
                if (UFS_VALIDAS.has(v)) return { estado: 'valido', msg: `✓ ${v}` };
                return { estado: 'aviso', msg: `${v.length}/2 letras` };
            }
        },
        'cad_cpais': {
            labelPadrao: '2 a 4 dígitos (BACEN)',
            maxlength: 4,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 a 4 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 4) return { estado: 'valido', msg: `✓ ${limpo}` };
                return { estado: 'aviso', msg: 'Mín. 2 dígitos' };
            }
        },
        'edit_cpais': {
            labelPadrao: '2 a 4 dígitos (BACEN)',
            maxlength: 4,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '2 a 4 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length >= 2 && limpo.length <= 4) return { estado: 'valido', msg: `✓ ${limpo}` };
                return { estado: 'aviso', msg: 'Mín. 2 dígitos' };
            }
        },
        'cad_fone': {
            labelPadrao: '10 ou 11 dígitos',
            maxlength: 15,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '10 ou 11 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 10 || limpo.length === 11) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos` };
                if (limpo.length < 10) return { estado: 'aviso', msg: `${limpo.length}/10-11 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/11 dígitos (excedeu)` };
            }
        },
        'edit_fone': {
            labelPadrao: '10 ou 11 dígitos',
            maxlength: 15,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '10 ou 11 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 10 || limpo.length === 11) return { estado: 'valido', msg: `✓ ${limpo.length} dígitos` };
                if (limpo.length < 10) return { estado: 'aviso', msg: `${limpo.length}/10-11 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/11 dígitos (excedeu)` };
            }
        },

        // --- 8. Teste de CEP em Localidades ---
        'input-teste-cep': {
            labelPadrao: '8 dígitos (CEP)',
            maxlength: 9,
            validar: function (val) {
                if (!val) return { estado: 'neutro', msg: '8 dígitos' };
                const limpo = String(val).replace(/\D/g, '');
                if (limpo.length === 8) return { estado: 'valido', msg: '✓ 8/8 (CEP)' };
                if (limpo.length < 8) return { estado: 'aviso', msg: `${limpo.length}/8 dígitos` };
                return { estado: 'erro', msg: `${limpo.length}/8 dígitos (excedeu)` };
            }
        }
    };

    function obterOuCriarBadge(inputEl, id, regra) {
        if (regra.badgeId) {
            const b = document.getElementById(regra.badgeId);
            if (b) return b;
        }

        let badge = document.querySelector(`.nft-regex-tag[data-field-id="${id}"]`);
        if (badge) return badge;

        // Tenta achar o label associado
        let label = document.querySelector(`label[for="${id}"]`);
        if (!label) {
            const parent = inputEl.closest('.col-md-1, .col-md-2, .col-md-3, .col-md-4, .col-md-5, .col-md-6, .col-md-7, .col-md-8, .col-md-12, .col-12, .col-6, div');
            if (parent) {
                label = parent.querySelector('label');
            }
        }

        badge = document.createElement('span');
        badge.className = 'nft-regex-tag nft-regex-tag-neutral';
        badge.setAttribute('data-field-id', id);
        badge.innerText = regra.labelPadrao;

        if (label) {
            label.appendChild(badge);
        } else if (inputEl.parentNode) {
            inputEl.parentNode.insertBefore(badge, inputEl.nextSibling);
        }

        return badge;
    }

    function aplicarValidacaoVisual(inputEl, id, regra) {
        if (!inputEl || inputEl.type === 'hidden') return;

        // Configura maxlength de auxílio se não existir
        if (regra.maxlength && !inputEl.hasAttribute('maxlength')) {
            inputEl.setAttribute('maxlength', regra.maxlength);
        }

        const val = inputEl.value || '';
        const res = regra.validar(val);

        if (id === 'refNFe') {
            const refBadge = document.getElementById('refNFe_badge');
            if (refBadge) {
                refBadge.innerText = res.msg;
                if (res.estado === 'valido') {
                    refBadge.className = 'badge bg-success font-monospace';
                } else if (res.estado === 'aviso') {
                    refBadge.className = 'badge bg-warning text-dark font-monospace';
                } else if (res.estado === 'erro') {
                    refBadge.className = 'badge bg-danger font-monospace';
                } else {
                    refBadge.className = 'badge bg-secondary font-monospace';
                }
            }
        } else {
            const badge = obterOuCriarBadge(inputEl, id, regra);
            if (badge) {
                badge.innerText = res.msg;
                badge.className = 'nft-regex-tag';
                if (res.estado === 'valido') {
                    badge.classList.add('nft-regex-tag-success');
                } else if (res.estado === 'aviso') {
                    badge.classList.add('nft-regex-tag-warning');
                } else if (res.estado === 'erro') {
                    badge.classList.add('nft-regex-tag-danger');
                } else {
                    badge.classList.add('nft-regex-tag-neutral');
                }
            }
        }

        // Aplica classe no input
        inputEl.classList.add('nft-regex-field');
        inputEl.classList.remove('nft-regex-valid', 'nft-regex-invalid', 'nft-regex-error');
        if (res.estado === 'valido') {
            inputEl.classList.add('nft-regex-valid');
        } else if (res.estado === 'aviso') {
            inputEl.classList.add('nft-regex-invalid');
        } else if (res.estado === 'erro') {
            inputEl.classList.add('nft-regex-error');
        }
    }

    function validarTodosOsCampos() {
        Object.keys(REGRAS_CAMPOS).forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                aplicarValidacaoVisual(el, id, REGRAS_CAMPOS[id]);
            }
        });
    }

    // Delegação de eventos globais
    document.addEventListener('input', function (e) {
        if (e.target && e.target.id && REGRAS_CAMPOS[e.target.id]) {
            aplicarValidacaoVisual(e.target, e.target.id, REGRAS_CAMPOS[e.target.id]);
        }
    });

    document.addEventListener('change', function (e) {
        if (e.target && e.target.id && REGRAS_CAMPOS[e.target.id]) {
            aplicarValidacaoVisual(e.target, e.target.id, REGRAS_CAMPOS[e.target.id]);
        }
        if (e.target && e.target.id === 'dest_tpDoc') {
            const destDoc = document.getElementById('dest_CNPJ_CPF');
            if (destDoc) aplicarValidacaoVisual(destDoc, 'dest_CNPJ_CPF', REGRAS_CAMPOS['dest_CNPJ_CPF']);
        }
    });

    document.addEventListener('blur', function (e) {
        if (e.target && e.target.id && REGRAS_CAMPOS[e.target.id]) {
            aplicarValidacaoVisual(e.target, e.target.id, REGRAS_CAMPOS[e.target.id]);
        }
    }, true);

    // Monitora abertura de modals (como o Modal de Item)
    document.addEventListener('shown.bs.modal', function () {
        setTimeout(validarTodosOsCampos, 50);
    });

    // Monitora troca de abas
    document.addEventListener('shown.bs.tab', function () {
        setTimeout(validarTodosOsCampos, 50);
    });

    // Inicialização ao carregar página
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            validarTodosOsCampos();
            setTimeout(validarTodosOsCampos, 300);
            setTimeout(validarTodosOsCampos, 1000);
        });
    } else {
        validarTodosOsCampos();
        setTimeout(validarTodosOsCampos, 300);
        setTimeout(validarTodosOsCampos, 1000);
    }

    // Exposição global segura para outros módulos chamarem quando preencherem dados
    window.validarCamposRegexVisual = validarTodosOsCampos;
    window.regrasRegexCampos = REGRAS_CAMPOS;
})();

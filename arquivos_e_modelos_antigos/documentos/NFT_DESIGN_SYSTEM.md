# 🎨 NFT Logistics — Guia Oficial do Design System

> **Documentação de Padronização Visual & Interface (UI/UX)**  
> **Aplicações:** Site Institucional (`nft`), Portal de Documentação (`docs.nft`) e Sistema Emissor/Gerador NF-e (`gerador`).  
> **Versão:** 1.0 (Atualizado em 2026)

---

## 1. Visão Geral e Filosofia de Design

O Design System da **NFT Logistics** foi projetado para transmitir precisão técnica, modernidade, sofisticação e robustez corporativa para comércio exterior e logística aduaneira internacional.

* **Tom:** Profissional, técnico, direto, ágil e acolhedor.
* **Princípios:**
  1. **Clareza Informacional:** Hierarquia visual nítida para dados fiscais densos (tabelas, códigos NCM, alíquotas).
  2. **Contraste & Acessibilidade:** Conformidade visual tanto em ambientes claros (escritórios) quanto em modo escuro (turnos noturnos/operacionais).
  3. **Identidade Forte:** Uso intencional do **Laranja Vibrante NFT (`#ed5a24`)** como ponto focal de ação primária.

---

## 2. Tipografia

### 2.1 Famílias de Fontes
* **Fonte Primária (Interface & Textos):** [`Manrope`](https://fonts.google.com/specimen/Manrope) (Google Fonts).  
  *Fallback:* `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
* **Fonte Técnica (Códigos NCM, Tags XML, Valores, Moedas):** [`JetBrains Mono`](https://fonts.google.com/specimen/JetBrains+Mono).  
  *Fallback:* `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`.

### 2.2 Escala Tipográfica e Pesos
| Nível / Elemento | Tamanho (px / rem) | Peso (Font Weight) | Line Height | Espaçamento (Tracking) | Uso |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hero / H1** | `30px / 1.875rem` | Bold (700) | `1.25` | `-0.02em` | Títulos principais de tela |
| **H2 / Seção** | `24px / 1.5rem` | Bold (700) | `1.3` | `-0.015em` | Títulos de seções ou abas |
| **H3 / Subseção** | `20px / 1.25rem` | SemiBold (600) | `1.4` | `-0.01em` | Cabeçalhos de cards |
| **H4 / Bloco** | `18px / 1.125rem` | SemiBold (600) | `1.4` | `normal` | Subtítulos ou agrupadores |
| **H5 / Título Tabela** | `16px / 1.0rem` | SemiBold (600) | `1.45` | `normal` | Títulos de blocos menores |
| **Body (Texto Padrão)** | `14px / 0.875rem` | Regular (400) ou Medium (500) | `1.5 - 1.6` | `normal` | Textos gerais, formulários |
| **Small / Labels** | `12px - 13px` | Medium (500) ou SemiBold (600) | `1.4` | `0.01em` | Rótulos de inputs e notas |
| **Monospace / Dados** | `12px - 13px` | Regular (400) ou SemiBold (600) | `1.5` | `normal` | NCMs, uTrib, CFOP, CST |

### 2.3 Regra de Ouro: Cores Padronizadas de Títulos (Consistência Visual)
> [!IMPORTANT]
> **Títulos não devem ter cores dispersas ou aleatórias.**  
> Todos os cabeçalhos (`<h1>` a `<h6>`), títulos de cards e modais compartilham **estritamente uma única cor uniforme**:
> * **Modo Claro (Light):** `var(--heading)` = `#161110` (Grafite escuro uniforme de alto contraste).
> * **Modo Escuro (Dark):** `var(--heading)` = `#f8fafc` (Branco gelo suave de alto contraste).
> 
> **Diretrizes obrigatórias:**
> 1. **Proibido colorir títulos:** Nunca aplicar classes utilitárias como `text-primary`, `text-secondary`, `text-success`, `text-info` ou `text-purple` em títulos.
> 2. **O Laranja NFT (`#ed5a24`) é para ação:** A cor primária da marca é reservada exclusivamente para botões de ação primária, abas ativas, halos de foco e elementos interativos.
> 3. **Subtítulos e legendas:** Devem utilizar sempre e unicamente a classe `.text-muted` (`var(--muted-foreground)`: `#818cab` no claro / `#94a3b8` no escuro).

---

## 3. Paleta de Cores e Tokens

### 3.1 Cores da Marca (Brand Assets)
* **Primary (Laranja NFT):** `#ed5a24`
  * *Hover:* `#d84b16`
  * *Active:* `#c23f11`
  * *Subtle (Fundo translúcido):* `rgba(237, 90, 36, 0.08)` (Light) / `rgba(237, 90, 36, 0.18)` (Dark)
  * *Border / Focus Ring:* `rgba(237, 90, 36, 0.35)`
* **Secondary (Slate Blue):** `#818cab`
  * *Hover:* `#6b7696`

---

### 3.2 Variações de Tema: Normal (Light) vs. Dark Theme

| Token CSS | Normal (Light Theme) | Dark Theme | Descrição / Aplicação |
| :--- | :--- | :--- | :--- |
| `--primary` | `#ed5a24` | `#ed5a24` | Ações principais, destaques, links ativos |
| `--primary-hover` | `#d84b16` | `#fa6c38` | Estado hover de botões e links |
| `--background` | `#f1f1f1` | `#181b20` | Fundo geral da página |
| `--surface` | `#ffffff` | `#111317` | Fundo de cards, modais, painéis e inputs |
| `--surface-secondary` | `#f8fafc` | `#1e2229` | Cabeçalho de tabelas, áreas zebradas |
| `--foreground` | `#21242a` | `#cbd5e1` | Cor padrão do texto corrido |
| `--heading` | `#161110` | `#f8fafc` | Cor de títulos e textos em destaque |
| `--muted-foreground` | `#818cab` | `#94a3b8` | Textos secundários, legendas e placeholders |
| `--border` | `#e2e8f0` | `#282c35` | Bordas de divisórias, cards e inputs |
| `--card-shadow` | `0 1px 3px rgba(0,0,0,0.05)` | `0 1px 3px rgba(0,0,0,0.4)` | Sombra sutil de relevo |

---

### 3.3 Cores de Feedback & Alíquotas Fiscais

| Estado / Tipo | Hex | Fundo Sutil (Subtle) | Aplicação no Sistema |
| :--- | :--- | :--- | :--- |
| **Sucesso / Ativo** | `#10b981` | `rgba(16, 185, 129, 0.12)` | Badges de PIS/COFINS, XML carregado, sucesso |
| **Alerta / Atenção** | `#f59e0b` | `rgba(245, 158, 11, 0.12)` | Alíquota IPI, alertas de conferência |
| **Erro / Perigo** | `#ef4444` | `rgba(239, 68, 68, 0.12)` | Erros de validação de XML, cancelamento |
| **Informativo / II** | `#0ea5e9` | `rgba(14, 165, 233, 0.12)` | Alíquota II (Imposto de Importação) |
| **Especial / COFINS**| `#8b5cf6` | `rgba(139, 92, 246, 0.12)` | Regime especial COFINS, categorizações |

---

## 4. Dimensões, Espaçamentos & Raios de Borda (Border Radius)

* **Sistema de Grade (Grid):** Múltiplos de **4px** (4, 8, 12, 16, 20, 24, 32, 48px).
* **Raios de Borda:**
  * `var(--radius-sm): 6px` — Badges, tags, células de tabela, checkboxes.
  * `var(--radius-md): 10px` — Botões padrão, inputs, selects, dropdowns.
  * `var(--radius-lg): 14px` — Cards de conteúdo, painéis, modais, caixas de alerta.
  * `var(--radius-xl): 18px` — Botões flutuantes, cards com destaque visual.

---

## 5. Componentes Padronizados

### 5.1 Botões (`.btn`)
* **Primary (`.btn-primary`):**  
  Fundo `--primary`, texto branco, sombra `0 2px 4px rgba(237,90,36,0.25)`, hover com saturação e leve brilho. Efeito de compressão tátil ao clicar (`active: scale(0.98)`).
* **Secondary / Outline (`.btn-outline-secondary`):**  
  Fundo transparente, borda `--border`, texto `--foreground`.
* **Success (`.btn-success`):**  
  Fundo verde esmeralda `#10b981`, texto branco. Usado para "Gerar XML" e "Baixar Excel".
* **Theme Toggle (`.theme-toggle-btn`):**  
  Botão circular/quadrado arredondado (`38x38px`) com ícone do Sol ☀️ no modo escuro e Lua 🌙 no modo claro.

### 5.2 Formulários & Inputs
* **Estilo Padrão:** Fundo `--surface`, borda fina `1px solid var(--border)`, cantos arredondados `8px`.
* **Foco:** Borda destacada em `--primary` com anel de foco `box-shadow: 0 0 0 3px rgba(237, 90, 36, 0.2)`.

### 5.3 Abas de Navegação (`.nav-tabs`)
* Fundo transparente, sem contorno de caixinha cinza tradicional do Bootstrap antigo.
* Item ativo com borda inferior de **3px** na cor `--primary` e texto em destaque.
* Efeito hover com fundo translúcido `--primary-subtle`.

### 5.4 Tabelas de Dados (Data Grids & Tabulator)
* **Cabeçalhos:** Fundo `--surface-secondary`, texto em caixa alta, fonte tamanho `11px - 12px`, peso `700`, espaçamento entre letras `0.03em`.
* **Linhas:** Altura confortável (`padding: 8px 10px`), alternância zebrada suave, destaque no hover com `--primary-subtle`.

---

## 6. Mecanismo de Alternância de Tema (Light & Dark)

### 6.1 Como o tema é acionado
O sistema utiliza atributos na tag raiz do documento:
```html
<!-- Modo Claro -->
<html lang="pt-BR" data-theme="light">

<!-- Modo Escuro -->
<html lang="pt-BR" class="dark" data-theme="dark">
```

### 6.2 Alternância Dinâmica de Logos
Para evitar que o usuário veja imagens invertidas ou incorretas, os arquivos SVG oficiais da marca são inseridos aos pares no HTML com classes específicas:
```html
<!-- Exibido apenas no Light Theme -->
<img src="/static/img/brand/nft_logo_vetor_logo_black.svg" class="logo-theme-black" alt="NFT Logistics">

<!-- Exibido apenas no Dark Theme -->
<img src="/static/img/brand/nft_logo_vetor_logo_white.svg" class="logo-theme-white" alt="NFT Logistics">
```
As regras CSS controlam a visibilidade automaticamente com `display: none !important;` e `display: inline-block !important;`.

### 6.3 Persistência do Tema
O script `static/js/theme.js` gerencia o estado através de:
1. `localStorage.getItem('nft_theme')`
2. Fallback para preferência do sistema operacional (`window.matchMedia('(prefers-color-scheme: dark)')`)
3. Execução imediata no `<head>` para **eliminar qualquer flash branco/escuro** no carregamento da tela.

---

## 7. Estrutura de Arquivos Estáticos

```text
gerador/
├── static/
│   ├── css/
│   │   └── nft-theme.css          # Folha de estilos central do Design System
│   ├── js/
│   │   └── theme.js               # Gerenciador de alternância Light / Dark
│   └── img/
│       └── brand/
│           ├── nft_logo_vetor_logo_black.svg   # Logo completo para fundo claro
│           ├── nft_logo_vetor_logo_white.svg   # Logo completo para fundo escuro
│           ├── nft_logo_vetor_icone_black.svg  # Ícone/símbolo para fundo claro
│           └── nft_logo_vetor_icone_white.svg  # Ícone/símbolo para fundo escuro
├── templates/
│   ├── index.html                 # Interface Principal do Emissor NF-e
│   └── banco_ncm.html             # Interface da Grande Tabela NCM
└── NFT_DESIGN_SYSTEM.md           # Este guia de referência
```

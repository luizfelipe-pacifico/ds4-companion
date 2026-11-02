# Design

Inspirado na interface do PS4: **fundo preto profundo** e **azul PlayStation forte**,
tipografia humanista limpa, muito espaço e foco bem visível (pensado também para navegar com o controle).

## Paleta

| Token | Hex | Uso |
|---|---|---|
| `ps-black` | `#000000` | fundo da janela |
| `ps-surface` | `#0D0D12` | cartões e barra lateral |
| `ps-surface-2` | `#1A1A22` | linhas, itens ao passar o mouse |
| **`ps-blue`** | **`#003791`** | cor de destaque: botões principais, slider, item selecionado |
| `ps-blue-bright` | `#0070D1` | foco, links, brilho do item focado |
| `ps-blue-deep` | `#00205B` | gradiente do cabeçalho (`ps-blue` → `ps-blue-deep`) |
| `text` | `#FFFFFF` | texto principal |
| `text-muted` | `#A0A3AD` | texto secundário |
| `ok` | `#2EBD59` | faixa verde do volume |
| `warn` | `#F5A623` | faixa amarela do volume |
| `danger` | `#E5383B` | faixa vermelha / limite |

`#003791` é o *PlayStation Blue* oficial (Pantone 287C, RGB 0/55/145), conforme o guia de marca
do PS4 Pro. `#0070D1` é o azul mais claro usado nas interfaces recentes da PlayStation; aqui serve
para foco, porque `#003791` sobre preto tem pouco contraste para textos pequenos.

**Contraste (WCAG):** branco sobre `#003791` ≈ 10:1 (AAA). Texto pequeno em azul sobre preto:
usar `#0070D1` ou mais claro, nunca `#003791`.

## Tipografia

| Uso | Fonte | Peso | Tamanho |
|---|---|---|---|
| Título da página | Inter | Light (300) | 28 px |
| Título de seção | Inter | Medium (500) | 17 px |
| Texto | Inter | Regular (400) | 14 px |
| Valores (dB, %) | Inter, `tnum` (números tabulares) | SemiBold (600) | 15 px |

- A fonte do PS4 é a **SST** (Monotype, feita para a Sony). Ela é **paga** (licença na Monotype/MyFonts)
  e **não pode ser distribuída** no pacote.
- Padrão: **Inter** (`inter-font`, licença OFL, repositório `extra`), a substituta livre mais próxima.
- Se o usuário tiver a SST instalada e licenciada, o app usa: `font-family: "SST", "Inter", sans-serif;`.
- Os pesos leves nos títulos (Light) são o que dá a cara de PS4.

## Aplicação no GTK4/libadwaita

Estilo escuro forçado (`Adw.StyleManager.set_color_scheme(FORCE_DARK)`) e CSS do app:

```css
@define-color accent_bg_color   #003791;
@define-color accent_color      #0070D1;
@define-color accent_fg_color   #FFFFFF;
@define-color window_bg_color   #000000;
@define-color view_bg_color     #000000;
@define-color card_bg_color     #0D0D12;
@define-color sidebar_bg_color  #0D0D12;
@define-color headerbar_bg_color #000000;

window, label { font-family: "SST", "Inter", sans-serif; }
.title-1 { font-weight: 300; font-size: 28px; }
.numeric { font-feature-settings: "tnum"; font-weight: 600; }

/* foco estilo PS4: borda azul brilhante + brilho */
:focus-visible {
  outline: 2px solid #0070D1;
  box-shadow: 0 0 12px alpha(#0070D1, 0.6);
}
.header-hero { background: linear-gradient(135deg, #003791, #00205B); }
```

## Componentes

- **Slider de volume:** trilho `ps-surface-2`, preenchimento `ps-blue`; marcas verde/amarelo/vermelho
  (ver [SECURITY.md](../../SECURITY.md)); o rótulo em dB fica vermelho acima de 0 dB.
- **Cartão do controle:** ícone do DS4, estado (cabo/Bluetooth), bateria; borda `ps-blue` quando conectado.
- **Botões:** principal `ps-blue` com texto branco; secundário transparente com borda `ps-surface-2`.
- **Navegação pelo controle (v0.4):** D-pad move o foco, ✕ confirma, ◯ volta.

## Marca

- Usar só a **paleta e o estilo**. Não usar logotipo da PlayStation, os símbolos △◯✕□ como
  marca, nem "PlayStation" no nome ou ícone do app.
- "DualShock" e "PlayStation" são marcas da Sony. A documentação cita os nomes só para dizer com o que o app é compatível.
- Ícone do app: desenho próprio (controle genérico em `ps-blue` sobre preto).

## Referências

- PS4 Pro Brand Guidelines (Pantone 287C / RGB 0-55-145): https://retrocdn.net/images/b/b4/PS4Pro_BrandGuidelinesV1_US.pdf
- SST na Monotype: https://www.monotype.com/fonts/sst
- SST (Wikipedia): https://en.wikipedia.org/wiki/SST_(typeface)

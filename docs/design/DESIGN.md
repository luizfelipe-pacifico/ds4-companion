# Design

Escuro e fino, com luz azul. A interface imita o controle no escuro: um corpo preto, em camadas
quase iguais, e uma única luz azul, a da barra de luz do DualShock 4. Tudo o que não é luz fica
quieto: traços de 1 px, pesos leves, nenhuma cor sobrando.

Três ideias seguram o sistema:

1. **Cinco cores, nenhuma a mais.** Azul, branco e três pretos. Hierarquia vem de camada, peso e
   opacidade, não de cor nova.
2. **Profundidade por camada, não por sombra.** Cada nível de elevação é um preto um pouco mais
   claro. Sombra só existe no que flutua (popover, diálogo).
3. **Slim.** Trilhos de 2 px, bordas de 1 px, títulos em peso leve, cantos pequenos. O conteúdo
   respira; os controles não engordam.

## Paleta

| Token | Hex | Papel |
|---|---|---|
| `black-0` | `#060709` | fundo da janela; o “vazio” |
| `black-1` | `#111318` | superfícies: barra lateral, cartões, cabeçalho rolado |
| `black-2` | `#1D2027` | elevado e interativo: linha em hover/foco, trilho do slider, popover, botão secundário |
| **`led-blue`** | **`#2B6CF6`** | a luz: ação principal, preenchimento do slider, interruptor ligado, foco, item selecionado |
| `white` | `#FFFFFF` | texto e ícones |

Os pretos puxam levemente para o azul (canal B maior), para que a luz azul pareça vir de dentro
do mesmo material. Os três degraus são sutis de propósito (≈1,1:1 entre vizinhos): separam
componentes sem desenhar caixas.

### Opacidades (não são cores novas)

Só `white` e `led-blue` ganham variações, e só por opacidade:

| Uso | Valor |
|---|---|
| Texto secundário, legendas, unidades | `white` 60% |
| Texto e ícone desabilitados | `white` 32% |
| Traço (hairline): bordas, divisores, marcas do slider | `white` 8% |
| Aresta superior de superfície elevada (luz batendo no material) | `white` 6% |
| Fundo do item selecionado na barra lateral | `led-blue` 16% |
| Pressionado (`:active`) | camada escurece para o preto anterior |

### Contraste (WCAG 2.2)

| Par | Razão | Nível |
|---|---|---|
| `white` sobre `black-0` / `black-1` / `black-2` | 20,2 / 18,6 / 16,3 : 1 | AAA |
| `white` 60% sobre `black-1` | ≈ 7 : 1 | AAA |
| `white` sobre `led-blue` (texto do botão principal) | 4,6 : 1 | AA |
| `led-blue` sobre `black-0` / `black-1` / `black-2` (foco, ícone, preenchimento) | 4,4 / 4,1 / 3,6 : 1 | ≥ 3:1 (não-texto) |

Texto pequeno **em** azul só sobre `black-0` e com peso ≥ 500; o normal é texto branco e o azul
ficar no controle, não na letra.

### Por que este azul

O LED do controle no Jogador 1 é azul puro (`#0000FF` no relatório HID). Na tela, `#0000FF` sobre
preto tem 2,4:1 e vibra. `#2B6CF6` é o mesmo azul como o olho o vê através do difusor da barra de
luz: saturado, um pouco mais claro, e com contraste suficiente para foco e para texto branco.

### Exceção única: a cor real da barra de luz

Quando o app **mostra** a cor que está (ou estará) no controle, por exemplo o seletor de cor da
barra de luz e a faixa do cartão do controle, ele desenha a cor do hardware. É dado, não tema.
Nenhum outro elemento usa cor fora da paleta.

## Estados sem cores de alerta

Não há verde, amarelo nem vermelho. Estado se comunica com **texto + ícone + contraste**,
o que também cumpre WCAG 1.4.1 (cor nunca é o único sinal).

| Estado | Como aparece |
|---|---|
| Normal | branco sobre preto |
| Ativo / ligado | `led-blue` |
| Aviso (volume alto) | ícone `dialog-warning-symbolic` + rótulo “alto”, texto em peso 500 |
| Limite / perigo (acima de 0 dB) | **inversão**: o preenchimento passa de azul para `white`, o valor em dB fica em peso 600 com ícone de aviso e o texto “acima do limite”; ir além exige confirmação |
| Erro | ícone `dialog-error-symbolic` + mensagem que diz o problema e como resolver |
| Desabilitado | `white` 32%, sem hover |

A inversão para branco é o sinal mais forte que uma paleta escura de cinco cores tem; por isso
fica reservada para o limite de volume.

## Tipografia

Fonte: **Inter** (`inter-font`, OFL, repositório `extra`). Se o usuário tiver a **SST** instalada e
licenciada, ela entra primeiro (`"SST", "Inter", sans-serif`). A SST é paga e não vai no pacote.

| Uso | Tamanho | Peso | Espaçamento | Altura de linha |
|---|---|---|---|---|
| Título da página | 26 px | Light 300 | −0,02em | 1,15 |
| Título de grupo | 15 px | Medium 500 | −0,005em | 1,3 |
| Texto | 14 px | Regular 400 | 0 | 1,45 |
| Secundário | 12 px | Regular 400 (`white` 60%) | +0,01em | 1,4 |
| Valores (dB, %, bateria) | 15 px | Medium 500, `tnum` | 0 | 1 |

- O espaçamento acompanha o tamanho: aperta nos títulos grandes, fica neutro no texto, abre um
  pouco no texto pequeno.
- Hierarquia por **peso**, não por cor: título leve e grande, rótulo médio, valor médio tabular.
- Os tamanhos são para o fator de escala padrão do GNOME; no CSS usam porcentagem sobre a fonte do
  sistema para acompanhar *Texto grande* nas configurações de acessibilidade.

## Forma e espaço

| Token | Valor |
|---|---|
| Espaçamento | 4 · 8 · 12 · 16 · 24 · 32 px |
| Raio de controles (botão, entrada, linha) | 6 px |
| Raio de superfícies (cartão, popover) | 10 px |
| Borda | 1 px, `white` 8% |
| Trilho do slider | 2 px de altura; botão 14 px |
| Interruptor | 36 × 20 px, botão 14 px |
| Altura de linha de preferência | 48 px (área de toque e foco por controle) |
| Foco | contorno 2 px `led-blue`, afastado 2 px; linha focada também ganha `black-2` |

Elevação:

| Nível | Superfície | Sombra |
|---|---|---|
| 0 | `black-0` | nenhuma |
| 1 | `black-1` + aresta superior `white` 6% | nenhuma |
| 2 | `black-2` + borda `white` 8% | só em popover/diálogo: `0 8px 24px` preto 50% |

Sem gradiente, sem brilho difuso ao redor do foco, sem vidro/blur decorativo.

## Movimento

- Resposta no **pressionar**, não no soltar: `:active` muda a camada na hora (≤ 100 ms).
- Hover e foco: 150 ms, *ease-out*. Nada entra com atraso.
- Slider e vibração acompanham o dedo/analógico 1:1; o valor em dB atualiza a cada passo, não só
  ao soltar.
- **Um momento autoral:** quando o controle conecta, a faixa de luz do cartão acende (opacidade
  0 → 1 em 300 ms, *ease-out*) e, ao desconectar, apaga pelo mesmo caminho.
- O GTK desliga as transições quando *Reduzir animação* está ativo no GNOME
  (`gtk-enable-animations`); nenhum estado depende de animação para ser entendido.

## Aplicação no GTK4/libadwaita

Estilo escuro forçado (`Adw.StyleManager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)`) e o CSS
do app sobre as variáveis do libadwaita (1.6+):

```css
:root {
  /* paleta */
  --black-0: #060709;
  --black-1: #111318;
  --black-2: #1D2027;
  --led-blue: #2B6CF6;

  /* mapeamento libadwaita */
  --accent-bg-color: var(--led-blue);
  --accent-fg-color: #FFFFFF;
  --accent-color: var(--led-blue);
  --window-bg-color: var(--black-0);
  --window-fg-color: #FFFFFF;
  --view-bg-color: var(--black-0);
  --view-fg-color: #FFFFFF;
  --headerbar-bg-color: var(--black-0);
  --headerbar-fg-color: #FFFFFF;
  --sidebar-bg-color: var(--black-1);
  --sidebar-fg-color: #FFFFFF;
  --card-bg-color: var(--black-1);
  --card-fg-color: #FFFFFF;
  --popover-bg-color: var(--black-2);
  --dialog-bg-color: var(--black-1);
  --border-color: alpha(#FFFFFF, 0.08);
  --dim-opacity: 0.6;
  --disabled-opacity: 0.32;

  /* sem cores de alerta: estados usam ícone + texto */
  --success-color: #FFFFFF;
  --warning-color: #FFFFFF;
  --error-color: #FFFFFF;
  --destructive-bg-color: var(--black-2);
  --destructive-fg-color: #FFFFFF;
  --destructive-color: #FFFFFF;
}

window { font-family: "SST", "Inter", sans-serif; }

.title-1   { font-size: 186%; font-weight: 300; letter-spacing: -0.02em; }
.heading   { font-size: 107%; font-weight: 500; }
.caption   { font-size: 86%;  letter-spacing: 0.01em; opacity: 0.6; }
.numeric   { font-feature-settings: "tnum"; font-weight: 500; }

.card {
  border-radius: 10px;
  box-shadow: inset 0 1px alpha(#FFFFFF, 0.06);   /* aresta de luz, sem sombra */
}

row.activatable:hover,
row:focus-visible       { background-color: var(--black-2); }
row.activatable:active  { background-color: var(--black-1); transition: none; }

*:focus-visible {
  outline: 2px solid var(--led-blue);
  outline-offset: 2px;
}

scale trough            { min-height: 2px; background-color: var(--black-2); }
scale highlight         { background-color: var(--led-blue); }
scale slider            { min-width: 14px; min-height: 14px; margin: -6px; }
scale.over-limit highlight,
scale.over-limit slider { background-color: #FFFFFF; }

.light-strip            { min-height: 2px; border-radius: 1px; transition: opacity 300ms ease-out; }
.light-strip.off        { opacity: 0; }
```

Prefira os widgets do libadwaita (`AdwPreferencesPage`, `AdwActionRow`, `AdwSwitchRow`,
`AdwToast`); o CSS acima só ajusta cor, peso e espessura, sem redesenhar comportamento.

## Componentes

- **Slider de volume:** trilho `black-2` de 2 px, preenchimento `led-blue`. Marcas de 1 px em −6 dB
  (`white` 32%) e em 0 dB (`white`, o limite). De −6 a 0 dB aparece o aviso “alto” com ícone. Acima
  de 0 dB a classe `over-limit` inverte preenchimento e botão para branco e pede confirmação; nunca
  passa de `max_db` (ver [SECURITY.md](../../SECURITY.md)).
- **Cartão do controle:** superfície `black-1`. No topo, a **faixa de luz**: 2 px na cor real da
  barra de luz do controle, acesa quando conectado. Abaixo: nome, conexão (cabo/Bluetooth) e
  bateria em `.numeric`.
- **Botões:** principal `led-blue` com texto branco; secundário `black-2` com texto branco;
  plano (`.flat`) só texto. No máximo um botão principal por tela.
- **Interruptores:** fino (36 × 20), trilho `black-2` desligado e `led-blue` ligado.
- **Barra lateral:** `black-1`; item selecionado com fundo `led-blue` 16% e ícone em `led-blue`.
  O cabeçalho dela não tem título (o nome cortaria com os botões da janela à esquerda).
- **Amostras de cor da luz:** círculo na cor real do LED; a escolhida ganha fundo `led-blue` 16%,
  anel branco de 2 px e rótulo em peso 500 (a seleção nunca depende só de cor).
- **Jogadores:** botões finos lado a lado, `black-2` desligado e `led-blue` ligado.
- **Estado dentro de uma página:** ilustração de 96 px ao lado do título e da descrição (ex.:
  Áudio aguardando o RPCS3); a tela inteira usa 176 px.
- **Avisos acima de 100 % (vibração) e de −6 dB (volume):** ícone + rótulo "alto" em peso 500.
- **Navegação pelo controle (v0.4):** D-pad move o foco, ✕ confirma, ◯ volta. O foco é sempre
  visível (contorno azul + linha `black-2`).

## Ícones

Todo ícone do projeto é **SVG**: logo, ícones da interface, ícone da bandeja e da documentação.
Nada de PNG, JPG ou ícone em fonte.

- **Ícones da interface:** primeiro os do tema Adwaita (`*-symbolic`), para combinar com o GNOME.
  Ícone próprio só quando não existir equivalente.
- **Ícones próprios:** versão simbólica `nome-symbolic.svg` (16×16, uma cor só, que o GTK recolore
  conforme o tema) em `data/icons/`, carregados por nome via GResource.
- **Logo do app:** `hicolor/scalable/apps/<app-id>.svg` colorido + `<app-id>-symbolic.svg`
  (ver [ROADMAP](../desenvolvimento/ROADMAP.md)).
- SVG limpo: sem imagem embutida (`<image>`/base64), sem script, texto convertido em caminho;
  otimizar com `scour` ou `svgo` antes do commit.
- Traço dos ícones próprios: 1,5 px a 16 px, cantos arredondados, para combinar com o peso leve da
  tipografia.

## Ilustrações

Telas de estado (vazio, espera, aviso, erro, sucesso) usam ilustrações *flat* em SVG com as mesmas
cinco cores, traço fino e uma única luz azul. Nunca têm texto dentro e sempre vêm com título e
descrição na interface. Catálogo, descrições e textos em [ILLUSTRATIONS.md](ILLUSTRATIONS.md).

## Marca

- Usar só a **paleta e o estilo**. Não usar logotipo da PlayStation, os símbolos △◯✕□ como
  marca, nem "PlayStation" no nome ou ícone do app.
- "DualShock" e "PlayStation" são marcas da Sony. A documentação cita os nomes só para dizer com o que o app é compatível.
- Ícone do app: desenho próprio (controle genérico com a faixa de luz em `led-blue` sobre `black-0`).

## Referências

- SST na Monotype: https://www.monotype.com/fonts/sst
- SST (Wikipedia): https://en.wikipedia.org/wiki/SST_(typeface)
- Variáveis de cor do libadwaita: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html
- WCAG 2.2, contraste e uso de cor: https://www.w3.org/TR/WCAG22/#use-of-color

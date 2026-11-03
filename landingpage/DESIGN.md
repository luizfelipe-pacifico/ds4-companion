---
name: DS4 Companion (landing page)
description: A página como a própria janela do app; escuro e fino, com uma única luz azul.
colors:
  black-0: "#060709"
  black-1: "#111318"
  black-2: "#1d2027"
  led-blue: "#2b6cf6"
  white: "#ffffff"
  text-body: "rgb(255 255 255 / 0.78)"
  text-2: "rgb(255 255 255 / 0.6)"
  text-off: "rgb(255 255 255 / 0.32)"
  hairline: "rgb(255 255 255 / 0.08)"
  edge: "rgb(255 255 255 / 0.06)"
  blue-16: "rgb(43 108 246 / 0.16)"
  led: "#0000ff"
typography:
  display:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "clamp(2.75rem, 6vw, 5rem)"
    fontWeight: 300
    lineHeight: 1.02
    letterSpacing: "-0.04em"
  numeral:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "clamp(4.5rem, 13vw, 10rem)"
    fontWeight: 200
    lineHeight: 0.9
    letterSpacing: "-0.04em"
    fontFeature: "\"tnum\""
  headline:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "clamp(2rem, 4.2vw, 3.5rem)"
    fontWeight: 300
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  title:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 300
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  lead:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "clamp(1.0625rem, 1.4vw, 1.1875rem)"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 500
    lineHeight: 1.3
  control:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
  caption:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0.01em"
  value:
    fontFamily: "SST, Inter, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 500
    lineHeight: 1
    fontFeature: "\"tnum\""
  code:
    fontFamily: "ui-monospace, JetBrains Mono, DejaVu Sans Mono, monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  dot: "2px"
  control: "6px"
  segmented: "8px"
  surface: "10px"
  window: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
  gutter: "clamp(16px, 4vw, 48px)"
  column-gap: "clamp(32px, 6vw, 96px)"
  section: "clamp(96px, 14vw, 176px)"
  content: "1200px"
components:
  button-primary:
    backgroundColor: "{colors.led-blue}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 20px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.black-2}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 20px"
    height: "44px"
  button-secondary-active:
    backgroundColor: "{colors.black-1}"
  button-flat:
    backgroundColor: "transparent"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 20px"
    height: "44px"
  button-flat-hover:
    backgroundColor: "{colors.black-2}"
  button-small:
    typography: "{typography.control}"
    padding: "0 14px"
    height: "36px"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.text-2}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "36px"
  nav-link-hover:
    backgroundColor: "{colors.black-2}"
    textColor: "{colors.white}"
  tag:
    backgroundColor: "transparent"
    textColor: "{colors.text-2}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
  card:
    backgroundColor: "{colors.black-1}"
    rounded: "{rounded.surface}"
  window:
    backgroundColor: "{colors.black-0}"
    rounded: "{rounded.window}"
  window-sidebar:
    backgroundColor: "{colors.black-1}"
    width: "200px"
  sidebar-item-selected:
    backgroundColor: "{colors.blue-16}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    height: "40px"
  pref-row:
    typography: "{typography.control}"
    padding: "8px 16px"
    height: "48px"
  switch:
    backgroundColor: "{colors.black-2}"
    width: "36px"
    height: "20px"
  switch-on:
    backgroundColor: "{colors.led-blue}"
  fader:
    backgroundColor: "{colors.black-2}"
    height: "28px"
  fader-big:
    height: "48px"
  command:
    backgroundColor: "{colors.black-1}"
    textColor: "{colors.white}"
    typography: "{typography.code}"
    rounded: "{rounded.surface}"
    padding: "16px 18px"
---

# Design System: DS4 Companion (landing page)

Esta página herda o sistema do app, descrito em [`docs/design/DESIGN.md`](../docs/design/DESIGN.md):
as cinco cores, as opacidades, a regra de estados sem cores de alerta, a tipografia Inter/SST, os
raios 6/10 px, os traços de 1 px e trilhos de 2 px, o movimento de 150 ms e a exceção da cor real da
barra de luz. Aquele documento manda; este registra só o que a web acrescenta: escala tipográfica
grande, ritmo de seções, tratamento das fotos, composição da abertura e das linhas de chamada, o
fader em dB, a prévia da janela, os pontos de quebra e o movimento.

## Overview

**Creative North Star: "A janela no escuro"**

A página é a própria janela do app. O primeiro viewport não é um herói de produto com cartões: é a
janela libadwaita escura, com barra lateral e controles que funcionam, flutuando logo abaixo da barra
de luz acesa de um DualShock 4 fotografado no escuro. Tudo o que não é luz fica quieto; a única coisa
que brilha é o azul (`led-blue` na interface, `led` na foto e na faixa do cartão).

As seções abaixo seguem o mesmo material: fundo `black-0` contínuo, colunas de texto e foto lado a
lado, divisores de 1 px no lugar de caixas, títulos grandes em peso leve. A densidade é baixa fora da
janela e de app dentro dela: lá dentro valem as medidas do app (linhas de 48 px, título de página de
26 px), cá fora a escala sobe para leitura em tela grande.

**Key Characteristics:**
- Janela do app como abertura, interativa e rotulada como prévia.
- Fotos noturnas tratadas para que só a luz azul brilhe.
- Títulos em Light 300 (exibição em 300, numeral do fader em 200), aperto de −0,03 a −0,04em.
- Um único numeral aceso, tabular, que troca no lugar: o valor em dB.
- Divisores e linhas de chamada de 1 px; trilhos de 2 px.

## Colors

As cinco cores do app e suas opacidades, sem nenhum matiz novo; a web só acrescenta um degrau de
opacidade para texto corrido.

### Primary
- **Luz do Jogador 1** (`led-blue`): ação principal ("Acompanhar no GitHub"), preenchimento do fader e
  dos sliders, interruptor ligado, foco, item selecionado da barra lateral (com `blue-16` de fundo),
  ponto de status e fio extra do grafo em paralelo. Nunca em texto corrido.

### Neutral
- **Vazio** (`black-0`): fundo da página inteira e da janela.
- **Corpo do controle** (`black-1`): barra lateral da janela, cartões, bloco do comando, moldura do grafo.
- **Camada elevada** (`black-2`): botão secundário, hover, trilhos, código inline, caixa de confirmação do limite.
- **Branco** (`white`): títulos, rótulos, linha de chamada (a 60%) e a inversão acima de 0 dB.
- **Texto corrido** (`text-body`, branco 78%): lead da abertura e parágrafos das seções. É o degrau que
  a web acrescenta: parágrafos longos em tela grande pedem menos brilho que os títulos, mais que a legenda.
- **Secundário** (`text-2`, branco 60%), **desligado** (`text-off`, 32%), **traço** (`hairline`, 8%),
  **aresta** (`edge`, 6%): como no app.

### Named Rules
**The Hardware Color Rule.** `led` é dado, não tema: aparece só na faixa de luz do cartão, nos
seletores de cor da página Luz, no nó do controle no grafo e, via `hue-rotate`/`saturate` da foto da
abertura, na barra de luz fotografada. Trocar a cor na prévia retinge os quatro juntos.

**The Inversion Rule.** Acima de 0 dB o preenchimento do fader e a borda da faixa ativa passam para
branco e o rótulo vai a peso 600. É o sinal mais forte da paleta e fica reservado ao limite de volume.

## Typography

**Display Font:** SST, se instalada e licenciada; senão Inter variável (subconjunto latino, servida localmente, `font-display: swap`).
**Body Font:** a mesma.
**Label/Mono Font:** `ui-monospace` para comandos e código.

**Character:** um só sans em pesos leves; a hierarquia vem de tamanho e peso, nunca de cor.

### Hierarchy
- **Display** (300, `clamp(2.75rem, 6vw, 5rem)`, 1,02, −0,04em, máx. 15ch): só o título da abertura.
- **Numeral** (200, `clamp(4.5rem, 13vw, 10rem)`, 0,9, `tnum`): só o valor em dB sobre o fader grande; unidade ao lado em 300, `text-2`.
- **Headline** (300, `clamp(2rem, 4.2vw, 3.5rem)`, 1,08, −0,03em, `text-wrap: balance`): título de cada seção.
- **Title** (300, 26 px, 1,15): título de página dentro da janela, igual ao app.
- **Lead** (400, `clamp(1.0625rem, 1.4vw, 1.1875rem)`, 1,55, máx. 34rem): parágrafo da abertura.
- **Body** (400, 17 px, 1,55, máx. 36–40rem): parágrafos das seções.
- **Label** (500, 15 px): botões, nome do controle, títulos de fato, faixas do fader.
- **Control** (400, 14 px): linhas de preferência, links do topo, botão pequeno.
- **Caption** (400, 13 px, +0,01em, `text-2`): legendas, chamadas, notas de status.
- **Tag** (500, 11 px, +0,02em): só o selo "planejado".

### Named Rules
**The One Lit Numeral Rule.** Só o valor em dB é numeral grande e aceso; ele troca no lugar,
tabular, sem animar dígitos. Nenhum outro número da página (fases, bateria, porcentagem) passa de 15 px.

## Layout

Coluna de conteúdo de 1200 px com margem lateral fluida (`gutter`); a barra do topo alinha seu
conteúdo a essa mesma coluna. Cada seção abre com `section` de respiro acima, título, 24 px até o
primeiro parágrafo e 32 px até o próximo bloco. As seções de duas colunas usam proporções de 12
colunas (5/7 no paralelo, 5/6 no cabeçalho do volume, 6/6 em conexão, 4/8 em instalar) com
`column-gap` entre elas; a foto troca de lado de uma seção para outra. Fatos e fases são listas com
divisores de 1 px, nunca cartões.

**Abertura.** Título e lead à esquerda no topo (topo em `clamp(96px, 13vh, 132px)`), ações logo
abaixo. A foto ocupa a largura toda em faixa 3:1 (máx. 720 px), dissolvendo no preto nas duas pontas.
A janela (máx. 1040 px) sobe sobre a foto (`margin-top: min(-19vw, -120px)`) e nasce logo abaixo da
barra de luz, que fica acesa atrás dela. Duas linhas de chamada de 1 px, posicionadas em % da faixa,
ligam a barra de luz e a porta micro-USB aos recursos.

**Pontos de quebra.**
- **≤ 960 px:** chamadas somem (a faixa fica estreita demais para os rótulos); seções de duas colunas
  viram uma; foto de conexão sobe para antes do texto; foto do paralelo vira 16:10; fatos em 2 colunas.
- **≤ 720 px:** links do topo somem (fica o botão do repositório); foto da abertura vira 16:9 e a
  janela sobe só 72 px; a barra lateral da janela vira faixa de 4 abas com ícone sobre rótulo (56 px);
  seletores de cor em 2 colunas; faixas do fader empilham; o comando empilha com o botão copiar
  embaixo (44 px); fatos em 1 coluna.

## Elevation & Depth

Profundidade por camada, como no app. Sombra só no que flutua sobre a foto: a janela.

### Shadow Vocabulary
- **Janela** (`0 0 0 1px hairline, inset 0 1px 0 edge, 0 24px 64px rgb(0 0 0 / 0.6)`): a prévia flutuando sobre a foto.
- **Aresta** (`inset 0 1px 0 edge`): cartões, seletores, moldura do grafo, bloco do comando.
- **Contorno** (`inset 0 0 0 1px hairline`): botão secundário, interruptor desligado, botão do repositório.
- **Botão do fader** (`0 1px 4px rgb(0 0 0 / 0.5)`): separa o botão branco do trilho.

### Named Rules
**The Legible Header Rule.** O único desfoque da página é o da barra do topo depois de rolar
(`blur(16px)` sobre `black-0` 72%, com divisor de 1 px), e existe para manter os links legíveis sobre
fotos; com `prefers-reduced-transparency` ou sem suporte vira `black-0` sólido. Nenhum outro vidro.

**The Dissolve Rule.** As fotos não ganham moldura nem degradê de cor; a da abertura só se dissolve
no preto pela máscara (transparente até 6%, opaca de 20% a 72%, transparente em 100%).

## Shapes

Cantos pequenos e concêntricos: 6 px em controles, 10 px em superfícies e fotos das seções, 12 px na
janela (o raio de janela do libadwaita), 8 px no contêiner do segmentado (6 + 2 de folga). Pílula só
no selo "planejado" e no interruptor. Pontos de 5–6 px marcam a ponta da linha de chamada e o estado
"agora". Traços de 1 px em divisores e marcas do fader; trilhos de 2 px; botão do slider de 14 px
(20 px no fader grande).

**Tratamento das fotos.** Toda foto é noturna e tratada para que só o azul brilhe: duotom
preto-azulado, ou tudo o que não é azul dessaturado e escurecido, ou fundo levado ao preto. Cada
raster tem procedência em `assets/CREDITS.md` e sai em WebP com `srcset` e JPEG de reserva.

## Components

### Buttons
- **Shape:** cantos de controle (6 px), altura 44 px (36 px no pequeno).
- **Primary:** `led-blue` com texto branco, Label. Um por tela.
- **Secondary:** `black-2` com contorno `hairline`.
- **Flat:** só texto; hover em `black-2`. Em ≤ 720 px, na abertura, perde o recuo e sublinha no hover.
- **Hover e pressionar sem cor nova:** o principal escurece com preto por cima (12% no hover, 24%
  ao pressionar), o que também aumenta o contraste do texto; o secundário ganha a aresta `white` 6%.
- **Pressionar:** `scale(0.98)` imediato; o secundário volta a `black-1`.

### Chips
- **Selo "planejado":** pílula de 1 px `hairline`, texto `text-2` em 11 px/500, ao lado do título
  do recurso que ainda não existe. Não é rótulo de seção.

### Cards / Containers
- **Corner Style:** 10 px. **Background:** `black-1`. **Shadow Strategy:** aresta. **Border:** nenhuma; divisores internos de 1 px.
- **Cartão do controle:** faixa de luz de 96 × 2 px no topo, na cor `led`, centralizada.

### Inputs / Fields
- **Interruptor:** 36 × 20, botão 14 px; ligado em `led-blue`, desliza 16 px em 200 ms.
- **Slider nativo (vibração):** trilho 2 px `black-2`, preenchimento `led-blue`, botão branco 14 px.
- **Segmentado:** contêiner `black-2`, opção marcada em `black-0` com contorno `hairline`.
- **Seletor de cor:** grade de 4 (2 no celular), cada opção com faixa de 48 × 2 px na cor `led` a
  40%; marcada a 100% e com contorno `led-blue`.
- **Foco:** contorno 2 px `led-blue`, afastado 2 px (4 px no fader).

### Navigation
- **Barra do topo:** 60 px, transparente sobre a abertura, sólida/desfocada depois de rolar. Links em
  Control `text-2`, hover branco sobre `black-2`; botão do repositório com contorno.
- **Barra lateral da janela:** 200 px, `black-1`, itens de 40 px; selecionado em `blue-16` com ícone `led-blue`.

### Fader em dB (componente próprio)
Escala de −30 a +6 dB. Trilho de 2 px `black-2`, preenchimento `led-blue`, botão branco; marcas de 1 px
em −6 dB (`text-off`, 12 px) e em 0 dB (branco, o limite). Faixas abaixo do fader grande em
proporção da escala (66,667 / 16,666 / 16,667%): Livre, Alto, Acima do limite, com divisor superior
que acende em `led-blue` (branco na última). Acima de 0 dB vale a inversão e o fader para no teto até
a confirmação ("Manter em 0 dB" plano, "Passar do limite" secundário). Arrasta com ponteiro
(`touch-action: none`), anda por teclado, o botão cresce para 1,15 ao arrastar. Versão de linha
(28 px) dentro da janela e versão grande (48 px, botão 20 px) na seção de volume, sincronizadas.

### Prévia da janela
Cabeçalho de 46 px com título centrado e botão de fechar decorativo; corpo em grade 200 px + conteúdo,
mín. 460 px; páginas Status, Áudio, Vibração e Luz como abas reais (`tablist`), cada uma até 560 px.
Sempre com legenda dizendo que é prévia e que os valores são de demonstração. Por Bluetooth a página
Áudio mostra a ilustração de estado do app em vez do fader.

### Linhas de chamada
Linha de 1 px branco 60% com ponto branco de 5 px na ponta que toca o objeto; rótulo em Caption com
o nome em 500 branco. Só para partes visíveis na foto.

### Movimento
- Hover 150 ms *ease-out*; pressionar imediato; troca de página na janela 220 ms (opacidade e 4 px)
  com `cubic-bezier(0.16, 1, 0.3, 1)`.
- Faixa de luz e retinta da foto em 300 ms; pulso da faixa ao testar o som (400 ms).
- Fios do grafo correm em tracejado contínuo (1,2 s, linear); ao trocar a saída, o fio principal
  religa em 420 ms.
- Sem controle no navegador, o teste de vibração sacode a janela (4 × 90 ms, até 3 px).
- **`prefers-reduced-motion`:** rolagem suave desligada, animações e transições reduzidas a 0,01 ms,
  pulso e sacudida da janela não rodam. Nenhum estado depende de movimento.

## Do's and Don'ts

### Do:
- **Do** começar pela janela do app sobre foto escura, rotulada como prévia.
- **Do** usar `text-body` (branco 78%) em parágrafos e `text-2` em legendas.
- **Do** tratar toda foto nova para que só a luz azul brilhe e registrar a procedência em `assets/CREDITS.md`.
- **Do** manter um só botão `led-blue` por seção.
- **Do** separar listas e tabelas com divisores de 1 px `hairline`.

### Don't:
- **Don't** criar cor nova fora das cinco e de suas opacidades; variação é opacidade ou camada.
- **Don't** usar verde, amarelo ou vermelho para estado; o alerta é ícone, texto, peso e a inversão para branco.
- **Don't** pôr chamada em parte que a foto não mostra (alto-falante, motores).
- **Don't** usar logotipo da PlayStation nem △◯✕□ como marca.

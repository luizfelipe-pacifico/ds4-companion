---
version: 1
slug: "index-html"
primary_target: "index.html"
related_targets: []
---

# Landing page — DS4 Companion

Modo: Persuade. Público: quem joga no RPCS3 com DualShock 4 no Arch Linux. Ação: acompanhar/contribuir
no GitHub (o pacote ainda não existe; o comando de instalação aparece como "como vai ser").
Prova: a interface do app em funcionamento (prévia sintética, rotulada), o fluxo em paralelo e o
teto em dB. Restrições: design system de docs/design/DESIGN.md (5 cores, slim, uma luz azul), sem
marcas da Sony como marca, PT-BR, sem depoimentos ou números inventados.

Rodada de direção feita sem atendimento (o mantenedor pediu execução direta): a estrutura sorteada
na frente foi adotada.

## Direction contract

THESIS: A página é a própria janela do app. Em vez de headline + botão + cards, o primeiro viewport é a janela libadwaita escura, com barra lateral (Status, Áudio, Vibração, Luz) e controles que funcionam; recusa o hero de produto genérico e a página-terminal.

OWN-WORLD: black-0 #060709 como vazio, black-1/black-2 como camadas, uma única luz led-blue #2B6CF6, branco com opacidades. Traços 1 px, trilhos 2 px, raios 6/10 px, Inter leve nos títulos, numerais tabulares. Fotos noturnas do controle, dessaturadas e escuras, onde só a luz azul brilha.

STORY: entende em uma linha que o som vai para a TV e para o controle ao mesmo tempo; acredita porque vê o fluxo em paralelo, o slider em dB que inverte para branco acima de 0 dB e a honestidade sobre Bluetooth; age indo ao GitHub ou copiando o comando de instalação futuro.

FIRST VIEWPORT: título leve à esquerda no topo (≈ 64–80 px) com a frase do produto; logo e links mínimos numa barra fina; a janela do app ocupa ~60% da largura, inclinada zero, flutuando sobre foto escura do controle com a faixa de luz acesa; ação principal "Ver no GitHub" (led-blue) + comando copiável ao lado. Raise (estrutura 4, sala à noite): foto real de controle no escuro como chão do hero. Raise (estrutura 3, fader): o slider em dB da janela é arrastável e mostra livre/alto/acima do limite com inversão.

FORM: estrutura 6 de 7 (página como janela do app), sorteada na frente; seed:d69856b8a6825e94. Desafiantes recusados; disciplina mantida da prancha de patente: anatomia do controle com linhas de chamada finas ligando peças a recursos. Do contador nixie: o valor em dB é o único numeral aceso, tabular, que troca no lugar.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

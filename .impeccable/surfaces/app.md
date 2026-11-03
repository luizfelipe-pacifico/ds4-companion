---
version: 1
slug: "app"
primary_target: "src/ds4_companion/app"
related_targets: ["data/style.css", "data/illustrations"]
---

# Interface do app — DS4 Companion

Modo: Operate. Público e tarefa em `PRODUCT.md`: abrir, conferir se o som está indo para o controle,
ajustar volume, vibração ou luz e fechar. Composição fixada por `docs/design/UI.md` e pelo GNOME HIG
(barra lateral + páginas de preferências); mundo fixado por `docs/design/DESIGN.md`. Sem rodada de
estruturas: o brief já define a direção.

## Direction contract

THESIS: o app é o controle no escuro — um corpo preto em camadas e uma única luz. Recusa o painel
de configurações cinza com cartões iguais e cores de alerta.

OWN-WORLD: três pretos azulados, `led-blue` só no que está ligado ou é ação, branco com opacidade
para hierarquia; traços de 1 px, trilhos de 2 px, títulos em Inter leve, valores `tnum`. Estado por
texto + ícone, limite de volume por inversão para branco.

STORY: em um olhar a pessoa sabe se o controle está conectado, por onde e se o som está chegando
nele; ajusta com um gesto e entende o que vale agora e o que vale ao reabrir o RPCS3.

FIRST VIEWPORT: barra lateral `black-1` com Status, Áudio, Vibração, Luz, Avançado; à direita, a
página Status abre com o cartão do controle (faixa de luz no topo, nome, conexão, bateria) seguido
das linhas Áudio no controle, Volume do controle, RPCS3 e Saída principal. Nenhum botão principal
na página Status. (Áudio e Volume vieram para cima na construção: a STORY põe "o som está chegando
no controle" como a primeira pergunta, e o volume com o teto é o dado de segurança que se confere.)

FORM: barra lateral + AdwPreferencesPage (padrão GNOME), posição 1 da lista; seed: none (unavailable).
Movimento-assinatura: a faixa de luz do cartão acende na cor real do LED ao conectar (300 ms) e
apaga ao desconectar.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

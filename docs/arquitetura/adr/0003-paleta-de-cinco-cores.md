# 0003. Paleta de cinco cores, sem cores de alerta

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
A primeira paleta tinha 11 cores (três azuis, dois cinzas, verde/amarelo/vermelho). O pedido foi
um visual escuro e *slim* com poucas cores: o azul da barra de luz do controle, o branco do texto e
três pretos para separar componentes e criar profundidade.

## Decisão
- Cinco cores: `black-0 #060709`, `black-1 #111318`, `black-2 #1D2027`, `led-blue #2B6CF6`, `white #FFFFFF`.
  Variações só por opacidade de `white` e `led-blue`.
- `#2B6CF6` em vez do `#0000FF` do LED: o azul puro tem 2,4:1 sobre preto; `#2B6CF6` passa AA com
  texto branco (4,6:1) e tem 4,4:1 sobre `black-0`.
- Sem verde/amarelo/vermelho. Estados usam texto + ícone; o limite de volume (> 0 dB) usa
  **inversão para branco** e confirmação.
- Única exceção: elementos que mostram a cor real da barra de luz do controle (dado do hardware).
- Profundidade por camada de preto; sombra só em popover/diálogo. Detalhes em
  [DESIGN.md](../../design/DESIGN.md).

## Consequências
- Interface coesa e reconhecível; cumpre WCAG 1.4.1 (cor nunca é o único sinal).
- O aviso de volume perde o vermelho "universal"; o texto e o ícone precisam ser claros e testados.
- Se um teste com usuários mostrar que o limite não é percebido, reabrir com nova ADR (opção:
  um vermelho só para `> 0 dB`).

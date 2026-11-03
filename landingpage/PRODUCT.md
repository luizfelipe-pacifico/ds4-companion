# Product

<!-- impeccable:product-schema 1 -->

> Escrito a partir do pedido do mantenedor e da documentação do repositório (README, `docs/`,
> `SECURITY.md`). O mantenedor pediu execução direta, sem rodada de perguntas; os itens marcados
> *inferido* vêm do repositório e não de uma entrevista.

## Platform

web

## Stack

Estático: HTML + CSS + um pouco de JavaScript sem framework e sem build, dentro de `landingpage/`.
*Inferido:* o projeto evita runtime embutido e dependência fora do necessário (ADR 0001); uma página
estática combina com isso e pode ir para o GitHub Pages sem etapa de build.

## Users

Quem joga no PC com Arch Linux, usa o emulador RPCS3 e tem um DualShock 4. Joga na TV, no monitor
HDMI ou no notebook, quase sempre à noite, e quer o som do jogo também no alto-falante ou fone do
controle, como era no PS4, sem perder a saída de áudio principal. Usuário de Linux que lê, confere
e instala pelo terminal (`pacman`, AUR).

Público secundário: quem pode contribuir (Python, GTK, PipeWire).

## Product Purpose

DS4 Companion é um app nativo (GTK4 + libadwaita) que manda o som do RPCS3 **em paralelo** para o
DualShock 4, controla o volume do controle em dB com teto de segurança e ajusta a força da vibração,
por cabo e Bluetooth. Sucesso: o juiz apita no jogo e apita na TV e no controle ao mesmo tempo,
sem o usuário abrir o terminal.

## Positioning

Não troca a saída de áudio e não cria saída virtual: o daemon liga as portas do RPCS3 também ao
controle no PipeWire, então a latência é praticamente zero e a troca de saída no GNOME não quebra o
som do controle. Volume em dB com teto que protege o alto-falante de ~0,5 W.

## Capabilities and Constraints

- Áudio em paralelo: só por cabo USB. Por Bluetooth o Linux não envia áudio ao DS4 (limitação do
  kernel/PipeWire); vibração, luz e bateria funcionam nos dois.
- Volume em dB; teto `max_db` padrão 0 dB; −6 a 0 dB mostra aviso "alto"; acima pede confirmação.
- Vibração: força dos motores forte e fraco, teste de no máximo 2 s.
- Cor da barra de luz: planejada (v0.2).
- Componentes: `ds4-companion` (GUI), `ds4-companiond` (daemon systemd de usuário), `ds4ctl` (CLI).
- Tudo como usuário comum; root só na instalação (regra udev). Sem telemetria, sem rede.
- **Status real:** documentação e planejamento. Fase 0 (scripts) funciona; o pacote ainda não
  existe. A página não pode prometer download pronto.

## Brand Commitments

- Nome: DS4 Companion. Ícone próprio em `data/icons/hicolor/scalable/apps/ds4-companion.svg`.
- Design system em `docs/design/DESIGN.md` (ADR 0003): cinco cores, sem cores de alerta, visual
  escuro e *slim*, uma única luz azul (`led-blue #2B6CF6`).
- Não usar logotipo da PlayStation, os símbolos △◯✕□ como marca, nem "PlayStation" no nome.
  Citar DualShock/PlayStation só para dizer compatibilidade, com o aviso de marca da Sony.
- Idioma: português do Brasil.

## Evidence on Hand

- Ícone do app e 8 ilustrações de estado em SVG (`data/illustrations/`).
- Diagrama do fluxo de áudio e tabelas de recursos/compatibilidade do README.
- Roadmap por fases (`docs/desenvolvimento/ROADMAP.md`).
- Não há: depoimentos, número de usuários, estrelas, benchmarks medidos, capturas da GUI (ainda
  não existe). Nada disso pode ser inventado.

## Product Principles

1. Paralelo, nunca no lugar: a saída que a pessoa escolheu não muda.
2. O hardware vem antes do volume: teto em dB e confirmação para passar dele.
3. Nativo e transparente: pacotes do `extra`, código aberto, sem root em execução.
4. Honestidade sobre limites: Bluetooth sem áudio é dito com clareza, não escondido.

## Accessibility & Inclusion

WCAG 2.2 AA; cor nunca é o único sinal (estados por texto + ícone); navegável por teclado;
respeitar `prefers-reduced-motion`.

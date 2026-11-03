# Product

<!-- impeccable:product-schema 1 -->

> Interface do app (GTK4 + libadwaita). A landing page tem o próprio registro em
> `landingpage/PRODUCT.md`. Confirmado pelo mantenedor em 2026-11-02 a partir do README e de `docs/`.

## Platform

linux-desktop

## Users

Quem joga no PC com Arch Linux + GNOME, usa o emulador RPCS3 e tem um DualShock 4. Joga na TV, no
monitor HDMI ou no notebook. Abre o app de vez em quando para ajustar volume, vibração ou a cor da
luz e depois esquece: o daemon segue trabalhando em segundo plano.

## Product Purpose

Mandar o som do RPCS3 **em paralelo** para o alto-falante ou fone do controle, como no PS4, sem
trocar a saída de áudio principal; controlar o volume do controle em dB com teto de segurança, a
força da vibração e a cor da barra de luz, por cabo e Bluetooth. Sucesso: o usuário liga uma vez e
nunca mais pensa nisso, e o alto-falante do controle nunca é danificado.

## Positioning

O som vai para o controle e para a saída de sempre ao mesmo tempo (links extras no PipeWire, sem
saída virtual nem latência), com um teto de volume que protege o hardware e só cede com confirmação.

## Operating Context

- Usado no intervalo entre partidas, às vezes com o controle na mão: precisa ser navegável por
  teclado e (v0.4) pelo próprio controle.
- O RPCS3 só lê a configuração ao abrir: mudanças de vibração e cor feitas com ele aberto ficam
  pendentes e precisam dizer isso.
- Por Bluetooth o Linux não entrega áudio ao DualShock 4; vibração, luz e bateria continuam.

## Capabilities and Constraints

- GUI sem lógica de negócio: tudo passa pelo `ds4-companiond` via D-Bus (ADR 0001, 0008).
- Só pacotes do repositório `extra` do Arch; sem Flatpak, Electron ou runtime embutido.
- Textos em português, com `gettext`.
- Limites do SECURITY.md: teto `max_db` (padrão 0 dB), confirmação acima de 0 dB, teste de vibração
  de no máximo 2 s, nada no hidraw com o RPCS3 aberto.

## Brand Commitments

- Visual fixado em `docs/design/DESIGN.md` (ADR 0003): cinco cores, *slim*, uma única luz azul.
- Ícone e ilustrações próprias em `data/`. Sem logotipo da PlayStation, sem △◯✕□ como marca,
  sem "PlayStation" no nome.

## Evidence on Hand

Ícone do app em `data/icons/`, oito ilustrações de estado em `data/illustrations/` com textos em
`docs/design/ILLUSTRATIONS.md`. Não há depoimentos, números de uso nem capturas de tela publicadas.

## Product Principles

1. Proteger o hardware vem antes de qualquer conveniência.
2. Ligar uma vez e esquecer: o padrão certo dispensa ajuste.
3. Dizer o estado real (cabo, Bluetooth, RPCS3 aberto, pendente) em texto, nunca só por cor.
4. Nativo do GNOME: widgets do libadwaita antes de qualquer componente próprio.

## Accessibility & Inclusion

WCAG AA de contraste, cor nunca é o único sinal, navegável por teclado, rótulos acessíveis em todos
os controles, respeita *Reduzir animação* e *Texto grande* do GNOME.

# CLAUDE.md

Guia para o Claude Code trabalhar neste repositório.

## O projeto

DS4 Companion: app nativo para Arch Linux (GTK4 + libadwaita) que envia o som do RPCS3 em paralelo
para o DualShock 4, controla volume em dB com teto de segurança e a força da vibração, via cabo e
Bluetooth. Status atual: **documentação / planejamento** — ainda não há código em `src/`.

Leia antes de mexer em algo grande:

- Arquitetura e fluxo do áudio: `docs/arquitetura/ARCHITECTURE.md`
- Boas práticas (fonte da verdade para estilo, testes, Git, CI, empacotamento): `docs/desenvolvimento/BEST_PRACTICES.md`
- Roadmap: `docs/desenvolvimento/ROADMAP.md`
- Interface e visual: `docs/design/UI.md`, `docs/design/DESIGN.md`
- Segurança e limites de volume/hardware: `SECURITY.md`

## Stack

Python 3, GTK4 + libadwaita (PyGObject), PipeWire/WirePlumber, `hidraw` + udev (`python-pyudev`),
D-Bus de sessão (`python-dbus-next`), systemd de usuário, PKGBUILD/AUR.
Só pacotes do repositório oficial `extra`. Nada de Flatpak, Electron ou runtime embutido.

Componentes: `ds4-companion` (GUI), `ds4-companiond` (daemon), `ds4ctl` (CLI). A GUI não tem lógica
de negócio: fala com o daemon por D-Bus.

## Comandos

```bash
python -m venv --system-site-packages .venv && . .venv/bin/activate
pip install -e '.[dev]'
python -m ds4_companion.daemon --foreground --debug
python -m ds4_companion.app
ruff check && ruff format --check
mypy --strict src/
pytest --cov
```

## Regras

- **Idioma:** documentação, textos da interface e mensagens de commit em português. Textos da UI com `gettext`.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`), com sign-off (`git commit -s`).
- **Sem atribuição do Claude:** não adicionar `Co-Authored-By: Claude` nem "Generated with Claude Code" em commits ou PRs.
- **Registrar decisões:** toda decisão importante (stack, arquitetura, design system, processo) vira uma ADR em
  `docs/arquitetura/adr/NNNN-titulo.md` e entra no índice `docs/arquitetura/adr/README.md`, no mesmo commit da mudança.
  Mudar de ideia = nova ADR que substitui a antiga. Se a decisão muda uma regra deste arquivo, atualize-o também.
- **Changelog:** atualizar a seção *Não lançado* do `CHANGELOG.md` e a documentação no mesmo PR que o código.
- **Cabeçalho SPDX** em todo arquivo de código:
  ```python
  # SPDX-License-Identifier: GPL-3.0-or-later
  # SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
  ```
- **Segurança:** nada roda como root; `subprocess.run([...])` com lista, nunca `shell=True`;
  nomes de nós do PipeWire, propriedades udev e YAML do RPCS3 são dados não confiáveis.
  Nunca logar serial/MAC completos nem commitar segredos ou dumps (`pw-dump*.json`, `hid-dump*`).
- **Hardware:** respeitar o teto `max_db`; não enviar vibração por `hidraw` enquanto o RPCS3 estiver com jogo aberto.
- **Interface:** seguir o GNOME HIG e usar widgets do libadwaita (`AdwPreferencesPage`, `AdwActionRow`, `AdwToast`)
  em vez de reinventar; contraste WCAG AA; navegável por teclado e controle.

## Skills de design instaladas

Em `.claude/skills/`:

- `impeccable` (pbakaus/impeccable) — auditoria e crítica de design (`/impeccable audit`, `/impeccable critique`).
- `apple-design` (emilkowalski/skills) — princípios de interface e movimento da Apple.

As duas foram escritas pensando em web. Aqui a interface é GTK4/libadwaita: aproveite os princípios
(hierarquia, ritmo, movimento, contraste) e traduza para widgets e CSS do GTK; não introduza HTML/React.

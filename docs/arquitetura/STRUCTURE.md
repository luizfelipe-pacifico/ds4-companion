# Estrutura de arquivos

Onde cada coisa fica no repositório e onde colocar o que for novo. Decisão registrada na
[ADR 0006](adr/0006-organizacao-dos-arquivos.md).

Legenda: ✅ já existe · 🗓️ planejado (ainda não criado).

## Visão geral

```
ds4-companion/
├── README.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md     ✅ arquivos de comunidade (GitHub)
├── SECURITY.md  CHANGELOG.md  LICENSE                 ✅
├── CLAUDE.md                                          ✅ guia para o Claude Code
├── pyproject.toml                                     ✅ metadados, dependências e config das ferramentas
├── install.sh                                         🗓️ instalador executável (ADR 0005)
│
├── src/ds4_companion/                                 ✅ código Python
│   ├── app/                                           🗓️ GUI (GTK4/libadwaita)
│   ├── daemon/                                        ✅ ds4-companiond
│   ├── cli/                                           🗓️ ds4ctl
│   └── common/                                        ✅ código compartilhado
│
├── data/                                              arquivos instalados que não são código
│   ├── icons/hicolor/                                 ✅ ícone do app (SVG)
│   ├── illustrations/                                 ✅ ilustrações das telas de estado (SVG)
│   └── …                                              🗓️ .desktop, AppStream, serviço, udev, D-Bus, CSS
│
├── po/                                                🗓️ traduções (gettext)
├── tests/                                             testes automatizados
│   ├── ci/                                            ✅ testes dos verificadores do CI
│   ├── unit/                                          ✅
│   └── integration/                                   ✅
├── packaging/                                         🗓️ PKGBUILD e arquivos do AUR
├── scripts/                                           scripts de desenvolvimento e CI
│   ├── check.sh                                       ✅ roda as verificações do CI localmente
│   └── ci/                                            ✅ verificadores (SVG, dados sensíveis, SPDX, commits)
│
├── docs/                                              ✅ documentação (ver abaixo)
├── .github/                                           ✅ templates de issue/PR e workflows
└── .claude/  skills-lock.json                         ✅ configuração e skills do Claude Code
```

## Raiz

Só o que o GitHub, o Python ou o usuário procuram na raiz. Todo o resto vai para uma pasta.

| Arquivo | Para quê |
|---|---|
| `README.md` | O que é, para quem, como instalar. Responde em 30 s |
| `CONTRIBUTING.md` | Fluxo de contribuição, ambiente, testes |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| `SECURITY.md` | Permissões, limites de hardware e relato de vulnerabilidade |
| `CHANGELOG.md` | Keep a Changelog, com a seção *Não lançado* no topo |
| `LICENSE` | GPL-3.0-or-later |
| `CLAUDE.md` | Regras e comandos para o Claude Code |
| `pyproject.toml` ✅ | Fonte única de metadados e config de `ruff`, `mypy` e `pytest` |
| `install.sh` 🗓️ | Instalador para usuário comum ([ADR 0005](adr/0005-instalacao-por-um-comando.md)) |
| `.editorconfig`, `.gitattributes`, `.gitignore` | Formatação, fim de linha LF, o que nunca vai para o Git |

## `docs/` — documentação

Organizada **por público**. Nomes de arquivo em inglês e maiúsculas (`AUDIO.md`); pastas e textos
em português. Índice em [docs/README.md](../README.md).

| Pasta | Público | Conteúdo |
|---|---|---|
| `guia/` | Quem usa o app | Instalação, configuração, áudio, vibração, solução de problemas |
| `arquitetura/` | Quem mexe no código | Arquitetura, esta estrutura, ADRs |
| `arquitetura/adr/` | Quem decide | `NNNN-titulo-curto.md` + índice `README.md` |
| `design/` | Interface e visual | Design system, telas, ilustrações |
| `desenvolvimento/` | Contribuidores e mantenedores | Boas práticas, roadmap |

Imagens da documentação **não** ficam em `docs/`: os docs apontam para os SVGs de `data/`, para
existir uma cópia só de cada imagem.

## `src/ds4_companion/` — código 🗓️

Layout `src/` (o pacote só é importável depois de instalado, o que pega erro de empacotamento cedo).
A GUI não tem lógica de negócio: tudo passa pelo daemon via D-Bus.

```
src/ds4_companion/
├── __init__.py
├── app/                    # ds4-companion (GUI)
│   ├── __main__.py         # python -m ds4_companion.app
│   ├── window.py
│   ├── pages/              # status.py, audio.py, vibration.py, light.py, advanced.py
│   ├── widgets/            # componentes próprios (slider em dB, cartão do controle, …)
│   └── states.py           # telas de estado (AdwStatusPage + ilustrações)
├── daemon/                 # ds4-companiond
│   ├── __main__.py         # python -m ds4_companion.daemon
│   ├── audio/              # graph.py (pw-dump → links), pipewire.py (pw-link, wpctl, eventos)
│   ├── hid/                # relatórios USB 0x05 / BT 0x11 (CRC32) e acesso ao hidraw
│   ├── rpcs3/              # edição do Default.yml com backup; RPCS3 aberto (/proc)
│   ├── device.py           # detecção cabo ↔ Bluetooth e bateria via udev
│   └── dbus.py             # serviço D-Bus exposto para GUI e CLI
├── cli/                    # ds4ctl
│   └── __main__.py
└── common/                 # usado por todos
    ├── config.py           # config.toml: leitura, validação, padrões
    ├── db.py               # conversão dB ↔ volume do PipeWire (escala cúbica)
    ├── models.py           # tipos compartilhados (estado, cores da luz)
    ├── updates.py          # consulta de versão nova no GitHub Releases (ADR 0009)
    └── names.py            # app ID e nomes do D-Bus (ADR 0008)
```

- Um módulo por responsabilidade; nomes em `snake_case` e em inglês.
- Todo arquivo `.py` começa com o cabeçalho SPDX (ver [BEST_PRACTICES](../desenvolvimento/BEST_PRACTICES.md#10-licença)).

## `data/` — arquivos instalados

Tudo que o pacote instala e não é Python. Nomes em `kebab-case` e em inglês.

| Caminho | Instala em | Status |
|---|---|---|
| `icons/hicolor/scalable/apps/ds4-companion.svg` | `/usr/share/icons/hicolor/scalable/apps/` | ✅ |
| `icons/hicolor/symbolic/apps/ds4-companion-symbolic.svg` | `/usr/share/icons/hicolor/symbolic/apps/` | ✅ |
| `icons/*-symbolic.svg` (ícones próprios da interface) | GResource | 🗓️ |
| `illustrations/*.svg` ([catálogo](../design/ILLUSTRATIONS.md)) | GResource | ✅ |
| `style.css` (CSS do [DESIGN.md](../design/DESIGN.md#aplicação-no-gtk4libadwaita)) | GResource | 🗓️ |
| `ds4-companion.gresource.xml` | compilado para `.gresource` | 🗓️ |
| `<app-id>.desktop.in` | `/usr/share/applications/` | 🗓️ |
| `<app-id>.metainfo.xml.in` | `/usr/share/metainfo/` | 🗓️ |
| `ds4-companion.service` | `/usr/lib/systemd/user/` | 🗓️ |
| `70-ds4-companion.rules` | `/usr/lib/udev/rules.d/` | 🗓️ |
| `<app-id>.xml` (interface D-Bus) | `/usr/share/dbus-1/interfaces/` | 🗓️ |

Os arquivos com `<app-id>` e o ícone `ds4-companion*.svg` são renomeados quando o app ID for definido.

## `tests/` — testes

Espelha `src/`: o teste de `daemon/hid/` fica em `tests/unit/daemon/test_hid.py`.

| Pasta | O quê |
|---|---|
| `unit/` ✅ | Rápidos e sem hardware: conversão dB, relatórios HID e CRC32, parser de config, edição do YAML |
| `integration/` ✅ | PipeWire de teste com `pw-play` fingindo ser o RPCS3 |
| `fixtures/` ✅ | Dados de exemplo **sintéticos** (nunca dumps reais de dispositivo) |
| `ci/` ✅ | Testes dos scripts de CI |

Testes com hardware real são manuais (checklist em [CONTRIBUTING](../../CONTRIBUTING.md#testes)).

## `packaging/` — empacotamento 🗓️

| Arquivo | Para quê |
|---|---|
| `PKGBUILD` | O mesmo para AUR e GitHub Releases |
| `.SRCINFO` | Regenerado a cada mudança (`makepkg --printsrcinfo > .SRCINFO`) |
| `ds4-companion.install` | Avisos pós-instalação (reconectar o controle, migração da Fase 0) |

O que o `makepkg` gera (`src/`, `pkg/`, `*.pkg.tar.*`) é ignorado pelo Git.

## `scripts/` — automação

Scripts de apoio, nunca instalados no sistema. `scripts/ci/` ✅ guarda o que os workflows chamam
(ver [ADR 0007](adr/0007-ci-e-verificacoes-de-seguranca.md)), e `scripts/check.sh` ✅ roda o mesmo localmente;
scripts de desenvolvimento (gerar recursos, otimizar SVG) ficam direto em `scripts/`.

## `.github/` — GitHub

| Caminho | Para quê |
|---|---|
| `ISSUE_TEMPLATE/` ✅ | Formulários de bug e de recurso; issues em branco desativadas |
| `PULL_REQUEST_TEMPLATE.md` ✅ | Checklist do PR |
| `workflows/` ✅ | `ci.yml` (lint, testes, build, pacote, instalador), `security.yml` (gitleaks, CodeQL, dependências), `scorecard.yml` |
| `dependabot.yml` ✅ | Atualização semanal de Actions e ferramentas do CI |

## `.claude/` — Claude Code

`settings.json` (sem atribuição em commits), `agents/` e `skills/` usados pelo Claude Code;
`skills-lock.json` fixa a versão das skills instaladas. `settings.local.json` é pessoal.

## Onde colocar algo novo

| Quero adicionar… | Vai em |
|---|---|
| Uma página da interface | `src/ds4_companion/app/pages/` + seção em `docs/design/UI.md` |
| Um comando do `ds4ctl` | `src/ds4_companion/cli/` + `docs/guia/CONFIGURATION.md` |
| Uma opção do `config.toml` | `src/ds4_companion/common/config.py` + `docs/guia/CONFIGURATION.md` |
| Um ícone | `data/icons/` em SVG ([regras](../design/DESIGN.md#ícones)) |
| Uma ilustração | `data/illustrations/` + catálogo em `docs/design/ILLUSTRATIONS.md` |
| Uma decisão importante | `docs/arquitetura/adr/NNNN-titulo.md` + índice |
| Um guia para o usuário | `docs/guia/` + `docs/README.md` |
| Um arquivo instalado no sistema | `data/` + `packaging/PKGBUILD` + `install.sh` + `docs/guia/INSTALL.md` |
| Um texto da interface | string com `_()` no código; tradução em `po/` |

## O que nunca entra no repositório

Bloqueado pelo `.gitignore`: ambientes virtuais, caches, cobertura, saída do `makepkg`, `.env` e
chaves, `config.local.toml`, logs, backups (`*.bak*`) e dumps de PipeWire/HID (`pw-dump*.json`,
`hid-dump*`). Templates de issue pedem para não colar MAC, serial ou e-mail.

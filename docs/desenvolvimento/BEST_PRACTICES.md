# Boas práticas

Regras que o projeto segue. Cada seção diz **o quê**, **por quê** e a **fonte**.

## 1. Repositório público

| Prática | Como aplicamos |
|---|---|
| Arquivos de comunidade padrão | `README`, `LICENSE`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `CHANGELOG` na raiz |
| Canais separados | Issues = bugs/propostas · Discussions = dúvidas · Security tab = vulnerabilidades |
| Templates | Issue forms e template de PR em `.github/` |
| Nada pessoal no Git | `.gitignore` bloqueia `.env`, logs, backups, dumps; templates pedem para não colar MAC/serial/e-mail |
| Branch principal protegida | `main` só recebe PR com CI verde e revisão |

Fontes: [Hyperledger — Common Repository Structure](https://wiki.hyperledger.org/x/OJHQB),
[OpenSSF Best Practices Badge](https://www.bestpractices.dev/).

## 2. Segurança

- **Relato privado de vulnerabilidade** pelo GitHub (Settings → Advanced Security → *Private vulnerability reporting* → Enable).
- **Menor privilégio:** nada roda como root; acesso ao hidraw só via `uaccess` (ver [SECURITY.md](../../SECURITY.md)).
- **Dependências em dia:** Dependabot para GitHub Actions e Python; CodeQL no CI.
- **Nunca commitar segredos.** Se acontecer: revogar o segredo primeiro, depois reescrever o histórico.
- **Entrada externa é dado:** nomes de nós do PipeWire, propriedades udev e YAML do RPCS3 nunca são passados para shell
  sem escape; usar `subprocess.run([...])` com lista, nunca `shell=True`.
- Meta: atingir o selo **OpenSSF Best Practices (passing)**.

Fontes: [GitHub Docs — private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/working-with-repository-security-advisories/configuring-private-vulnerability-reporting-for-a-repository),
[Hyperledger](https://wiki.hyperledger.org/x/OJHQB).

## 3. Código Python

| Ferramenta | Papel | Onde roda |
|---|---|---|
| `pyproject.toml` | fonte única de metadados e config das ferramentas | — |
| `ruff check` / `ruff format` | lint + formatação (substitui flake8, black, isort) | pre-commit e CI |
| `mypy --strict` | tipagem | CI (lento demais para pre-commit) |
| `pytest --cov` | testes + cobertura | CI |
| `uv` (dev) | ambiente e lockfile (`uv.lock` versionado) | máquina do dev |

- Funções pequenas, nomes claros, sem lógica de negócio na camada de interface (GUI chama o daemon por D-Bus).
- Erros tratados na borda (PipeWire, hidraw, arquivos) com mensagem útil ao usuário; nada de `except: pass`.
- Logs via `logging` (vão para o journal); nunca logar serial/MAC completos.
- Textos da interface com `gettext` desde o início.

Fontes: [Logic-py/python-template](https://github.com/Logic-py/python-template),
[Modern Python project initialization](https://medium.com/@hasithvikasitha/modern-python-project-initialization-d8a31a6e9bf5).

## 4. Testes

- **Pirâmide:** muitos testes unitários (conversão dB, geradores de relatório HID, parser de config),
  alguns de integração (PipeWire de teste com `pw-play`), poucos manuais com hardware.
- Toda correção de bug vem com um teste que falhava antes.
- Hardware real: checklist manual em **cabo e Bluetooth** antes de cada release (ver [CONTRIBUTING.md](../../CONTRIBUTING.md)).

## 5. Git e versões

- **Conventional Commits:** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`; quebra de compatibilidade com `!` (`feat!:`) e rodapé `BREAKING CHANGE:`.
- **SemVer** `MAJOR.MINOR.PATCH`: quebra → MAJOR, recurso → MINOR, correção → PATCH. Enquanto `0.x`, a API pode mudar.
- **Keep a Changelog:** seções *Adicionado, Alterado, Corrigido, Removido, Segurança* e uma seção *Não lançado* no topo.
- Tags `vX.Y.Z` assinadas; release no GitHub com notas copiadas do changelog.
- PRs pequenos, um assunto por PR.

Fontes: [semver.org](https://semver.org/lang/pt-BR/), [conventionalcommits.org](https://www.conventionalcommits.org/pt-br/),
[keepachangelog.com](https://keepachangelog.com/pt-BR/).

## 6. CI (GitHub Actions)

Em todo PR e push na `main`:

1. `ruff check` + `ruff format --check`
2. `mypy --strict src/`
3. `pytest --cov`
4. `namcap` no PKGBUILD e no pacote gerado (container `archlinux:latest`)
5. CodeQL (Python)

Actions fixadas por SHA, permissões mínimas (`permissions: contents: read`).

## 7. Empacotamento Arch / AUR

- Seguir as **Arch package guidelines**: nome em minúsculas, `pkgver` sem hífen, `pkgrel` volta a 1 a cada versão nova.
- Declarar **todas as dependências diretas** em `depends`; opcionais (`rpcs3-bin`, `gamemode`) em `optdepends`.
- Variáveis próprias no PKGBUILD com prefixo `_`; mensagens com `printf`/`echo`.
- Rodar `namcap` no PKGBUILD e no `.pkg.tar.zst`.
- Regenerar `.SRCINFO` a cada mudança: `makepkg --printsrcinfo > .SRCINFO`.
- Pedir revisão pública (fórum/AUR mailing list) antes do primeiro envio.

Fontes: [ArchWiki — Arch package guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines),
[AUR submission guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines).

## 8. Interface (GNOME)

- Seguir o **GNOME HIG**: simplicidade, consistência, acessibilidade como princípio.
- Usar widgets do libadwaita (`AdwPreferencesPage`, `AdwActionRow`, `AdwToast`) em vez de reinventar.
- Navegável só pelo teclado e pelo controle; rótulos acessíveis em todos os controles.
- Contraste mínimo WCAG AA (ver [DESIGN.md](../design/DESIGN.md)).
- Ícones e logo **só em SVG**, preferindo os simbólicos do Adwaita (ver [DESIGN.md](../design/DESIGN.md#ícones)).
- Metadados AppStream (`.metainfo.xml`) com descrição, capturas de tela e licença.

Fontes: [Adwaita (Wikipedia)](https://en.wikipedia.org/wiki/Adwaita_(design_language)), [GNOME HIG](https://developer.gnome.org/hig/).

## 9. Documentação

- README responde em 30 s: o que é, para quem, como instalar.
- Documentação muda **no mesmo PR** que o código.
- Decisões de arquitetura importantes registradas em `docs/arquitetura/adr/NNNN-titulo.md` (ADR).

## 10. Licença

- Código: **GPL-3.0-or-later** (arquivo [LICENSE](../../LICENSE)), padrão no ecossistema GNOME;
  compatível com GTK4/libadwaita/PyGObject (LGPL).
- Todo arquivo de código começa com:
  ```python
  # SPDX-License-Identifier: GPL-3.0-or-later
  # SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
  ```
- Contribuições aceitas com *sign-off* (`git commit -s`, DCO).

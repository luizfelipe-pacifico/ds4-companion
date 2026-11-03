# Contribuindo

Ao participar você concorda com o [Código de Conduta](CODE_OF_CONDUCT.md).
Leia também as [boas práticas](docs/desenvolvimento/BEST_PRACTICES.md).

## Fluxo

1. Abra (ou escolha) uma issue.
2. Crie um branch: `feat/nome-curto` ou `fix/nome-curto`.
3. Commits em [Conventional Commits](https://www.conventionalcommits.org/pt-br/) com sign-off: `git commit -s`.
4. Atualize `CHANGELOG.md` (seção *Não lançado*) e a documentação.
5. Abra o PR usando o template; o CI precisa passar.

## Ambiente

```bash
sudo pacman -S --needed python python-gobject python-cairo gtk4 libadwaita python-pyudev python-dbus-next \
                        inter-font pipewire wireplumber jq
python -m venv --system-site-packages .venv && . .venv/bin/activate
pip install -e '.[dev]'     # pytest, ruff, mypy
pip install -r requirements-ci.txt
sudo pacman -S --needed gitleaks shellcheck
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Antes de cada commit e push, rode `scripts/check.sh` (os testes da interface rodam num display
invisível com `scripts/headless.sh`, sem abrir janelas na sua sessão) (as mesmas verificações do CI que não precisam
de container). O CI completo está descrito em [BEST_PRACTICES.md](docs/desenvolvimento/BEST_PRACTICES.md#6-ci-github-actions).

## Rodando

```bash
python -m ds4_companion.daemon --foreground --debug
python -m ds4_companion.app
```

## Testes

- Unitários: conversão dB ↔ volume linear, parser de config, gerador de relatórios HID (USB e BT com CRC32).
- Integração: PipeWire + WirePlumber isolados (sem tocar no áudio da sessão nem no hardware), com
  null sinks no papel da saída e do controle e o `pw-play` fingindo ser o RPCS3:
  ```bash
  dbus-run-session -- scripts/ci/run-integration.sh
  ```
- Hardware: checklist manual em cabo **e** Bluetooth, com DualShock 4 **e** DualSense, antes de cada versão.

## Estilo

- `ruff` + `mypy --strict` no `src/`
- Commits no formato `tipo: descrição` (`feat`, `fix`, `docs`, `refactor`)
- Textos da interface em português, com suporte a tradução (gettext)

## Release

1. Atualize a versão em `pyproject.toml`, `src/ds4_companion/__init__.py` e `packaging/PKGBUILD`
   (`pkgrel=1`), regenere o `.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`) e acrescente a versão no
   `<releases>` do AppStream (`data/*.metainfo.xml`).
2. Mova as entradas de *Não lançado* do `CHANGELOG.md` para a versão nova.
3. Crie e envie a tag assinada: `git tag -s vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.

O workflow `release.yml` confere que as versões batem, monta o pacote num Arch limpo e publica o
pacote (com versão e com o nome fixo `ds4-companion.pkg.tar.zst`), o `SHA256SUMS` e o `install.sh`.
Com o segredo `GPG_PRIVATE_KEY` definido no repositório, também publica a assinatura `.sig`.

# 0007. CI e verificações de segurança em todo commit

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
Todo commit precisa passar por lint, testes, build e checagens de segurança (segredos, dados
pessoais, dependências) antes de chegar à `main`. O projeto ainda é só documentação, mas o CI deve
valer desde já e crescer com o código sem ser reescrito.

## Decisão
Três workflows no GitHub Actions, em todo push e PR:

| Workflow | Jobs |
|---|---|
| `ci.yml` | repositório (EditorConfig, yamllint, actionlint, zizmor, SVG, dados sensíveis, SPDX, testes dos verificadores) · commits (Conventional Commits, DCO, sem atribuição de IA) · links da documentação · shellcheck · Python (ruff, `mypy --strict`, pytest com cobertura ≥ 80 %, `pip-audit`, build) · integração com PipeWire isolado · pacote do Arch (makepkg, namcap, `.SRCINFO`, validação de `.desktop`/AppStream/systemd/udev, instala e remove) · `install.sh` num Arch limpo |
| `security.yml` | gitleaks no histórico inteiro e na árvore · CodeQL (`actions` e Python) · revisão de dependências e licenças em PR · também toda segunda-feira |
| `scorecard.yml` | OpenSSF Scorecard na `main` e semanal |

- Jobs de Python, pacote e instalador só rodam quando `pyproject.toml`, `packaging/PKGBUILD` e
  `install.sh` existem. Jobs em container usam `archlinux:base-devel` fixado por digest.
- Actions fixadas por SHA, `permissions: contents: read` por padrão, `persist-credentials: false`,
  ferramentas com versão exata em `requirements-ci.txt` e binários conferidos por SHA-256.
  Dependabot atualiza Actions e ferramentas toda semana.
- Verificadores próprios em `scripts/ci/` (Python, só biblioteca padrão) com testes em `tests/ci/`.
- Localmente: `scripts/check.sh` e `pre-commit` (inclui hook `commit-msg`) rodam as mesmas checagens.
- Proteção da `main`: exigir os checks **CI ok** e **Segurança ok**, PR com revisão, sem push forçado.

## Consequências
- Nada chega à `main` sem passar pela bateria inteira; segredos e dados pessoais são barrados no
  commit (pre-commit) e de novo no CI.
- Commits antigos que não seguem as regras ficam em `scripts/ci/commit-allowlist.txt`; commits
  novos não entram lá: a mensagem é corrigida antes do merge.
- Ao criar `pyproject.toml`, `PKGBUILD` ou `install.sh`, os comandos que o CI espera precisam
  existir: `ds4ctl --version`, `ds4-companion --version`, `install.sh --package <arquivo>`,
  `--uninstall` e `--no-service`.
- Trocar o digest da imagem do Arch exige atualizar todos os jobs de container juntos.

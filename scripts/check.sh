#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
#
# Roda localmente as mesmas verificações do CI que não precisam de container.
# Uso: scripts/check.sh            (tudo)
#      scripts/check.sh --rapido   (pula Python/pacote, para pré-commit)
# Ferramentas: pip install -r requirements-ci.txt ; gitleaks e shellcheck via pacman.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

rapido=false
[[ "${1:-}" == "--rapido" ]] && rapido=true

falhas=()
pulados=()

etapa() {
    local nome=$1
    shift
    printf '\n== %s\n' "$nome"
    if "$@"; then
        printf 'ok: %s\n' "$nome"
    else
        falhas+=("$nome")
    fi
}

ferramenta() {
    local nome=$1 cmd=$2
    shift 2
    if command -v "$cmd" >/dev/null 2>&1; then
        etapa "$nome" "$cmd" "$@"
    else
        pulados+=("$nome (falta '$cmd')")
    fi
}

etapa "testes dos verificadores" python3 -I -m unittest discover -s tests/ci
etapa "git diff --check" git diff --check HEAD
etapa "SVG" python3 -I scripts/ci/check_svg.py
etapa "dados sensíveis" python3 -I scripts/ci/check_sensitive.py
etapa "SPDX" python3 -I scripts/ci/check_spdx.py
etapa "commits ainda não publicados" python3 -I scripts/ci/check_commits.py \
    "$(git rev-parse --verify --quiet '@{upstream}' || echo '')" HEAD
ferramenta "segredos (gitleaks, histórico)" gitleaks git --config .gitleaks.toml --redact .
ferramenta "segredos (gitleaks, árvore)" gitleaks dir --config .gitleaks.toml --redact .
ferramenta "editorconfig" ec
ferramenta "YAML" yamllint --strict .
ferramenta "workflows (actionlint)" actionlint
ferramenta "workflows (zizmor)" zizmor --offline --min-severity=low .github/workflows

mapfile -t scripts_sh < <(git ls-files '*.sh' ':!.claude/**')
if ((${#scripts_sh[@]})); then
    ferramenta "shellcheck" shellcheck --severity=style --external-sources "${scripts_sh[@]}"
fi

if ! $rapido && [[ -f pyproject.toml ]]; then
    ferramenta "ruff check" ruff check .
    ferramenta "ruff format" ruff format --check .
    ferramenta "mypy" mypy --strict src/
    ferramenta "pytest" pytest --ignore=tests/integration --cov=ds4_companion --cov-fail-under=80
fi

printf '\n'
for p in "${pulados[@]}"; do printf 'PULADO: %s\n' "$p"; done
if ((${#falhas[@]})); then
    for f in "${falhas[@]}"; do printf 'FALHOU: %s\n' "$f"; done
    exit 1
fi
printf 'Tudo certo%s.\n' "$( ((${#pulados[@]})) && echo ' (com etapas puladas, ver acima)')"

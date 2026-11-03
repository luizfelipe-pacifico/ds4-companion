#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
#
# Instalador do DS4 Companion (ADR 0005). Rode como usuário comum, sem sudo: ele pede a senha só
# para o pacman. Leia antes de rodar: less install.sh
#
#   ./install.sh                         baixa a última versão, confere o SHA256SUMS e instala
#   ./install.sh --package <arquivo>     instala um .pkg.tar.zst que você já tem
#   ./install.sh --uninstall             desativa o serviço e remove o pacote
#   --no-service                         não mexe no serviço de usuário (ex.: container sem sessão)

set -euo pipefail

REPO="luizfelipe-pacifico/ds4-companion"
# A URL só muda em teste (file://); a soma SHA-256 é conferida do mesmo jeito.
RELEASE="${DS4_COMPANION_RELEASE_URL:-https://github.com/$REPO/releases/latest/download}"
PACKAGE_NAME="ds4-companion"
UNIT="ds4-companion.service"
OLD_UNIT="ds4-audio-mirror.service"

say() { printf '>>> %s\n' "$*"; }
die() {
    printf 'Erro: %s\n' "$*" >&2
    exit 1
}

usage() {
    sed -n '5,/^$/p' "$0" | sed -e 's/^# \{0,1\}//' -e '/^$/d'
}

action=install
package=""
service=true
while (($#)); do
    case "$1" in
        --package)
            [[ $# -ge 2 ]] || die "--package precisa do caminho do arquivo"
            package=$2
            shift
            ;;
        --uninstall) action=uninstall ;;
        --no-service) service=false ;;
        -h | --help)
            usage
            exit 0
            ;;
        *) die "opção desconhecida: $1 (veja --help)" ;;
    esac
    shift
done

check_system() {
    [[ $EUID -ne 0 ]] || die "rode como usuário comum, sem sudo (o serviço é do seu usuário)"
    [[ -f /etc/arch-release ]] || command -v pacman >/dev/null || die "este instalador é para Arch Linux"
    command -v sudo >/dev/null || die "precisa do sudo para instalar o pacote"
}

download() {
    local dir=$1
    command -v curl >/dev/null || die "precisa do curl para baixar"
    say "Baixando a última versão"
    curl -fsSL -o "$dir/SHA256SUMS" "$RELEASE/SHA256SUMS"
    local name
    name=$(grep -oE '[^ *]+\.pkg\.tar\.zst$' "$dir/SHA256SUMS" | grep -E "^$PACKAGE_NAME-[0-9]" | head -n1)
    [[ -n $name ]] || die "SHA256SUMS sem o pacote do $PACKAGE_NAME"
    [[ $name != */* ]] || die "nome de arquivo inesperado no SHA256SUMS"
    curl -fsSL -o "$dir/$name" "$RELEASE/$name"
    say "Conferindo a soma SHA-256"
    (cd "$dir" && grep -E " [* ]?$name\$" SHA256SUMS | sha256sum --check --strict --quiet) ||
        die "a soma não confere; nada foi instalado"
    package="$dir/$name"
}

migrate_phase0() {
    # Scripts da Fase 0 (ds4-audio-mirror): o daemon novo faz o mesmo trabalho.
    if systemctl --user cat "$OLD_UNIT" >/dev/null 2>&1; then
        say "Desativando os scripts antigos ($OLD_UNIT)"
        systemctl --user disable --now "$OLD_UNIT" || true
    fi
    local f
    for f in "$HOME/.local/bin/ds4-audio-mirror" "$HOME/.config/systemd/user/$OLD_UNIT"; do
        if [[ -e $f ]]; then
            mv -- "$f" "$f.bak-$(date +%Y%m%d-%H%M%S)"
            say "Guardado como backup: $f.bak-*"
        fi
    done
}

tmpdir=""  # global: o trap de saída roda depois que a função já terminou
cleanup() { [[ -z $tmpdir ]] || rm -rf -- "$tmpdir"; }
trap cleanup EXIT

install_package() {
    if [[ -z $package ]]; then
        tmpdir=$(mktemp -d)
        download "$tmpdir"
    fi
    [[ -f $package ]] || die "pacote não encontrado: $package"
    say "Instalando $(basename "$package") (o pacman pede a senha)"
    sudo pacman -U --needed --noconfirm -- "$package"

    if $service; then
        migrate_phase0
        systemctl --user daemon-reload
        systemctl --user enable --now "$UNIT"
        say "Serviço ativo: $UNIT"
    fi
    say "Pronto. Desconecte e conecte o controle para a regra de permissão valer."
}

uninstall() {
    if $service; then
        systemctl --user disable --now "$UNIT" 2>/dev/null || true
    fi
    if pacman -Q "$PACKAGE_NAME" >/dev/null 2>&1; then
        say "Removendo o pacote (o pacman pede a senha)"
        sudo pacman -R --noconfirm "$PACKAGE_NAME"
    else
        say "O pacote não estava instalado"
    fi
    say "Suas configurações continuam em ~/.config/ds4-companion (apague se quiser)."
}

check_system
case $action in
    install) install_package ;;
    uninstall) uninstall ;;
esac

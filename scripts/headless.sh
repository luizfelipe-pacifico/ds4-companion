#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
#
# Roda um comando com um display próprio e invisível (mutter headless), para os testes da
# interface não abrirem janelas e diálogos na sua sessão. Sem mutter, roda o comando como está.
# Uso: scripts/headless.sh <comando> [argumentos...]
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v mutter >/dev/null 2>&1; then
    exec "$@"
fi

runtime=$(mktemp -d)
chmod 700 "$runtime"
display=ds4-headless-$$
# O compositor usa um XDG_RUNTIME_DIR próprio; o comando mantém o da sessão (D-Bus, PipeWire).
XDG_RUNTIME_DIR=$runtime mutter --headless --wayland --no-x11 --virtual-monitor 1280x800 \
    --wayland-display="$display" >/dev/null 2>&1 &
mutter_pid=$!
trap 'kill "$mutter_pid" 2>/dev/null || true; wait "$mutter_pid" 2>/dev/null || true; rm -rf "$runtime"' EXIT
for _ in $(seq 50); do
    [ -S "$runtime/$display" ] && break
    sleep 0.1
done

status=0
env -u DISPLAY WAYLAND_DISPLAY="$runtime/$display" GDK_BACKEND=wayland "$@" || status=$?
exit "$status"

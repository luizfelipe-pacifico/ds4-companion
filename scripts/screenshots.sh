#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
#
# Capturas das páginas num mutter headless (monitor virtual), sem abrir janela na sessão.
# Uso: scripts/screenshots.sh <pasta de saída> [LARGURAxALTURA]
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:?pasta de saída}
size=${2:-880x640}
runtime=$(mktemp -d)
chmod 700 "$runtime"
export XDG_RUNTIME_DIR=$runtime
unset DISPLAY
display=ds4-shots
mutter --headless --wayland --no-x11 --virtual-monitor 1600x1000 --wayland-display="$display" >/dev/null 2>&1 &
mutter_pid=$!
trap 'kill "$mutter_pid" 2>/dev/null || true; wait 2>/dev/null || true; rm -rf "$runtime"' EXIT
for _ in $(seq 50); do [ -S "$runtime/$display" ] && break; sleep 0.1; done
WAYLAND_DISPLAY=$display GDK_BACKEND=wayland "${PYTHON:-.venv/bin/python}" "${SCRIPT:-scripts/screenshots.py}" "$out" "$size"

#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
#
# Sobe um PipeWire + WirePlumber isolados (XDG_RUNTIME_DIR próprio, sem tocar no áudio da
# sessão) e roda os testes de integração. Precisa de um D-Bus de sessão próprio:
#   dbus-run-session -- scripts/ci/run-integration.sh [argumentos do pytest]

set -euo pipefail
cd "$(dirname "$0")/../.."

runtime=$(mktemp -d)
chmod 700 "$runtime"
export XDG_RUNTIME_DIR=$runtime
# Sem isso o PipeWire de teste herdaria as variáveis do PipeWire da sessão.
unset PIPEWIRE_REMOTE PULSE_SERVER

pipewire &
pw_pid=$!
wireplumber &
wp_pid=$!
trap 'kill "$wp_pid" "$pw_pid" 2>/dev/null || true; wait 2>/dev/null || true; rm -rf "$runtime"' EXIT

for _ in $(seq 50); do
    pw-cli info 0 >/dev/null 2>&1 && break
    sleep 0.2
done
pw-cli info 0 >/dev/null

"${PYTHON:-.venv/bin/python}" -m pytest tests/integration --strict-markers -ra "$@"

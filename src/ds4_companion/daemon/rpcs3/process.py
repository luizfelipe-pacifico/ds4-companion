# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Detecção do RPCS3 aberto pelo `/proc/*/comm` (sem rodar `ps` nem shell)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

RPCS3_PROCESSES = ("rpcs3", "AppRun.wrapped")
_COMM_LIMIT = 15  # o kernel corta o nome do processo em 15 caracteres


def is_running(names: Iterable[str] = RPCS3_PROCESSES, proc: Path = Path("/proc")) -> bool:
    wanted = {n[:_COMM_LIMIT].casefold() for n in names}
    try:
        entries = list(proc.iterdir())
    except OSError:
        return False
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue  # processo terminou no meio da leitura
        if comm.casefold() in wanted:
            return True
    return False

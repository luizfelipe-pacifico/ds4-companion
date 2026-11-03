# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Escrita e leitura no `/dev/hidrawN` do controle, como usuário comum (regra udev `uaccess`)."""

from __future__ import annotations

import errno
import os
import select


class HidError(OSError):
    """Falha ao falar com o controle."""


class HidAccessError(HidError):
    """Sem permissão no hidraw: a regra udev ainda não valeu."""


def _open(path: str, flags: int) -> int:
    try:
        return os.open(path, flags | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM):
            raise HidAccessError(exc.errno, "sem permissão no controle", path) from exc
        raise HidError(exc.errno, exc.strerror or "erro no controle", path) from exc


def write_report(path: str, report: bytes) -> None:
    fd = _open(path, os.O_WRONLY)
    try:
        written = os.write(fd, report)
    except OSError as exc:
        raise HidError(exc.errno, exc.strerror or "falha ao escrever no controle", path) from exc
    finally:
        os.close(fd)
    if written != len(report):
        raise HidError(errno.EIO, "relatório escrito pela metade", path)


def read_report(path: str, size: int = 64, timeout: float = 0.1) -> bytes | None:
    """Lê um relatório de entrada; None se nada chegar dentro do tempo."""
    fd = _open(path, os.O_RDONLY)
    try:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        return os.read(fd, size)
    except OSError as exc:
        raise HidError(exc.errno, exc.strerror or "falha ao ler o controle", path) from exc
    finally:
        os.close(fd)


def can_write(path: str) -> bool:
    return os.access(path, os.W_OK)

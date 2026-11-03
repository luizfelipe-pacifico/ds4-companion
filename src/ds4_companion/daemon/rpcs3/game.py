# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Qual jogo está aberto no RPCS3, lido do `RPCS3.log` (o RPCS3 não tem outra interface para isso).

Ao abrir um jogo, o `Emulator::Load` escreve `SYS: Title: <título>` e `SYS: Serial: <ID>`; ao
parar, `SYS: Stopping emulator...`. Cada execução do RPCS3 começa um log novo. O arquivo é lido
aos poucos, só o que cresceu desde a última vez.

O log é dado não confiável: o serial precisa ter o formato dos jogos de PS3 (`BLUS30001`) e o
título perde caracteres de controle e fica com no máximo MAX_TITLE caracteres.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

MAX_TITLE = 128
MAX_READ = 1 << 20
"""Bytes lidos por consulta: um log enorme é lido em partes, sem travar o daemon."""

_SERIAL = re.compile(r"[A-Z]{4}\d{5}")
_TITLE_MARK = b"SYS: Title: "
_SERIAL_MARK = b"SYS: Serial: "
_STOP_MARK = b"SYS: Stopping emulator..."


@dataclass(frozen=True)
class Game:
    serial: str
    title: str


def default_log_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "rpcs3" / "RPCS3.log"


def clean_title(raw: str) -> str:
    text = "".join(ch for ch in raw if ch.isprintable()).strip()
    return text[:MAX_TITLE]


class LogWatcher:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_log_path()
        self.game: Game | None = None
        self._inode: int | None = None
        self._offset = 0
        self._title = ""

    def reset(self) -> None:
        self.game = None
        self._inode = None
        self._offset = 0
        self._title = ""

    def poll(self) -> Game | None:
        """Lê o que o log ganhou e devolve o jogo aberto agora (ou None)."""
        try:
            st = os.stat(self.path)
            if st.st_ino != self._inode or st.st_size < self._offset:
                self.reset()  # log novo: o RPCS3 abriu de novo
                self._inode = st.st_ino
            if st.st_size == self._offset:
                return self.game
            with open(self.path, "rb") as f:
                f.seek(self._offset)
                chunk = f.read(MAX_READ)
        except OSError:
            self.reset()
            return None
        end = chunk.rfind(b"\n")
        if end < 0:
            if len(chunk) == MAX_READ:
                self._offset += len(chunk)  # uma "linha" gigante: não é do formato esperado
            return self.game
        for line in chunk[: end + 1].splitlines():
            self._parse(line)
        self._offset += end + 1
        return self.game

    def _parse(self, line: bytes) -> None:
        if _STOP_MARK in line:
            self.game = None
            self._title = ""
            return
        index = line.find(_TITLE_MARK)
        if index >= 0:
            self._title = clean_title(line[index + len(_TITLE_MARK) :].decode("utf-8", errors="replace"))
            return
        index = line.find(_SERIAL_MARK)
        if index >= 0:
            serial = line[index + len(_SERIAL_MARK) :].decode("ascii", errors="replace").strip()
            if _SERIAL.fullmatch(serial):
                self.game = Game(serial, self._title or serial)
            self._title = ""

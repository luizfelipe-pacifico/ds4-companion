# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Funções compartilhadas pelos verificadores do CI."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Conteúdo de terceiros versionado sem alteração; verificado na origem.
VENDORED = (".claude/skills/", ".claude/agents/")


@dataclass(frozen=True)
class Problem:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: {self.message}"


def tracked_files(root: Path = ROOT) -> list[str]:
    """Arquivos versionados (e staged), relativos à raiz do repositório."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    return [p for p in out.decode().split("\0") if p and (root / p).is_file()]


def is_vendored(path: str) -> bool:
    return path.startswith(VENDORED)


def report(name: str, problems: Iterable[Problem]) -> int:
    found = list(problems)
    for p in found:
        # Formato de anotação do GitHub Actions; legível no terminal também.
        print(f"::error file={p.path},line={p.line or 1}::{p.message}", file=sys.stderr)
        print(f"  {p}")
    if found:
        print(f"{name}: {len(found)} problema(s).")
        return 1
    print(f"{name}: ok.")
    return 0

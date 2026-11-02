# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Exige o cabeçalho SPDX em todo arquivo de código (BEST_PRACTICES.md §10)."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, Problem, is_vendored, report, tracked_files  # noqa: E402

CODE_SUFFIXES = (".py", ".sh")
CODE_NAMES = ("install.sh", "PKGBUILD")
LICENSE_TAG = "SPDX-License-Identifier: GPL-3.0-or-later"
COPYRIGHT_TAG = "SPDX-FileCopyrightText:"
HEADER_LINES = 5


def is_code(path: str) -> bool:
    return path.endswith(CODE_SUFFIXES) or Path(path).name in CODE_NAMES


def check_header(path: str, text: str) -> list[Problem]:
    head = "\n".join(text.splitlines()[:HEADER_LINES])
    problems = []
    if LICENSE_TAG not in head:
        problems.append(Problem(path, 1, f"falta '{LICENSE_TAG}' nas primeiras {HEADER_LINES} linhas"))
    if COPYRIGHT_TAG not in head:
        problems.append(Problem(path, 1, f"falta '{COPYRIGHT_TAG}' nas primeiras {HEADER_LINES} linhas"))
    return problems


def main(argv: list[str]) -> int:
    paths = argv or [p for p in tracked_files() if is_code(p) and not is_vendored(p)]
    problems: list[Problem] = []
    for p in paths:
        problems += check_header(p, (ROOT / p).read_text(encoding="utf-8", errors="replace"))
    return report("SPDX", problems)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

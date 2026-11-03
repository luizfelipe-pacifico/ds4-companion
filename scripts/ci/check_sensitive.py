# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Procura dados pessoais e arquivos que nunca devem ser versionados.

Complementa o gitleaks (que cuida de tokens e chaves): aqui ficam regras do
projeto, como MAC/serial do controle, e-mails pessoais, caminhos de home,
dumps do PipeWire/HID, logs e backups (ver SECURITY.md e .gitignore).
Uma linha pode ser liberada com o comentário `ds4-allow-sensitive`.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, Problem, is_vendored, report, tracked_files

FORBIDDEN_FILES = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "*.log",
    "*.bak",
    "*.bak-*",
    "pw-dump*.json",
    "hid-dump*",
    "config.local.toml",
    "*.pkg.tar.*",
    ".claude/settings.local.json",
)
ALLOWED_FILES = (".env.example",)

ALLOW_MARK = "ds4-allow-sensitive"
ALLOWED_EMAIL = re.compile(
    r"(@(example\.(com|org|net)|users\.noreply\.github\.com)$|^noreply@|^git@github\.com$)",
    re.IGNORECASE,
)

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("endereço MAC", re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f:])")),
    ("caminho de home com nome de usuário", re.compile(r"/home/[a-z_][a-z0-9_-]*/")),
    ("chave privada", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("número de série do controle", re.compile(r"\b(?:serial|uniq)\s*[=:]\s*['\"]?[0-9A-Fa-f]{12}\b", re.IGNORECASE)),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def forbidden_file(path: str) -> bool:
    name = Path(path).name
    if name in ALLOWED_FILES:
        return False
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(path, pat) for pat in FORBIDDEN_FILES)


def check_text(path: str, text: str) -> list[Problem]:
    problems: list[Problem] = []
    for n, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        for label, pat in PATTERNS:
            if pat.search(line):
                problems.append(Problem(path, n, f"possível {label}"))
        for m in EMAIL.finditer(line):
            if not ALLOWED_EMAIL.search(m.group(0)):
                problems.append(Problem(path, n, f"e-mail pessoal: {m.group(0)}"))
    return problems


def check_file(path: str, data: bytes) -> list[Problem]:
    if forbidden_file(path):
        return [Problem(path, 0, "tipo de arquivo que não pode ser versionado (ver .gitignore)")]
    if b"\0" in data[:8192]:
        return []  # binário: o gitleaks cobre
    return check_text(path, data.decode("utf-8", errors="replace"))


def main(argv: list[str]) -> int:
    paths = argv or [p for p in tracked_files() if not is_vendored(p)]
    problems: list[Problem] = []
    for p in paths:
        if p == "scripts/ci/check_sensitive.py":
            continue  # contém os próprios padrões
        problems += check_file(p, (ROOT / p).read_bytes())
    return report("Dados sensíveis", problems)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

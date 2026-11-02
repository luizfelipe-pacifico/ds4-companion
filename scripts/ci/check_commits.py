# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Valida as mensagens de commit de um intervalo.

- Conventional Commits no título (BEST_PRACTICES.md §5).
- Sign-off do DCO (`git commit -s`), com o e-mail do autor.
- Nenhuma atribuição de IA (ADR 0004).

Uso: check_commits.py <base> <head>   (commits em head que não estão em base)
     check_commits.py --all           (histórico inteiro)
     check_commits.py --message-file F  (hook commit-msg do pre-commit)
Commits anteriores à adoção das regras ficam em commit-allowlist.txt.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, Problem, report  # noqa: E402

TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert|security"
TITLE = re.compile(rf"^(?:{TYPES})(?:\([a-z0-9._/-]+\))?!?: \S.{{0,99}}$")
MERGE = re.compile(r"^(Merge|Revert) ")
AI_ATTRIBUTION = re.compile(
    r"(co-authored-by:.*(claude|anthropic|copilot|chatgpt|openai|gemini|cursor)"
    r"|generated with \[?claude code"
    r"|🤖 generated with)",
    re.IGNORECASE,
)
ALLOWLIST = Path(__file__).with_name("commit-allowlist.txt")
SEP = "\x1e"
ZERO = "0" * 40


def allowlisted() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    lines = ALLOWLIST.read_text().splitlines()
    return {ln.split()[0] for ln in lines if ln.strip() and not ln.startswith("#")}


def check_message(sha: str, author_email: str, message: str) -> list[Problem]:
    ref = f"commit {sha[:10]}"
    lines = message.strip().splitlines()
    title = lines[0] if lines else ""
    problems: list[Problem] = []
    if not MERGE.match(title) and not TITLE.match(title):
        problems.append(Problem(ref, 0, f"título fora do Conventional Commits: {title!r}"))
    signoffs = re.findall(r"^Signed-off-by: .+ <(.+)>$", message, re.MULTILINE)
    if not signoffs:
        problems.append(Problem(ref, 0, "falta 'Signed-off-by' (use git commit -s)"))
    elif author_email.lower() not in (s.lower() for s in signoffs):
        problems.append(Problem(ref, 0, f"sign-off não corresponde ao autor <{author_email}>"))
    if AI_ATTRIBUTION.search(message):
        problems.append(Problem(ref, 0, "atribuição de IA na mensagem (ADR 0004)"))
    return problems


def commits(rev_args: list[str]) -> list[tuple[str, str, str]]:
    out = subprocess.run(
        ["git", "log", "--no-merges", f"--format=%H%x1f%ae%x1f%B{SEP}", *rev_args],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    result = []
    for chunk in out.split(SEP):
        chunk = chunk.strip("\n")
        if chunk:
            sha, email, body = chunk.split("\x1f", 2)
            result.append((sha, email, body))
    return result


def check_message_file(path: str) -> int:
    message = Path(path).read_text(encoding="utf-8")
    # Linhas de comentário do editor do Git não fazem parte da mensagem.
    message = "\n".join(ln for ln in message.splitlines() if not ln.startswith("#"))
    email = subprocess.run(
        ["git", "config", "user.email"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    return report("Mensagem de commit", check_message("novo" + "0" * 36, email, message))


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--message-file":
        return check_message_file(argv[1])
    if argv == ["--all"]:
        rev_args = ["HEAD"]
    elif len(argv) == 2:
        base, head = argv
        rev_args = [head] if base in ("", ZERO) else [head, f"^{base}"]
    else:
        print(__doc__)
        return 2
    skip = allowlisted()
    problems: list[Problem] = []
    for sha, email, body in commits(rev_args):
        if sha not in skip:
            problems += check_message(sha, email, body)
    return report("Commits", problems)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

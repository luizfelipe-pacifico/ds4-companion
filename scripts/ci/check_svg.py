# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Valida os SVGs do projeto conforme docs/design/DESIGN.md (seção Ícones).

Regras: XML bem-formado, raiz <svg> com viewBox, sem script, sem manipuladores
de evento, sem imagem embutida, sem referência externa e sem <text> (texto deve
virar caminho). Ícones em hicolor/scalable/apps devem ser quadrados (1:1).
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, Problem, is_vendored, report, tracked_files

FORBIDDEN_TAGS = {"script", "image", "text", "foreignObject", "iframe", "embed", "object"}
EXTERNAL_REF = re.compile(r"^\s*(https?:|//|data:|javascript:|file:)", re.IGNORECASE)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def check_svg(path: str, data: bytes) -> list[Problem]:
    problems: list[Problem] = []
    if b"<!ENTITY" in data or b"<!DOCTYPE" in data:
        # Evita entidades (XXE / "billion laughs") antes de qualquer parse.
        return [Problem(path, 0, "DOCTYPE/ENTITY não permitido em SVG")]
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        return [Problem(path, exc.position[0], f"XML inválido: {exc}")]

    if _local(root.tag) != "svg":
        problems.append(Problem(path, 0, "raiz não é <svg>"))
    view_box = root.get("viewBox")
    if not view_box:
        problems.append(Problem(path, 0, "falta viewBox"))

    for el in root.iter():
        tag = _local(el.tag)
        if tag in FORBIDDEN_TAGS:
            problems.append(Problem(path, 0, f"elemento <{tag}> não permitido"))
        for attr, value in el.attrib.items():
            name = _local(attr)
            if name.lower().startswith("on"):
                problems.append(Problem(path, 0, f"atributo de evento '{name}' não permitido"))
            if name == "href" and EXTERNAL_REF.match(value):
                problems.append(Problem(path, 0, f"referência externa/embutida em href: {value[:40]}"))
        if tag == "style" and el.text and re.search(r"url\(\s*['\"]?(https?:|data:)", el.text):
            problems.append(Problem(path, 0, "url() externa/embutida em <style>"))

    if "/hicolor/scalable/apps/" in f"/{path}" and view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4 and float(parts[2]) != float(parts[3]):
            problems.append(Problem(path, 0, f"ícone do app não é 1:1 (viewBox {view_box})"))
    return problems


def main(argv: list[str]) -> int:
    paths = argv or [p for p in tracked_files() if p.endswith(".svg") and not is_vendored(p)]
    problems: list[Problem] = []
    for p in paths:
        problems += check_svg(p, (ROOT / p).read_bytes())
    return report("SVG", problems)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

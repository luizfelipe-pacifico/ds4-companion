# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Carrega o GResource (CSS, ilustrações, ícones). Instalado: /usr/share/ds4-companion.
No código-fonte, compila `data/ds4-companion.gresource.xml` no cache do usuário."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib

from ..common.names import RESOURCE_PREFIX

log = logging.getLogger(__name__)

RESOURCE_FILE = "ds4-companion.gresource"
SYSTEM_DIRS = (Path("/usr/share/ds4-companion"), Path("/usr/local/share/ds4-companion"))
SOURCE_DATA = Path(__file__).resolve().parents[3] / "data"


def _candidates() -> list[Path]:
    env = os.environ.get("DS4_COMPANION_DATADIR")
    dirs = [Path(env)] if env else []
    return [d / RESOURCE_FILE for d in (*dirs, *SYSTEM_DIRS)]


def compile_from_source(data_dir: Path = SOURCE_DATA) -> Path | None:
    manifest = data_dir / "ds4-companion.gresource.xml"
    if not manifest.exists():
        return None
    out = Path(GLib.get_user_cache_dir()) / "ds4-companion" / RESOURCE_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["glib-compile-resources", f"--sourcedir={data_dir}", f"--target={out}", str(manifest)],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        log.warning("não deu para compilar os recursos: %s", exc)
        return None
    return out


def register() -> bool:
    """Registra o primeiro GResource encontrado. Devolve False se nenhum existir."""
    try:
        Gio.resources_get_info(f"{RESOURCE_PREFIX}/style.css", Gio.ResourceLookupFlags.NONE)
        return True
    except GLib.Error:
        pass
    path = next((p for p in _candidates() if p.exists()), None) or compile_from_source()
    if path is None:
        return False
    Gio.resources_register(Gio.Resource.load(str(path)))
    return True


def illustration(name: str) -> str:
    return f"{RESOURCE_PREFIX}/illustrations/{name}.svg"

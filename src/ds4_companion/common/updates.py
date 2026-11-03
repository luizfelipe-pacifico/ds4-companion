# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Consulta rápida de nova versão no GitHub Releases e comando para atualizar (ADR 0009).

A resposta da API é dado não confiável: a versão e o nome do pacote são conferidos por expressão
regular e a URL de download é montada aqui, nunca copiada da resposta.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from typing import Any

from .. import __version__

log = logging.getLogger(__name__)

REPO = "luizfelipe-pacifico/ds4-companion"
LATEST_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_BASE = f"https://github.com/{REPO}/releases/download"
# Nome fixo sem versão que sempre aponta para a última release (ADR 0005).
LATEST_PACKAGE_URL = f"https://github.com/{REPO}/releases/latest/download/ds4-companion.pkg.tar.zst"

TIMEOUT_S = 5.0
MAX_RESPONSE_BYTES = 1 << 20

_VERSION = re.compile(r"(\d{1,4})\.(\d{1,4})\.(\d{1,4})")
_TAG = re.compile(r"v?(\d{1,4}\.\d{1,4}\.\d{1,4})")
_PACKAGE = re.compile(r"ds4-companion-(\d{1,4}\.\d{1,4}\.\d{1,4})-\d{1,4}-any\.pkg\.tar\.zst")


@dataclass(frozen=True)
class Update:
    """Versão nova publicada e o pacote para instalá-la."""

    current: str
    latest: str
    package_url: str

    @property
    def command(self) -> str:
        """Comando para colar no terminal."""
        return f"sudo pacman -U {self.package_url}"

    @property
    def argv(self) -> list[str]:
        """Atualização pelo botão: o polkit pede a senha; só o pacman roda como root."""
        return ["pkexec", "pacman", "-U", "--noconfirm", self.package_url]


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = _VERSION.fullmatch(text)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def _package_url(version: str, assets: Any) -> str:
    """URL do pacote da versão; sem o arquivo versionado, cai no nome fixo da última release."""
    if isinstance(assets, list):
        for asset in assets:
            name = asset.get("name") if isinstance(asset, dict) else None
            match = _PACKAGE.fullmatch(name) if isinstance(name, str) else None
            if match is not None and match.group(1) == version:
                return f"{DOWNLOAD_BASE}/v{version}/{name}"
    return LATEST_PACKAGE_URL


def from_release(release: Any, current: str = __version__) -> Update | None:
    """Interpreta a resposta de `releases/latest`. Devolve None se não há versão mais nova."""
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        return None
    tag = release.get("tag_name")
    match = _TAG.fullmatch(tag) if isinstance(tag, str) else None
    if match is None:
        return None
    latest = match.group(1)
    latest_v, current_v = parse_version(latest), parse_version(current)
    if latest_v is None or current_v is None or latest_v <= current_v:
        return None
    return Update(current=current, latest=latest, package_url=_package_url(latest, release.get("assets")))


def check(current: str = __version__, timeout: float = TIMEOUT_S) -> Update | None:
    """Uma requisição HTTPS, sem dados do usuário. Qualquer falha de rede vira "sem atualização"."""
    request = urllib.request.Request(
        LATEST_API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"ds4-companion/{current}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, ValueError) as exc:
        log.info("consulta de atualização falhou: %s", exc)
        return None
    if len(body) > MAX_RESPONSE_BYTES:
        log.info("consulta de atualização: resposta grande demais, ignorada")
        return None
    try:
        release = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        log.info("consulta de atualização: resposta inválida, ignorada")
        return None
    return from_release(release, current)

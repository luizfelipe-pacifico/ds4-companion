# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""install.sh com sudo, pacman e systemctl falsos: confere o que seria executado, sem instalar nada."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

INSTALL = Path(__file__).parents[2] / "install.sh"
PKG = "ds4-companion-0.1.0-1-any.pkg.tar.zst"


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "calls.log"
    for name in ("sudo", "pacman", "systemctl"):
        script = bindir / name
        body = f'echo "{name} $*" >> "{log}"\n'
        if name == "sudo":
            body += 'exec "$@"\n'
        if name == "systemctl":
            # A unidade antiga só "existe" se o teste criar o marcador.
            body += f'if [ "$2" = cat ] && [ ! -e "{tmp_path}/old-unit" ]; then exit 1; fi\n'
        if name == "pacman":
            body += f'if [ "$1" = -Q ] && [ ! -e "{tmp_path}/installed" ]; then exit 1; fi\n'
        script.write_text("#!/bin/sh\n" + body)
        script.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    return {
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(home),
        "TMPDIR": str(tmp_path),
        "LANG": "C.UTF-8",
    }


def run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(INSTALL), *args], env=env, capture_output=True, text=True, check=False)


def calls(env: dict[str, str]) -> list[str]:
    log = Path(env["TMPDIR"]) / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def release(tmp_path: Path, content: bytes = b"pacote", checksum: str | None = None) -> str:
    rel = tmp_path / "release"
    rel.mkdir(exist_ok=True)
    (rel / PKG).write_bytes(content)
    digest = checksum or hashlib.sha256(content).hexdigest()
    (rel / "SHA256SUMS").write_text(f"{digest}  {PKG}\n{'0' * 64}  install.sh\n")
    return f"file://{rel}"


skip_root = pytest.mark.skipif(os.geteuid() == 0, reason="o instalador recusa root de propósito")


@skip_root
def test_install_local_package_without_service(env: dict[str, str], tmp_path: Path) -> None:
    pkg = tmp_path / PKG
    pkg.write_bytes(b"x")
    result = run(env, "--package", str(pkg), "--no-service")
    assert result.returncode == 0, result.stderr
    assert f"pacman -U --needed --noconfirm -- {pkg}" in calls(env)
    assert not any(c.startswith("systemctl") for c in calls(env))


@skip_root
def test_install_downloads_checks_sum_and_enables_service(env: dict[str, str], tmp_path: Path) -> None:
    env["DS4_COMPANION_RELEASE_URL"] = release(tmp_path)
    (tmp_path / "old-unit").touch()
    old = Path(env["HOME"]) / ".local" / "bin" / "ds4-audio-mirror"
    old.parent.mkdir(parents=True)
    old.write_text("#!/bin/sh\n")
    result = run(env)
    assert result.returncode == 0, result.stderr
    log = calls(env)
    assert any(c.startswith("pacman -U") and c.endswith(PKG) for c in log)
    assert "systemctl --user disable --now ds4-audio-mirror.service" in log
    assert "systemctl --user enable --now ds4-companion.service" in log
    assert not old.exists()
    assert list(old.parent.glob("ds4-audio-mirror.bak-*"))


@skip_root
def test_wrong_checksum_installs_nothing(env: dict[str, str], tmp_path: Path) -> None:
    env["DS4_COMPANION_RELEASE_URL"] = release(tmp_path, checksum="f" * 64)
    result = run(env)
    assert result.returncode != 0
    assert "soma não confere" in result.stderr
    assert not any(c.startswith("pacman -U") for c in calls(env))


@skip_root
def test_uninstall(env: dict[str, str], tmp_path: Path) -> None:
    (tmp_path / "installed").touch()
    result = run(env, "--uninstall")
    assert result.returncode == 0, result.stderr
    log = calls(env)
    assert "systemctl --user disable --now ds4-companion.service" in log
    assert "pacman -R --noconfirm ds4-companion" in log
    (tmp_path / "installed").unlink()
    assert "não estava instalado" in run(env, "--uninstall", "--no-service").stdout


@skip_root
def test_bad_arguments(env: dict[str, str], tmp_path: Path) -> None:
    assert run(env, "--package").returncode != 0
    missing = run(env, "--package", str(tmp_path / "nada.pkg.tar.zst"))
    assert "não encontrado" in missing.stderr
    assert "--uninstall" in run(env, "--help").stdout

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Jogo aberto no RPCS3, lido do RPCS3.log (linhas sintéticas no formato do Emulator::Load)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ds4_companion.daemon.rpcs3 import game

BOOT = (
    "·! 0:00:01.000001 SYS: Booting from gamelist per doubleclick...\n"
    '    Serial: ""\n'  # linha da configuração, sem o prefixo SYS: não conta
    "·! 0:00:01.000100 SYS: Title: Jogo de Teste\n"
    "·! 0:00:01.000100 SYS: Serial: BLUS30001\n"
    "·! 0:00:01.000101 SYS: Category: DG\n"
)


@pytest.fixture
def log(tmp_path: Path) -> Path:
    return tmp_path / "RPCS3.log"


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def test_detects_boot_switch_and_stop(log: Path) -> None:
    watcher = game.LogWatcher(log)
    assert watcher.poll() is None  # ainda sem log
    log.write_text("·! 0:00:00.1 SYS: RPCS3 v0.0.38\n")
    assert watcher.poll() is None
    append(log, BOOT)
    assert watcher.poll() == game.Game("BLUS30001", "Jogo de Teste")
    assert watcher.poll() == game.Game("BLUS30001", "Jogo de Teste")  # nada novo: mesmo jogo
    append(log, "·! 0:00:09.0 SYS: Stopping emulator...\n")
    assert watcher.poll() is None
    append(log, "·! 0:00:10.0 SYS: Title: Outro\n·! 0:00:10.0 SYS: Serial: NPEB00002\n")
    assert watcher.poll() == game.Game("NPEB00002", "Outro")


def test_new_log_file_starts_over(log: Path) -> None:
    log.write_text(BOOT)
    watcher = game.LogWatcher(log)
    assert watcher.poll() is not None
    # O RPCS3 reabriu: log novo (menor) sem jogo ainda.
    log.write_text("·! 0:00:00.1 SYS: RPCS3 v0.0.38\n")
    assert watcher.poll() is None


def test_partial_line_waits_for_the_rest(log: Path) -> None:
    watcher = game.LogWatcher(log)
    log.write_text("·! 0:00:01 SYS: Title: Jogo\n·! 0:00:01 SYS: Serial: BLES0")
    assert watcher.poll() is None
    append(log, "1234\n")
    assert watcher.poll() == game.Game("BLES01234", "Jogo")


@pytest.mark.parametrize("serial", ["blus30001", "BLUS3000", "BLUS300011", "../../etc", "BLUS 3000"])
def test_rejects_invalid_serials(log: Path, serial: str) -> None:
    log.write_text(f"·! 0:00:01 SYS: Title: X\n·! 0:00:01 SYS: Serial: {serial}\n")
    assert game.LogWatcher(log).poll() is None


def test_title_is_cleaned_and_limited(log: Path) -> None:
    title = "Jogo\x1b[31m vermelho " + "x" * 300
    log.write_text(f"·! 0:00:01 SYS: Title: {title}\n·! 0:00:01 SYS: Serial: BCUS98174\n")
    found = game.LogWatcher(log).poll()
    assert found is not None
    assert "\x1b" not in found.title
    assert len(found.title) <= game.MAX_TITLE
    assert found.title.startswith("Jogo[31m vermelho")


def test_serial_without_title_uses_serial(log: Path) -> None:
    log.write_text("·! 0:00:01 SYS: Serial: BCES00001\n")
    assert game.LogWatcher(log).poll() == game.Game("BCES00001", "BCES00001")


def test_reads_big_logs_in_chunks(log: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(game, "MAX_READ", 64)
    log.write_text("·! ruído\n" * 40 + BOOT)
    watcher = game.LogWatcher(log)
    found = None
    for _ in range(40):
        found = watcher.poll() or found
    assert found == game.Game("BLUS30001", "Jogo de Teste")


def test_default_path_follows_xdg_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert game.default_log_path() == tmp_path / "rpcs3" / "RPCS3.log"


def test_unreadable_log(log: Path) -> None:
    log.mkdir()  # caminho existe mas não é arquivo
    assert game.LogWatcher(log).poll() is None

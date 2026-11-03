# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from pathlib import Path

import pytest

from ds4_companion.daemon.rpcs3 import input_config as ic
from ds4_companion.daemon.rpcs3 import process

FIXTURE = Path(__file__).parents[2] / "fixtures" / "Default.yml"


@pytest.fixture
def text() -> str:
    return FIXTURE.read_text()


def test_players(text: str) -> None:
    assert ic.players(text) == {1: "DualShock 4", 2: "DualShock 4", 3: "Keyboard"}


def test_read_vibration(text: str) -> None:
    assert ic.read_vibration(text, 1) == ic.Vibration(100, 100, False)
    assert ic.read_vibration(text, 2) is None  # falta o motor fraco
    assert ic.read_vibration(text, 9) is None
    assert ic.read_values("Player 1 Input:\n  Handler: DualShock 4\n", 1) == {}


def test_apply_vibration_changes_only_vibration_keys(text: str) -> None:
    new, warnings = ic.apply_vibration(text, [1, 2], ic.Vibration(150, 60, True))
    assert warnings == []
    assert ic.read_vibration(new, 1) == ic.Vibration(150, 60, True)
    assert ic.read_vibration(new, 2) == ic.Vibration(150, 60, True)
    assert ic.read_values(new, 3)[ic.LARGE] == "100"  # teclado intocado
    old_lines = [ln for ln in text.splitlines() if "Vibration" not in ln]
    new_lines = [ln for ln in new.splitlines() if "Vibration" not in ln]
    assert old_lines == new_lines  # comentários, Device e o resto ficam iguais
    assert new.endswith("\n")


def test_missing_keys_are_inserted_inside_config(text: str) -> None:
    new, _ = ic.apply_vibration(text, [2], ic.Vibration(100, 100, False))
    block = new.split("Player 2 Input:")[1].split("Player 3 Input:")[0]
    assert "    Small Vibration Motor Multiplier: 100\n" in block
    assert "    Switch Vibration Motors: false\n" in block
    assert block.rstrip().endswith("Switch Vibration Motors: false")


def test_apply_color(text: str) -> None:
    new, warnings = ic.apply_color(text, [1, 2, 3, 4], (255, 20, 147))
    assert warnings == [
        "Jogador 3 não usa DualShock 4 nem DualSense no RPCS3",
        "Jogador 4 não está no arquivo do RPCS3",
    ]
    for player in (1, 2):
        values = ic.read_values(new, player)
        assert (values["Color Value R"], values["Color Value G"], values["Color Value B"]) == ("255", "20", "147")
    assert "Color Value" not in new.split("Player 3 Input:")[1]


def test_minimal_file_from_vibration_doc() -> None:
    doc = (
        'Player 1 Input:\n  Handler: DualShock 4\n  Device: "DS4 Pad #1"\n  Config:\n'
        "    Large Vibration Motor Multiplier: 100\n    Small Vibration Motor Multiplier: 100\n"
        "    Switch Vibration Motors: false\n"
    )
    new, _ = ic.apply_color(doc, [1], (0, 0, 255))
    assert new.endswith("    Color Value B: 255\n")
    assert '"DS4 Pad #1"' in new


def test_player_without_config_block() -> None:
    with pytest.raises(ic.Rpcs3ConfigError, match="Config"):
        ic.set_values("Player 1 Input:\n  Handler: DualShock 4\n", 1, {"X": "1"})


def test_empty_config_block_uses_default_indent() -> None:
    new = ic.set_values("Player 1 Input:\n  Handler: 'DualShock 4'\n  Config:\n", 1, {"X": "1"})
    assert new == "Player 1 Input:\n  Handler: 'DualShock 4'\n  Config:\n    X: 1\n"


def test_handler_with_comment() -> None:
    text = "Player 1 Input: # p1\n  Handler: DualShock 4 # ds4\n  Config:\n    X: 0\n"
    assert ic.players(text) == {1: "DualShock 4"}
    assert ic.set_values(text, 1, {"X": "2"}).endswith("    X: 2\n")


def test_write_with_backup(tmp_path: Path, text: str) -> None:
    path = tmp_path / "Default.yml"
    path.write_text(text)
    path.chmod(0o600)
    assert ic.write_with_backup(path, text) is None  # sem mudança, sem backup
    assert not list(tmp_path.glob("*.bak-*"))

    new, _ = ic.apply_vibration(text, [1], ic.Vibration(50, 50, False))
    backup = ic.write_with_backup(path, new)
    assert backup is not None
    assert backup.read_text() == text
    assert path.read_text() == new
    assert path.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".*.tmp"))

    newer, _ = ic.apply_vibration(new, [1], ic.Vibration(10, 10, False))
    assert ic.write_with_backup(path, newer, backup=False) is None
    assert path.read_text() == newer


def test_write_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ic.Rpcs3ConfigError, match="não encontrado"):
        ic.write_with_backup(tmp_path / "Default.yml", "x")


def _proc(tmp_path: Path, comms: dict[str, str]) -> Path:
    for pid, comm in comms.items():
        (tmp_path / pid).mkdir()
        if comm:
            (tmp_path / pid / "comm").write_text(comm + "\n")
    (tmp_path / "self").mkdir()
    return tmp_path


def test_process_running(tmp_path: Path) -> None:
    proc = _proc(tmp_path, {"1": "systemd", "42": "AppRun.wrapped", "50": ""})
    assert process.is_running(proc=proc)
    assert not process.is_running(["steam"], proc=proc)


def test_process_not_running(tmp_path: Path) -> None:
    assert not process.is_running(proc=_proc(tmp_path, {"1": "bash"}))
    assert not process.is_running(proc=tmp_path / "nada")


def test_process_long_name_is_truncated_like_kernel(tmp_path: Path) -> None:
    proc = _proc(tmp_path, {"7": "um-nome-muito-l"})
    assert process.is_running(["um-nome-muito-longo"], proc=proc)


def test_dualsense_players_are_edited_too() -> None:
    text = (
        "Player 1 Input:\n"
        "  Handler: DualSense\n"
        '  Device: "DualSense Pad #1"\n'
        "  Config:\n"
        "    Large Vibration Motor Multiplier: 100\n"
        "Player 2 Input:\n"
        "  Handler: DualShock 3\n"
        "  Config:\n"
        "    Large Vibration Motor Multiplier: 100\n"
    )
    out, warnings = ic.apply_vibration(text, [1, 2], ic.Vibration(70, 80, True))
    assert ic.read_vibration(out, 1) == ic.Vibration(70, 80, True)
    assert warnings == ["Jogador 2 não usa DualShock 4 nem DualSense no RPCS3"]
    assert "Large Vibration Motor Multiplier: 100" in out.split("Player 2 Input:")[1]

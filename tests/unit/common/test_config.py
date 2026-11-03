# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
import tomllib
from pathlib import Path

import pytest

from ds4_companion.common import config as cfg


def test_defaults_match_configuration_doc() -> None:
    c = cfg.Config()
    assert c.audio.mirror_enabled
    assert c.audio.apps == ["rpcs3", "AppRun.wrapped"]
    assert c.audio.volume_db == -6.0
    assert c.audio.max_db == 0.0
    assert c.audio.headphone_max_db == -6.0
    assert c.vibration.players == [1, 2]
    assert c.led.color == "blue"
    assert c.updates.check_on_start
    assert c.rpcs3.input_file.parts[-3:] == ("input_configs", "global", "Default.yml")


def test_missing_file_uses_defaults(tmp_path: Path) -> None:
    c, warnings = cfg.load(tmp_path / "config.toml")
    assert c == cfg.Config()
    assert warnings == []


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "config.toml"
    c = cfg.Config()
    c.audio.apps = ['jogo "aspas"', "ação"]
    c.audio.volume_db = -12.5
    c.vibration.players = [1, 3]
    c.led.color = "pink"
    cfg.save(c, path)
    loaded, warnings = cfg.load(path)
    assert warnings == []
    assert loaded == c
    tomllib.loads(path.read_text())  # TOML válido


def test_invalid_values_fall_back_with_warning() -> None:
    c, warnings = cfg.from_dict(
        {
            "audio": {"volume_db": "alto", "max_db": 99, "apps": ["", "x"], "mirror_enabled": "sim"},
            "vibration": {"large_percent": 300, "small_percent": True, "players": [0, 9]},
            "led": {"color": "magenta"},
            "rpcs3": {"config_dir": ""},
            "extra": {},
            "ui": [],
        }
    )
    assert c == cfg.Config()
    assert len(warnings) == 11
    assert any("seção desconhecida [extra]" in w for w in warnings)


def test_unknown_key_is_ignored() -> None:
    c, warnings = cfg.from_dict({"audio": {"volume": 1}})
    assert c == cfg.Config()
    assert warnings == ["audio.volume desconhecido, ignorado"]


def test_volume_never_above_ceiling() -> None:
    c, warnings = cfg.from_dict({"audio": {"volume_db": 3.0, "max_db": 0.0, "headphone_max_db": 2.0}})
    assert c.audio.volume_db == 0.0
    assert c.audio.headphone_max_db == 0.0
    assert len(warnings) == 2


def test_apps_are_trimmed_and_deduplicated() -> None:
    assert cfg.validate_apps([" rpcs3 ", "RPCS3", "steam"]) == ["rpcs3", "steam"]
    with pytest.raises(cfg.ConfigError):
        cfg.validate_apps(["a\nb"])
    with pytest.raises(cfg.ConfigError):
        cfg.validate_apps("rpcs3")
    with pytest.raises(cfg.ConfigError):
        cfg.validate_apps([1])


def test_players_are_sorted_unique() -> None:
    assert cfg.validate_players([2, 1, 2]) == [1, 2]
    with pytest.raises(cfg.ConfigError):
        cfg.validate_players("1")


def test_broken_file_is_backed_up(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[audio\nvolume_db = ")
    c, warnings = cfg.load(path)
    assert c == cfg.Config()
    assert "inválido" in warnings[0]
    assert list(tmp_path.glob("config.toml.bak-*"))


def test_unreadable_file(tmp_path: Path) -> None:
    c, warnings = cfg.load(tmp_path)  # diretório: não dá para ler como arquivo
    assert c == cfg.Config()
    assert "não deu para ler" in warnings[0]


def test_default_path_respects_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert cfg.default_path() == tmp_path / "ds4-companion" / "config.toml"


def test_toml_value_rejects_unknown_type() -> None:
    with pytest.raises(TypeError):
        cfg._toml_value(object())


def test_update_check_can_be_turned_off() -> None:
    c, warnings = cfg.from_dict({"updates": {"check_on_start": False}})
    assert warnings == []
    assert not c.updates.check_on_start

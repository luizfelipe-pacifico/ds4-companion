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


def test_apps_accept_patterns_but_not_everything() -> None:
    assert cfg.validate_apps(["*.exe", "wine*"]) == ["*.exe", "wine*"]
    # "*" mandaria todo o som do computador (navegador, chamadas) para o controle.
    for everything in ("*", "**", "?*", "[a-z]*"):
        with pytest.raises(cfg.ConfigError, match="todo o som"):
            cfg.validate_apps([everything])


def test_led_custom_color_and_mode() -> None:
    c, warnings = cfg.from_dict({"led": {"color": "#a1b2c3", "mode": "battery"}})
    assert warnings == []
    assert c.led.color == "#A1B2C3"
    assert c.led.mode == "battery"
    c, warnings = cfg.from_dict({"led": {"color": "#zzzzzz", "mode": "piscar"}})
    assert c.led.color == "blue"
    assert c.led.mode == "fixed"
    assert len(warnings) == 2


PROFILES_TOML = """
[audio]
max_db = 0.0

[profiles.BLUS30001]
title = "Jogo de Teste"
volume_db = -3.0
mirror_enabled = true
large_percent = 150
led_color = "#FF8000"

[profiles.NPEB00002]
mirror_enabled = false
large_percent = 0
small_percent = 0
"""


def test_profiles_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(PROFILES_TOML)
    c, warnings = cfg.load(path)
    assert warnings == []
    fifa = c.profiles["BLUS30001"]
    assert (fifa.title, fifa.volume_db, fifa.mirror_enabled, fifa.large_percent) == ("Jogo de Teste", -3.0, True, 150)
    assert fifa.small_percent is None  # o que o perfil não define vem dos ajustes gerais
    assert fifa.led_color == "#FF8000"
    assert c.profiles["NPEB00002"].mirror_enabled is False
    cfg.save(c, path)
    again, warnings = cfg.load(path)
    assert warnings == []
    assert again.profiles == c.profiles


def test_profile_values_are_validated(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        "[profiles.BLUS30001]\nvolume_db = 4.0\nlarge_percent = 900\ncor = 1\n"
        "[profiles.nao-e-serial]\nvolume_db = -1.0\n"
        '[profiles.BLUS30002]\ntitle = "x\\u001b[31m"\n'
    )
    c, warnings = cfg.load(path)
    assert set(c.profiles) == {"BLUS30001", "BLUS30002"}
    profile = c.profiles["BLUS30001"]
    assert profile.volume_db == 0.0  # nunca acima do teto
    assert profile.large_percent is None
    assert c.profiles["BLUS30002"].title == "x[31m"
    assert any("nao-e-serial" in w for w in warnings)
    assert any("large_percent" in w for w in warnings)
    assert any("profiles.BLUS30001.cor" in w for w in warnings)


def test_profiles_section_must_be_tables(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('profiles = "x"\n[profiles2]\n')
    c, warnings = cfg.load(path)
    assert c.profiles == {}
    assert warnings


def test_led_per_player_option(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[led]\nper_player = true\n")
    c, warnings = cfg.load(path)
    assert c.led.per_player
    assert warnings == []
    path.write_text('[led]\nper_player = "sim"\n')
    c, warnings = cfg.load(path)
    assert not c.led.per_player
    assert warnings


def test_player_colors_follow_ps4() -> None:
    from ds4_companion.common.models import PLAYER_LEDS

    assert [PLAYER_LEDS[n] for n in (1, 2, 3, 4)] == ["blue", "red", "green", "pink"]
    assert set(PLAYER_LEDS) == set(range(1, 8))

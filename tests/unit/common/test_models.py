# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
import pytest

from ds4_companion.common.models import LED_PRESETS, Connection, Status, led_preset


def test_presets_match_roadmap() -> None:
    table = {p.id: p.hex for p in LED_PRESETS}
    assert table == {
        "blue": "#0000FF",
        "red": "#FF0000",
        "green": "#00FF00",
        "pink": "#FF1493",
        "purple": "#8000FF",
        "cyan": "#00FFFF",
        "orange": "#FF8000",
        "white": "#FFFFFF",
        "off": "#000000",
    }


@pytest.mark.parametrize(("name", "expected"), [("azul", "blue"), ("Rosa", "pink"), ("RED", "red")])
def test_led_aliases(name: str, expected: str) -> None:
    assert led_preset(name).id == expected


def test_unknown_led() -> None:
    with pytest.raises(KeyError):
        led_preset("magenta")


def test_status_round_trip() -> None:
    status = Status(connection=Connection.USB, battery=80, players=[1, 2], volume_db=-3.0)
    assert Status.from_mapping(status.to_dict()) == status
    assert status.connected
    assert status.led_hex == "#0000FF"


def test_status_ignores_wrong_types_and_unknown_keys() -> None:
    status = Status.from_mapping(
        {"battery": "80", "charging": 1, "volume_db": 2, "apps": ("rpcs3",), "x": 1, "connection": 3}
    )
    assert status.battery == -1
    assert status.charging is False
    assert status.volume_db == 2.0
    assert status.apps == ["rpcs3"]
    assert status.connection == Connection.NONE
    assert not status.connected


def test_status_bad_led_falls_back() -> None:
    assert Status(led_color="nope").led_hex == "#0000FF"

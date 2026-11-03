# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Tipos compartilhados entre daemon, CLI e GUI."""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Connection(StrEnum):
    NONE = "none"
    USB = "usb"
    BLUETOOTH = "bluetooth"


class Model(StrEnum):
    """Família do controle: muda o formato dos relatórios HID e o handler do RPCS3."""

    DS4 = "ds4"
    DUALSENSE = "dualsense"


class Motor(StrEnum):
    STRONG = "strong"
    WEAK = "weak"
    BOTH = "both"


@dataclass(frozen=True)
class LedPreset:
    id: str
    rgb: tuple[int, int, int]

    @property
    def hex(self) -> str:
        return "#{:02X}{:02X}{:02X}".format(*self.rgb)


# Cores do ROADMAP (Fase 2): o RGB é o que vai no relatório HID, não a cor do tema.
LED_PRESETS: tuple[LedPreset, ...] = (
    LedPreset("blue", (0x00, 0x00, 0xFF)),
    LedPreset("red", (0xFF, 0x00, 0x00)),
    LedPreset("green", (0x00, 0xFF, 0x00)),
    LedPreset("pink", (0xFF, 0x14, 0x93)),
    LedPreset("purple", (0x80, 0x00, 0xFF)),
    LedPreset("cyan", (0x00, 0xFF, 0xFF)),
    LedPreset("orange", (0xFF, 0x80, 0x00)),
    LedPreset("white", (0xFF, 0xFF, 0xFF)),
    LedPreset("off", (0x00, 0x00, 0x00)),
)
DEFAULT_LED = "blue"

# Nomes aceitos pela CLI em português.
LED_ALIASES = {
    "azul": "blue",
    "vermelho": "red",
    "verde": "green",
    "rosa": "pink",
    "roxo": "purple",
    "ciano": "cyan",
    "laranja": "orange",
    "branco": "white",
    "desligada": "off",
    "desligado": "off",
}


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
LED_MODES = ("fixed", "battery")
BATTERY_LOW = 20
BATTERY_MID = 50
BATTERY_LOW_RGB = (0xFF, 0x00, 0x00)
BATTERY_MID_RGB = (0xFF, 0x80, 0x00)


def led_preset(color_id: str) -> LedPreset:
    """Cor pelo nome (pt ou en) ou personalizada em `#RRGGBB`."""
    if HEX_COLOR.match(color_id):
        value = color_id.upper()
        return LedPreset(value, (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)))
    key = LED_ALIASES.get(color_id.casefold(), color_id.casefold())
    for preset in LED_PRESETS:
        if preset.id == key:
            return preset
    raise KeyError(color_id)


def led_rgb(color_id: str, mode: str = "fixed", battery: int = -1) -> tuple[int, int, int]:
    """A cor que vai para o controle. No modo bateria: laranja abaixo de 50 %, vermelha abaixo de 20 %."""
    try:
        base = led_preset(color_id).rgb
    except KeyError:
        base = led_preset(DEFAULT_LED).rgb
    if mode != "battery" or battery < 0:
        return base
    if battery < BATTERY_LOW:
        return BATTERY_LOW_RGB
    if battery < BATTERY_MID:
        return BATTERY_MID_RGB
    return base


@dataclass
class Status:
    """Retrato do estado do daemon, transportado como `a{sv}` no D-Bus."""

    connection: str = Connection.NONE
    controller_name: str = ""
    controller_model: str = ""
    battery: int = -1
    charging: bool = False
    hid_access: bool = True
    headphones: bool = False
    rpcs3_running: bool = False
    game_serial: str = ""
    """Jogo aberto no RPCS3 (ID do PS3, ex.: BLUS30001), lido do RPCS3.log."""
    game_title: str = ""
    game_running: bool = False
    mirror_enabled: bool = True
    mirror_active: bool = False
    sink_present: bool = False
    volume_db: float = -6.0
    max_db: float = 0.0
    configured_max_db: float = 0.0
    output_name: str = ""
    apps: list[str] = field(default_factory=list)
    playing: list[str] = field(default_factory=list)
    limiter: bool = True
    limiter_active: bool = False
    """Apps tocando som agora (dado do PipeWire), para a interface sugerir."""
    large_percent: int = 100
    small_percent: int = 100
    swap_motors: bool = False
    players: list[int] = field(default_factory=list)
    vibration_pending: bool = False
    led_color: str = DEFAULT_LED
    led_mode: str = "fixed"
    rpcs3_config_dir: str = ""
    backup_before_edit: bool = True
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Status:
        """Lê só os campos conhecidos e com o tipo certo; o resto fica no padrão."""
        defaults = cls()
        values: dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            expected = getattr(defaults, f.name)
            if isinstance(expected, bool):
                ok = isinstance(value, bool)
            elif isinstance(expected, float):
                ok = isinstance(value, int | float) and not isinstance(value, bool)
                value = float(value) if ok else value
            elif isinstance(expected, int):
                ok = isinstance(value, int) and not isinstance(value, bool)
            elif isinstance(expected, list):
                ok = isinstance(value, list | tuple)
                value = list(value) if ok else value
            else:
                ok = isinstance(value, str)
            if ok:
                values[f.name] = value
        return cls(**values)

    @property
    def connected(self) -> bool:
        return self.connection != Connection.NONE

    @property
    def led_hex(self) -> str:
        """A cor real no controle agora (com o modo bateria aplicado)."""
        return "#{:02X}{:02X}{:02X}".format(*led_rgb(self.led_color, self.led_mode, self.battery))

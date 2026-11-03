# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Detecção do DualShock 4 e do DualSense (cabo ↔ Bluetooth) e da bateria pelo udev.

Propriedades do udev são dados não confiáveis: só números do HID_ID são usados para decidir algo,
e o nome da bateria (que contém o MAC) nunca vai para o log sem `redact`.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.models import Connection, Model

log = logging.getLogger(__name__)

SONY_VENDOR = 0x054C
PRODUCTS: dict[int, tuple[str, Model]] = {
    0x05C4: ("DualShock 4", Model.DS4),
    0x09CC: ("DualShock 4", Model.DS4),
    0x0BA0: ("DualShock 4 (adaptador sem fio)", Model.DS4),
    0x0CE6: ("DualSense", Model.DUALSENSE),
    0x0DF2: ("DualSense Edge", Model.DUALSENSE),
}
WIRELESS_ADAPTER = 0x0BA0
EDGE_PRODUCT = 0x0DF2  # o Edge sempre usa a vibração v2
BUS_USB = 0x0003
BUS_BLUETOOTH = 0x0005

_MAC = re.compile(r"(?:[0-9A-Fa-f]{2}[:_-]){5}([0-9A-Fa-f]{2})")


@dataclass(frozen=True)
class Controller:
    hidraw: str
    connection: Connection
    product: int
    battery_dir: str | None = None

    @property
    def name(self) -> str:
        return PRODUCTS.get(self.product, ("DualShock 4", Model.DS4))[0]

    @property
    def model(self) -> Model:
        return PRODUCTS.get(self.product, ("DualShock 4", Model.DS4))[1]


def parse_hid_id(value: str) -> tuple[int, int, int] | None:
    """`HID_ID=0003:0000054C:000009CC` → (bus, fabricante, produto)."""
    parts = value.strip().split(":")
    if len(parts) != 3:
        return None
    try:
        bus, vendor, product = (int(p, 16) for p in parts)
    except ValueError:
        return None
    return bus, vendor, product


def classify(hid_id: str) -> tuple[Connection, int] | None:
    parsed = parse_hid_id(hid_id)
    if parsed is None:
        return None
    bus, vendor, product = parsed
    if vendor != SONY_VENDOR or product not in PRODUCTS:
        return None
    # O adaptador sem fio é USB para o kernel, mas o controle fala com ele por rádio.
    if bus == BUS_USB and product != WIRELESS_ADAPTER:
        return Connection.USB, product
    if bus in (BUS_BLUETOOTH, BUS_USB):
        return Connection.BLUETOOTH, product
    return None


def pick(controllers: Iterable[Controller]) -> Controller | None:
    """Com mais de um controle, prefere o do cabo (é o único com áudio)."""
    ordered = sorted(controllers, key=lambda c: (c.connection != Connection.USB, c.hidraw))
    return ordered[0] if ordered else None


def read_battery(battery_dir: str | None) -> tuple[int, bool]:
    """(porcentagem, carregando). -1 quando não dá para ler."""
    if not battery_dir:
        return -1, False
    base = Path(battery_dir)
    try:
        capacity = int((base / "capacity").read_text().strip())
        status = (base / "status").read_text().strip()
    except (OSError, ValueError):
        return -1, False
    return min(max(capacity, 0), 100), status in ("Charging", "Full")


def redact(text: str) -> str:
    """Esconde MACs: só o último byte aparece no log."""
    return _MAC.sub(lambda m: "XX:XX:XX:XX:XX:" + m.group(1), text)


class DeviceMonitor:
    """Lista os controles e avisa (`on_change`) quando um conecta, desconecta ou muda a bateria."""

    def __init__(self, context: Any = None) -> None:
        if context is None:
            import pyudev

            context = pyudev.Context()
        self._context = context
        self._monitor: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def scan(self) -> list[Controller]:
        found = []
        for dev in self._context.list_devices(subsystem="hidraw"):
            parent = dev.find_parent("hid")
            if parent is None or dev.device_node is None:
                continue
            kind = classify(str(parent.properties.get("HID_ID", "")))
            if kind is None:
                continue
            batteries = sorted(Path(parent.sys_path, "power_supply").glob("*"))
            battery = str(batteries[0]) if batteries else None
            found.append(Controller(str(dev.device_node), kind[0], kind[1], battery))
        return found

    def start(self, loop: asyncio.AbstractEventLoop, on_change: Callable[[], None]) -> None:
        import pyudev

        monitor = pyudev.Monitor.from_netlink(self._context)
        monitor.filter_by("hidraw")
        monitor.filter_by("power_supply")
        monitor.start()

        def ready() -> None:
            changed = False
            while monitor.poll(timeout=0) is not None:
                changed = True
            if changed:
                on_change()

        loop.add_reader(monitor.fileno(), ready)
        self._monitor = monitor
        self._loop = loop

    def stop(self) -> None:
        if self._monitor is not None and self._loop is not None:
            self._loop.remove_reader(self._monitor.fileno())
            self._monitor = None

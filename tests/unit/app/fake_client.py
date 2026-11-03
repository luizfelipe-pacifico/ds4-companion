# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Cliente falso com a mesma interface do DaemonClient, para testes e capturas de tela."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gi.repository import GObject

from ds4_companion.common.models import Connection, Status

Done = Callable[[str | None, str, Any], None]


def sample(**changes: Any) -> Status:
    """Controle por cabo, RPCS3 fechado, espelhamento ligado: o caso comum."""
    base = Status(
        connection=Connection.USB,
        controller_name="DualShock 4",
        battery=80,
        charging=True,
        sink_present=True,
        volume_db=-6.0,
        max_db=0.0,
        configured_max_db=0.0,
        output_name="Monitor HDMI",
        apps=["rpcs3", "AppRun.wrapped"],
        players=[1, 2],
        rpcs3_config_dir="~/.config/rpcs3",
    )
    for key, value in changes.items():
        setattr(base, key, value)
    return base


class FakeClient(GObject.Object):
    __gsignals__ = {  # noqa: RUF012
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "availability-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self) -> None:
        super().__init__()
        self.status = sample()
        self.available = False
        self.calls: list[tuple[Any, ...]] = []
        self.errors: dict[str, tuple[str, str]] = {}
        self.results: dict[str, Any] = {}  # valor devolvido por método (ex.: GetProfiles)

    def set_available(self, available: bool) -> None:
        self.available = available
        self.emit("availability-changed", available)

    def push(self, status: Status) -> None:
        self.status = status
        self.emit("status-changed", status)

    def call(self, method: str, *args: Any, done: Done | None = None) -> None:
        self.calls.append((method, *args))
        if method in self.errors:
            code, message = self.errors[method]
            if done:
                done(code, message, None)
            return
        if done:
            done(None, "", self.results.get(method, args[0] if method == "SetVolume" else None))

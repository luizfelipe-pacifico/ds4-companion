# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Interface D-Bus do daemon (ADR 0008). As anotações são assinaturas D-Bus, não tipos Python."""

from typing import Any

from dbus_next.constants import PropertyAccess
from dbus_next.errors import DBusError
from dbus_next.service import ServiceInterface, dbus_property, method
from dbus_next.signature import Variant

from .. import __version__
from ..common.models import Status
from ..common.names import INTERFACE
from .service import Daemon, DaemonError

ERROR_PREFIX = f"{INTERFACE}.Error."


def to_variant(value: Any) -> Variant:
    if isinstance(value, bool):
        return Variant("b", value)
    if isinstance(value, int):
        return Variant("i", value)
    if isinstance(value, float):
        return Variant("d", value)
    if isinstance(value, str):
        return Variant("s", value)
    if isinstance(value, list) and all(isinstance(v, int) and not isinstance(v, bool) for v in value) and value:
        return Variant("ai", value)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return Variant("as", value)
    raise TypeError(f"sem tipo D-Bus para {value!r}")


def status_variants(status: Status) -> dict[str, Variant]:
    data = status.to_dict()
    if not data["players"]:
        data["players"] = []
    result = {k: to_variant(v) for k, v in data.items() if k != "players"}
    result["players"] = Variant("ai", list(data["players"]))
    return result


def _error(exc: DaemonError) -> DBusError:
    return DBusError(ERROR_PREFIX + exc.code, str(exc))


class DaemonInterface(ServiceInterface):
    def __init__(self, daemon: Daemon) -> None:
        super().__init__(INTERFACE)
        self._daemon = daemon
        daemon.subscribe(self._changed)

    def _changed(self, status: Status) -> None:
        self.emit_properties_changed({"Status": status_variants(status)})

    @dbus_property(access=PropertyAccess.READ)
    def Status(self) -> "a{sv}":
        return status_variants(self._daemon.status)

    @dbus_property(access=PropertyAccess.READ)
    def Version(self) -> "s":
        return __version__

    @method()
    async def Refresh(self) -> None:
        await self._daemon.refresh()

    @method()
    async def SetMirror(self, enabled: "b") -> None:
        await self._call(self._daemon.set_mirror(enabled))

    @method()
    async def SetVolume(self, db: "d", confirm: "b") -> "d":
        result: float = await self._call(self._daemon.set_volume(db, confirm))
        return result

    @method()
    async def SetLimiter(self, enabled: "b") -> None:
        await self._call(self._daemon.set_limiter(enabled))

    @method()
    async def SetVibration(self, large: "u", small: "u", swap: "b") -> None:
        await self._call(self._daemon.set_vibration(large, small, swap))

    @method()
    async def SetPlayers(self, players: "ai") -> None:
        await self._call(self._daemon.set_players(list(players)))

    @method()
    async def TestRumble(self, motor: "s") -> None:
        await self._call(self._daemon.test_rumble(motor))

    @method()
    async def SetLed(self, color: "s") -> None:
        await self._call(self._daemon.set_led(color))

    @method()
    async def SetLedMode(self, mode: "s") -> None:
        await self._call(self._daemon.set_led_mode(mode))

    @method()
    async def PlayTestTone(self) -> None:
        await self._call(self._daemon.play_test_tone())

    @method()
    async def SetApps(self, apps: "as") -> None:
        await self._call(self._daemon.set_apps(list(apps)))

    @method()
    async def SetRpcs3Dir(self, path: "s") -> None:
        await self._call(self._daemon.set_rpcs3_dir(path))

    @method()
    async def SetBackup(self, enabled: "b") -> None:
        await self._call(self._daemon.set_backup(enabled))

    @method()
    async def RestoreDefaults(self) -> None:
        await self._call(self._daemon.restore_defaults())

    @method()
    def GetProfiles(self) -> "a{sa{sv}}":
        return {
            serial: {key: to_variant(value) for key, value in values.items()}
            for serial, values in self._daemon.get_profiles().items()
        }

    @method()
    async def SetProfile(self, serial: "s", values: "a{sv}", confirm: "b") -> None:
        plain = {key: variant.value for key, variant in values.items()}
        await self._call(self._daemon.set_profile(serial, plain, confirm))

    @method()
    async def DeleteProfile(self, serial: "s") -> None:
        await self._call(self._daemon.delete_profile(serial))

    @staticmethod
    async def _call(awaitable: Any) -> Any:
        try:
            return await awaitable
        except DaemonError as exc:
            raise _error(exc) from exc

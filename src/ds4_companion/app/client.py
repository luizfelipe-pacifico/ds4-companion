# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Cliente D-Bus da GUI: `Gio.DBusProxy` no laço do GTK (ADR 0008). A GUI não tem lógica de
negócio; cada ação vira uma chamada ao daemon e o estado volta pelo sinal PropertiesChanged."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gi.repository import Gio, GLib, GObject

from ..common.models import Status
from ..common.names import BUS_NAME, INTERFACE, OBJECT_PATH

log = logging.getLogger(__name__)

Done = Callable[[str | None, str, Any], None]
"""Retorno de uma chamada: (código do erro ou None, mensagem, valor)."""

ERROR_PREFIX = f"{INTERFACE}.Error."

# Assinatura de cada método, para montar o GLib.Variant.
SIGNATURES = {
    "Refresh": "()",
    "SetMirror": "(b)",
    "SetLimiter": "(b)",
    "SetVolume": "(db)",
    "SetVibration": "(uub)",
    "SetPlayers": "(ai)",
    "TestRumble": "(s)",
    "SetLed": "(s)",
    "SetLedMode": "(s)",
    "PlayTestTone": "()",
    "SetApps": "(as)",
    "SetRpcs3Dir": "(s)",
    "SetBackup": "(b)",
    "RestoreDefaults": "()",
}


def parse_error(error: GLib.Error) -> tuple[str, str]:
    """(código curto, mensagem para o usuário) de um erro D-Bus remoto."""
    remote = Gio.DBusError.get_remote_error(error) or ""
    # Gio.DBusError.strip_remote_error mexe na cópia em C, não no GLib.Error do Python:
    # o prefixo "GDBus.Error:<nome>: " sai aqui.
    message = error.message.removeprefix(f"GDBus.Error:{remote}: ") if remote else error.message
    code = remote.removeprefix(ERROR_PREFIX) if remote.startswith(ERROR_PREFIX) else "Failed"
    return code, message


class DaemonClient(GObject.Object):
    """Sinais: `status-changed(Status)` e `availability-changed(bool)`."""

    __gsignals__ = {  # noqa: RUF012 - formato exigido pelo PyGObject
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "availability-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self) -> None:
        super().__init__()
        self.status = Status()
        self.available = False
        self._proxy: Gio.DBusProxy | None = None

    def connect_bus(self) -> None:
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.DO_NOT_AUTO_START,
            None,
            BUS_NAME,
            OBJECT_PATH,
            INTERFACE,
            None,
            self._on_proxy,
        )

    def _on_proxy(self, _source: object, result: Gio.AsyncResult) -> None:
        try:
            self._proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error as exc:
            log.warning("sem D-Bus de sessão: %s", exc.message)
            self._set_available(False)
            return
        self._proxy.connect("g-properties-changed", self._on_properties)
        self._proxy.connect("notify::g-name-owner", lambda *_: self._sync_owner())
        self._sync_owner()

    def _sync_owner(self) -> None:
        owner = self._proxy.get_name_owner() if self._proxy else None
        self._set_available(owner is not None)
        if owner is not None:
            self._read_status()

    def _read_status(self) -> None:
        if self._proxy is None:
            return
        value = self._proxy.get_cached_property("Status")
        if value is None:
            # Logo depois de o daemon subir, o cache ainda está vazio: lê direto.
            self.call("Refresh")
            return
        self._emit_status(value.unpack())

    def _on_properties(self, _proxy: Gio.DBusProxy, changed: GLib.Variant, _invalid: list[str]) -> None:
        data = changed.unpack()
        if "Status" in data:
            self._emit_status(data["Status"])

    def _emit_status(self, data: dict[str, Any]) -> None:
        self.status = Status.from_mapping(data)
        self.emit("status-changed", self.status)

    def _set_available(self, available: bool) -> None:
        if available != self.available:
            self.available = available
            self.emit("availability-changed", available)

    def call(self, method: str, *args: Any, done: Done | None = None) -> None:
        if self._proxy is None or not self.available:
            if done:
                done("NotRunning", "O serviço não está rodando.", None)
            return
        params = GLib.Variant(SIGNATURES[method], args) if args else None

        def finished(proxy: Gio.DBusProxy, result: Gio.AsyncResult) -> None:
            try:
                value = proxy.call_finish(result).unpack()
            except GLib.Error as exc:
                code, message = parse_error(exc)
                log.info("%s: %s", method, message)
                if done:
                    done(code, message, None)
                return
            if method == "Refresh":
                cached = proxy.get_cached_property("Status")
                if cached is not None:
                    self._emit_status(cached.unpack())
            if done:
                done(None, "", value[0] if value else None)

        self._proxy.call(method, params, Gio.DBusCallFlags.NONE, 10_000, None, finished)

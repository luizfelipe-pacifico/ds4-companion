# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Ícone na bandeja pelo protocolo StatusNotifierItem (extensão AppIndicator no GNOME, KDE…).

Feito direto no D-Bus com Gio, sem biblioteca extra. Sem o StatusNotifierWatcher na sessão (GNOME
sem a extensão), `start` devolve False e o app segue sem bandeja.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from gettext import gettext as _

from gi.repository import Gio, GLib

from ..common.db import format_db
from ..common.models import Connection, Status
from ..common.names import APP_ID

log = logging.getLogger(__name__)

WATCHER_NAME = "org.kde.StatusNotifierWatcher"
WATCHER_PATH = "/StatusNotifierWatcher"
ITEM_PATH = "/StatusNotifierItem"
ITEM_IFACE = "org.kde.StatusNotifierItem"

ITEM_XML = f"""
<node>
  <interface name="{ITEM_IFACE}">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionMovieName" type="s" access="read"/>
    <method name="Activate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/><arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewToolTip"/>
    <signal name="NewStatus"><arg name="status" type="s"/></signal>
  </interface>
</node>
"""


def tooltip_text(s: Status) -> str:
    if s.connection == Connection.NONE:
        return _("Nenhum controle conectado")
    parts = [_("Cabo USB") if s.connection == Connection.USB else _("Bluetooth")]
    if s.battery >= 0:
        parts.append(_("bateria {level} %").format(level=s.battery))
    if s.mirror_active:
        parts.append(_("som no controle a {db}").format(db=format_db(s.volume_db)))
    return " · ".join(parts)


class TrayIcon:
    def __init__(
        self,
        on_activate: Callable[[], None],
        *,
        bus: Gio.DBusConnection | None = None,
        watcher: str = WATCHER_NAME,
    ) -> None:
        self._on_activate = on_activate
        self._bus = bus
        self._watcher = watcher
        self._registration = 0
        self.tooltip = _("DS4 Companion")
        self.active = False
        self.name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"

    def start(self) -> bool:
        """Registra o ícone. False se não houver bandeja na sessão.

        Só fala de forma síncrona com o próprio barramento (que responde na hora); o pedido ao
        watcher é assíncrono para uma bandeja lenta nunca travar a abertura da janela.
        """
        try:
            bus = self._bus or Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._bus = bus
            if not self._bus_call("NameHasOwner", GLib.Variant("(s)", (self._watcher,))).unpack()[0]:
                log.info("sem bandeja na sessão (%s); seguindo sem ícone", self._watcher)
                return False
            info = Gio.DBusNodeInfo.new_for_xml(ITEM_XML).interfaces[0]
            self._registration = bus.register_object(ITEM_PATH, info, self._on_call, self._on_get, None)
            self._bus_call("RequestName", GLib.Variant("(su)", (self.name, 0)))
        except GLib.Error as exc:
            log.info("sem bandeja na sessão (%s); seguindo sem ícone", exc.message)
            self.stop()
            return False
        bus.call(
            self._watcher,
            WATCHER_PATH,
            WATCHER_NAME,
            "RegisterStatusNotifierItem",
            # Pelo nome único da conexão: a extensão AppIndicator do GNOME recusa o nome
            # bem-conhecido e o caminho do objeto ("Invalid element in string array").
            GLib.Variant("(s)", (bus.get_unique_name(),)),
            None,
            Gio.DBusCallFlags.NO_AUTO_START,
            5000,
            None,
            self._on_registered,
        )
        self.active = True
        return True

    def _bus_call(self, method: str, params: GLib.Variant) -> GLib.Variant:
        assert self._bus is not None  # noqa: S101 - só chamado depois de obter o barramento
        return self._bus.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            method,
            params,
            None,
            Gio.DBusCallFlags.NONE,
            2000,
            None,
        )

    def _on_registered(self, bus: Gio.DBusConnection, result: Gio.AsyncResult) -> None:
        # Só avisa: a extensão AppIndicator do GNOME põe o ícone no painel e só depois pode
        # falhar ao anunciar a lista de itens (por causa de item quebrado de outro app).
        # Tirar o objeto aqui apagaria um ícone que já está à vista.
        try:
            bus.call_finish(result)
        except GLib.Error as exc:
            log.warning("a bandeja respondeu com erro ao registrar o ícone: %s", exc.message)

    def stop(self) -> None:
        if self._bus is not None and self._registration:
            self._bus.unregister_object(self._registration)
        self._registration = 0
        self.active = False

    def update(self, status: Status) -> None:
        text = tooltip_text(status)
        if text != self.tooltip:
            self.tooltip = text
            self._emit("NewToolTip", None)

    def _emit(self, signal: str, params: GLib.Variant | None) -> None:
        if self._bus is not None and self.active:
            self._bus.emit_signal(None, ITEM_PATH, ITEM_IFACE, signal, params)

    def _on_get(self, _bus: object, _sender: str, _path: str, _iface: str, prop: str) -> GLib.Variant | None:
        values = {
            "Category": GLib.Variant("s", "Hardware"),
            "Id": GLib.Variant("s", "ds4-companion"),
            "Title": GLib.Variant("s", "DS4 Companion"),
            "Status": GLib.Variant("s", "Active"),
            "IconName": GLib.Variant("s", f"{APP_ID}-symbolic"),
            "ToolTip": GLib.Variant("(sa(iiay)ss)", (f"{APP_ID}-symbolic", [], "DS4 Companion", self.tooltip)),
            "ItemIsMenu": GLib.Variant("b", False),
            # O resto do protocolo, vazio: algumas bandejas (AppIndicator do GNOME) leem tudo.
            "WindowId": GLib.Variant("i", 0),
            "IconThemePath": GLib.Variant("s", ""),
            "Menu": GLib.Variant("o", "/NO_DBUSMENU"),
            "IconPixmap": GLib.Variant("a(iiay)", []),
            "OverlayIconName": GLib.Variant("s", ""),
            "OverlayIconPixmap": GLib.Variant("a(iiay)", []),
            "AttentionIconName": GLib.Variant("s", ""),
            "AttentionIconPixmap": GLib.Variant("a(iiay)", []),
            "AttentionMovieName": GLib.Variant("s", ""),
        }
        return values.get(prop)

    def _on_call(
        self,
        _bus: object,
        _sender: str,
        _path: str,
        _iface: str,
        method: str,
        _params: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        if method in ("Activate", "SecondaryActivate", "ContextMenu"):
            self._on_activate()
        invocation.return_value(None)

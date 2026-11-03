# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import spin, spin_until
from fake_client import FakeClient, sample
from gi.repository import Gio, GLib

from ds4_companion.app import tray
from ds4_companion.common.models import Connection

# Nome de teste: nunca disputa com a bandeja real da sessão.
FAIL_AFTER_ADDING: list[bool] = []
FAKE_WATCHER = f"io.github.luizfelipe_pacifico.TesteWatcher{os.getpid()}"
WATCHER_XML = """
<node><interface name="org.kde.StatusNotifierWatcher">
  <method name="RegisterStatusNotifierItem"><arg name="service" type="s" direction="in"/></method>
</interface></node>
"""


@pytest.fixture
def bus() -> Gio.DBusConnection:
    try:
        return Gio.bus_get_sync(Gio.BusType.SESSION, None)
    except GLib.Error:
        pytest.skip("sem D-Bus de sessão")


@pytest.fixture
def watcher(bus: Gio.DBusConnection) -> Iterator[list[str]]:
    registered: list[str] = []
    info = Gio.DBusNodeInfo.new_for_xml(WATCHER_XML).interfaces[0]

    def on_call(*args: Any) -> None:
        method, params, invocation = args[4], args[5], args[6]
        if method == "RegisterStatusNotifierItem":
            registered.append(params.unpack()[0])
            if FAIL_AFTER_ADDING and FAIL_AFTER_ADDING[-1]:
                # Como a extensão AppIndicator do GNOME: põe o ícone no painel e depois falha ao
                # anunciar a lista de itens por causa de um item quebrado de outro app.
                invocation.return_dbus_error("org.gnome.gjs.JSError.ValueError", "Invalid element in string array")
                return
        invocation.return_value(None)

    reg = bus.register_object(tray.WATCHER_PATH, info, on_call, None, None)
    owner = Gio.bus_own_name_on_connection(bus, FAKE_WATCHER, Gio.BusNameOwnerFlags.NONE, None, None)
    spin(0.2)
    yield registered
    Gio.bus_unown_name(owner)
    bus.unregister_object(reg)


def _call(bus: Gio.DBusConnection, iface: str, method: str, params: GLib.Variant | None) -> Any:
    """Chamada assíncrona + laço girando: o objeto é deste mesmo processo, call_sync travaria."""
    box: list[Any] = []
    bus.call(
        bus.get_unique_name(),
        tray.ITEM_PATH,
        iface,
        method,
        params,
        None,
        0,
        2000,
        None,
        lambda b, r: box.append(b.call_finish(r)),
    )
    assert spin_until(lambda: box)
    return box[0]


def call_item(bus: Gio.DBusConnection, method: str, params: GLib.Variant | None) -> Any:
    return _call(bus, tray.ITEM_IFACE, method, params)


def get_prop(bus: Gio.DBusConnection, name: str) -> Any:
    params = GLib.Variant("(ss)", (tray.ITEM_IFACE, name))
    return _call(bus, "org.freedesktop.DBus.Properties", "Get", params).unpack()[0]


def test_tooltip_text() -> None:
    assert tray.tooltip_text(sample(connection=Connection.NONE)) == "Nenhum controle conectado"
    text = tray.tooltip_text(sample(mirror_active=True, volume_db=-6.0))
    assert text == "Cabo USB · bateria 80 % · som no controle a −6 dB"
    assert tray.tooltip_text(sample(connection=Connection.BLUETOOTH, battery=-1)) == "Bluetooth"


def test_registers_answers_and_activates(bus: Gio.DBusConnection, watcher: list[str]) -> None:
    opened: list[int] = []
    icon = tray.TrayIcon(lambda: opened.append(1), bus=bus, watcher=FAKE_WATCHER)
    assert icon.start()
    assert spin_until(lambda: watcher)
    assert watcher == [bus.get_unique_name()]

    assert get_prop(bus, "Id") == "ds4-companion"
    assert get_prop(bus, "IconName").endswith("-symbolic")
    icon.update(sample(mirror_active=True))
    assert "som no controle" in get_prop(bus, "ToolTip")[3]
    icon.update(sample(mirror_active=True))  # sem mudança, sem sinal novo

    call_item(bus, "Activate", GLib.Variant("(ii)", (0, 0)))
    call_item(bus, "Scroll", GLib.Variant("(is)", (1, "vertical")))
    assert opened == [1]
    icon.stop()
    assert not icon.active


def test_without_watcher_there_is_no_tray(bus: Gio.DBusConnection) -> None:
    icon = tray.TrayIcon(lambda: None, bus=bus, watcher="io.github.luizfelipe_pacifico.NinguemAqui")
    assert not icon.start()
    assert not icon.active
    icon.update(sample())  # não quebra sem bandeja


def test_application_with_tray(
    bus: Gio.DBusConnection, watcher: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ds4_companion.app.application import Application

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "ds4-companion").mkdir()
    (tmp_path / "ds4-companion" / "config.toml").write_text(
        "[ui]\nstart_minimized = true\n[updates]\ncheck_on_start = false\n"
    )
    client = FakeClient()
    app = Application(client_factory=lambda: client)
    app._tray_options = {"bus": bus, "watcher": FAKE_WATCHER}
    app.set_application_id("io.github.luizfelipe_pacifico.DS4CompanionTesteBandeja")
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    app.activate()
    window = app.get_windows()[0]
    assert app.tray.active  # type: ignore[attr-defined]
    assert window.get_hide_on_close()
    assert not window.get_visible()  # começou minimizado na bandeja
    client.push(sample(mirror_active=True))
    assert "som no controle" in app.tray.tooltip  # type: ignore[attr-defined]
    app.activate()  # clicar no atalho de novo traz a janela escondida
    assert window.get_visible()
    app.tray.stop()  # type: ignore[attr-defined]
    window.destroy()


def test_host_error_after_adding_keeps_icon(bus: Gio.DBusConnection, watcher: list[str]) -> None:
    # Regressão: o erro da extensão do GNOME vinha depois de o ícone já estar no painel, e o app
    # removia o próprio ícone ao tratar isso como recusa.
    FAIL_AFTER_ADDING.append(True)
    try:
        icon = tray.TrayIcon(lambda: None, bus=bus, watcher=FAKE_WATCHER)
        assert icon.start()
        assert spin_until(lambda: watcher)
        spin(0.3)
        assert icon.active
        icon.stop()
    finally:
        FAIL_AFTER_ADDING.clear()

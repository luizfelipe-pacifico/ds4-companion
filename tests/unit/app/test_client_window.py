# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import spin, spin_until
from fake_client import FakeClient, sample
from gi.repository import Adw, Gio

from ds4_companion.app import client as client_mod
from ds4_companion.app.window import Window
from ds4_companion.common.models import Connection, Status

sys.path.insert(0, str(Path(__file__).parents[1] / "daemon"))

TEST_BUS = "io.github.luizfelipe_pacifico.DS4Companion.DaemonTeste"


@pytest.fixture
def daemon_on_bus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """A interface D-Bus verdadeira do daemon (com hardware falso) sob um nome de teste."""
    from test_service import Env

    from ds4_companion.daemon.dbus import DaemonInterface

    env = Env(tmp_path)
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    holder: dict[str, Any] = {}

    async def serve() -> None:
        from dbus_next.aio.message_bus import MessageBus

        from ds4_companion.common.names import OBJECT_PATH

        try:
            bus = await MessageBus().connect()
        except Exception as exc:
            holder["error"] = exc
            ready.set()
            return
        bus.export(OBJECT_PATH, DaemonInterface(env.daemon))
        await env.daemon.refresh()
        await bus.request_name(TEST_BUS)
        holder["bus"] = bus
        ready.set()

    thread = threading.Thread(target=lambda: (loop.run_until_complete(serve()), loop.run_forever()), daemon=True)
    thread.start()
    ready.wait(10)
    if "error" in holder:
        pytest.skip(f"sem D-Bus de sessão: {holder['error']}")
    monkeypatch.setattr(client_mod, "BUS_NAME", TEST_BUS)
    yield env
    loop.call_soon_threadsafe(holder["bus"].disconnect)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(5)


def test_client_against_real_interface(daemon_on_bus: Any) -> None:
    c = client_mod.DaemonClient()
    statuses: list[Status] = []
    c.connect("status-changed", lambda _c, s: statuses.append(s))
    c.connect_bus()
    assert spin_until(lambda: c.available and statuses)
    assert statuses[-1].connection == Connection.USB

    results: list[tuple[Any, ...]] = []
    c.call("SetVolume", -9.0, False, done=lambda *r: results.append(r))
    assert spin_until(lambda: results)
    assert results[-1] == (None, "", -9.0)
    assert spin_until(lambda: abs(c.status.volume_db + 9.0) < 0.05)

    c.call("SetLed", "magenta", done=lambda *r: results.append(r))
    assert spin_until(lambda: len(results) == 2)
    assert results[-1][0] == "InvalidArgument"
    assert "magenta" in results[-1][1]

    c.call("SetVibration", 120, 80, True)
    c.call("Refresh", done=lambda *r: results.append(r))
    assert spin_until(lambda: len(results) == 3)
    assert spin_until(lambda: c.status.large_percent == 120)


def test_client_without_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_mod, "BUS_NAME", "io.github.luizfelipe_pacifico.NinguemAqui")
    c = client_mod.DaemonClient()
    c.connect_bus()
    spin(0.3)
    assert not c.available
    got: list[tuple[Any, ...]] = []
    c.call("Refresh", done=lambda *r: got.append(r))
    assert got[0][0] == "NotRunning"


def test_parse_error() -> None:
    err = Gio.DBusError.new_for_dbus_error(f"{client_mod.ERROR_PREFIX}Busy", "Espere.")
    assert client_mod.parse_error(err) == ("Busy", "Espere.")
    other = Gio.DBusError.new_for_dbus_error("org.freedesktop.DBus.Error.Failed", "x")
    assert client_mod.parse_error(other)[0] == "Failed"


@pytest.fixture
def window(app: Adw.Application) -> Iterator[tuple[Window, FakeClient, list[list[str]]]]:
    client = FakeClient()
    win = Window(app, client)
    commands: list[list[str]] = []
    result = {"code": 0}

    def fake_run(argv: list[str], done: Any) -> None:
        commands.append(argv)
        done(result["code"], "")

    win.ctx.run = fake_run  # type: ignore[method-assign]
    win._result = result  # type: ignore[attr-defined]
    yield win, client, commands
    win.destroy()


def test_window_first_open_enables_service(window: tuple[Window, FakeClient, list[list[str]]]) -> None:
    win, client, commands = window
    assert win.root.get_visible_child_name() == "loading"
    client.set_available(True)
    client.set_available(False)  # daemon não está rodando: ativa o serviço uma vez
    assert commands[-1] == ["systemctl", "--user", "enable", "--now", "ds4-companion.service"]
    client.set_available(True)
    assert win.root.get_visible_child_name() == "main"


def test_window_service_stopped_and_start(window: tuple[Window, FakeClient, list[list[str]]]) -> None:
    win, client, commands = window
    win._started_once = True
    client.set_available(True)
    client.set_available(False)
    assert win.root.get_visible_child_name() == "stopped"
    win._result["code"] = 5  # type: ignore[attr-defined]
    win.start_service()
    assert commands[-1] == ["systemctl", "--user", "start", "ds4-companion.service"]
    assert win.root.get_visible_child_name() == "stopped"


def test_window_pages_and_banner(window: tuple[Window, FakeClient, list[list[str]]]) -> None:
    win, client, _ = window
    client.set_available(True)
    client.push(sample(error="pw-dump falhou"))
    assert win.banner.get_revealed()
    assert "pw-dump falhou" in win.banner.get_title()
    for page in win.pages:
        win.show_page(page.page_id)
        assert win.stack.get_visible_child() is page
        assert win.content_page.get_title() == page.title
    row = win.sidebar.get_row_at_index(1)
    win.sidebar.emit("row-activated", row)
    assert win.stack.get_visible_child() is win.pages[1]
    client.push(sample())
    assert not win.banner.get_revealed()


def test_application_version_and_actions(capsys: pytest.CaptureFixture[str]) -> None:
    from ds4_companion.app.__main__ import main

    assert main(["ds4-companion", "--version"]) == 0
    assert "ds4-companion 0.1.0" in capsys.readouterr().out


def test_application_activate_with_fake_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from ds4_companion.app.application import Application

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "ds4-companion").mkdir()
    (tmp_path / "ds4-companion" / "config.toml").write_text("[updates]\ncheck_on_start = false\n")
    client = FakeClient()
    app = Application(client_factory=lambda: client)
    # NON_UNIQUE: o teste nunca conversa com uma janela real do app aberta na sessão.
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    app.activate()
    window = app.get_active_window()
    assert isinstance(window, Window)
    app.activate()  # segunda ativação só traz a janela para frente
    assert app.get_active_window() is window
    app.lookup_action("about").activate(None)
    spin(0.1)
    window.destroy()

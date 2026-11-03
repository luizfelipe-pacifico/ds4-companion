# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest
from dbus_next.aio.message_bus import MessageBus
from dbus_next.errors import DBusError
from dbus_next.signature import Variant

from ds4_companion.common.models import Status
from ds4_companion.common.names import INTERFACE, OBJECT_PATH
from ds4_companion.daemon import __main__ as daemon_main
from ds4_companion.daemon import dbus as ddbus
from ds4_companion.daemon.device import Controller

sys.path.insert(0, str(Path(__file__).parent))
from test_service import Env


def test_to_variant() -> None:
    assert ddbus.to_variant(True).signature == "b"
    assert ddbus.to_variant(3).signature == "i"
    assert ddbus.to_variant(1.5).signature == "d"
    assert ddbus.to_variant("x").signature == "s"
    assert ddbus.to_variant([1, 2]).signature == "ai"
    assert ddbus.to_variant(["a"]).signature == "as"
    assert ddbus.to_variant([]).signature == "as"
    with pytest.raises(TypeError):
        ddbus.to_variant(object())


def test_status_variants_round_trip() -> None:
    status = Status(players=[], apps=["rpcs3"], battery=50)
    variants = ddbus.status_variants(status)
    assert variants["players"].signature == "ai"
    assert variants["playing"].signature == "as"  # lista vazia também vai como texto
    assert Status.from_mapping({k: v.value for k, v in variants.items()}) == status
    playing = Status(playing=["Firefox", "eldenring.exe"])
    variants = ddbus.status_variants(playing)
    assert Status.from_mapping({k: v.value for k, v in variants.items()}).playing == playing.playing


async def _session() -> tuple[MessageBus, MessageBus] | None:
    try:
        server = await MessageBus().connect()
        client = await MessageBus().connect()
    except Exception:
        return None
    return server, client


def test_interface_over_session_bus(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario() -> None:
        buses = await _session()
        if buses is None:
            pytest.skip("sem D-Bus de sessão")
        server, client = buses
        server.export(OBJECT_PATH, ddbus.DaemonInterface(env.daemon))
        intro = await client.introspect(server.unique_name, OBJECT_PATH)
        proxy = client.get_proxy_object(server.unique_name, OBJECT_PATH, intro).get_interface(INTERFACE)
        p: Any = proxy

        changes: list[dict[str, Variant]] = []
        props = client.get_proxy_object(server.unique_name, OBJECT_PATH, intro).get_interface(
            "org.freedesktop.DBus.Properties"
        )
        props.on_properties_changed(lambda iface, changed, invalid: changes.append(changed))  # type: ignore[attr-defined]

        await p.call_refresh()
        status = {k: v.value for k, v in (await p.get_status()).items()}
        assert status["connection"] == "usb"
        assert await p.get_version()
        assert await p.call_set_volume(-9.0, False) == -9.0
        await p.call_set_mirror(False)
        await p.call_set_mirror(True)
        await p.call_set_limiter(False)
        await p.call_set_limiter(True)
        await p.call_set_vibration(80, 90, False)
        await p.call_set_players([1])
        await p.call_test_rumble("both")
        await p.call_set_led("green")
        await p.call_set_led_mode("battery")
        await p.call_play_test_tone()
        await p.call_set_apps(["rpcs3"])
        await p.call_set_rpcs3_dir(str(tmp_path))
        await p.call_set_backup(True)
        await p.call_restore_defaults()
        with pytest.raises(DBusError) as info:
            await p.call_set_led("magenta")
        assert info.value.type == f"{INTERFACE}.Error.InvalidArgument"
        await asyncio.sleep(0.1)
        assert changes
        assert "Status" in changes[-1]
        server.disconnect()
        client.disconnect()

    asyncio.run(scenario())


def test_main_args_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    args = daemon_main.parse_args(["--foreground", "--debug"])
    assert args.foreground
    assert args.debug
    assert not args.stop_motors
    with pytest.raises(SystemExit) as info:
        daemon_main.main(["--version"])
    assert info.value.code == 0
    assert "ds4-companiond 0.1.0" in capsys.readouterr().out


def test_stop_motors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dev = tmp_path / "hidraw7"
    dev.write_bytes(b"")
    from ds4_companion.common.models import Connection
    from ds4_companion.daemon import device

    class Fake:
        def scan(self) -> list[Controller]:
            return [Controller(str(dev), Connection.USB, 0x09CC), Controller(str(tmp_path / "nada"), Connection.USB, 1)]

    monkeypatch.setattr(device, "DeviceMonitor", Fake)
    assert daemon_main.main(["--stop-motors"]) == 0
    data = dev.read_bytes()
    assert data[0] == 0x05
    assert data[1] == 0x01
    assert data[4:6] == b"\0\0"


def _signature(xml_text: str) -> set[tuple[str, ...]]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)  # noqa: S314 - arquivo do próprio repositório
    found: set[tuple[str, ...]] = set()
    for iface in root.iter("interface"):
        for item in iface:
            args = tuple(f"{a.get('direction', '')}:{a.get('type')}" for a in item.iter("arg"))
            found.add((iface.get("name", ""), item.tag, item.get("name", ""), item.get("type", ""), *args))
    return found


def test_published_xml_matches_code() -> None:
    from dbus_next.introspection import Node

    class Fake:
        status = Status()

        def subscribe(self, listener: object) -> None: ...

    code = Node(None, [ddbus.DaemonInterface(Fake()).introspect()]).tostring()  # type: ignore[arg-type]
    published = (Path(__file__).parents[3] / "data" / f"{INTERFACE}.xml").read_text()
    assert _signature(published) == _signature(code)

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from ds4_companion.common.models import Connection
from ds4_companion.daemon import device


@pytest.mark.parametrize(
    ("hid_id", "expected"),
    [
        ("0003:0000054C:000009CC", (Connection.USB, 0x09CC)),
        ("0005:0000054C:000005C4", (Connection.BLUETOOTH, 0x05C4)),
        ("0003:0000054C:00000BA0", (Connection.BLUETOOTH, 0x0BA0)),
        ("0003:00001C4F:00000048", None),
        ("0003:0000054C:00000CE6", None),
        ("0018:0000054C:000009CC", None),
        ("lixo", None),
        ("zz:yy:xx", None),
    ],
)
def test_classify(hid_id: str, expected: tuple[Connection, int] | None) -> None:
    assert device.classify(hid_id) == expected


def test_pick_prefers_usb() -> None:
    bt = device.Controller("/dev/hidraw1", Connection.BLUETOOTH, 0x09CC)
    usb = device.Controller("/dev/hidraw5", Connection.USB, 0x09CC)
    assert device.pick([bt, usb]) == usb
    assert device.pick([]) is None
    assert usb.name == "DualShock 4"
    assert device.Controller("/dev/x", Connection.BLUETOOTH, 0x0BA0).name.endswith("(adaptador sem fio)")


def test_read_battery(tmp_path: Path) -> None:
    (tmp_path / "capacity").write_text("85\n")
    (tmp_path / "status").write_text("Charging\n")
    assert device.read_battery(str(tmp_path)) == (85, True)
    (tmp_path / "status").write_text("Discharging\n")
    (tmp_path / "capacity").write_text("130\n")
    assert device.read_battery(str(tmp_path)) == (100, False)
    (tmp_path / "capacity").write_text("x")
    assert device.read_battery(str(tmp_path)) == (-1, False)
    assert device.read_battery(None) == (-1, False)


def test_redact_hides_mac() -> None:
    name = "ps-controller-battery-" + ":".join(["a1", "b2", "c3", "d4", "e5", "f6"])
    assert device.redact(name) == "ps-controller-battery-XX:XX:XX:XX:XX:f6"


@dataclass
class FakeDev:
    device_node: str | None
    parent: Any = None

    def find_parent(self, subsystem: str) -> Any:
        return self.parent


@dataclass
class FakeParent:
    sys_path: str
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class FakeContext:
    devices: list[FakeDev]

    def list_devices(self, subsystem: str) -> list[FakeDev]:
        return self.devices


def test_scan(tmp_path: Path) -> None:
    hid = tmp_path / "0003:054C:09CC.0001"
    (hid / "power_supply" / "ps-controller-battery-teste").mkdir(parents=True)
    ctx = FakeContext(
        [
            FakeDev("/dev/hidraw2", FakeParent(str(hid), {"HID_ID": "0003:0000054C:000009CC"})),
            FakeDev("/dev/hidraw0", FakeParent(str(tmp_path), {"HID_ID": "0003:00001C4F:00000048"})),
            FakeDev("/dev/hidraw3", None),
            FakeDev(None, FakeParent(str(hid), {"HID_ID": "0003:0000054C:000009CC"})),
        ]
    )
    found = device.DeviceMonitor(ctx).scan()
    assert found == [
        device.Controller(
            "/dev/hidraw2", Connection.USB, 0x09CC, str(hid / "power_supply" / "ps-controller-battery-teste")
        )
    ]


def test_scan_without_battery(tmp_path: Path) -> None:
    ctx = FakeContext([FakeDev("/dev/hidraw2", FakeParent(str(tmp_path), {"HID_ID": "0005:0000054C:000009CC"}))])
    (found,) = device.DeviceMonitor(ctx).scan()
    assert found.battery_dir is None
    assert found.connection == Connection.BLUETOOTH


def test_real_udev_scan_does_not_crash() -> None:
    pytest.importorskip("pyudev")
    for c in device.DeviceMonitor().scan():
        assert c.hidraw.startswith("/dev/hidraw")


def test_monitor_start_stop() -> None:
    pytest.importorskip("pyudev")
    mon = device.DeviceMonitor()
    loop = asyncio.new_event_loop()
    try:
        try:
            mon.start(loop, lambda: None)
        except OSError:
            pytest.skip("sem netlink do udev neste ambiente")
        mon.stop()
        mon.stop()
    finally:
        loop.close()


def test_monitor_ready_drains_events(monkeypatch: pytest.MonkeyPatch) -> None:
    pyudev = pytest.importorskip("pyudev")

    class FakeMonitor:
        def __init__(self) -> None:
            self.events = [object(), object()]

        def filter_by(self, subsystem: str) -> None: ...
        def start(self) -> None: ...
        def fileno(self) -> int:
            return 99

        def poll(self, timeout: int) -> object | None:
            return self.events.pop() if self.events else None

    class FakeLoop:
        callback: Any = None

        def add_reader(self, fd: int, cb: Any) -> None:
            self.callback = cb

        def remove_reader(self, fd: int) -> None: ...

    monkeypatch.setattr(pyudev.Monitor, "from_netlink", lambda ctx: FakeMonitor())
    calls: list[int] = []
    loop = FakeLoop()
    mon = device.DeviceMonitor(FakeContext([]))
    mon.start(loop, lambda: calls.append(1))  # type: ignore[arg-type]
    loop.callback()
    loop.callback()
    assert calls == [1]
    mon.stop()

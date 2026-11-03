# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
import os
import zlib
from pathlib import Path

import pytest

from ds4_companion.common.models import Connection
from ds4_companion.daemon.hid import hidraw, reports


def test_usb_rumble_layout() -> None:
    r = reports.output_report(Connection.USB, motors=(200, 50))
    assert len(r) == 32
    assert r[0] == 0x05
    assert r[1] == reports.FLAG_MOTOR
    assert (r[4], r[5]) == (50, 200)  # fraco, forte
    assert r[6:9] == b"\0\0\0"


def test_usb_led_layout() -> None:
    r = reports.output_report(Connection.USB, rgb=(0x12, 0x34, 0x56))
    assert r[1] == reports.FLAG_LED
    assert r[6:9] == bytes([0x12, 0x34, 0x56])
    assert (r[4], r[5]) == (0, 0)


def test_bluetooth_layout_and_crc() -> None:
    r = reports.output_report(Connection.BLUETOOTH, motors=(255, 128), rgb=(1, 2, 3))
    assert len(r) == 78
    assert (r[0], r[1]) == (0x11, 0xC0)
    assert r[3] == reports.FLAG_MOTOR | reports.FLAG_LED
    assert (r[6], r[7]) == (128, 255)
    assert r[8:11] == bytes([1, 2, 3])
    expected = zlib.crc32(b"\xa2" + r[:74]) & 0xFFFFFFFF
    assert int.from_bytes(r[74:], "little") == expected


def test_crc_changes_with_payload() -> None:
    a = reports.output_report(Connection.BLUETOOTH, motors=(1, 0))
    b = reports.output_report(Connection.BLUETOOTH, motors=(2, 0))
    assert a[74:] != b[74:]


def test_rejects_empty_and_disconnected() -> None:
    with pytest.raises(ValueError, match="sem motores"):
        reports.output_report(Connection.USB)
    with pytest.raises(ValueError, match="desconectado"):
        reports.output_report(Connection.NONE, motors=(0, 0))
    with pytest.raises(ValueError, match="0–255"):
        reports.output_report(Connection.USB, motors=(256, 0))


@pytest.mark.parametrize(("percent", "byte"), [(0, 0), (50, 128), (100, 255), (150, 255), (-5, 0)])
def test_percent_to_byte(percent: int, byte: int) -> None:
    assert reports.percent_to_byte(percent) == byte


def test_parse_usb_input() -> None:
    data = bytearray(64)
    data[0] = 0x01
    data[30] = 0x10 | 0x20 | 0x0B
    status = reports.parse_usb_input(bytes(data))
    assert status == reports.InputStatus(battery_level=11, cable=True, headphones=True, mic=False)
    assert reports.parse_usb_input(b"\x11" + bytes(63)) is None
    assert reports.parse_usb_input(b"\x01") is None


def test_write_and_read(tmp_path: Path) -> None:
    dev = tmp_path / "hidraw9"
    dev.write_bytes(b"")
    hidraw.write_report(str(dev), b"\x05abc")
    assert dev.read_bytes() == b"\x05abc"
    assert hidraw.can_write(str(dev))

    rfd, wfd = os.pipe()
    os.write(wfd, b"\x01" + bytes(63))
    path = f"/proc/self/fd/{rfd}"
    assert hidraw.read_report(path) == b"\x01" + bytes(63)
    assert hidraw.read_report(path, timeout=0.01) is None
    os.close(rfd)
    os.close(wfd)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_access_error(tmp_path: Path) -> None:
    dev = tmp_path / "hidraw9"
    dev.write_bytes(b"")
    dev.chmod(0)
    with pytest.raises(hidraw.HidAccessError):
        hidraw.write_report(str(dev), b"\x05")
    assert not hidraw.can_write(str(dev))


def test_missing_device(tmp_path: Path) -> None:
    with pytest.raises(hidraw.HidError) as info:
        hidraw.write_report(str(tmp_path / "nada"), b"\x05")
    assert not isinstance(info.value, hidraw.HidAccessError)
    with pytest.raises(hidraw.HidError):
        hidraw.read_report(str(tmp_path / "nada"))


def test_short_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = tmp_path / "hidraw9"
    dev.write_bytes(b"")
    monkeypatch.setattr(os, "write", lambda fd, data: 1)
    with pytest.raises(hidraw.HidError, match="metade"):
        hidraw.write_report(str(dev), b"\x05abc")


def test_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = tmp_path / "hidraw9"
    dev.write_bytes(b"")

    def boom(fd: int, data: bytes) -> int:
        raise OSError(5, "I/O")

    monkeypatch.setattr(os, "write", boom)
    with pytest.raises(hidraw.HidError):
        hidraw.write_report(str(dev), b"\x05")

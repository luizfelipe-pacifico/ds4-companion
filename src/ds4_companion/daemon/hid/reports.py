# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Relatórios HID de saída do DualShock 4 (vibração e barra de luz) e leitura do estado.

Mesmo layout do driver `hid-playstation` do kernel:

- USB: relatório 0x05, 32 bytes. Bytes 4/5 = motor fraco/forte, 6/7/8 = R/G/B.
- Bluetooth: relatório 0x11, 78 bytes, os mesmos campos deslocados em 2 e CRC32 no final
  (semente 0xA2, little-endian nos últimos 4 bytes).
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

from ...common.models import Connection

USB_OUTPUT_ID = 0x05
USB_OUTPUT_SIZE = 32
BT_OUTPUT_ID = 0x11
BT_OUTPUT_SIZE = 78
BT_HW_CONTROL = 0xC0  # relatório HID + CRC32
BT_CRC_SEED = b"\xa2"

FLAG_MOTOR = 0x01
FLAG_LED = 0x02

# Posição do bloco comum (flags, motores, RGB) dentro de cada relatório.
_COMMON_OFFSET = {Connection.USB: 1, Connection.BLUETOOTH: 3}

USB_INPUT_ID = 0x01
_USB_STATUS_BYTE = 30
_STATUS_CABLE = 0x10
_STATUS_HEADPHONES = 0x20
_STATUS_MIC = 0x40


def percent_to_byte(percent: int) -> int:
    """0–100 % → 0–255. Fora da faixa é recortado."""
    return round(min(max(percent, 0), 100) * 255 / 100)


def bt_crc32(payload: bytes) -> int:
    return zlib.crc32(BT_CRC_SEED + payload) & 0xFFFFFFFF


def output_report(
    connection: Connection,
    *,
    motors: tuple[int, int] | None = None,
    rgb: tuple[int, int, int] | None = None,
) -> bytes:
    """Monta o relatório. `motors` = (forte, fraco) em 0–255; só os campos pedidos valem."""
    if connection == Connection.USB:
        report = bytearray(USB_OUTPUT_SIZE)
        report[0] = USB_OUTPUT_ID
    elif connection == Connection.BLUETOOTH:
        report = bytearray(BT_OUTPUT_SIZE)
        report[0] = BT_OUTPUT_ID
        report[1] = BT_HW_CONTROL
    else:
        raise ValueError("controle desconectado")

    base = _COMMON_OFFSET[connection]
    flags = 0
    if motors is not None:
        strong, weak = (_byte(v) for v in motors)
        flags |= FLAG_MOTOR
        report[base + 3] = weak
        report[base + 4] = strong
    if rgb is not None:
        flags |= FLAG_LED
        report[base + 5 : base + 8] = bytes(_byte(v) for v in rgb)
    if not flags:
        raise ValueError("relatório sem motores nem cor")
    report[base] = flags

    if connection == Connection.BLUETOOTH:
        crc = bt_crc32(bytes(report[:-4]))
        report[-4:] = crc.to_bytes(4, "little")
    return bytes(report)


def _byte(value: int) -> int:
    if not 0 <= value <= 255:
        raise ValueError(f"valor fora de 0–255: {value}")
    return value


@dataclass(frozen=True)
class InputStatus:
    battery_level: int
    cable: bool
    headphones: bool
    mic: bool


def parse_usb_input(report: bytes) -> InputStatus | None:
    """Lê o byte de estado do relatório de entrada USB 0x01 (fone, microfone, cabo)."""
    if len(report) <= _USB_STATUS_BYTE or report[0] != USB_INPUT_ID:
        return None
    status = report[_USB_STATUS_BYTE]
    return InputStatus(
        battery_level=status & 0x0F,
        cable=bool(status & _STATUS_CABLE),
        headphones=bool(status & _STATUS_HEADPHONES),
        mic=bool(status & _STATUS_MIC),
    )

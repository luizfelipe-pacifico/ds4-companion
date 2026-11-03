# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Relatórios HID de saída (vibração e barra de luz) e leitura do estado do controle.

Mesmo layout do driver `hid-playstation` do kernel.

DualShock 4:
- USB: relatório 0x05, 32 bytes. Bytes 4/5 = motor fraco/forte, 6/7/8 = R/G/B.
- Bluetooth: relatório 0x11, 78 bytes, os mesmos campos deslocados em 2 e CRC32 no final
  (semente 0xA2, little-endian nos últimos 4 bytes).

DualSense (bloco comum de 47 bytes: flags, motores, …, RGB nos três últimos):
- USB: relatório 0x02, 63 bytes, bloco a partir do byte 1.
- Bluetooth: relatório 0x31, 78 bytes: sequência no nibble alto do byte 1, tag 0x10 no byte 2,
  bloco a partir do byte 3 e CRC32 no final.
- Vibração "compatível": firmware ≥ 2.21 (e o Edge) usa a v2, sinalizada no valid_flag2.
"""

from __future__ import annotations

import itertools
import zlib
from dataclasses import dataclass

from ...common.models import Connection, Model

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


DS_USB_OUTPUT_ID = 0x02
DS_USB_OUTPUT_SIZE = 63
DS_BT_OUTPUT_ID = 0x31
DS_BT_OUTPUT_SIZE = 78
DS_BT_TAG = 0x10
_DS_COMMON_OFFSET = {Connection.USB: 1, Connection.BLUETOOTH: 3}
# Posições dentro do bloco comum de 47 bytes.
_DS_FLAG0, _DS_FLAG1, _DS_MOTOR_RIGHT, _DS_MOTOR_LEFT, _DS_FLAG2, _DS_RGB = 0, 1, 2, 3, 39, 44
DS_FLAG0_COMPATIBLE_VIBRATION = 0x01
DS_FLAG0_HAPTICS_SELECT = 0x02
DS_FLAG1_LIGHTBAR = 0x04
DS_FLAG2_COMPATIBLE_VIBRATION2 = 0x04
DS_FEATURE_FIRMWARE_INFO = 0x20
DS_FEATURE_FIRMWARE_SIZE = 64
_DS_UPDATE_VERSION_OFFSET = 44
_DS_VIBRATION_V2_FROM = (2 << 8) | 21  # DS_FEATURE_VERSION(2, 21)
_DS_USB_INPUT_SIZE = 64
_DS_STATUS0, _DS_STATUS1 = 53, 54
_DS_STATUS1_HEADPHONES = 0x01
_DS_STATUS1_MIC = 0x02

# O DualSense por Bluetooth quer um número de sequência (0–15) novo a cada relatório.
_ds_sequence = itertools.count()


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
    model: Model = Model.DS4,
    vibration_v2: bool = True,
) -> bytes:
    """Monta o relatório. `motors` = (forte, fraco) em 0–255; só os campos pedidos valem.

    `vibration_v2` só vale para o DualSense (ver `uses_vibration_v2`).
    """
    if model == Model.DUALSENSE:
        return _dualsense_report(connection, motors, rgb, vibration_v2)
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


def _dualsense_report(
    connection: Connection,
    motors: tuple[int, int] | None,
    rgb: tuple[int, int, int] | None,
    vibration_v2: bool,
) -> bytes:
    if connection == Connection.USB:
        report = bytearray(DS_USB_OUTPUT_SIZE)
        report[0] = DS_USB_OUTPUT_ID
    elif connection == Connection.BLUETOOTH:
        report = bytearray(DS_BT_OUTPUT_SIZE)
        report[0] = DS_BT_OUTPUT_ID
        report[1] = (next(_ds_sequence) % 16) << 4
        report[2] = DS_BT_TAG
    else:
        raise ValueError("controle desconectado")
    if motors is None and rgb is None:
        raise ValueError("relatório sem motores nem cor")

    base = _DS_COMMON_OFFSET[connection]
    if motors is not None:
        strong, weak = (_byte(v) for v in motors)
        report[base + _DS_FLAG0] |= DS_FLAG0_HAPTICS_SELECT
        if vibration_v2:
            report[base + _DS_FLAG2] |= DS_FLAG2_COMPATIBLE_VIBRATION2
        else:
            report[base + _DS_FLAG0] |= DS_FLAG0_COMPATIBLE_VIBRATION
        report[base + _DS_MOTOR_LEFT] = strong
        report[base + _DS_MOTOR_RIGHT] = weak
    if rgb is not None:
        report[base + _DS_FLAG1] |= DS_FLAG1_LIGHTBAR
        report[base + _DS_RGB : base + _DS_RGB + 3] = bytes(_byte(v) for v in rgb)

    if connection == Connection.BLUETOOTH:
        report[-4:] = bt_crc32(bytes(report[:-4])).to_bytes(4, "little")
    return bytes(report)


def uses_vibration_v2(feature: bytes) -> bool:
    """Lê o relatório de feature 0x20 (firmware): v2 a partir da versão 2.21.

    Sem os bytes da versão, assume v2, a dos firmwares atuais: errar só deixa o teste sem vibrar.
    """
    if len(feature) < _DS_UPDATE_VERSION_OFFSET + 2:
        return True
    version = int.from_bytes(feature[_DS_UPDATE_VERSION_OFFSET : _DS_UPDATE_VERSION_OFFSET + 2], "little")
    return version >= _DS_VIBRATION_V2_FROM


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


def parse_dualsense_usb_input(report: bytes) -> InputStatus | None:
    """Lê `status[0]` (bateria) e `status[1]` (fone, microfone) do relatório de entrada USB 0x01."""
    if len(report) < _DS_USB_INPUT_SIZE or report[0] != USB_INPUT_ID:
        return None
    status0, status1 = report[_DS_STATUS0], report[_DS_STATUS1]
    return InputStatus(
        battery_level=status0 & 0x0F,
        cable=True,
        headphones=bool(status1 & _DS_STATUS1_HEADPHONES),
        mic=bool(status1 & _DS_STATUS1_MIC),
    )

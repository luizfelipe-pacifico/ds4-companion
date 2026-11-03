# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Protótipo: áudio no DualShock 4 por Bluetooth (pesquisa do ROADMAP, não usado pelo app).

O DS4 não usa A2DP: recebe SBC dentro de relatórios HID de saída. O layout abaixo vem de
implementações independentes (ver docs/desenvolvimento/BLUETOOTH_AUDIO.md) e **ainda não foi
conferido em hardware** por este projeto:

- 0x11 (78 bytes, CRC32) arma o caminho de áudio: byte 2 = 0xA0, flags no byte 3, volumes do fone
  nos bytes 21/22, do alto-falante no 24 (0x00–0x4F) e 0x85 no byte 25.
- 0x17 (462 bytes, CRC32) a cada 16 ms: 0x17, 0x40, 0xA0, contador de quadros (16 bits, LE),
  destino (0x02 alto-falante, 0x24 fone) e quatro quadros SBC de 109 bytes a partir do byte 6.
- SBC: 32 kHz, estéreo conjunto, 16 blocos, 8 sub-bandas, alocação SNR, bitpool 48.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from enum import IntEnum

from .reports import bt_crc32

RATE = 32000
CHANNELS = 2
FRAME_LENGTH = 109
CODESIZE = 512
"""Bytes de PCM s16le estéreo por quadro SBC: 128 amostras por canal, 4 ms a 32 kHz."""
FRAMES_PER_REPORT = 4
REPORT_INTERVAL_S = FRAMES_PER_REPORT * (CODESIZE // (CHANNELS * 2)) / RATE  # 16 ms

AUDIO_REPORT_ID = 0x17
AUDIO_REPORT_SIZE = 462
AUDIO_FLAGS = 0x40  # só CRC (o 0x11 usa 0xC0: relatório HID + CRC)
INPUT_MODE = 0xA0  # mantém os relatórios de entrada chegando; 0xA2 trava a entrada em alguns DS4
SBC_OFFSET = 6

CONTROL_REPORT_ID = 0x11
CONTROL_SIZE = 78
CONTROL_HW = 0xC0
FLAG_HEADPHONE_VOLUME = 0x10 | 0x20
FLAG_SPEAKER_VOLUME = 0x80
HEADPHONE_LEFT, HEADPHONE_RIGHT, SPEAKER = 21, 22, 24
AUDIO_ENABLE_BYTE, AUDIO_ENABLE = 25, 0x85
MAX_VOLUME = 0x4F
"""Acima disso o valor invade campos vizinhos do DSP do controle."""

SBC_SYNCWORD = 0x9C

# sbc.h
_SBC_FREQ_32000 = 0x01
_SBC_BLK_16 = 0x03
_SBC_MODE_JOINT_STEREO = 0x03
_SBC_AM_SNR = 0x01
_SBC_SB_8 = 0x01
_SBC_LE = 0x00
_BITPOOL = 48


class Target(IntEnum):
    SPEAKER = 0x02
    HEADPHONES = 0x24


class SbcUnavailable(RuntimeError):
    """`libsbc` (pacote `sbc` do Arch) não está instalada."""


class _Sbc(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_ulong),
        ("frequency", ctypes.c_uint8),
        ("blocks", ctypes.c_uint8),
        ("subbands", ctypes.c_uint8),
        ("mode", ctypes.c_uint8),
        ("allocation", ctypes.c_uint8),
        ("bitpool", ctypes.c_uint8),
        ("endian", ctypes.c_uint8),
        ("priv", ctypes.c_void_p),
        ("priv_alloc_base", ctypes.c_void_p),
    ]


def _load() -> ctypes.CDLL:
    name = ctypes.util.find_library("sbc") or "libsbc.so.1"
    try:
        lib = ctypes.CDLL(name)
    except OSError as exc:
        raise SbcUnavailable("libsbc não encontrada; instale o pacote sbc") from exc
    lib.sbc_init.argtypes = [ctypes.POINTER(_Sbc), ctypes.c_ulong]
    lib.sbc_init.restype = ctypes.c_int
    lib.sbc_encode.argtypes = [
        ctypes.POINTER(_Sbc),
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_ssize_t),
    ]
    lib.sbc_encode.restype = ctypes.c_ssize_t
    lib.sbc_get_frame_length.argtypes = [ctypes.POINTER(_Sbc)]
    lib.sbc_get_frame_length.restype = ctypes.c_size_t
    lib.sbc_get_codesize.argtypes = [ctypes.POINTER(_Sbc)]
    lib.sbc_get_codesize.restype = ctypes.c_size_t
    lib.sbc_finish.argtypes = [ctypes.POINTER(_Sbc)]
    lib.sbc_finish.restype = None
    return lib


class SbcEncoder:
    """Codificador SBC com os parâmetros do DS4. PCM de entrada: s16le estéreo a 32 kHz."""

    def __init__(self) -> None:
        self._lib = _load()
        self._sbc = _Sbc()
        if self._lib.sbc_init(ctypes.byref(self._sbc), 0) < 0:
            raise SbcUnavailable("sbc_init falhou")
        self._sbc.frequency = _SBC_FREQ_32000
        self._sbc.blocks = _SBC_BLK_16
        self._sbc.subbands = _SBC_SB_8
        self._sbc.mode = _SBC_MODE_JOINT_STEREO
        self._sbc.allocation = _SBC_AM_SNR
        self._sbc.bitpool = _BITPOOL
        self._sbc.endian = _SBC_LE
        self.frame_length = int(self._lib.sbc_get_frame_length(ctypes.byref(self._sbc)))
        self.codesize = int(self._lib.sbc_get_codesize(ctypes.byref(self._sbc)))
        self._open = True

    def encode(self, pcm: bytes) -> bytes:
        """Codifica um bloco de exatamente `codesize` bytes num quadro SBC."""
        if len(pcm) != self.codesize:
            raise ValueError(f"o bloco precisa ter {self.codesize} bytes de PCM")
        out = ctypes.create_string_buffer(self.frame_length)
        written = ctypes.c_ssize_t(0)
        consumed = self._lib.sbc_encode(
            ctypes.byref(self._sbc), pcm, len(pcm), out, self.frame_length, ctypes.byref(written)
        )
        if consumed != len(pcm) or written.value != self.frame_length:
            raise RuntimeError("sbc_encode não gerou um quadro completo")
        return out.raw

    def close(self) -> None:
        if self._open:
            self._lib.sbc_finish(ctypes.byref(self._sbc))
            self._open = False

    def __enter__(self) -> SbcEncoder:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _with_crc(report: bytearray) -> bytes:
    report[-4:] = bt_crc32(bytes(report[:-4])).to_bytes(4, "little")
    return bytes(report)


def audio_report(frames: list[bytes], counter: int, target: Target) -> bytes:
    """Relatório 0x17 com quatro quadros SBC. `counter` conta quadros (avança 4 por relatório)."""
    if len(frames) != FRAMES_PER_REPORT or any(len(f) != FRAME_LENGTH for f in frames):
        raise ValueError(f"precisa de {FRAMES_PER_REPORT} quadros SBC de {FRAME_LENGTH} bytes")
    report = bytearray(AUDIO_REPORT_SIZE)
    report[0:3] = bytes([AUDIO_REPORT_ID, AUDIO_FLAGS, INPUT_MODE])
    report[3:5] = (counter & 0xFFFF).to_bytes(2, "little")
    report[5] = target
    payload = b"".join(frames)
    report[SBC_OFFSET : SBC_OFFSET + len(payload)] = payload
    return _with_crc(report)


def volume_byte(percent: int) -> int:
    """0–100 % → 0x00–0x4F (o teto do DSP). Fora da faixa é recortado."""
    return round(min(max(percent, 0), 100) * MAX_VOLUME / 100)


def control_report(target: Target | None, volume: int = 0) -> bytes:
    """0x11 que arma (`target`) ou desarma (`None`) o áudio. `volume` em 0x00–0x4F."""
    if not 0 <= volume <= MAX_VOLUME:
        raise ValueError(f"volume fora de 0–{MAX_VOLUME:#04x}")
    report = bytearray(CONTROL_SIZE)
    report[0:3] = bytes([CONTROL_REPORT_ID, CONTROL_HW, INPUT_MODE])
    # As duas saídas sempre recebem valor: o destino que não está em uso fica em 0.
    report[3] = FLAG_HEADPHONE_VOLUME | FLAG_SPEAKER_VOLUME
    if target == Target.HEADPHONES:
        report[HEADPHONE_LEFT] = report[HEADPHONE_RIGHT] = volume
    elif target == Target.SPEAKER:
        report[SPEAKER] = volume
    report[AUDIO_ENABLE_BYTE] = AUDIO_ENABLE if target is not None else 0
    return _with_crc(report)


def parse_sbc_header(frame: bytes) -> dict[str, int]:
    """Lê o cabeçalho de um quadro SBC (para conferir os parâmetros nos testes e no protótipo)."""
    if len(frame) < 3 or frame[0] != SBC_SYNCWORD:
        raise ValueError("não é um quadro SBC")
    b = frame[1]
    return {
        "rate": (16000, 32000, 44100, 48000)[b >> 6],
        "blocks": (4, 8, 12, 16)[(b >> 4) & 0x03],
        "mode": (b >> 2) & 0x03,
        "allocation": (b >> 1) & 0x01,
        "subbands": (4, 8)[b & 0x01],
        "bitpool": frame[2],
    }

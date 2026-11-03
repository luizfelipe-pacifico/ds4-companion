# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
import math
import struct
import zlib

import pytest

from ds4_companion.daemon.hid import bt_audio
from ds4_companion.daemon.hid.bt_audio import Target


def crc_ok(report: bytes) -> bool:
    return int.from_bytes(report[-4:], "little") == zlib.crc32(b"\xa2" + report[:-4]) & 0xFFFFFFFF


def test_timing_matches_four_frames_every_16_ms() -> None:
    assert pytest.approx(0.016) == bt_audio.REPORT_INTERVAL_S
    assert bt_audio.SBC_OFFSET + 4 * bt_audio.FRAME_LENGTH <= bt_audio.AUDIO_REPORT_SIZE - 4


def test_audio_report_layout() -> None:
    frames = [bytes([0x9C, i]) + bytes(107) for i in range(4)]
    r = bt_audio.audio_report(frames, counter=0x1_0004, target=Target.SPEAKER)
    assert len(r) == 462
    assert r[:3] == bytes([0x17, 0x40, 0xA0])
    assert r[3:5] == (0x0004).to_bytes(2, "little")  # o contador dá a volta em 16 bits
    assert r[5] == 0x02
    assert r[6 : 6 + 436] == b"".join(frames)
    assert r[6 + 436 : -4] == bytes(462 - 4 - 6 - 436)
    assert crc_ok(r)


def test_audio_report_rejects_wrong_frames() -> None:
    with pytest.raises(ValueError, match="4 quadros"):
        bt_audio.audio_report([bytes(109)] * 3, 0, Target.SPEAKER)
    with pytest.raises(ValueError, match="109 bytes"):
        bt_audio.audio_report([bytes(108)] * 4, 0, Target.SPEAKER)


def test_control_report_arms_speaker_and_mutes_jack() -> None:
    r = bt_audio.control_report(Target.SPEAKER, 0x40)
    assert len(r) == 78
    assert r[:4] == bytes([0x11, 0xC0, 0xA0, 0xB0])
    assert (r[21], r[22], r[24], r[25]) == (0, 0, 0x40, 0x85)
    assert crc_ok(r)


def test_control_report_headphones_and_disarm() -> None:
    hp = bt_audio.control_report(Target.HEADPHONES, 0x20)
    assert (hp[21], hp[22], hp[24], hp[25]) == (0x20, 0x20, 0, 0x85)
    off = bt_audio.control_report(None)
    assert (off[21], off[22], off[24], off[25]) == (0, 0, 0, 0)
    assert crc_ok(off)


def test_control_report_never_passes_dsp_ceiling() -> None:
    with pytest.raises(ValueError, match="volume"):
        bt_audio.control_report(Target.SPEAKER, 0x50)


@pytest.mark.parametrize(("percent", "byte"), [(0, 0), (50, 40), (100, 0x4F), (180, 0x4F), (-1, 0)])
def test_volume_byte(percent: int, byte: int) -> None:
    assert bt_audio.volume_byte(percent) == byte


def test_parse_sbc_header_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="SBC"):
        bt_audio.parse_sbc_header(b"\x00\x00\x00")


@pytest.fixture
def encoder() -> bt_audio.SbcEncoder:
    try:
        return bt_audio.SbcEncoder()
    except bt_audio.SbcUnavailable:
        pytest.skip("libsbc não instalada (pacote sbc)")


def test_encoder_produces_ds4_frames(encoder: bt_audio.SbcEncoder) -> None:
    with encoder:
        assert (encoder.frame_length, encoder.codesize) == (bt_audio.FRAME_LENGTH, bt_audio.CODESIZE)
        samples = [round(8000 * math.sin(2 * math.pi * 880 * i / 32000)) for i in range(128)]
        pcm = b"".join(struct.pack("<hh", s, s) for s in samples)
        frame = encoder.encode(pcm)
        assert len(frame) == 109
        assert bt_audio.parse_sbc_header(frame) == {
            "rate": 32000,
            "blocks": 16,
            "mode": 3,  # estéreo conjunto
            "allocation": 1,  # SNR
            "subbands": 8,
            "bitpool": 48,
        }
        with pytest.raises(ValueError, match="512 bytes"):
            encoder.encode(pcm[:-4])
    encoder.close()  # fechar de novo não quebra


def test_missing_library(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_name: str) -> None:
        raise OSError("nope")

    monkeypatch.setattr(bt_audio.ctypes.util, "find_library", lambda _n: None)
    monkeypatch.setattr(bt_audio.ctypes, "CDLL", fail)
    with pytest.raises(bt_audio.SbcUnavailable, match="sbc"):
        bt_audio.SbcEncoder()

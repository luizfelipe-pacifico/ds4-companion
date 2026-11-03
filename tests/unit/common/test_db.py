# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
import math

import pytest

from ds4_companion.common import db


def test_base_volume_is_zero_db() -> None:
    assert db.volume_to_db(0.4) == pytest.approx(0.0)
    assert db.db_to_volume(0.0) == pytest.approx(0.4)


@pytest.mark.parametrize(("volume", "expected"), [(0.32, -5.8), (0.25, -12.2)])
def test_table_from_audio_doc(volume: float, expected: float) -> None:
    # Tabela de docs/guia/AUDIO.md: 32 % ≈ −6 dB, 25 % ≈ −12 dB.
    assert db.volume_to_db(volume) == pytest.approx(expected, abs=0.1)


@pytest.mark.parametrize("value", [-30.0, -6.0, -0.5, 0.0, 3.0, 6.0])
def test_round_trip(value: float) -> None:
    assert db.volume_to_db(db.db_to_volume(value)) == pytest.approx(value)


@pytest.mark.parametrize("volume", [0.0, -1.0, math.nan, math.inf * -1])
def test_mute_and_invalid_become_floor(volume: float) -> None:
    assert db.volume_to_db(volume) == db.FLOOR_DB


def test_floor_is_silence() -> None:
    assert db.db_to_volume(db.FLOOR_DB) == 0.0
    assert db.db_to_volume(-100.0) == 0.0


@pytest.mark.parametrize("value", [math.nan, math.inf])
def test_rejects_non_finite(value: float) -> None:
    with pytest.raises(ValueError, match="finito"):
        db.db_to_volume(value)
    with pytest.raises(ValueError, match="finito"):
        db.clamp_db(value, 0.0)


def test_clamp_respects_ceiling_and_absolute_max() -> None:
    assert db.clamp_db(3.0, 0.0) == 0.0
    assert db.clamp_db(-80.0, 0.0) == db.FLOOR_DB
    assert db.clamp_db(20.0, 50.0) == db.ABSOLUTE_MAX_DB
    assert db.clamp_db(-6.0, 0.0) == -6.0


@pytest.mark.parametrize(
    ("value", "zone"),
    [
        (-12.0, db.VolumeZone.FREE),
        (-6.0, db.VolumeZone.FREE),
        (-5.9, db.VolumeZone.HIGH),
        (0.0, db.VolumeZone.HIGH),
        (0.1, db.VolumeZone.OVER_LIMIT),
    ],
)
def test_zones_match_security_doc(value: float, zone: db.VolumeZone) -> None:
    assert db.zone_for(value) == zone


@pytest.mark.parametrize(
    ("value", "text"),
    [(-6.0, "−6 dB"), (-5.75, "−5.8 dB"), (0.0, "0 dB"), (-0.01, "0 dB"), (2.0, "+2 dB"), (-60.0, "−∞ dB")],
)
def test_format(value: float, text: str) -> None:
    assert db.format_db(value) == text

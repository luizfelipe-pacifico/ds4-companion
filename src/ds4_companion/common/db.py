# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Conversão entre volume do PipeWire (escala cúbica do wpctl) e dB.

O sink do DualShock 4 tem *base volume* em 0,4 (40 %), que é o 0 dB do hardware.
Na escala cúbica, amplitude = v³, então dB = 20·log10(v³ / base³) = 60·log10(v / base).
"""

from __future__ import annotations

import math
from enum import StrEnum

BASE_VOLUME = 0.4
FLOOR_DB = -60.0
HIGH_FROM_DB = -6.0
LIMIT_DB = 0.0
ABSOLUTE_MAX_DB = 6.0
"""Teto que nem o config.toml pode passar: acima disso o alto-falante clipa muito."""


class VolumeZone(StrEnum):
    FREE = "free"
    HIGH = "high"
    OVER_LIMIT = "over-limit"


def volume_to_db(volume: float, base: float = BASE_VOLUME) -> float:
    """Volume cúbico (0,0–1,5) → dB relativo ao volume nativo. Mudo vira FLOOR_DB."""
    if not math.isfinite(volume) or volume <= 0:
        return FLOOR_DB
    return max(FLOOR_DB, 60.0 * math.log10(volume / base))


def db_to_volume(db: float, base: float = BASE_VOLUME) -> float:
    """dB → volume cúbico para `wpctl set-volume`."""
    if not math.isfinite(db):
        raise ValueError("volume em dB precisa ser um número finito")
    if db <= FLOOR_DB:
        return 0.0
    return base * 10 ** (db / 60.0)


def clamp_db(db: float, max_db: float) -> float:
    """Prende o volume entre o piso e o teto efetivo (nunca acima de ABSOLUTE_MAX_DB)."""
    if not math.isfinite(db):
        raise ValueError("volume em dB precisa ser um número finito")
    ceiling = min(max_db, ABSOLUTE_MAX_DB)
    return min(max(db, FLOOR_DB), ceiling)


def zone_for(db: float) -> VolumeZone:
    """Faixa do SECURITY.md: ≤ −6 dB livre, até 0 dB alto, acima disso acima do limite."""
    if db > LIMIT_DB:
        return VolumeZone.OVER_LIMIT
    if db > HIGH_FROM_DB:
        return VolumeZone.HIGH
    return VolumeZone.FREE


def format_db(db: float) -> str:
    """Texto com o sinal de menos tipográfico, como a interface mostra: “−6 dB”."""
    if db <= FLOOR_DB:
        return "−∞ dB"
    rounded = round(db, 1)
    if rounded == 0:
        return "0 dB"
    text = f"{abs(rounded):.1f}".rstrip("0").rstrip(".")
    return f"{'−' if rounded < 0 else '+'}{text} dB"

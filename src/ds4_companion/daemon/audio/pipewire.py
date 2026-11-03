# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Comandos do PipeWire/WirePlumber (`pw-dump`, `pw-link`, `wpctl`, `pw-play`) via asyncio.

Sempre lista de argumentos, sem shell; IDs numéricos onde der e `--opção=valor` para nomes, para
que um nome começando com `-` nunca vire opção.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import struct
import wave
from collections.abc import AsyncIterator
from pathlib import Path

from .graph import Graph, parse_dump

log = logging.getLogger(__name__)

TIMEOUT_S = 5.0


class PipeWireError(RuntimeError):
    """Comando do PipeWire falhou; a mensagem é para o log e para o usuário."""


async def _run(*argv: str, timeout: float = TIMEOUT_S) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise PipeWireError(f"{argv[0]} não encontrado; instale pipewire e wireplumber") from exc
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise PipeWireError(f"{argv[0]} não respondeu em {timeout:g} s") from exc
    if proc.returncode != 0:
        detail = err.decode(errors="replace").strip().splitlines()
        raise PipeWireError(f"{argv[0]} falhou: {detail[-1] if detail else proc.returncode}")
    return out.decode(errors="replace")


class PipeWire:
    async def dump(self) -> Graph:
        text = await _run("pw-dump", "--no-colors")
        try:
            return parse_dump(json.loads(text))
        except json.JSONDecodeError as exc:
            raise PipeWireError("pw-dump devolveu JSON inválido") from exc

    async def link(self, output_port: int, input_port: int) -> None:
        try:
            await _run("pw-link", str(output_port), str(input_port))
        except PipeWireError as exc:
            if "exists" not in str(exc).casefold():
                raise

    async def unlink(self, output_port: int, input_port: int) -> None:
        await _run("pw-link", "--disconnect", str(output_port), str(input_port))

    async def set_volume(self, node_id: int, volume: float) -> None:
        if not math.isfinite(volume) or volume < 0:
            raise ValueError("volume inválido")
        await _run("wpctl", "set-volume", str(node_id), f"{volume:.4f}")

    async def play(self, path: Path, target: str) -> None:
        await _run("pw-play", f"--target={target}", str(path), timeout=10.0)

    async def events(self) -> AsyncIterator[None]:
        """Um item a cada mudança no grafo (`pw-dump --monitor`). Termina se o processo morrer."""
        proc = await asyncio.create_subprocess_exec(
            "pw-dump",
            "--monitor",
            "--no-colors",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if proc.stdout is None:  # pragma: no cover - stdout=PIPE sempre cria o leitor
            return
        try:
            while chunk := await proc.stdout.read(65536):
                del chunk
                yield None
        finally:
            if proc.returncode is None:
                proc.kill()
                with contextlib.suppress(ProcessLookupError):
                    await proc.wait()


def write_test_tone(path: Path, db: float = -12.0, seconds: float = 0.4, freq: float = 880.0) -> Path:
    """Apito estéreo de 48 kHz a `db` dBFS, com rampa de 10 ms para não estalar."""
    rate = 48000
    amplitude = 10 ** (db / 20) * 32767
    frames = int(rate * seconds)
    ramp = int(rate * 0.01)
    data = bytearray()
    for i in range(frames):
        gain = min(1.0, i / ramp, (frames - 1 - i) / ramp)
        sample = int(amplitude * gain * math.sin(2 * math.pi * freq * i / rate))
        data += struct.pack("<hh", sample, sample)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(bytes(data))
    return path

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""O limitador de verdade num PipeWire de teste: um tom a 0 dBFS entra, mede-se o pico que chega ao
"controle" (null sink) com e sem o limitador. Roda só via scripts/ci/run-integration.sh."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
import wave
from collections.abc import Iterator
from pathlib import Path

import pytest

from ds4_companion.daemon.audio import graph as g
from ds4_companion.daemon.audio.limiter import Limiter, limit_amplitude
from ds4_companion.daemon.audio.pipewire import PipeWire, write_test_tone

pytestmark = pytest.mark.skipif(
    os.environ.get("DS4_INTEGRATION") != "1", reason="só no PipeWire isolado de scripts/ci/run-integration.sh"
)

APPS = ["rpcs3"]
DS4 = "Wireless_Controller_limitador"


def null_sink(name: str) -> None:
    props = (
        "{ factory.name=support.null-audio-sink node.name=" + name + " media.class=Audio/Sink "
        "audio.position=[ FL FR ] object.linger=true }"
    )
    subprocess.run(["pw-cli", "create-node", "adapter", props], check=True, capture_output=True)


def dump() -> g.Graph:
    return asyncio.run(PipeWire().dump())


def wait_for(predicate: object, timeout: float = 10.0) -> g.Graph:
    deadline = time.monotonic() + timeout
    while True:
        graph = dump()
        if predicate(graph):  # type: ignore[operator]
            return graph
        if time.monotonic() > deadline:
            raise AssertionError("o grafo não chegou no estado esperado")
        time.sleep(0.2)


def link_all(pairs: list[tuple[int, int]]) -> None:
    async def go() -> None:
        pw = PipeWire()
        for out_port, in_port in pairs:
            await pw.link(out_port, in_port)

    asyncio.run(go())


def unlink_all(pairs: list[tuple[int, int]]) -> None:
    async def go() -> None:
        pw = PipeWire()
        for out_port, in_port in pairs:
            await pw.unlink(out_port, in_port)

    asyncio.run(go())


def record_peak(path: Path, seconds: float = 1.5) -> float:
    """Grava o monitor do 'controle' e devolve o pico (0–1)."""
    proc = subprocess.Popen(
        [
            "pw-record",
            f"--target={DS4}",
            "--properties={ stream.capture.sink = true }",
            "--channels=2",
            "--rate=48000",
            "--format=s16",
            str(path),
        ]
    )
    time.sleep(seconds)
    proc.terminate()
    proc.wait()
    with wave.open(str(path)) as w:
        frames = w.readframes(w.getnframes())
    samples = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in range(0, len(frames), 2)]
    return max((abs(s) for s in samples), default=0) / 32768


@pytest.fixture
def loud_game(tmp_path: Path) -> Iterator[None]:
    null_sink("saida_principal_lim")
    null_sink(DS4)
    graph = wait_for(
        lambda gr: gr.ds4_sink() is not None and any(n.name == "saida_principal_lim" for n in gr.nodes.values())
    )
    main = next(n for n in graph.nodes.values() if n.name == "saida_principal_lim")
    subprocess.run(["wpctl", "set-default", str(main.id)], check=True)
    tone = write_test_tone(tmp_path / "alto.wav", db=0.0, seconds=60)  # pico em 0 dBFS
    proc = subprocess.Popen(
        ["pw-play", "--properties={ application.name = RPCS3 }", "--target=saida_principal_lim", str(tone)]
    )
    try:
        wait_for(lambda gr: any(gr.ports_of(s.id, "out") for s in gr.streams(APPS)))
        yield
    finally:
        proc.terminate()
        proc.wait()


@pytest.mark.usefixtures("loud_game")
def test_limiter_holds_peaks_at_minus_one_dbfs(tmp_path: Path) -> None:
    # Controle: direto ao controle, o pico passa de −1 dBFS.
    link_all(g.missing_links(dump(), APPS))
    wait_for(lambda gr: g.is_mirroring(gr, APPS))
    direct_peak = record_peak(tmp_path / "direto.wav")
    assert direct_peak > limit_amplitude() + 0.03

    limiter = Limiter(conf_dir=tmp_path)
    loop = asyncio.new_event_loop()  # o processo do limitador vive num laço só
    try:
        assert loop.run_until_complete(limiter.ensure(DS4))
        graph = wait_for(lambda gr: gr.limiter_input() is not None and gr.ports_of(gr.limiter_input().id, "in"))  # type: ignore[union-attr]
        unlink_all(g.stale_links(graph, APPS))
        link_all(g.missing_links(dump(), APPS))
        wait_for(lambda gr: g.is_mirroring(gr, APPS) and not g.stale_links(gr, APPS))
        limited_peak = record_peak(tmp_path / "limitado.wav")
    finally:
        loop.run_until_complete(limiter.stop())
        loop.close()

    assert limited_peak <= limit_amplitude() + 0.01  # nada passa de −1 dBFS
    assert limited_peak > 0.5  # e o som continua chegando

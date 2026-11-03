# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Áudio em paralelo num PipeWire de teste: null sinks fazem o papel da saída e do controle e o
`pw-play` finge ser o RPCS3. Roda só via `dbus-run-session -- scripts/ci/run-integration.sh`."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from ds4_companion.daemon.audio import graph as g
from ds4_companion.daemon.audio.pipewire import PipeWire, write_test_tone

pytestmark = pytest.mark.skipif(
    os.environ.get("DS4_INTEGRATION") != "1", reason="só no PipeWire isolado de scripts/ci/run-integration.sh"
)

APPS = ["rpcs3"]


def null_sink(name: str) -> None:
    props = (
        "{ factory.name=support.null-audio-sink node.name=" + name + " media.class=Audio/Sink "
        "audio.position=[ FL FR ] object.linger=true }"
    )
    subprocess.run(["pw-cli", "create-node", "adapter", props], check=True, capture_output=True)


def wait_for(predicate: object, timeout: float = 10.0) -> g.Graph:
    deadline = time.monotonic() + timeout
    while True:
        graph = asyncio.run(PipeWire().dump())
        if predicate(graph):  # type: ignore[operator]
            return graph
        if time.monotonic() > deadline:
            raise AssertionError("o grafo não chegou no estado esperado")
        time.sleep(0.2)


@pytest.fixture
def game(tmp_path: Path) -> Iterator[None]:
    null_sink("saida_principal")
    null_sink("Wireless_Controller_teste")
    graph = wait_for(lambda gr: gr.ds4_sink() is not None)
    main = next(n for n in graph.nodes.values() if n.name == "saida_principal")
    subprocess.run(["wpctl", "set-default", str(main.id)], check=True)
    tone = write_test_tone(tmp_path / "jogo.wav", seconds=30)
    proc = subprocess.Popen(
        ["pw-play", "--properties={ application.name = RPCS3 }", "--target=saida_principal", str(tone)]
    )
    try:
        wait_for(lambda gr: any(gr.ports_of(s.id, "out") for s in gr.streams(APPS)))
        yield
    finally:
        proc.terminate()
        proc.wait()


@pytest.mark.usefixtures("game")
def test_mirror_on_and_off() -> None:
    pw = PipeWire()
    graph = asyncio.run(pw.dump())
    assert not g.is_mirroring(graph, APPS)
    pairs = g.missing_links(graph, APPS)
    assert len(pairs) == 2

    async def link_all() -> None:
        for out_port, in_port in pairs:
            await pw.link(out_port, in_port)

    asyncio.run(link_all())
    graph = wait_for(lambda gr: g.is_mirroring(gr, APPS))
    assert g.missing_links(graph, APPS) == []
    # A saída principal continua recebendo o jogo.
    main = next(n for n in graph.nodes.values() if n.name == "saida_principal")
    main_inputs = {p.id for p in graph.ports_of(main.id, "in")}
    assert any(link.input_port in main_inputs for link in graph.links)

    async def unlink_all() -> None:
        for out_port, in_port in g.mirror_links(graph, APPS):
            await pw.unlink(out_port, in_port)

    asyncio.run(unlink_all())
    wait_for(lambda gr: not g.is_mirroring(gr, APPS))


@pytest.mark.usefixtures("game")
def test_set_volume_on_controller_sink() -> None:
    pw = PipeWire()
    sink = asyncio.run(pw.dump()).ds4_sink()
    assert sink is not None
    asyncio.run(pw.set_volume(sink.id, 0.32))
    graph = wait_for(
        lambda gr: (s := gr.ds4_sink()) is not None and s.volume is not None and abs(s.volume - 0.32) < 0.01
    )
    assert graph.ds4_sink() is not None

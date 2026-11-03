# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
import json
import os
import stat
import sys
import wave
from pathlib import Path

import pytest

from ds4_companion.daemon.audio import graph as g
from ds4_companion.daemon.audio import pipewire as pw

sys.path.insert(0, str(Path(__file__).parent))
import pwfixtures as fx

APPS = ["rpcs3", "AppRun.wrapped"]


def test_parse_dump() -> None:
    graph = g.parse_dump(fx.dump())
    sink = graph.ds4_sink()
    assert sink is not None
    assert sink.id == 97
    assert sink.volume == pytest.approx(0.4)
    assert graph.default_sink == fx.HDMI_SINK
    default = graph.default_sink_node()
    assert default is not None
    assert default.description == "Monitor HDMI"
    assert [n.id for n in graph.streams(APPS)] == [120]
    assert [p.id for p in graph.ports_of(97, "out")] == []  # monitor fica de fora


def test_parse_garbage_does_not_crash() -> None:
    assert g.parse_dump({"x": 1}) == g.Graph()
    garbage = [
        1,
        {"id": "x"},
        {"id": True, "type": "PipeWire:Interface:Node"},
        {"id": 5, "type": "PipeWire:Interface:Node", "info": "nada"},
        {"id": 6, "type": "PipeWire:Interface:Port", "info": {"props": {"node.id": "lixo"}}},
        {"id": 7, "type": "PipeWire:Interface:Link", "info": {"output-port-id": None}},
        {"id": "8", "type": "PipeWire:Interface:Node", "info": {"params": {"Props": [1, {"channelVolumes": ["a"]}]}}},
        {"id": 9, "type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": 3},
        {"id": 10, "type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": [1]},
    ]
    graph = g.parse_dump(garbage)
    assert set(graph.nodes) == {5, 8}
    assert graph.nodes[8].volume is None
    assert graph.ports == []
    assert graph.links == []


def test_plan_links_for_stereo_game() -> None:
    graph = g.parse_dump(fx.dump())
    assert g.missing_links(graph, APPS) == [(121, 99), (122, 100)]
    assert not g.is_mirroring(graph, APPS)
    assert g.mirror_links(graph, APPS) == []


def test_already_mirrored() -> None:
    graph = g.parse_dump(fx.dump(mirrored=True))
    assert g.missing_links(graph, APPS) == []
    assert g.is_mirroring(graph, APPS)
    assert g.mirror_links(graph, APPS) == [(121, 99), (122, 100)]


def test_ds4_as_default_output_is_not_unlinked() -> None:
    graph = g.parse_dump(fx.dump(mirrored=True, default=fx.DS4_SINK))
    assert g.mirror_links(graph, APPS) == []


def test_no_controller_or_no_game() -> None:
    assert g.missing_links(g.parse_dump(fx.dump(ds4=False)), APPS) == []
    assert g.missing_links(g.parse_dump(fx.dump(game=False)), APPS) == []
    assert g.mirror_links(g.parse_dump(fx.dump(ds4=False)), APPS) == []


def test_other_apps_are_not_mirrored() -> None:
    objs = [
        *fx.dump(game=False),
        fx.node(200, "Firefox", "Stream/Output/Audio", **{"application.name": "Firefox"}),
        fx.port(201, 200, "out", "FL"),
    ]
    assert g.missing_links(g.parse_dump(objs), APPS) == []


def test_binary_match_and_surround_downmix() -> None:
    objs = [
        *fx.dump(game=False),
        fx.node(300, "x", "Stream/Output/Audio", **{"application.process.binary": "AppRun.wrapped"}),
        fx.port(301, 300, "out", "FC"),
        fx.port(302, 300, "out", "LFE"),
        fx.port(303, 300, "out", "RR"),
        fx.port(304, 300, "out", "MONO"),
    ]
    links = g.missing_links(g.parse_dump(objs), APPS)
    assert links == [(301, 99), (301, 100), (303, 100), (304, 99), (304, 100)]


# --- comandos ------------------------------------------------------------------------------


@pytest.fixture
def fake_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """pw-dump/pw-link/wpctl/pw-play falsos: gravam os argumentos em calls.log."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "calls.log"
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps(fx.dump()))
    script = f"""#!{sys.executable}
import os, sys, time
name = os.path.basename(sys.argv[0])
with open({str(log)!r}, "a") as f:
    f.write(" ".join([name, *sys.argv[1:]]) + "\\n")
mode = os.environ.get("FAKE_MODE", "")
if mode == "fail":
    sys.stderr.write("erro qualquer\\nFile exists\\n" if name == "pw-link" else "deu ruim\\n")
    sys.exit(1)
if mode == "slow":
    time.sleep(5)
if name == "pw-dump":
    if "--monitor" in sys.argv:
        for _ in range(3):
            sys.stdout.write("[]\\n"); sys.stdout.flush(); time.sleep(0.05)
    elif mode == "badjson":
        sys.stdout.write("{{")
    else:
        sys.stdout.write(open({str(dump)!r}).read())
"""
    for name in ("pw-dump", "pw-link", "wpctl", "pw-play"):
        exe = bindir / name
        exe.write_text(script)
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    return tmp_path


def calls(fake_bin: Path) -> list[str]:
    return (fake_bin / "calls.log").read_text().splitlines()


def test_commands(fake_bin: Path) -> None:
    async def scenario() -> None:
        p = pw.PipeWire()
        graph = await p.dump()
        assert graph.ds4_sink() is not None
        await p.link(121, 99)
        await p.unlink(121, 99)
        await p.set_volume(97, 0.4)
        await p.play(fake_bin / "a.wav", "-nome")
        events = [e async for e in p.events()]
        assert len(events) >= 1

    asyncio.run(scenario())
    assert calls(fake_bin)[:5] == [
        "pw-dump --no-colors",
        "pw-link 121 99",
        "pw-link --disconnect 121 99",
        "wpctl set-volume 97 0.4000",
        f"pw-play --target=-nome {fake_bin / 'a.wav'}",
    ]


def test_link_that_already_exists_is_ok(fake_bin: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_MODE", "fail")
    asyncio.run(pw.PipeWire().link(1, 2))
    with pytest.raises(pw.PipeWireError, match="deu ruim"):
        asyncio.run(pw.PipeWire().set_volume(1, 0.3))


def test_bad_json(fake_bin: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_MODE", "badjson")
    with pytest.raises(pw.PipeWireError, match="JSON"):
        asyncio.run(pw.PipeWire().dump())


def test_timeout(fake_bin: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_MODE", "slow")
    with pytest.raises(pw.PipeWireError, match="não respondeu"):
        asyncio.run(pw._run("wpctl", "status", timeout=0.2))


def test_missing_binary() -> None:
    with pytest.raises(pw.PipeWireError, match="não encontrado"):
        asyncio.run(pw._run("comando-que-nao-existe-ds4"))


@pytest.mark.parametrize("volume", [-1.0, float("nan")])
def test_invalid_volume(volume: float) -> None:
    with pytest.raises(ValueError, match="inválido"):
        asyncio.run(pw.PipeWire().set_volume(1, volume))


def test_test_tone(tmp_path: Path) -> None:
    path = pw.write_test_tone(tmp_path / "apito.wav", db=-12.0, seconds=0.1)
    with wave.open(str(path)) as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (2, 48000, 4800)
        frames = w.readframes(w.getnframes())
    samples = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in range(0, len(frames), 4)]
    assert samples[0] == 0
    assert max(abs(s) for s in samples) <= int(32767 * 10 ** (-12 / 20)) + 1


def proton_dump() -> list[object]:
    """Um jogo do Proton (Wine dá o nome do .exe ao stream), o Firefox e o RPCS3."""
    return [
        *fx.dump(),
        fx.node(
            400,
            "Elden Ring",
            "Stream/Output/Audio",
            **{"application.name": "eldenring.exe", "application.process.binary": "wine64-preloader"},
        ),
        fx.port(401, 400, "out", "FL"),
        fx.port(402, 400, "out", "FR"),
        fx.node(200, "Firefox", "Stream/Output/Audio", **{"application.name": "Firefox"}),
        fx.port(201, 200, "out", "FL"),
        fx.node(210, "Firefox 2", "Stream/Output/Audio", **{"application.name": "Firefox"}),
    ]


def test_patterns_match_proton_games_case_insensitively() -> None:
    graph = g.parse_dump(proton_dump())
    assert [n.id for n in graph.streams(["*.EXE"])] == [400]
    assert [n.id for n in graph.streams(["wine*"])] == [400]
    assert [n.id for n in graph.streams(["rpcs3", "*.exe"])] == [120, 400]
    assert (401, 99) in g.missing_links(graph, ["*.exe"])
    # Um nome sem curinga continua exato: "rpcs" não pega o "RPCS3".
    assert graph.streams(["rpcs"]) == []


def test_playing_lists_every_app_once() -> None:
    graph = g.parse_dump(proton_dump())
    assert graph.playing() == ["RPCS3", "Firefox", "eldenring.exe"]  # ordem do ID do nó
    assert g.parse_dump(fx.dump(game=False)).playing() == []

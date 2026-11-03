# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
import os
import stat
import sys
from pathlib import Path

import pytest

from ds4_companion.daemon.audio import graph as g
from ds4_companion.daemon.audio import limiter as lim

sys.path.insert(0, str(Path(__file__).parent))
import pwfixtures as fx

APPS = ["rpcs3"]


def with_limiter(mirrored_direct: bool = False, via_limiter: bool = False) -> list[object]:
    objs = fx.dump(mirrored=mirrored_direct)
    objs += [
        fx.node(150, g.LIMITER_INPUT, "Stream/Input/Audio"),
        fx.port(151, 150, "in", "FL"),
        fx.port(152, 150, "in", "FR"),
        fx.node(160, g.LIMITER_OUTPUT, "Stream/Output/Audio", **{"application.name": "rpcs3"}),
        fx.port(161, 160, "out", "FL"),
    ]
    if via_limiter:
        objs += [fx.link(170, 121, 151), fx.link(171, 122, 152)]
    return objs


def test_target_is_limiter_when_present() -> None:
    graph = g.parse_dump(with_limiter())
    target = graph.mirror_target()
    assert target is not None
    assert target.name == g.LIMITER_INPUT
    assert g.missing_links(graph, APPS) == [(121, 151), (122, 152)]
    # A saída do limitador nunca é tratada como app, mesmo que o nome case.
    assert [n.id for n in graph.streams(APPS)] == [120]


def test_direct_links_become_stale_with_limiter() -> None:
    graph = g.parse_dump(with_limiter(mirrored_direct=True, via_limiter=True))
    assert g.stale_links(graph, APPS) == [(121, 99), (122, 100)]
    assert g.is_mirroring(graph, APPS)
    assert g.mirror_links(graph, APPS) == [(121, 151), (122, 152), (121, 99), (122, 100)]


def test_without_limiter_nothing_is_stale() -> None:
    graph = g.parse_dump(fx.dump(mirrored=True))
    assert g.stale_links(graph, APPS) == []
    assert graph.mirror_target() is graph.ds4_sink()
    assert g.parse_dump(fx.dump(ds4=False)).mirror_target() is None


def test_config_text_escapes_untrusted_sink_name() -> None:
    text = lim.config_text('sink "com" aspas\\barra')
    assert 'target.object      = "sink \\"com\\" aspas\\\\barra"' in text
    assert '"Max" = 0.891251' in text
    assert '"Min" = -0.891251' in text
    assert f'node.name         = "{g.LIMITER_INPUT}"' in text
    assert "node.autoconnect  = false" in text
    assert lim.limit_amplitude(0.0) == 1.0


@pytest.fixture
def fake_pipewire(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "starts.log"
    exe = bindir / "pipewire"
    exe.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexec sleep 30\n')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    return tmp_path


def test_limiter_process_lifecycle(fake_pipewire: Path) -> None:
    async def scenario() -> None:
        limiter = lim.Limiter(conf_dir=fake_pipewire)
        assert await limiter.ensure(None) is False
        assert await limiter.ensure("sink_a") is True
        assert limiter.running
        assert await limiter.ensure("sink_a") is False  # mesmo destino: nada muda
        assert await limiter.ensure("sink_b") is True  # destino novo: reinicia
        assert "sink_b" in (fake_pipewire / "ds4-companion-limiter.conf").read_text()
        assert await limiter.ensure(None) is True
        assert not limiter.running
        await limiter.stop()

    asyncio.run(scenario())
    starts = (fake_pipewire / "starts.log").read_text().splitlines()
    assert len(starts) == 2
    assert starts[0].startswith("-c ")


def test_limiter_without_pipewire_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    limiter = lim.Limiter(conf_dir=tmp_path)
    assert asyncio.run(limiter.ensure("x")) is False
    assert not limiter.running


def test_limiter_stop_kills_stubborn_process(fake_pipewire: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        limiter = lim.Limiter(conf_dir=fake_pipewire)
        await limiter.ensure("x")
        real_wait_for = asyncio.wait_for

        async def no_patience(aw: object, timeout: float) -> object:
            if timeout == 3:
                aw.close()  # type: ignore[attr-defined]
                raise TimeoutError
            return await real_wait_for(aw, timeout)  # type: ignore[arg-type]

        monkeypatch.setattr(lim.asyncio, "wait_for", no_patience)
        await limiter.stop()
        assert not limiter.running

    asyncio.run(scenario())


def test_runtime_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert lim.runtime_dir() == tmp_path


def test_limiter_that_exits_at_start_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "pipewire"
    exe.write_text("#!/bin/sh\nexit 1\n")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))
    limiter = lim.Limiter(conf_dir=tmp_path)
    assert asyncio.run(limiter.ensure("x")) is False
    assert not limiter.running


def test_limiter_never_upmixes_to_dualsense_haptic_channels() -> None:
    # O sink do DualSense tem 4 canais e RL/RR são os atuadores hápticos: o estéreo do limitador
    # não pode ser espalhado para trás pelo upmix do PipeWire (ADR 0011).
    text = lim.config_text("alsa_output.usb-Sony_DualSense_Wireless_Controller-00.analog-surround-40")
    playback = text.split("playback.props")[1]
    assert "channelmix.upmix   = false" in playback

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Coroutine
from pathlib import Path
from typing import Any

import pytest

from ds4_companion.common import config as cfg
from ds4_companion.common.db import db_to_volume
from ds4_companion.common.models import Connection, Status
from ds4_companion.daemon import service
from ds4_companion.daemon.audio import graph as g
from ds4_companion.daemon.audio.pipewire import PipeWireError
from ds4_companion.daemon.device import Controller
from ds4_companion.daemon.hid import hidraw

sys.path.insert(0, str(Path(__file__).parent))
import pwfixtures as fx

FIXTURE = Path(__file__).parents[2] / "fixtures" / "Default.yml"


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


class FakeAudio:
    """PipeWire em memória: link/volume mudam o próprio dump."""

    def __init__(self, objs: list[Any]) -> None:
        self.objs = objs
        self.calls: list[tuple[Any, ...]] = []
        self.fail = False
        self.next_link = 500

    async def dump(self) -> g.Graph:
        if self.fail:
            raise PipeWireError("pw-dump não encontrado")
        return g.parse_dump(self.objs)

    async def link(self, output_port: int, input_port: int) -> None:
        self.calls.append(("link", output_port, input_port))
        self.objs.append(fx.link(self.next_link, output_port, input_port))
        self.next_link += 1

    async def unlink(self, output_port: int, input_port: int) -> None:
        self.calls.append(("unlink", output_port, input_port))
        self.objs = [
            o
            for o in self.objs
            if not (
                o.get("type") == "PipeWire:Interface:Link"
                and (o["info"]["output-port-id"], o["info"]["input-port-id"]) == (output_port, input_port)
            )
        ]

    async def set_volume(self, node_id: int, volume: float) -> None:
        self.calls.append(("volume", node_id, round(volume, 4)))
        for o in self.objs:
            if o.get("id") == node_id:
                o["info"]["params"] = {"Props": [{"channelVolumes": [volume**3, volume**3]}]}

    async def play(self, path: Path, target: str) -> None:
        self.calls.append(("play", path.name, target))


class FakeDevices:
    def __init__(self, controllers: list[Controller]) -> None:
        self.controllers = controllers

    def scan(self) -> list[Controller]:
        return list(self.controllers)


class Env:
    def __init__(self, tmp_path: Path, objs: list[Any] | None = None, connection: Connection = Connection.USB):
        self.hidraw = tmp_path / "hidraw7"
        self.hidraw.write_bytes(b"")
        battery = tmp_path / "bat"
        battery.mkdir()
        (battery / "capacity").write_text("70")
        (battery / "status").write_text("Discharging")
        rpcs3 = tmp_path / "rpcs3" / "input_configs" / "global"
        rpcs3.mkdir(parents=True)
        self.yml = rpcs3 / "Default.yml"
        self.yml.write_text(FIXTURE.read_text())
        self.config_path = tmp_path / "config.toml"
        c = cfg.Config()
        c.rpcs3.config_dir = str(tmp_path / "rpcs3")
        cfg.save(c, self.config_path)

        self.audio = FakeAudio(objs if objs is not None else fx.dump())
        self.devices = FakeDevices([Controller(str(self.hidraw), connection, 0x09CC, str(battery))])
        self.reports: list[bytes] = []
        self.rpcs3 = False
        self.input: bytes | None = None
        self.read_error: OSError | None = None
        self.write_error: OSError | None = None
        self.statuses: list[Status] = []

        async def no_sleep(seconds: float) -> None:
            await asyncio.sleep(0)

        def write(path: str, report: bytes) -> None:
            if self.write_error:
                raise self.write_error
            self.reports.append(report)

        def read(path: str) -> bytes | None:
            if self.read_error:
                raise self.read_error
            return self.input

        self.daemon = service.Daemon(
            self.audio,
            self.devices,
            self.config_path,
            write_report=write,
            read_report=read,
            rpcs3_running=lambda: self.rpcs3,
            sleep=no_sleep,
        )
        self.daemon.subscribe(self.statuses.append)


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def test_refresh_mirrors_and_reports_status(env: Env) -> None:
    run(env.daemon.refresh())
    s = env.daemon.status
    assert ("link", 121, 99) in env.audio.calls
    assert ("link", 122, 100) in env.audio.calls
    assert s.connection == Connection.USB
    assert s.battery == 70
    assert not s.charging
    assert s.mirror_active
    assert s.game_running
    assert s.sink_present
    assert s.output_name == "Monitor HDMI"
    assert s.playing == ["RPCS3"]
    assert s.volume_db == pytest.approx(-6.0, abs=0.01)  # volume salvo reaplicado ao achar o controle
    assert env.statuses
    assert env.statuses[-1] == s
    # A cor salva vai para o controle assim que ele aparece.
    assert env.reports
    assert env.reports[0][1] == 0x02


def test_second_refresh_does_not_relink(env: Env) -> None:
    run(env.daemon.refresh())
    count = len(env.audio.calls)
    run(env.daemon.refresh())
    assert len(env.audio.calls) == count


def test_mirror_off_removes_links(env: Env) -> None:
    run(env.daemon.refresh())
    run(env.daemon.set_mirror(False))
    assert ("unlink", 121, 99) in env.audio.calls
    assert not env.daemon.status.mirror_active
    assert not cfg.load(env.config_path)[0].audio.mirror_enabled


def test_volume_needs_confirmation_above_zero(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.daemon.config.audio.max_db = 3.0
    run(env.daemon.refresh())
    with pytest.raises(service.DaemonError) as info:
        run(env.daemon.set_volume(2.0))
    assert info.value.code == "NeedsConfirmation"
    assert run(env.daemon.set_volume(2.0, confirm=True)) == 2.0
    assert run(env.daemon.set_volume(9.0, confirm=True)) == 3.0  # nunca passa do teto


def test_volume_is_clamped_to_ceiling(env: Env) -> None:
    run(env.daemon.refresh())
    assert run(env.daemon.set_volume(5.0)) == 0.0
    assert run(env.daemon.set_volume(-12.0)) == -12.0
    assert env.daemon.status.volume_db == pytest.approx(-12.0, abs=0.01)
    assert cfg.load(env.config_path)[0].audio.volume_db == -12.0
    with pytest.raises(service.DaemonError, match="número"):
        run(env.daemon.set_volume(float("nan")))


def test_external_volume_change_above_ceiling_is_lowered(env: Env) -> None:
    run(env.daemon.refresh())
    run(env.audio.set_volume(97, db_to_volume(6.0)))  # outro app aumentou o volume
    run(env.daemon.refresh())
    assert env.daemon.status.volume_db == pytest.approx(0.0, abs=0.01)


def test_headphones_lower_the_ceiling(env: Env) -> None:
    report = bytearray(64)
    report[0], report[30] = 0x01, 0x30
    env.input = bytes(report)
    run(env.daemon.set_volume(-1.0))
    run(env.daemon.refresh())
    assert env.daemon.status.headphones
    assert env.daemon.status.max_db == -6.0
    assert env.daemon.status.volume_db == pytest.approx(-6.0, abs=0.01)


def test_hid_access_error_is_reported(env: Env) -> None:
    env.read_error = hidraw.HidAccessError(13, "sem permissão")
    run(env.daemon.refresh())
    assert not env.daemon.status.hid_access
    env.read_error = OSError(5, "I/O")
    run(env.daemon.refresh())


def test_vibration_is_written_to_rpcs3_with_backup(env: Env) -> None:
    run(env.daemon.refresh())
    run(env.daemon.set_vibration(150, 40, True))
    text = env.yml.read_text()
    assert "Large Vibration Motor Multiplier: 150" in text
    assert "Small Vibration Motor Multiplier: 40" in text
    assert list(env.yml.parent.glob("Default.yml.bak-*"))
    assert not env.daemon.status.vibration_pending


def test_rpcs3_open_keeps_changes_pending(env: Env) -> None:
    env.rpcs3 = True
    run(env.daemon.refresh())
    reports_before = len(env.reports)
    run(env.daemon.set_vibration(120, 120, False))
    run(env.daemon.set_led("red"))
    assert env.daemon.status.vibration_pending
    assert env.daemon.status.rpcs3_running
    assert "120" not in env.yml.read_text()
    assert len(env.reports) == reports_before  # nada no hidraw com o RPCS3 aberto
    with pytest.raises(service.DaemonError) as info:
        run(env.daemon.test_rumble("both"))
    assert info.value.code == "Busy"

    env.rpcs3 = False  # fechou o RPCS3: aplica tudo
    run(env.daemon.refresh())
    text = env.yml.read_text()
    assert "Large Vibration Motor Multiplier: 120" in text
    assert "Color Value R: 255" in text
    assert env.reports[-1][6:9] == bytes([255, 0, 0])
    assert not env.daemon.status.vibration_pending


def test_players_validation(env: Env) -> None:
    run(env.daemon.set_players([2, 1]))
    assert env.daemon.status.players == [1, 2]
    with pytest.raises(service.DaemonError):
        run(env.daemon.set_players([0]))
    with pytest.raises(service.DaemonError):
        run(env.daemon.set_vibration(201, 0, False))


def test_rumble(env: Env) -> None:
    run(env.daemon.refresh())
    env.reports.clear()
    run(env.daemon.test_rumble("strong"))
    start, stop = env.reports
    assert (start[4], start[5]) == (0, 255)
    assert (stop[4], stop[5]) == (0, 0)
    with pytest.raises(service.DaemonError) as info:
        run(env.daemon.test_rumble("weak"))  # intervalo mínimo
    assert info.value.code == "Busy"
    env.daemon._last_rumble = -1e9
    env.daemon.config.vibration.swap_motors = True
    env.reports.clear()
    run(env.daemon.test_rumble("weak"))
    assert (env.reports[0][4], env.reports[0][5]) == (0, 255)  # invertido: o fraco vira o forte
    with pytest.raises(service.DaemonError):
        run(env.daemon.test_rumble("lateral"))


def test_rumble_errors(env: Env) -> None:
    run(env.daemon.refresh())
    env.write_error = hidraw.HidAccessError(13, "x")
    with pytest.raises(service.DaemonError) as info:
        run(env.daemon.test_rumble("both"))
    assert info.value.code == "AccessDenied"
    env.daemon._last_rumble = -1e9
    env.write_error = OSError(5, "I/O")
    with pytest.raises(service.DaemonError) as info:
        run(env.daemon.test_rumble("both"))
    assert info.value.code == "Failed"


def test_without_controller(tmp_path: Path) -> None:
    env = Env(tmp_path, fx.dump(ds4=False))
    env.devices.controllers = []
    run(env.daemon.refresh())
    s = env.daemon.status
    assert s.connection == Connection.NONE
    assert not s.sink_present
    assert s.battery == -1
    with pytest.raises(service.DaemonError) as info:
        run(env.daemon.test_rumble("both"))
    assert info.value.code == "NotConnected"
    with pytest.raises(service.DaemonError):
        run(env.daemon.play_test_tone())
    run(env.daemon.set_volume(-3.0))  # sem controle: só salva
    assert cfg.load(env.config_path)[0].audio.volume_db == -3.0
    env.daemon.stop_motors()


def test_bluetooth_has_no_audio(tmp_path: Path) -> None:
    env = Env(tmp_path, fx.dump(ds4=False), Connection.BLUETOOTH)
    run(env.daemon.refresh())
    assert env.daemon.status.connection == Connection.BLUETOOTH
    assert not env.daemon.status.sink_present
    assert not env.daemon.status.headphones
    assert env.reports[0][0] == 0x11


def test_led(env: Env) -> None:
    run(env.daemon.refresh())
    run(env.daemon.set_led("rosa"))
    assert env.daemon.status.led_color == "pink"
    assert env.reports[-1][6:9] == bytes([0xFF, 0x14, 0x93])
    assert "Color Value G: 20" in env.yml.read_text()
    with pytest.raises(service.DaemonError):
        run(env.daemon.set_led("magenta"))


def test_led_failure_keeps_pending(env: Env) -> None:
    env.write_error = hidraw.HidAccessError(13, "x")
    run(env.daemon.refresh())
    assert not env.daemon.status.hid_access
    env.write_error = None
    run(env.daemon.refresh())
    assert env.reports


def test_test_tone(env: Env, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    run(env.daemon.refresh())
    run(env.daemon.play_test_tone())
    assert env.audio.calls[-1] == ("play", "ds4-companion-apito.wav", fx.DS4_SINK)


def test_apps_dir_backup_and_defaults(env: Env, tmp_path: Path) -> None:
    run(env.daemon.set_apps(["rpcs3", "steam"]))
    assert env.daemon.status.apps == ["rpcs3", "steam"]
    with pytest.raises(service.DaemonError):
        run(env.daemon.set_apps([""]))
    with pytest.raises(service.DaemonError, match="todo o som"):
        run(env.daemon.set_apps(["*"]))
    run(env.daemon.set_rpcs3_dir(str(tmp_path)))
    assert env.daemon.status.rpcs3_config_dir == str(tmp_path)
    with pytest.raises(service.DaemonError):
        run(env.daemon.set_rpcs3_dir(str(tmp_path / "nada")))
    run(env.daemon.set_backup(False))
    assert not env.daemon.status.backup_before_edit
    run(env.daemon.restore_defaults())
    assert env.daemon.status.apps == ["rpcs3", "AppRun.wrapped"]
    assert env.daemon.status.backup_before_edit


def test_pipewire_failure_is_shown(env: Env) -> None:
    env.audio.fail = True
    run(env.daemon.refresh())
    assert "pw-dump" in env.daemon.status.error
    env.audio.fail = False
    run(env.daemon.refresh())
    assert env.daemon.status.error == ""


def test_link_failure_is_shown(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken(*args: Any) -> None:
        raise PipeWireError("pw-link falhou")

    monkeypatch.setattr(env.audio, "link", broken)
    run(env.daemon.refresh())
    assert "pw-link" in env.daemon.status.error
    monkeypatch.setattr(env.audio, "set_volume", broken)
    with pytest.raises(service.DaemonError, match="volume"):
        run(env.daemon.set_volume(-3.0))
    monkeypatch.setattr(env.audio, "play", broken)
    with pytest.raises(service.DaemonError, match="apito"):
        run(env.daemon.play_test_tone())


def test_missing_rpcs3_file(env: Env) -> None:
    env.yml.unlink()
    run(env.daemon.set_vibration(90, 90, False))
    assert not env.daemon.status.vibration_pending


def test_broken_rpcs3_dir(env: Env) -> None:
    env.yml.unlink()
    env.yml.mkdir()  # não dá para ler como arquivo
    run(env.daemon.set_vibration(90, 90, False))
    assert env.daemon.status.vibration_pending


def test_save_failure(env: Env) -> None:
    env.daemon._config_path = env.hidraw / "x" / "config.toml"
    with pytest.raises(service.DaemonError, match="salvar"):
        run(env.daemon.set_backup(True))


def test_schedule_refresh_and_watchers(env: Env) -> None:
    async def scenario() -> None:
        env.daemon.schedule_refresh()
        env.daemon.schedule_refresh()  # agrupado com o anterior
        assert env.daemon._refresh_task is not None
        await env.daemon._refresh_task

        async def events() -> AsyncIterator[None]:
            yield None
            raise PipeWireError("caiu")

        task = asyncio.ensure_future(env.daemon.watch_audio(events))
        poll = asyncio.ensure_future(env.daemon.poll_forever())
        for _ in range(20):
            await asyncio.sleep(0)
        task.cancel()
        poll.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    run(scenario())
    assert env.daemon.status.connection == Connection.USB


def test_refresh_errors_in_background_are_logged(env: Env, caplog: pytest.LogCaptureFixture) -> None:
    async def boom() -> None:
        raise RuntimeError("x")

    env.daemon.refresh = boom  # type: ignore[method-assign]

    async def scenario() -> None:
        env.daemon.schedule_refresh()
        assert env.daemon._refresh_task is not None
        await env.daemon._refresh_task
        poll = asyncio.ensure_future(env.daemon.poll_forever())
        for _ in range(5):
            await asyncio.sleep(0)
        poll.cancel()

    run(scenario())
    assert "falha ao atualizar" in caplog.text


def test_invalid_config_is_logged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    env = Env(tmp_path)
    env.config_path.write_text("[audio]\nvolume_db = 'alto'\n")
    service.Daemon(env.audio, env.devices, env.config_path)
    assert "volume_db" in caplog.text


def test_only_one_backup_per_daemon_run(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regressão: cada ajuste (ex.: arrastar o slider) criava um Default.yml.bak-* novo.
    from ds4_companion.daemon.rpcs3 import input_config

    ticks = iter(range(100))
    monkeypatch.setattr(input_config.time, "strftime", lambda fmt: f"20261102-2200{next(ticks):02d}")
    run(env.daemon.refresh())
    run(env.daemon.set_vibration(110, 100, False))
    env.daemon._rpcs3_pending = True
    run(env.daemon.set_vibration(120, 100, False))
    run(env.daemon.set_led("green"))
    assert len(list(env.yml.parent.glob("Default.yml.bak-*"))) == 1
    assert "Large Vibration Motor Multiplier: 120" in env.yml.read_text()


class FakeLimiter:
    def __init__(self) -> None:
        self.targets: list[str | None] = []
        self.current: str | None = None
        self.stopped = False

    async def ensure(self, target: str | None) -> bool:
        self.targets.append(target)
        changed = target != self.current
        self.current = target
        return changed

    async def stop(self) -> None:
        self.stopped = True


def test_limiter_follows_mirror_and_setting(tmp_path: Path) -> None:
    env = Env(tmp_path)
    fake = FakeLimiter()
    env.daemon._limiter = fake
    run(env.daemon.refresh())
    assert fake.current == fx.DS4_SINK
    assert env.daemon.status.limiter
    run(env.daemon.set_limiter(False))
    assert fake.current is None
    assert not cfg.load(env.config_path)[0].audio.limiter
    run(env.daemon.set_limiter(True))
    run(env.daemon.set_mirror(False))
    assert fake.current is None  # sem espelhamento, sem limitador
    run(env.daemon.stop_limiter())
    assert fake.stopped


def test_mirror_goes_through_limiter_and_drops_direct_links(tmp_path: Path) -> None:
    from ds4_companion.daemon.audio import graph as g

    objs = fx.dump(mirrored=True)
    objs += [
        fx.node(150, g.LIMITER_INPUT, "Stream/Input/Audio"),
        fx.port(151, 150, "in", "FL"),
        fx.port(152, 150, "in", "FR"),
    ]
    env = Env(tmp_path, objs)
    env.daemon._limiter = FakeLimiter()
    run(env.daemon.refresh())
    assert ("unlink", 121, 99) in env.audio.calls
    assert ("link", 121, 151) in env.audio.calls
    assert env.daemon.status.limiter_active
    assert env.daemon.status.mirror_active

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import asyncio
import io
from typing import Any

import pytest
from dbus_next.errors import DBusError
from dbus_next.signature import Variant

from ds4_companion.cli import __main__ as cli
from ds4_companion.common.models import Connection, Status
from ds4_companion.daemon.dbus import status_variants


class FakeProxy:
    def __init__(self, status: Status) -> None:
        self.status = status
        self.calls: list[tuple[Any, ...]] = []

    async def get_status(self) -> dict[str, Variant]:
        return status_variants(self.status)

    def __getattr__(self, name: str) -> Any:
        if not name.startswith("call_"):
            raise AttributeError(name)

        async def call(*args: Any) -> Any:
            self.calls.append((name, *args))
            if name == "call_set_led" and args[0] == "magenta":
                raise DBusError("x.Error.InvalidArgument", "Cor desconhecida: magenta.")
            if name == "call_set_volume":
                return min(args[0], self.status.max_db)
            if name == "call_set_vibration":
                self.status.large_percent, self.status.small_percent, self.status.swap_motors = args
            return None

        return call


class FakeBus:
    def __init__(self) -> None:
        self.disconnected = False

    def disconnect(self) -> None:
        self.disconnected = True


@pytest.fixture
def proxy(monkeypatch: pytest.MonkeyPatch) -> FakeProxy:
    p = FakeProxy(Status(connection=Connection.USB, battery=80, players=[1, 2], output_name="TV"))
    connections: list[int] = []

    async def fake_connect() -> tuple[FakeBus, FakeProxy]:
        connections.append(1)
        return FakeBus(), p

    monkeypatch.setattr(cli, "connect", fake_connect)
    p.connections = connections  # type: ignore[attr-defined]
    return p


def ds4ctl(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    code = asyncio.run(cli.amain(list(argv), out))
    return code, out.getvalue()


def test_status(proxy: FakeProxy) -> None:
    code, text = ds4ctl("status")
    assert code == 0
    assert "DualShock 4 — cabo USB" in text
    assert "bateria 80 %" in text
    assert "Saída principal: TV" in text
    assert "jogadores 1, 2" in text


def test_volume_and_ceiling(proxy: FakeProxy) -> None:
    assert ds4ctl("volume", "-6") == (0, "Volume do controle: −6 dB\n")
    code, text = ds4ctl("volume", "3", "--yes")
    assert code == 0
    assert "teto" in text
    assert ("call_set_volume", 3.0, True) in proxy.calls


def test_declined_over_limit_does_not_touch_the_bus(proxy: FakeProxy, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regressão: recusar desconectava no meio do registro do dbus-next e despejava um traceback.
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    code, text = ds4ctl("volume", "2")
    assert code == 1
    assert text == "Volume não alterado.\n"
    assert proxy.connections == []  # type: ignore[attr-defined]


def test_accepted_over_limit(proxy: FakeProxy, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "sim")
    assert ds4ctl("volume", "2")[0] == 0
    assert ("call_set_volume", 2.0, True) in proxy.calls


def test_confirm_handles_eof() -> None:
    def eof(prompt: str) -> str:
        raise EOFError

    assert not cli.confirm_over_limit(2.0, eof)


def test_mirror_led_rumble_tone(proxy: FakeProxy) -> None:
    assert ds4ctl("mirror", "off") == (0, "Som no controle desligado.\n")
    assert ds4ctl("mirror", "on")[0] == 0
    assert ds4ctl("limiter", "off") == (0, "Limitador desligado.\n")
    assert ("call_set_limiter", False) in proxy.calls
    assert ds4ctl("led", "rosa")[0] == 0
    assert ds4ctl("led-mode", "battery") == (0, "A luz mostra a bateria.\n")
    assert ds4ctl("led-mode", "fixed")[0] == 0
    assert ds4ctl("test-rumble")[0] == 0
    assert ds4ctl("test-tone")[0] == 0
    assert ("call_test_rumble", "both") in proxy.calls
    assert ds4ctl("led", "magenta")[0] == 1


def test_vibration_keeps_unchanged_values(proxy: FakeProxy) -> None:
    code, text = ds4ctl("vibration", "--large", "150", "--players", "1")
    assert code == 0
    assert ("call_set_vibration", 150, 100, False) in proxy.calls
    assert ("call_set_players", [1]) in proxy.calls
    assert "Vale ao abrir o RPCS3." in text
    proxy.status.vibration_pending = True
    assert "RPCS3 está aberto" in ds4ctl("vibration", "--swap")[1]


def test_no_daemon(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    async def fail() -> None:
        raise OSError("sem barramento")

    monkeypatch.setattr(cli, "connect", fail)
    assert ds4ctl("status")[0] == 3
    assert "systemctl --user start ds4-companion.service" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (Status(), "Controle: nenhum conectado"),
        (Status(connection=Connection.BLUETOOTH, battery=-1), "indisponível por Bluetooth"),
        (Status(connection=Connection.USB, hid_access=False), "sem acesso ao controle"),
        (Status(mirror_enabled=False), "Áudio no controle: desligado"),
        (Status(mirror_active=True, game_running=True, rpcs3_running=True), "jogo tocando"),
        (Status(headphones=True, swap_motors=True, error="pw-dump falhou"), "Aviso: pw-dump falhou"),
        (Status(connection=Connection.USB, charging=True, battery=10), "carregando"),
        (Status(volume_db=-12.0, led_color="off"), "Luz: desligada"),
    ],
)
def test_format_status(status: Status, expected: str) -> None:
    assert expected in cli.format_status(status)


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "ds4ctl 0.1.0" in capsys.readouterr().out


def test_apps_list_add_remove(proxy: FakeProxy) -> None:
    proxy.status.apps = ["rpcs3"]
    proxy.status.playing = ["Firefox", "eldenring.exe"]
    code, text = ds4ctl("apps")
    assert code == 0
    assert "rpcs3" in text
    assert "Tocando agora: Firefox, eldenring.exe" in text

    assert ds4ctl("apps", "add", "*.exe")[0] == 0
    assert proxy.calls[-1] == ("call_set_apps", ["rpcs3", "*.exe"])
    assert ds4ctl("apps", "add", "RPCS3")[0] == 0  # já está na lista: não chama o daemon
    assert proxy.calls[-1] == ("call_set_apps", ["rpcs3", "*.exe"])

    assert ds4ctl("apps", "remove", "RPCS3")[0] == 0
    assert proxy.calls[-1] == ("call_set_apps", [])
    code, _ = ds4ctl("apps", "remove", "steam")
    assert code == 1
    assert ds4ctl("apps", "add")[0] == 1


def test_status_shows_limiter() -> None:
    assert "limitador desligado" in cli.format_status(Status(limiter=False))
    assert "picos até −1 dBFS" in cli.format_status(Status(limiter=True, limiter_active=True))


def test_status_shows_led_mode() -> None:
    assert "mostra a bateria" in cli.format_status(Status(led_mode="battery"))


def test_led_with_rpcs3_open_says_it_is_pending(proxy: FakeProxy) -> None:
    # Regressão: com o RPCS3 aberto a cor fica pendente, mas a CLI dizia "Cor da luz alterada."
    proxy.status.rpcs3_running = True
    code, text = ds4ctl("led", "verde")
    assert code == 0
    assert "quando o RPCS3 fechar" in text
    code, text = ds4ctl("led-mode", "battery")
    assert "quando o RPCS3 fechar" in text

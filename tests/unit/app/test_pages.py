# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

from typing import Any

import pytest
from conftest import spin
from fake_client import FakeClient, sample
from gi.repository import Adw, Gtk

from ds4_companion.app import states
from ds4_companion.app.context import Context
from ds4_companion.app.pages.advanced import AdvancedPage
from ds4_companion.app.pages.audio import AudioPage
from ds4_companion.app.pages.light import LightPage
from ds4_companion.app.pages.status import StatusPage, audio_summary, rpcs3_summary
from ds4_companion.app.pages.vibration import VibrationPage
from ds4_companion.app.widgets.controller_card import battery_icon
from ds4_companion.app.widgets.volume_row import VolumeRow, zone_text
from ds4_companion.common.db import VolumeZone
from ds4_companion.common.models import Connection


class Ctx(Context):
    """Contexto de teste: registra toasts, confirmações, links e comandos em vez de mostrar."""

    def __init__(self, client: FakeClient) -> None:
        self.parent_widget = Gtk.Box()
        super().__init__(client, Adw.ToastOverlay(), self.parent_widget)
        self.toasts_seen: list[str] = []
        self.confirms: list[tuple[str, Any]] = []
        self.uris: list[str] = []
        self.commands: list[list[str]] = []
        self.command_result = (0, "linha 1\nlinha 2")

    def toast(self, text: str) -> None:
        self.toasts_seen.append(text)

    def confirm(self, heading: str, body: str, accept: str, on_accept: Any, *, destructive: bool = False) -> Any:
        self.confirms.append((heading, on_accept))
        return None

    def open_uri(self, uri: str) -> None:
        self.uris.append(uri)

    def run(self, argv: list[str], done: Any) -> None:
        self.commands.append(argv)
        done(*self.command_result)


@pytest.fixture
def client() -> FakeClient:
    c = FakeClient()
    c.available = True
    return c


@pytest.fixture
def ctx(client: FakeClient) -> Ctx:
    return Ctx(client)


def visible(page: Gtk.Stack) -> str:
    return page.get_visible_child_name() or ""


def test_summaries() -> None:
    assert audio_summary(sample(mirror_active=True)) == ("Tocando no controle", True)
    assert audio_summary(sample(mirror_enabled=False))[0] == "Desligado"
    assert "Bluetooth" in audio_summary(sample(connection=Connection.BLUETOOTH))[0]
    assert "áudio do controle" in audio_summary(sample(sink_present=False))[0]
    assert audio_summary(sample())[0] == "Ligado, aguardando o jogo"
    assert "problema" in audio_summary(sample(error="x"))[0]
    assert rpcs3_summary(sample()) == "Fechado"
    assert rpcs3_summary(sample(rpcs3_running=True)) == "Aberto"
    assert rpcs3_summary(sample(rpcs3_running=True, game_running=True)) == "Aberto · jogo tocando"
    assert battery_icon(-1, False) == "battery-missing-symbolic"
    assert battery_icon(84, True) == "battery-level-80-charging-symbolic"
    # Regressão: 100 % carregando não existe no Adwaita; o nome é "charged".
    assert battery_icon(100, True) == "battery-level-100-charged-symbolic"
    from gi.repository import Gdk, Gtk

    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    for level in range(0, 101, 10):
        for charging in (False, True):
            assert theme.has_icon(battery_icon(level, charging)), (level, charging)
    assert zone_text(VolumeZone.FREE) == ("", None)
    assert zone_text(VolumeZone.OVER_LIMIT)[0] == "acima do limite"


def test_status_page_states(ctx: Ctx, client: FakeClient) -> None:
    page = StatusPage(ctx)
    page.update(sample(headphones=True))
    assert visible(page) == "content"
    assert page.card.name.get_label() == "DualShock 4"
    assert page.card.battery.get_label() == "80 % · carregando"
    assert page.card.strip.lit
    assert page.volume.get_subtitle() == "Fone conectado no controle"
    page.update(sample(battery=-1, connection=Connection.BLUETOOTH, sink_present=False, led_color="off"))
    assert page.card.battery.get_label() == "Bateria desconhecida"
    assert not page.card.strip.lit
    assert not page.volume.get_visible()

    page.update(sample(connection=Connection.NONE))
    assert visible(page) == "no-controller"
    page._states["no-controller"].get_child().emit("clicked")
    assert ctx.uris

    page.update(sample(hid_access=False))
    assert visible(page) == "no-permission"
    page._states["no-permission"].get_child().emit("clicked")
    assert client.calls[-1] == ("Refresh",)


def test_light_strip_animates_and_recolors(ctx: Ctx) -> None:
    page = StatusPage(ctx)
    page.update(sample(led_color="red"))
    strip = page.card.strip
    assert strip.rgba.red == 1.0
    spin(0.5)
    assert strip.get_opacity() == pytest.approx(1.0)
    page.update(sample(connection=Connection.NONE))
    page.update(sample(battery=50, charging=False))
    assert page.card.battery.get_label() == "50 %"


def test_audio_page(ctx: Ctx, client: FakeClient) -> None:
    page = AudioPage(ctx)
    page.update(sample(headphones=True, max_db=-6.0, volume_db=-9.0))
    assert visible(page) == "content"
    assert page.waiting.get_visible()
    assert page.volume.get_tooltip_text()
    assert [r.get_title() for r in page._app_rows] == ["rpcs3", "AppRun.wrapped"]

    page.mirror.set_active(False)
    assert client.calls[-1] == ("SetMirror", False)
    page.tone.emit("activated")
    assert client.calls[-1] == ("PlayTestTone",)

    page.add_row.set_text("  steam  ")
    page.add_row.emit("apply")
    assert client.calls[-1] == ("SetApps", ["rpcs3", "AppRun.wrapped", "steam"])
    page.add_row.set_text("")
    page.add_row.emit("apply")
    page._app_rows[0].get_last_child()
    page._on_remove(Gtk.Button(), "rpcs3")
    assert client.calls[-1] == ("SetApps", ["AppRun.wrapped"])

    page.update(sample(apps=[], mirror_active=True))
    assert page.empty_apps.get_visible()
    assert not page.waiting.get_visible()

    page.update(sample(connection=Connection.BLUETOOTH))
    assert visible(page) == "bluetooth-no-audio"
    page.update(sample(connection=Connection.NONE))
    assert visible(page) == "no-controller"


def test_volume_row_sends_after_drag_and_needs_confirmation(ctx: Ctx, client: FakeClient) -> None:
    page = AudioPage(ctx)
    page.update(sample(max_db=3.0, volume_db=-6.0))
    row = page.volume
    row.scale.set_value(-3.0)
    assert row.value.get_label() == "−3 dB"
    assert row.zone.get_label() == "alto"
    spin(0.2)
    assert client.calls[-1] == ("SetVolume", -3.0, False)

    row.scale.set_value(2.0)  # passa do limite: para em 0 dB e pede confirmação
    assert row.scale.get_value() == 0.0
    assert ctx.confirms
    ctx.confirms[-1][1]()  # aceitou
    assert row.scale.get_value() == 2.0
    assert "over-limit" in row.scale.get_css_classes()
    spin(0.2)
    assert client.calls[-1] == ("SetVolume", 2.0, True)

    row.scale.set_value(-1.0)
    row.update(-12.0, 3.0)  # chegou estado do daemon no meio do arraste: não puxa o slider
    assert row.scale.get_value() == -1.0
    spin(0.2)
    row.update(-12.0, 0.0)
    assert row.scale.get_value() == -12.0


def test_vibration_page(ctx: Ctx, client: FakeClient) -> None:
    page = VibrationPage(ctx)
    page.update(sample(large_percent=150, players=[1, 3]))
    assert page.large.value.get_label() == "150 %"
    assert page.large.warning.get_visible()
    assert page.large.warning_label.get_visible()  # aviso por texto + ícone, não só ícone
    assert not page.small.warning_label.get_visible()
    assert [t.get_active() for t in page.players][:3] == [True, False, True]
    assert page.large.test.get_sensitive()

    page.small.scale.set_value(60)
    spin(0.6)
    assert client.calls[-1] == ("SetVibration", 150, 60, False)
    page.swap.set_active(True)
    page.large.test.emit("clicked")  # envia a mudança pendente antes de testar
    assert client.calls[-2] == ("SetVibration", 150, 60, True)
    assert client.calls[-1] == ("TestRumble", "strong")
    page.small.test.emit("clicked")
    page.both.emit("activated")
    assert client.calls[-1] == ("TestRumble", "both")

    page.players[1].set_active(True)
    assert client.calls[-1] == ("SetPlayers", [1, 2, 3])

    page.update(sample(rpcs3_running=True))
    assert page.banner.get_revealed()
    assert not page.both.get_sensitive()
    assert "Feche o RPCS3" in page.both.get_tooltip_text()
    page.update(sample(connection=Connection.NONE))
    assert "Conecte" in page.both.get_tooltip_text()
    page.update(sample(hid_access=False))
    assert "acesso" in page.both.get_tooltip_text()


def test_light_page(ctx: Ctx, client: FakeClient) -> None:
    page = LightPage(ctx)
    page.update(sample(led_color="green"))
    active = [s.preset.id for s in page.swatches if s.get_active()]
    assert active == ["green"]
    assert client.calls == []  # atualizar a tela não manda nada de volta
    page.swatches[3].set_active(True)
    assert client.calls[-1] == ("SetLed", "pink")
    page.update(sample(rpcs3_running=True))
    assert page.note.get_visible()
    page.update(sample(connection=Connection.NONE))
    assert "conectar" in page.note.get_label()
    page.update(sample())
    assert not page.note.get_visible()


def test_light_swatches_draw(ctx: Ctx) -> None:
    import cairo

    page = LightPage(ctx)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 40, 40)
    for swatch in page.swatches:
        swatch.set_active(swatch.preset.id in ("off", "blue"))
        swatch._draw(None, cairo.Context(surface), 40, 40)  # type: ignore[arg-type]


def test_advanced_page(ctx: Ctx, client: FakeClient) -> None:
    page = AdvancedPage(ctx)
    page.update(sample(backup_before_edit=False))
    assert page.folder.get_subtitle() == "~/.config/rpcs3"
    assert not page.backup.get_active()
    page.backup.set_active(True)
    assert client.calls[-1] == ("SetBackup", True)

    page.restart_service()
    assert ctx.commands[-1][:3] == ["systemctl", "--user", "restart"]
    assert ctx.toasts_seen[-1] == "Serviço reiniciado."
    ctx.command_result = (1, "falhou")
    page.restart_service()
    assert "Não deu" in ctx.toasts_seen[-1]

    page.confirm_restore()
    ctx.confirms[-1][1]()
    assert client.calls[-1] == ("RestoreDefaults",)


def test_context_call_reports_errors(ctx: Ctx, client: FakeClient) -> None:
    client.errors["SetLed"] = ("InvalidArgument", "Cor desconhecida: x.")
    ctx.call("SetLed", "x")
    assert ctx.toasts_seen[-1] == "Cor desconhecida: x."
    got: list[Any] = []
    ctx.call("SetVolume", -3.0, False, ok="feito", done=got.append)
    assert ctx.toasts_seen[-1] == "feito"
    assert got == [-3.0]


def test_real_context_helpers(client: FakeClient) -> None:
    overlay = Adw.ToastOverlay()
    real = Context(client, overlay, Gtk.Box())
    real.toast("oi")
    assert real.confirm("T", "B", "Ok", lambda: None) is not None
    out: list[tuple[int, str]] = []
    real.run(["printf", "ok"], lambda code, text: out.append((code, text)))
    from conftest import spin_until

    assert spin_until(lambda: out)
    assert out == [(0, "ok")]
    real.run(["comando-que-nao-existe-ds4"], lambda code, text: out.append((code, text)))
    assert out[-1][0] == 127


def test_state_catalog_matches_illustrations() -> None:
    from pathlib import Path

    data = Path(__file__).parents[3] / "data" / "illustrations"
    for key, state in states.catalog().items():
        assert (data / f"{state.illustration}.svg").exists(), key
        page = states.status_page(key, lambda _b: None)
        assert page.get_title() == state.title
    assert states.status_page("waiting-game", compact=True).has_css_class("compact")
    assert states.inline_state("waiting-game") is not None


def test_volume_row_standalone() -> None:
    sent: list[tuple[float, bool]] = []
    row = VolumeRow(lambda db, ok: sent.append((db, ok)), lambda accept: None)
    row.update(-6.0, 0.0)
    row.scale.set_value(4.0)  # recusado: fica no limite
    assert row.scale.get_value() == 0.0
    spin(0.2)
    assert sent[-1] == (0.0, False)

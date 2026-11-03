# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Vibração: força dos motores no RPCS3, teste no controle, inverter motores e jogadores."""

from __future__ import annotations

from collections.abc import Callable
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from ...common.models import Status
from ..context import Context
from .base import Page

SEND_DELAY_MS = 400  # cada envio grava o Default.yml: espera o arraste parar
MAX_PLAYERS = 7


class PercentRow(Adw.PreferencesRow):
    """Força de um motor, 0–200 %, com marca em 100 % e botão de teste."""

    def __init__(self, title: str, on_change: Callable[[], None], on_test: Callable[[], None]) -> None:
        super().__init__(title=title, activatable=False, focusable=False)
        self._on_change = on_change
        self._syncing = False
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("volume-row")
        header = Gtk.Box(spacing=8)
        header.append(Gtk.Label(label=title, xalign=0, hexpand=True))
        self.warning = Gtk.Image(icon_name="dialog-warning-symbolic", visible=False)
        self.warning_label = Gtk.Label(label=_("alto"), visible=False)
        self.warning_label.add_css_class("zone-label")
        self.warning_label.add_css_class("high")
        self.value = Gtk.Label(xalign=1, width_chars=6)
        self.value.add_css_class("numeric")
        self.test = Gtk.Button(label=_("Testar"))
        self.test.connect("clicked", lambda _b: on_test())
        header.append(self.warning)
        header.append(self.warning_label)
        header.append(self.value)
        box.append(header)
        row = Gtk.Box(spacing=12)
        self.scale = Gtk.Scale(
            adjustment=Gtk.Adjustment(lower=0, upper=200, step_increment=5, page_increment=10),
            draw_value=False,
            hexpand=True,
            valign=Gtk.Align.CENTER,
        )
        self.scale.add_mark(100, Gtk.PositionType.BOTTOM, None)
        self.scale.update_property([Gtk.AccessibleProperty.LABEL], [title])
        self.scale.connect("value-changed", self._changed)
        row.append(self.scale)
        row.append(self.test)
        box.append(row)
        self.set_child(box)

    @property
    def percent(self) -> int:
        return int(round(self.scale.get_value() / 5) * 5)

    def set_percent(self, value: int) -> None:
        self._syncing = True
        self.scale.set_value(value)
        self._syncing = False
        self._show()

    def _changed(self, _scale: Gtk.Scale) -> None:
        self._show()
        if not self._syncing:
            self._on_change()

    def _show(self) -> None:
        high = self.percent > 100
        self.value.set_label(f"{self.percent} %")
        self.warning.set_visible(high)
        self.warning_label.set_visible(high)
        self.warning.set_tooltip_text(
            _("Acima de 100 % o motor fica mais tempo no máximo e gasta mais bateria.") if self.percent > 100 else None
        )
        text = f"{self.percent} % {_('alto')}" if high else f"{self.percent} %"
        self.scale.update_property([Gtk.AccessibleProperty.VALUE_TEXT], [text])


class VibrationPage(Page):
    title = _("Vibração")
    icon = "ds4-vibration-symbolic"
    page_id = "vibration"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._pending = 0
        self._syncing = False

        self.banner = Adw.Banner(
            title=_("O RPCS3 está aberto. A vibração muda quando você fechar e abrir de novo."),
        )
        self.motors = Adw.PreferencesGroup(
            title=_("Força dos motores"), description=_("Vale para os jogos do RPCS3, ao abrir o emulador.")
        )
        self.large = PercentRow(_("Motor forte"), self._schedule, lambda: self._test("strong"))
        self.small = PercentRow(_("Motor fraco"), self._schedule, lambda: self._test("weak"))
        self.motors.add(self.large)
        self.motors.add(self.small)
        self.both = Adw.ButtonRow(title=_("Testar os dois motores"), start_icon_name="ds4-vibration-symbolic")
        self.both.connect("activated", lambda _r: self._test("both"))
        self.motors.add(self.both)
        self.prefs.add(self.motors)

        options = Adw.PreferencesGroup()
        self.swap = Adw.SwitchRow(title=_("Inverter motores"), subtitle=_("O forte vira o fraco e vice-versa."))
        self.swap.connect("notify::active", lambda *_: self._schedule())
        options.add(self.swap)
        self.prefs.add(options)

        players = Adw.PreferencesGroup(
            title=_("Jogadores"), description=_("Jogadores do RPCS3 que usam o DualShock 4.")
        )
        row = Adw.PreferencesRow(activatable=False, focusable=False)
        toggles = Gtk.Box(homogeneous=True, hexpand=True, spacing=4)
        toggles.add_css_class("players")
        toggles.update_property([Gtk.AccessibleProperty.LABEL], [_("Jogadores com DualShock 4")])
        self.players: list[Gtk.ToggleButton] = []
        for n in range(1, MAX_PLAYERS + 1):
            toggle = Gtk.ToggleButton(label=str(n))
            toggle.add_css_class("player-toggle")
            toggle.update_property([Gtk.AccessibleProperty.LABEL], [_("Jogador {n}").format(n=n)])
            toggle.connect("toggled", self._on_player)
            toggles.append(toggle)
            self.players.append(toggle)
        row.set_child(toggles)
        players.add(row)
        self.prefs.add(players)

        self.banner.set_visible(False)  # a janela mostra só enquanto esta página está à vista

    def top_bars(self) -> list[Gtk.Widget]:
        return [self.banner]

    def update(self, s: Status) -> None:
        self.banner.set_revealed(s.rpcs3_running)
        if not self._pending:
            self._syncing = True
            self.large.set_percent(s.large_percent)
            self.small.set_percent(s.small_percent)
            self.swap.set_active(s.swap_motors)
            for n, toggle in enumerate(self.players, start=1):
                toggle.set_active(n in s.players)
            self._syncing = False
        can_test = s.connected and s.hid_access and not s.rpcs3_running
        if not s.connected:
            reason = _("Conecte o controle para testar.")
        elif s.rpcs3_running:
            reason = _("Feche o RPCS3 para testar: ele está usando o controle.")
        elif not s.hid_access:
            reason = _("Sem acesso ao controle. Desconecte e conecte de novo.")
        else:
            reason = None
        for widget in (self.large.test, self.small.test, self.both):
            widget.set_sensitive(can_test)
            widget.set_tooltip_text(reason)

    def _schedule(self) -> None:
        if self._syncing:
            return
        if self._pending:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(SEND_DELAY_MS, self._send)

    def _send(self) -> bool:
        self._pending = 0
        self.ctx.call("SetVibration", self.large.percent, self.small.percent, self.swap.get_active())
        return False  # GLib.SOURCE_REMOVE

    def _on_player(self, _toggle: Gtk.ToggleButton) -> None:
        if self._syncing:
            return
        chosen = [n for n, t in enumerate(self.players, start=1) if t.get_active()]
        self.ctx.call("SetPlayers", chosen)

    def _test(self, motor: str) -> None:
        if self._pending:  # aplica a força nova antes de testar
            GLib.source_remove(self._pending)
            self._send()
        self.ctx.call("TestRumble", motor)

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Cartão do controle: faixa de luz na cor real do LED, nome, conexão e bateria.

O momento autoral do DESIGN.md: a faixa acende (opacidade 0 → 1 em 300 ms, ease-out) quando o
controle conecta e apaga pelo mesmo caminho. O libadwaita desliga a animação com *Reduzir animação*.
"""

from __future__ import annotations

from gettext import gettext as _
from typing import Any

from gi.repository import Adw, Gdk, Gtk

from ...common.models import Connection, Status

STRIP_MS = 300


def battery_icon(level: int, charging: bool) -> str:
    if level < 0:
        return "battery-missing-symbolic"
    step = min(100, max(0, round(level / 10) * 10))
    return f"battery-level-{step}{'-charging' if charging else ''}-symbolic"


class LightStrip(Gtk.DrawingArea):
    """2 px na cor do hardware (exceção única da paleta: é dado, não tema)."""

    def __init__(self) -> None:
        super().__init__(content_height=2, hexpand=True)
        self.add_css_class("light-strip")
        self.rgba = Gdk.RGBA()
        self.rgba.parse("#0000FF")
        self.set_draw_func(self._draw)
        self.set_opacity(0.0)
        target = Adw.CallbackAnimationTarget.new(self.set_opacity)
        self._animation = Adw.TimedAnimation.new(self, 0.0, 1.0, STRIP_MS, target)
        self._animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        self.lit = False

    def _draw(self, _area: Gtk.DrawingArea, cr: Any, width: int, height: int) -> None:
        Gdk.cairo_set_source_rgba(cr, self.rgba)
        cr.rectangle(0, 0, width, height)
        cr.fill()

    def set_color(self, hex_color: str) -> None:
        rgba = Gdk.RGBA()
        if rgba.parse(hex_color) and not rgba.equal(self.rgba):
            self.rgba = rgba
            self.queue_draw()

    def set_lit(self, lit: bool) -> None:
        if lit == self.lit:
            return
        self.lit = lit
        # Começa do valor que está na tela: interromper no meio não dá salto.
        self._animation.set_value_from(self.get_opacity())
        self._animation.set_value_to(1.0 if lit else 0.0)
        self._animation.play()


class ControllerCard(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("card")
        self.add_css_class("controller-card")
        self.strip = LightStrip()
        self.append(self.strip)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.add_css_class("controller-body")
        self.name = Gtk.Label(xalign=0)
        self.name.add_css_class("controller-name")
        body.append(self.name)

        details = Gtk.Box(spacing=16)
        self.connection_icon = Gtk.Image()
        self.connection = Gtk.Label(xalign=0)
        self.connection.add_css_class("dim-label")
        conn_box = Gtk.Box(spacing=6)
        conn_box.append(self.connection_icon)
        conn_box.append(self.connection)
        self.battery_icon = Gtk.Image()
        self.battery = Gtk.Label(xalign=0)
        self.battery.add_css_class("numeric")
        bat_box = Gtk.Box(spacing=6)
        bat_box.append(self.battery_icon)
        bat_box.append(self.battery)
        details.append(conn_box)
        details.append(bat_box)
        body.append(details)
        self.append(body)

    def update(self, s: Status) -> None:
        self.name.set_label(s.controller_name or "DualShock 4")
        if s.connection == Connection.USB:
            self.connection.set_label(_("Cabo USB"))
            self.connection_icon.set_from_icon_name("input-gaming-symbolic")
        elif s.connection == Connection.BLUETOOTH:
            self.connection.set_label(_("Bluetooth"))
            self.connection_icon.set_from_icon_name("bluetooth-active-symbolic")
        else:
            self.connection.set_label(_("Desconectado"))
            self.connection_icon.set_from_icon_name("input-gaming-symbolic")
        if s.battery < 0:
            text = _("Bateria desconhecida")
        elif s.charging:
            text = _("{level} % · carregando").format(level=s.battery)
        else:
            text = _("{level} %").format(level=s.battery)
        self.battery.set_label(text)
        self.battery_icon.set_from_icon_name(battery_icon(s.battery, s.charging))
        self.strip.set_color(s.led_hex)
        self.strip.set_lit(s.connected and s.led_color != "off")
        self.update_property(
            [Gtk.AccessibleProperty.LABEL],
            [f"{self.name.get_label()}, {self.connection.get_label()}, {text}"],
        )

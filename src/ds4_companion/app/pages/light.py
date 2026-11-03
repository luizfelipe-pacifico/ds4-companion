# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Luz: cor da barra de luz entre as cores pré-definidas, aplicada no controle na hora."""

from __future__ import annotations

import math
from gettext import gettext as _
from typing import Any

from gi.repository import Adw, Gdk, Gtk

from ...common.models import LED_PRESETS, LedPreset, Status
from ..context import Context
from .base import Page

SWATCH = 40
DOT_RADIUS = 14


def preset_names() -> dict[str, str]:
    return {
        "blue": _("Azul"),
        "red": _("Vermelho"),
        "green": _("Verde"),
        "pink": _("Rosa"),
        "purple": _("Roxo"),
        "cyan": _("Ciano"),
        "orange": _("Laranja"),
        "white": _("Branco"),
        "off": _("Desligada"),
    }


class Swatch(Gtk.ToggleButton):
    def __init__(self, preset: LedPreset, name: str) -> None:
        super().__init__()
        self.preset = preset
        self.add_css_class("swatch")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        dot = Gtk.DrawingArea(content_width=SWATCH, content_height=SWATCH, halign=Gtk.Align.CENTER)
        dot.set_draw_func(self._draw)
        self.connect("toggled", lambda *_: dot.queue_draw())
        label = Gtk.Label(label=name)
        label.add_css_class("swatch-name")
        box.append(dot)
        box.append(label)
        self.set_child(box)
        self.update_property([Gtk.AccessibleProperty.LABEL], [name])
        self.set_tooltip_text(name)

    def _draw(self, _area: Gtk.DrawingArea, cr: Any, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        if self.get_active():
            # Anel branco em volta da cor escolhida: forma, não só cor, marca a seleção.
            cr.arc(cx, cy, min(width, height) / 2 - 1, 0, 2 * math.pi)
            cr.set_source_rgba(1, 1, 1, 1)
            cr.set_line_width(2)
            cr.stroke()
        radius = DOT_RADIUS
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        if self.preset.id == "off":
            # Luz apagada: só o contorno, em branco 32 %.
            cr.set_source_rgba(1, 1, 1, 0.32)
            cr.set_line_width(1.5)
            cr.stroke()
            return
        rgba = Gdk.RGBA()
        rgba.parse(self.preset.hex)
        Gdk.cairo_set_source_rgba(cr, rgba)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.set_line_width(1)
        cr.stroke()


class LightPage(Page):
    title = _("Luz")
    icon = "display-brightness-symbolic"
    page_id = "light"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._syncing = False
        group = Adw.PreferencesGroup(
            title=_("Cor da barra de luz"),
            description=_("Muda no controle na hora e fica salva para a próxima conexão."),
        )
        grid = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            max_children_per_line=9,
            min_children_per_line=3,
            column_spacing=4,
            row_spacing=4,
            homogeneous=True,
        )
        grid.add_css_class("card")
        grid.set_margin_top(4)
        names = preset_names()
        self.swatches: list[Swatch] = []
        first: Swatch | None = None
        for preset in LED_PRESETS:
            swatch = Swatch(preset, names[preset.id])
            if first is None:
                first = swatch
            else:
                swatch.set_group(first)
            swatch.connect("toggled", self._on_toggled)
            grid.append(swatch)
            self.swatches.append(swatch)
        group.add(grid)
        self.note = Gtk.Label(xalign=0, wrap=True, visible=False)
        self.note.add_css_class("dim-label")
        self.note.add_css_class("caption")
        self.note.set_margin_top(12)
        group.add(self.note)
        self.prefs.add(group)

    def update(self, s: Status) -> None:
        self._syncing = True
        for swatch in self.swatches:
            swatch.set_active(swatch.preset.id == s.led_color)
        self._syncing = False
        if s.rpcs3_running:
            self.note.set_label(_("O RPCS3 está aberto: a cor vai para o controle quando ele fechar."))
        elif not s.connected:
            self.note.set_label(_("A cor fica salva e vai para o controle quando ele conectar."))
        self.note.set_visible(s.rpcs3_running or not s.connected)

    def _on_toggled(self, swatch: Swatch) -> None:
        if swatch.get_active() and not self._syncing:
            self.ctx.call("SetLed", swatch.preset.id)

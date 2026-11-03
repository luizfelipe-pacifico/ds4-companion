# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Volume do controle em dB: marcas em −6 dB e 0 dB, faixa livre/alto/acima do limite por texto +
ícone, inversão para branco acima de 0 dB e confirmação para passar do limite (SECURITY.md)."""

from __future__ import annotations

from collections.abc import Callable
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from ...common.db import HIGH_FROM_DB, LIMIT_DB, VolumeZone, format_db, zone_for

MIN_DB = -40.0
SEND_DELAY_MS = 80  # o rótulo segue o dedo 1:1; o daemon recebe no máximo ~12 pedidos/s


def zone_text(zone: VolumeZone) -> tuple[str, str | None]:
    """Rótulo e ícone de cada faixa: o estado nunca depende só da cor."""
    if zone == VolumeZone.HIGH:
        return _("alto"), "dialog-warning-symbolic"
    if zone == VolumeZone.OVER_LIMIT:
        return _("acima do limite"), "dialog-warning-symbolic"
    return "", None


class VolumeRow(Adw.PreferencesRow):
    """`on_change(db, confirmed)` é chamado com o valor final (sempre ≤ teto)."""

    def __init__(self, on_change: Callable[[float, bool], None], confirm: Callable[[Callable[[], None]], None]):
        super().__init__(title=_("Volume do controle"), activatable=False, focusable=False)
        self._on_change = on_change
        self._confirm = confirm
        self._ceiling = LIMIT_DB
        self._over_confirmed = False
        self._updating = False
        self._pending: int = 0

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("volume-row")
        header = Gtk.Box(spacing=8)
        title = Gtk.Label(label=_("Volume do controle"), xalign=0, hexpand=True)
        self.zone_icon = Gtk.Image(icon_name="dialog-warning-symbolic", visible=False)
        self.zone = Gtk.Label(xalign=1)
        self.zone.add_css_class("zone-label")
        self.value = Gtk.Label(xalign=1, width_chars=8)
        self.value.add_css_class("numeric")
        self.value.add_css_class("volume-value")
        header.append(title)
        header.append(self.zone_icon)
        header.append(self.zone)
        header.append(self.value)
        box.append(header)

        self.scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(lower=MIN_DB, upper=LIMIT_DB, step_increment=0.5, page_increment=3),
            draw_value=False,
            hexpand=True,
        )
        self.scale.update_property([Gtk.AccessibleProperty.LABEL], [_("Volume do controle em dB")])
        self.scale.connect("value-changed", self._on_value)
        box.append(self.scale)
        note = Gtk.Label(
            label=_("Acima de 0 dB o som distorce e pode danificar o alto-falante do controle."),
            xalign=0,
            wrap=True,
        )
        note.add_css_class("caption")
        note.add_css_class("dim-label")
        box.append(note)
        self._rebuild_marks()
        self.set_child(box)

    # --- estado vindo do daemon ---

    def update(self, db: float, ceiling: float) -> None:
        if ceiling != self._ceiling:
            self._ceiling = ceiling
            self.scale.get_adjustment().set_upper(max(ceiling, MIN_DB + 1))
            self._rebuild_marks()
        if self._pending:
            return  # o usuário está arrastando: não puxa o slider de volta
        self._updating = True
        self.scale.set_value(db)
        self._updating = False
        self._show(self.scale.get_value())

    def _rebuild_marks(self) -> None:
        self.scale.clear_marks()
        self.scale.add_mark(HIGH_FROM_DB, Gtk.PositionType.BOTTOM, None)
        self.scale.add_mark(LIMIT_DB, Gtk.PositionType.BOTTOM, "0 dB")

    # --- arraste ---

    def _on_value(self, scale: Gtk.Scale) -> None:
        db = round(scale.get_value() * 2) / 2
        if self._updating:
            return
        if db > LIMIT_DB and not self._over_confirmed:
            # Para no limite; passar dele só com confirmação.
            self._updating = True
            scale.set_value(LIMIT_DB)
            self._updating = False
            self._show(LIMIT_DB)
            self._schedule(LIMIT_DB)

            def accepted() -> None:
                self._over_confirmed = True
                scale.set_value(db)

            self._confirm(accepted)
            return
        self._show(db)
        self._schedule(db)

    def _schedule(self, db: float) -> None:
        if self._pending:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(SEND_DELAY_MS, self._send, db)

    def _send(self, db: float) -> bool:
        self._pending = 0
        self._on_change(db, db > LIMIT_DB and self._over_confirmed)
        if db <= LIMIT_DB:
            self._over_confirmed = False
        return False  # GLib.SOURCE_REMOVE

    def _show(self, db: float) -> None:
        zone = zone_for(db)
        text, icon = zone_text(zone)
        self.value.set_label(format_db(db))
        self.zone.set_label(text)
        self.zone_icon.set_visible(icon is not None)
        for widget in (self.zone, self.value, self.scale):
            for css in ("high", "over-limit"):
                widget.remove_css_class(css)
        if zone == VolumeZone.HIGH:
            self.zone.add_css_class("high")
        elif zone == VolumeZone.OVER_LIMIT:
            for widget in (self.zone, self.value, self.scale):
                widget.add_css_class("over-limit")
        label = f"{format_db(db)} {text}".strip()
        self.scale.update_property([Gtk.AccessibleProperty.VALUE_TEXT], [label])

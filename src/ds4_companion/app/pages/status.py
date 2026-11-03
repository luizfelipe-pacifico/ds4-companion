# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Status: o controle, por onde está conectado e se o som está chegando nele."""

from __future__ import annotations

from gettext import gettext as _

from gi.repository import Adw, Gtk

from ...common.db import format_db
from ...common.models import Connection, Status
from ...common.names import HELP_URL
from ..context import Context
from ..widgets.controller_card import ControllerCard
from .base import Page


def audio_summary(s: Status) -> tuple[str, bool]:
    """(texto, está tocando agora)."""
    if s.connection == Connection.BLUETOOTH:
        return _("Indisponível por Bluetooth — conecte o cabo"), False
    if not s.mirror_enabled:
        return _("Desligado"), False
    if s.mirror_active:
        return _("Tocando no controle"), True
    if not s.sink_present:
        return _("Aguardando o áudio do controle"), False
    return _("Ligado, aguardando o jogo"), False


def rpcs3_summary(s: Status) -> str:
    if not s.rpcs3_running:
        return _("Fechado")
    return _("Aberto · jogo tocando") if s.game_running else _("Aberto")


class StatusPage(Page):
    title = _("Status")
    icon = "input-gaming-symbolic"
    page_id = "status"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.card = ControllerCard()
        card_group = Adw.PreferencesGroup()
        card_group.add(self.card)
        self.prefs.add(card_group)

        group = Adw.PreferencesGroup()
        self.audio = Adw.ActionRow(title=_("Áudio no controle"))
        self.audio_dot = Gtk.Box(valign=Gtk.Align.CENTER)
        self.audio.add_prefix(self.audio_dot)
        self.rpcs3 = Adw.ActionRow(title=_("RPCS3"))
        self.output = Adw.ActionRow(title=_("Saída principal"), subtitle_selectable=True)
        self.volume = Adw.ActionRow(title=_("Volume do controle"))
        self.volume_value = Gtk.Label()
        self.volume_value.add_css_class("numeric")
        self.volume.add_suffix(self.volume_value)
        for row in (self.audio, self.volume, self.rpcs3, self.output):
            group.add(row)
        self.prefs.add(group)

    def update(self, s: Status) -> None:
        if not s.connected:
            self.state("no-controller", lambda _b: self.ctx.open_uri(HELP_URL))
            return
        if not s.hid_access:
            self.state("no-permission", lambda _b: self.ctx.call("Refresh"))
            return
        self.state(None)
        self.card.update(s)

        text, live = audio_summary(s)
        self.audio.set_subtitle(text)
        self.audio_dot.set_css_classes(["live-dot" if live else "idle-dot"])
        self.rpcs3.set_subtitle(rpcs3_summary(s))
        self.output.set_subtitle(s.output_name or _("Nenhuma saída padrão"))
        self.volume.set_visible(s.connection == Connection.USB and s.sink_present)
        ceiling = _("teto {db}").format(db=format_db(s.max_db))
        self.volume_value.set_label(f"{format_db(s.volume_db)} · {ceiling}")
        if s.headphones:
            self.volume.set_subtitle(_("Fone conectado no controle"))
        else:
            self.volume.set_subtitle("")

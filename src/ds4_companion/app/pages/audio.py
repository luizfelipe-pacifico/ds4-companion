# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Áudio: som do jogo em paralelo no controle, volume em dB com teto e apps espelhados."""

from __future__ import annotations

from gettext import gettext as _

from gi.repository import Adw, Gtk

from ...common.db import format_db
from ...common.models import Connection, Status
from ...common.names import AUDIO_HELP_URL, HELP_URL
from ..context import Context
from ..states import catalog, inline_state
from ..widgets.volume_row import VolumeRow
from .base import Page


class AudioPage(Page):
    title = _("Áudio")
    icon = "audio-speakers-symbolic"
    page_id = "audio"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._apps: list[str] = []
        self._syncing = False

        self.waiting = inline_state("waiting-game")
        self.waiting.set_visible(False)
        waiting_group = Adw.PreferencesGroup()
        waiting_group.add(self.waiting)
        self.prefs.add(waiting_group)

        mirror_group = Adw.PreferencesGroup()
        self.mirror = Adw.SwitchRow(
            title=_("Som do jogo no controle"),
            subtitle=_("Toca ao mesmo tempo na sua saída de áudio e no controle."),
        )
        self.mirror.connect("notify::active", self._on_mirror)
        mirror_group.add(self.mirror)
        self.prefs.add(mirror_group)

        volume_group = Adw.PreferencesGroup()
        self.volume = VolumeRow(self._on_volume, self._confirm_over_limit)
        volume_group.add(self.volume)
        self.tone = Adw.ButtonRow(title=_("Tocar apito de teste"), start_icon_name="media-playback-start-symbolic")
        self.tone.connect("activated", lambda _r: self.ctx.call("PlayTestTone"))
        volume_group.add(self.tone)
        self.prefs.add(volume_group)

        self.apps_group = Adw.PreferencesGroup(
            title=_("Apps no controle"), description=_("Só o som destes apps vai para o controle.")
        )
        empty = catalog()["empty-apps"]
        self.empty_apps = Adw.ActionRow(title=empty.title, subtitle=empty.description, activatable=False)
        self.apps_group.add(self.empty_apps)
        self.add_row = Adw.EntryRow(title=_("Adicionar app pelo nome do processo"), show_apply_button=True)
        self.add_row.connect("apply", self._on_add)
        self.apps_group.add(self.add_row)
        self._app_rows: list[Adw.ActionRow] = []
        self.prefs.add(self.apps_group)

    # --- daemon → tela ---

    def update(self, s: Status) -> None:
        if not s.connected:
            self.state("no-controller", lambda _b: self.ctx.open_uri(HELP_URL))
            return
        if s.connection == Connection.BLUETOOTH:
            self.state("bluetooth-no-audio", lambda _b: self.ctx.open_uri(AUDIO_HELP_URL))
            return
        self.state(None)
        self._syncing = True
        self.mirror.set_active(s.mirror_enabled)
        self._syncing = False
        self.waiting.set_visible(s.mirror_enabled and not s.mirror_active)
        self.volume.update(s.volume_db, s.max_db)
        self.volume.set_sensitive(s.sink_present)
        self.tone.set_sensitive(s.sink_present)
        if s.headphones:
            self.volume.set_tooltip_text(_("Fone no controle: teto de {db}").format(db=format_db(s.max_db)))
        else:
            self.volume.set_tooltip_text(None)
        if s.apps != self._apps:
            self._show_apps(s.apps)

    def _show_apps(self, apps: list[str]) -> None:
        self._apps = list(apps)
        for row in self._app_rows:
            self.apps_group.remove(row)
        self._app_rows = []
        for app in apps:
            row = Adw.ActionRow(title=app, title_selectable=True)
            remove = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, tooltip_text=_("Remover"))
            remove.add_css_class("flat")
            remove.update_property([Gtk.AccessibleProperty.LABEL], [_("Remover {app}").format(app=app)])
            remove.connect("clicked", self._on_remove, app)
            row.add_suffix(remove)
            self.apps_group.remove(self.add_row)
            self.apps_group.add(row)
            self.apps_group.add(self.add_row)
            self._app_rows.append(row)
        self.empty_apps.set_visible(not apps)

    # --- tela → daemon ---

    def _on_mirror(self, row: Adw.SwitchRow, _pspec: object) -> None:
        if not self._syncing:
            self.ctx.call("SetMirror", row.get_active())

    def _on_volume(self, db: float, confirmed: bool) -> None:
        self.ctx.call("SetVolume", db, confirmed)

    def _confirm_over_limit(self, accepted: object) -> None:
        self.ctx.confirm(
            _("Passar de 0 dB?"),
            _("Acima de 0 dB o som distorce e pode danificar o alto-falante do controle."),
            _("Passar do limite"),
            accepted,  # type: ignore[arg-type]
            destructive=True,
        )

    def _on_add(self, row: Adw.EntryRow) -> None:
        name = row.get_text().strip()
        if not name:
            return
        row.set_text("")
        self.ctx.call("SetApps", [*self._apps, name])

    def _on_remove(self, _button: Gtk.Button, app: str) -> None:
        self.ctx.call("SetApps", [a for a in self._apps if a != app])

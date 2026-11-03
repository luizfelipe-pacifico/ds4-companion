# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Avançado: pasta do RPCS3, backups, registros e controle do serviço, restaurar padrões."""

from __future__ import annotations

from gettext import gettext as _
from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

from ...common.models import Status
from ...common.names import SERVICE_UNIT
from ..context import Context
from .base import Page

LOG_LINES = "200"


class AdvancedPage(Page):
    title = _("Avançado")
    icon = "preferences-other-symbolic"
    page_id = "advanced"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._syncing = False

        rpcs3 = Adw.PreferencesGroup(title=_("RPCS3"))
        self.folder = Adw.ActionRow(title=_("Pasta de configuração"), subtitle_selectable=True)
        choose = Gtk.Button(label=_("Escolher…"), valign=Gtk.Align.CENTER)
        choose.connect("clicked", self._choose_folder)
        self.folder.add_suffix(choose)
        rpcs3.add(self.folder)
        self.backup = Adw.SwitchRow(
            title=_("Backup antes de editar"),
            subtitle=_("Guarda uma cópia do Default.yml com data e hora antes da primeira mudança."),
        )
        self.backup.connect("notify::active", self._on_backup)
        rpcs3.add(self.backup)
        self.prefs.add(rpcs3)

        service = Adw.PreferencesGroup(title=_("Serviço"))
        logs = Adw.ButtonRow(title=_("Ver registros do serviço"))
        logs.connect("activated", lambda _r: self.show_logs())
        restart = Adw.ButtonRow(title=_("Reiniciar serviço"))
        restart.connect("activated", lambda _r: self.restart_service())
        service.add(logs)
        service.add(restart)
        self.prefs.add(service)

        reset = Adw.PreferencesGroup()
        restore = Adw.ButtonRow(title=_("Restaurar padrões"))
        restore.add_css_class("destructive-action")
        restore.connect("activated", lambda _r: self.confirm_restore())
        reset.add(restore)
        self.prefs.add(reset)

    def update(self, s: Status) -> None:
        self.folder.set_subtitle(s.rpcs3_config_dir)
        self._syncing = True
        self.backup.set_active(s.backup_before_edit)
        self._syncing = False

    def _on_backup(self, row: Adw.SwitchRow, _pspec: object) -> None:
        if not self._syncing:
            self.ctx.call("SetBackup", row.get_active())

    def _choose_folder(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog(title=_("Pasta de configuração do RPCS3"))
        current = Path(self.folder.get_subtitle() or "~").expanduser()
        if current.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(current)))

        def chosen(d: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
            try:
                folder = d.select_folder_finish(result)
            except GLib.Error:
                return  # cancelado
            if folder is not None and folder.get_path():
                self.ctx.call("SetRpcs3Dir", folder.get_path(), ok=_("Pasta do RPCS3 alterada."))

        dialog.select_folder(self.get_root(), None, chosen)

    def show_logs(self) -> None:
        argv = ["journalctl", "--user", "-u", SERVICE_UNIT, "-n", LOG_LINES, "--no-pager", "-o", "short-iso"]

        def done(code: int, out: str) -> None:
            text = out.strip() or _("Nenhum registro ainda.")
            view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
            view.add_css_class("log-view")
            view.get_buffer().set_text(text)
            scroller = Gtk.ScrolledWindow(child=view, min_content_height=360, min_content_width=560)
            toolbar = Adw.ToolbarView(content=scroller)
            toolbar.add_top_bar(Adw.HeaderBar())
            dialog = Adw.Dialog(title=_("Registros do serviço"), child=toolbar, content_width=720)
            dialog.present(self)
            # A parte mais recente fica à vista.
            end = view.get_buffer().get_end_iter()
            view.scroll_to_iter(end, 0, False, 0, 0)

        self.ctx.run(argv, done)

    def restart_service(self) -> None:
        def done(code: int, out: str) -> None:
            if code == 0:
                self.ctx.toast(_("Serviço reiniciado."))
            else:
                self.ctx.toast(_("Não deu para reiniciar o serviço."))

        self.ctx.run(["systemctl", "--user", "restart", SERVICE_UNIT], done)

    def confirm_restore(self) -> None:
        self.ctx.confirm(
            _("Restaurar padrões?"),
            _("Volume, vibração, luz e apps voltam ao padrão. Os backups do RPCS3 ficam onde estão."),
            _("Restaurar"),
            lambda: self.ctx.call("RestoreDefaults", ok=_("Padrões restaurados.")),
            destructive=True,
        )

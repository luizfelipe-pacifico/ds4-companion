# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Adw.Application: estilo escuro forçado, CSS do design system e a janela principal."""

from __future__ import annotations

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from ..common import config  # noqa: E402
from ..common.names import APP_ID, RESOURCE_PREFIX  # noqa: E402
from . import resources  # noqa: E402

log = logging.getLogger(__name__)

REPO_URL = "https://github.com/luizfelipe-pacifico/ds4-companion"


class Application(Adw.Application):
    def __init__(self, client_factory: object = None) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.add_main_option("version", 0, 0, 0, _("Mostra a versão e sai"), None)  # 0 = GLib.OptionArg.NONE
        self._client_factory = client_factory
        self.client: object = None

    def do_handle_local_options(self, options: object) -> int:
        if options.contains("version"):  # type: ignore[attr-defined]
            print(f"ds4-companion {__version__}")
            return 0
        return -1

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        if resources.register():
            self.set_resource_base_path(RESOURCE_PREFIX)
            provider = Gtk.CssProvider()
            provider.load_from_resource(f"{RESOURCE_PREFIX}/style.css")
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_resource_path(f"{RESOURCE_PREFIX}/icons")
        else:
            log.warning("recursos do app não encontrados; usando o visual padrão")
        for name, handler in (("about", self._about), ("quit", lambda *_: self.quit())):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

    def do_activate(self) -> None:
        window = self.get_active_window()
        if window is not None:
            window.present()
            return
        from .client import DaemonClient
        from .window import Window

        client = self._client_factory() if callable(self._client_factory) else DaemonClient()
        self.client = client
        window = Window(self, client)
        window.present()
        if isinstance(client, DaemonClient):
            client.connect_bus()

        settings, warnings = config.load()
        for warning in warnings:
            log.warning("config: %s", warning)
        if settings.updates.check_on_start:
            from .updates import UpdateNotifier

            UpdateNotifier(window, window.toasts).check_in_background()

    def _about(self, *_args: object) -> None:
        about = Adw.AboutDialog(
            application_name="DS4 Companion",
            application_icon=APP_ID,
            version=__version__,
            developer_name=_("Contribuidores do DS4 Companion"),
            license_type=Gtk.License.GPL_3_0,
            website=REPO_URL,
            issue_url=f"{REPO_URL}/issues",
            comments=_("O som do RPCS3 também no seu DualShock 4, sem trocar a saída de áudio."),
        )
        about.add_legal_section(
            _("Marcas"),
            None,
            Gtk.License.CUSTOM,
            _(
                "PlayStation, DualShock e PS4 são marcas da Sony Interactive Entertainment. "
                "Este projeto não é afiliado, patrocinado nem endossado pela Sony."
            ),
        )
        about.present(self.get_active_window())

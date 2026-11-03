# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""`python -m ds4_companion.app`: abre a janela e procura versão nova (ADR 0009)."""

from __future__ import annotations

import gettext
import logging
import sys
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from ..common import config  # noqa: E402
from ..common.names import APP_ID, GETTEXT_DOMAIN  # noqa: E402
from .updates import UpdateNotifier  # noqa: E402

log = logging.getLogger(__name__)


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.add_main_option("version", 0, 0, 0, _("Mostra a versão e sai"), None)  # 0 = GLib.OptionArg.NONE

    def do_handle_local_options(self, options: object) -> int:
        if options.contains("version"):  # type: ignore[attr-defined]
            print(f"ds4-companion {__version__}")
            return 0
        return -1

    def do_activate(self) -> None:
        window = self.get_active_window()
        if window is not None:
            window.present()
            return
        toasts = Adw.ToastOverlay(
            child=Adw.StatusPage(icon_name=f"{APP_ID}-symbolic", title="DS4 Companion", description=__version__)
        )
        window = Adw.ApplicationWindow(application=self, title="DS4 Companion", default_width=720, default_height=560)
        window.set_content(Gtk.Box(orientation=Gtk.Orientation.VERTICAL))
        window.get_content().append(Adw.HeaderBar())
        window.get_content().append(toasts)
        toasts.set_vexpand(True)
        window.present()

        settings, warnings = config.load()
        for warning in warnings:
            log.warning("config: %s", warning)
        if settings.updates.check_on_start:
            UpdateNotifier(window, toasts).check_in_background()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    gettext.textdomain(GETTEXT_DOMAIN)
    return int(Application().run(sys.argv))


if __name__ == "__main__":
    sys.exit(main())

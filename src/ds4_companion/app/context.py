# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""O que as páginas usam da janela: cliente do daemon, toasts, confirmação, links e comandos."""

from __future__ import annotations

import logging
from collections.abc import Callable
from gettext import gettext as _
from typing import Any, Protocol

from gi.repository import Adw, Gio, GLib, Gtk

log = logging.getLogger(__name__)


class Client(Protocol):
    status: Any
    available: bool

    def call(self, method: str, *args: Any, done: Callable[[str | None, str, Any], None] | None = None) -> None: ...
    def connect(self, signal: str, handler: Callable[..., Any]) -> int: ...


class Context:
    def __init__(self, client: Client, toasts: Adw.ToastOverlay, parent: Gtk.Widget) -> None:
        self.client = client
        self.toasts = toasts
        self.parent = parent

    def toast(self, text: str) -> None:
        # As mensagens do daemon podem trazer stderr do PipeWire: texto puro, nunca markup.
        self.toasts.add_toast(Adw.Toast(title=text, timeout=4, use_markup=False))

    def call(self, method: str, *args: Any, ok: str | None = None, done: Callable[[Any], None] | None = None) -> None:
        """Chama o daemon; erro vira toast com a mensagem dele, sucesso opcionalmente também."""

        def finished(code: str | None, message: str, value: Any) -> None:
            if code is not None:
                self.toast(message)
                return
            if ok:
                self.toast(ok)
            if done:
                done(value)

        self.client.call(method, *args, done=finished)

    def confirm(
        self,
        heading: str,
        body: str,
        accept: str,
        on_accept: Callable[[], None],
        *,
        destructive: bool = False,
    ) -> Adw.AlertDialog:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("cancel", _("Cancelar"))
        dialog.add_response("accept", accept)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        appearance = Adw.ResponseAppearance.DESTRUCTIVE if destructive else Adw.ResponseAppearance.SUGGESTED
        dialog.set_response_appearance("accept", appearance)

        def response(_dialog: Adw.AlertDialog, answer: str) -> None:
            if answer == "accept":
                on_accept()

        dialog.connect("response", response)
        dialog.present(self.parent)
        return dialog

    def open_uri(self, uri: str) -> None:
        Gtk.UriLauncher.new(uri).launch(self.parent.get_root(), None, None, None)

    def run(self, argv: list[str], done: Callable[[int, str], None]) -> None:
        """Roda um comando (lista, sem shell) sem travar a janela; entrega código e saída."""
        try:
            proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE)
        except GLib.Error as exc:
            log.warning("não deu para rodar %s: %s", argv[0], exc.message)
            done(127, exc.message)
            return

        def finished(p: Gio.Subprocess, result: Gio.AsyncResult) -> None:
            try:
                _ok, out, _err = p.communicate_utf8_finish(result)
            except GLib.Error as exc:
                done(1, exc.message)
                return
            done(p.get_exit_status(), out or "")

        proc.communicate_utf8_async(None, None, finished)

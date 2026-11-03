# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Pop-up de versão nova: consulta ao abrir, botão para atualizar e comando para o terminal (ADR 0009)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

from ..common import updates  # noqa: E402
from ..common.names import SERVICE_UNIT  # noqa: E402

log = logging.getLogger(__name__)

# pkexec: 126 = senha cancelada ou não autorizada, 127 = falha na autenticação.
PKEXEC_CANCELED = frozenset({126, 127})

Checker = Callable[[], updates.Update | None]
Spawner = Callable[[list[str], Callable[[int], None]], None]


def spawn(argv: list[str], done: Callable[[int], None]) -> None:
    """Roda o comando sem travar a janela e entrega o código de saída no laço do GTK."""
    try:
        process = Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
    except GLib.Error as exc:
        log.warning("não deu para rodar %s: %s", argv[0], exc.message)
        done(127)
        return

    def finished(proc: Gio.Subprocess, result: Gio.AsyncResult) -> None:
        try:
            proc.wait_finish(result)
        except GLib.Error as exc:
            log.warning("%s interrompido: %s", argv[0], exc.message)
            done(1)
            return
        done(proc.get_exit_status())

    process.wait_async(None, finished)


class UpdateNotifier:
    """Mostra o aviso sobre `parent` e os resultados como toasts em `toasts`."""

    def __init__(
        self,
        parent: Gtk.Widget,
        toasts: Adw.ToastOverlay,
        check: Checker = updates.check,
        run: Spawner = spawn,
    ) -> None:
        self._parent = parent
        self._toasts = toasts
        self._check = check
        self._run = run
        self._progress: Adw.Toast | None = None

    def check_in_background(self) -> None:
        """Consulta rápida numa thread; a interface nunca espera a rede."""
        threading.Thread(target=self._worker, name="ds4-update-check", daemon=True).start()

    def _worker(self) -> None:
        update = self._check()
        if update is not None:
            GLib.idle_add(self._show_once, update)

    def _show_once(self, update: updates.Update) -> bool:
        self.show(update)
        return False  # GLib.SOURCE_REMOVE: roda uma vez só

    def show(self, update: updates.Update) -> Adw.AlertDialog:
        dialog = Adw.AlertDialog(
            heading=_("Nova versão disponível"),
            body=_("O DS4 Companion {latest} já pode ser instalado. Você está usando a versão {current}.").format(
                latest=update.latest, current=update.current
            ),
        )
        dialog.set_extra_child(self._command_box(update))
        dialog.add_response("later", _("Agora não"))
        dialog.add_response("copy", _("Copiar comando"))
        dialog.add_response("update", _("Atualizar agora"))
        dialog.set_response_appearance("update", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("update")
        dialog.set_close_response("later")
        dialog.connect("response", self._on_response, update)
        dialog.present(self._parent)
        return dialog

    @staticmethod
    def _command_box(update: updates.Update) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hint = Gtk.Label(label=_("Ou cole no terminal:"), xalign=0)
        hint.add_css_class("dim-label")
        # WORD_CHAR: a URL longa quebra em qualquer ponto em vez de alargar o diálogo.
        command = Gtk.Label(label=update.command, xalign=0, selectable=True, wrap=True)
        command.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        command.add_css_class("monospace")
        command.update_property([Gtk.AccessibleProperty.LABEL], [_("Comando para atualizar pelo terminal")])
        box.append(hint)
        box.append(command)
        return box

    def _on_response(self, _dialog: Adw.AlertDialog, response: str, update: updates.Update) -> None:
        if response == "copy":
            self.copy_command(update)
        elif response == "update":
            self.install(update)

    def copy_command(self, update: updates.Update) -> None:
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(update.command)
        self._toast(_("Comando copiado. Cole no terminal para atualizar."))

    def install(self, update: updates.Update) -> None:
        title = _("Atualizando para a versão {latest}…").format(latest=update.latest)
        self._progress = Adw.Toast(title=title, timeout=0)
        self._toasts.add_toast(self._progress)
        self._run(update.argv, lambda status: self._installed(update, status))

    def _installed(self, update: updates.Update, status: int) -> None:
        if self._progress is not None:
            self._progress.dismiss()
            self._progress = None
        if status == 0:
            # O daemon recarrega o código novo; a janela aberta continua na versão antiga até reabrir.
            self._run(["systemctl", "--user", "try-restart", SERVICE_UNIT], lambda _status: None)
            done = _("Atualizado para a versão {latest}. Feche e abra o app para usar.")
            self._toast(done.format(latest=update.latest))
            return
        if status in PKEXEC_CANCELED:
            self._toast(_("Atualização cancelada."))
            return
        log.warning("pacman -U terminou com código %d", status)
        toast = Adw.Toast(title=_("Não deu para atualizar. Tente pelo terminal."), timeout=0)
        toast.set_button_label(_("Copiar comando"))
        toast.connect("button-clicked", lambda _toast: self.copy_command(update))
        self._toasts.add_toast(toast)

    def _toast(self, title: str) -> None:
        self._toasts.add_toast(Adw.Toast(title=title))

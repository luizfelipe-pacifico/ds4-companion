# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from collections.abc import Callable
from typing import Any

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from ds4_companion.common import updates  # noqa: E402

pytestmark = pytest.mark.gui
if not Gtk.init_check():
    pytest.skip("sem display", allow_module_level=True)
Adw.init()

from ds4_companion.app.updates import UpdateNotifier  # noqa: E402

UPDATE = updates.Update(current="0.1.0", latest="0.2.0", package_url=updates.LATEST_PACKAGE_URL)


class Toasts:
    def __init__(self) -> None:
        self.toasts: list[Adw.Toast] = []

    def add_toast(self, toast: Adw.Toast) -> None:
        self.toasts.append(toast)

    @property
    def titles(self) -> list[str]:
        return [t.get_title() for t in self.toasts]


class Runner:
    def __init__(self, *statuses: int) -> None:
        self.statuses = list(statuses)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], done: Callable[[int], None]) -> None:
        self.calls.append(argv)
        done(self.statuses.pop(0) if self.statuses else 0)


def notifier(run: Runner, check: Any = lambda: None) -> tuple[UpdateNotifier, Toasts]:
    window = Gtk.Window()
    toasts = Toasts()
    return UpdateNotifier(window, toasts, check=check, run=run), toasts  # type: ignore[arg-type]


def iterate_until(condition: Callable[[], bool]) -> None:
    context = GLib.MainContext.default()
    for _ in range(200):
        if condition():
            return
        context.iteration(False)
        GLib.usleep(5000)
    raise AssertionError("tempo esgotado")


def test_dialog_offers_update_copy_and_later() -> None:
    n, _toasts = notifier(Runner())
    dialog = n.show(UPDATE)
    assert dialog.get_heading() == "Nova versão disponível"
    assert "0.2.0" in dialog.get_body()
    assert "0.1.0" in dialog.get_body()
    assert dialog.get_default_response() == "update"
    assert dialog.get_close_response() == "later"
    assert dialog.get_response_appearance("update") == Adw.ResponseAppearance.SUGGESTED
    labels = [dialog.get_response_label(r) for r in ("update", "copy", "later")]
    assert labels == ["Atualizar agora", "Copiar comando", "Agora não"]
    command = dialog.get_extra_child().get_last_child()
    assert command.get_label() == UPDATE.command
    assert command.get_selectable()
    dialog.force_close()


def test_background_check_shows_dialog_only_with_update() -> None:
    shown: list[updates.Update] = []
    n, _ = notifier(Runner(), check=lambda: UPDATE)
    n.show = shown.append  # type: ignore[method-assign,assignment]
    n.check_in_background()
    iterate_until(lambda: bool(shown))
    assert shown == [UPDATE]


def test_update_button_runs_pkexec_then_restarts_service() -> None:
    run = Runner(0, 0)
    n, toasts = notifier(run)
    n.show(UPDATE).emit("response", "update")
    assert run.calls == [UPDATE.argv, ["systemctl", "--user", "try-restart", "ds4-companion.service"]]
    assert toasts.titles[-1].startswith("Atualizado para a versão 0.2.0")


@pytest.mark.parametrize("status", [126, 127])
def test_canceled_password_is_not_an_error(status: int) -> None:
    run = Runner(status)
    n, toasts = notifier(run)
    n.install(UPDATE)
    assert run.calls == [UPDATE.argv]
    assert toasts.titles[-1] == "Atualização cancelada."


def test_failed_update_offers_terminal_command() -> None:
    n, toasts = notifier(Runner(1))
    n.install(UPDATE)
    failure = toasts.toasts[-1]
    assert failure.get_title() == "Não deu para atualizar. Tente pelo terminal."
    assert failure.get_button_label() == "Copiar comando"


def test_copy_puts_command_on_clipboard() -> None:
    n, toasts = notifier(Runner())
    n.show(UPDATE).emit("response", "copy")
    clipboard = Gdk.Display.get_default().get_clipboard()
    text: list[str] = []
    clipboard.read_text_async(None, lambda cb, result: text.append(cb.read_text_finish(result)))
    iterate_until(lambda: bool(text))
    assert text == [UPDATE.command]
    assert toasts.titles == ["Comando copiado. Cole no terminal para atualizar."]


def test_later_does_nothing() -> None:
    run = Runner()
    n, toasts = notifier(run)
    n.show(UPDATE).emit("response", "later")
    assert run.calls == []
    assert toasts.toasts == []

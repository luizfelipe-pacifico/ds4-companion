# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
from __future__ import annotations

import sys
from pathlib import Path

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))

if Gdk.Display.get_default() is None:
    pytest.skip("sem display para o GTK (use xvfb-run)", allow_module_level=True)

from ds4_companion.app import resources  # noqa: E402

Adw.init()
resources.register()


def spin(seconds: float = 0.05) -> None:
    """Roda o laço do GLib um pouco (sinais, timeouts, chamadas assíncronas)."""
    ctx = GLib.MainContext.default()
    end = GLib.get_monotonic_time() + int(seconds * 1e6)
    while GLib.get_monotonic_time() < end:
        ctx.iteration(False)


def spin_until(predicate: object, timeout: float = 5.0) -> bool:
    ctx = GLib.MainContext.default()
    end = GLib.get_monotonic_time() + int(timeout * 1e6)
    while GLib.get_monotonic_time() < end:
        if predicate():  # type: ignore[operator]
            return True
        ctx.iteration(False)
    return False


@pytest.fixture(scope="session")
def app() -> Adw.Application:
    from gi.repository import Gio

    application = Adw.Application(
        application_id="io.github.luizfelipe_pacifico.DS4CompanionTeste", flags=Gio.ApplicationFlags.NON_UNIQUE
    )
    application.register(None)
    return application

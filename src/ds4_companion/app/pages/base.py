# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Base das páginas: conteúdo (AdwPreferencesPage) ou uma tela de estado no lugar."""

from __future__ import annotations

from gi.repository import Adw, Gtk

from ...common.models import Status
from ..context import Context
from ..states import status_page


class Page(Gtk.Stack):
    title = ""
    icon = ""
    page_id = ""

    def __init__(self, ctx: Context) -> None:
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        self.ctx = ctx
        self.prefs = Adw.PreferencesPage()
        self.add_named(self.prefs, "content")
        self._states: dict[str, Adw.StatusPage] = {}

    def state(self, key: str | None, on_button: object = None) -> None:
        """Mostra a tela de estado `key` (criada uma vez) ou volta ao conteúdo com None."""
        if key is None:
            self.set_visible_child_name("content")
            return
        if key not in self._states:
            self._states[key] = status_page(key, on_button)  # type: ignore[arg-type]
            self.add_named(self._states[key], key)
        self.set_visible_child_name(key)

    def update(self, status: Status) -> None:
        raise NotImplementedError

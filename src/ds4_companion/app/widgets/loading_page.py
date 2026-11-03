# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Tela de carregamento: enquanto a janela espera o daemon (conectar, iniciar, ler o estado).

O ícone aparece na hora; spinner e texto só depois de REVEAL_MS, para uma resposta rápida não
piscar nada na tela. Se o serviço demorar, a tela diz isso e oferece os registros: ninguém fica
preso num spinner sem saída.
"""

from __future__ import annotations

from collections.abc import Callable
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from ...common.names import APP_ID

REVEAL_MS = 400
SLOW_MS = 10_000
ICON_SIZE = 96


def phase_text(phase: str) -> str:
    return {
        "connecting": _("Conectando ao serviço…"),
        "starting": _("Iniciando o serviço…"),
        "reading": _("Lendo o estado do controle…"),
    }[phase]


class LoadingPage(Adw.Bin):
    def __init__(self, on_logs: Callable[[], None]) -> None:
        super().__init__()
        self.phase = "connecting"
        self._reveal_id = 0
        self._slow_id = 0

        icon = Gtk.Image(icon_name=APP_ID, pixel_size=ICON_SIZE)
        icon.add_css_class("loading-icon")
        icon.update_property([Gtk.AccessibleProperty.LABEL], ["DS4 Companion"])

        self.spinner = Adw.Spinner(width_request=24, height_request=24, halign=Gtk.Align.CENTER)
        self.status = Gtk.Label(label=phase_text(self.phase), justify=Gtk.Justification.CENTER, wrap=True)
        self.status.add_css_class("dim-label")
        # O botão ocupa o lugar desde o começo (invisível e fora do foco): quando ele aparece, nada
        # na coluna se mexe.
        self.logs = Gtk.Button(label=_("Ver registros do serviço"), halign=Gtk.Align.CENTER)
        self._show_logs(False)
        self.logs.add_css_class("flat")
        self.logs.connect("clicked", lambda _b: on_logs())

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        details.append(self.spinner)
        details.append(self.status)
        details.append(self.logs)
        self.details = Gtk.Revealer(
            child=details, transition_type=Gtk.RevealerTransitionType.CROSSFADE, transition_duration=150
        )

        column = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            margin_start=24,
            margin_end=24,
        )
        column.add_css_class("loading-page")
        column.append(icon)
        column.append(self.details)

        view = Adw.ToolbarView(content=column)
        view.add_top_bar(Adw.HeaderBar(show_title=False))
        self.set_child(view)
        self.update_property([Gtk.AccessibleProperty.LABEL], [_("Carregando")])
        self.restart()

    def set_phase(self, phase: str) -> None:
        """Troca o texto da fase; volta a contar o tempo até o aviso de demora."""
        if phase != self.phase:
            self.phase = phase
            self.status.set_label(phase_text(phase))
            self._show_logs(False)
            self._cancel("_slow_id")
            self._slow_id = GLib.timeout_add(SLOW_MS, self._on_slow)

    def restart(self) -> None:
        """Volta ao começo: tudo escondido, spinner só depois de REVEAL_MS."""
        self.stop()
        self.details.set_reveal_child(False)
        self._show_logs(False)
        self.status.set_label(phase_text(self.phase))
        self._reveal_id = GLib.timeout_add(REVEAL_MS, self._on_reveal)
        self._slow_id = GLib.timeout_add(SLOW_MS, self._on_slow)

    def stop(self) -> None:
        """Cancela os timers (a janela saiu do carregamento)."""
        self._cancel("_reveal_id")
        self._cancel("_slow_id")

    def _cancel(self, attr: str) -> None:
        source = getattr(self, attr)
        if source:
            GLib.source_remove(source)
            setattr(self, attr, 0)

    def _on_reveal(self) -> bool:
        self._reveal_id = 0
        self._reveal()
        return False  # GLib.SOURCE_REMOVE

    def _on_slow(self) -> bool:
        self._slow_id = 0
        self._slow()
        return False

    def _show_logs(self, shown: bool) -> None:
        self.logs.set_opacity(1.0 if shown else 0.0)
        self.logs.set_sensitive(shown)
        self.logs.set_can_target(shown)
        self.logs.set_can_focus(shown)

    def _reveal(self) -> None:
        self.details.set_reveal_child(True)

    def _slow(self) -> None:
        self._reveal()
        self.status.set_label(_("O serviço está demorando para responder."))
        self._show_logs(True)

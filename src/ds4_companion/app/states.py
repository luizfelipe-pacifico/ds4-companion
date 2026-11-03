# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Telas de estado (AdwStatusPage + ilustrações de docs/design/ILLUSTRATIONS.md).

Toda ilustração vem com título e descrição; o texto alternativo vai no rótulo acessível.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from . import resources


@dataclass(frozen=True)
class State:
    illustration: str
    alt: str
    title: str
    description: str
    button: str | None = None
    primary: bool = False
    """O botão é a ação principal da tela (azul); links de ajuda ficam secundários."""


def catalog() -> dict[str, State]:
    """Textos do catálogo (ILLUSTRATIONS.md), traduzidos na hora de usar."""
    return {
        "no-controller": State(
            "no-controller",
            _("Controle desconectado"),
            _("Nenhum controle conectado"),
            _("Ligue o DualShock 4 pelo cabo USB ou pareie por Bluetooth."),
            _("Como parear"),
        ),
        "waiting-game": State(
            "waiting-game",
            _("Aguardando o jogo"),
            _("Aguardando o RPCS3"),
            _("Abra um jogo no RPCS3 e o som vai para o controle automaticamente."),
        ),
        "bluetooth-no-audio": State(
            "bluetooth-no-audio",
            _("Bluetooth sem áudio no controle"),
            _("Som no controle precisa do cabo"),
            _(
                "Por Bluetooth o Linux ainda não envia áudio para o DualShock 4. "
                "Vibração, luz e bateria continuam funcionando."
            ),
            _("Saiba mais"),
        ),
        "no-permission": State(
            "no-permission",
            _("Sem permissão"),
            _("Sem acesso ao controle"),
            _("A regra de permissão ainda não valeu. Desconecte e conecte o controle de novo."),
            _("Tentar de novo"),
            primary=True,
        ),
        "service-stopped": State(
            "service-stopped",
            _("Serviço parado"),
            _("Serviço parado"),
            _("O ds4-companiond não está rodando, então o som e a vibração não são ajustados."),
            _("Iniciar serviço"),
            primary=True,
        ),
        "empty-apps": State(
            "empty-list",
            _("Lista vazia"),
            _("Nenhum app no controle"),
            _("Adicione o RPCS3 ou outro app para o som dele ir para o controle."),
        ),
    }


def status_page(
    key: str,
    on_button: Callable[[Gtk.Button], None] | None = None,
    *,
    compact: bool = False,
    illustrated: bool = True,
) -> Adw.StatusPage:
    state = catalog()[key]
    page = Adw.StatusPage(title=state.title, description=state.description)
    if illustrated:
        try:
            page.set_paintable(Gtk.Svg.new_from_resource(resources.illustration(state.illustration)))
        except GLib.Error:
            page.set_icon_name("input-gaming-symbolic")
    if compact:
        page.add_css_class("compact")
    page.update_property([Gtk.AccessibleProperty.DESCRIPTION], [state.alt])
    if state.button and on_button:
        button = Gtk.Button(label=state.button, halign=Gtk.Align.CENTER)
        button.add_css_class("pill")
        if state.primary:
            button.add_css_class("suggested-action")
        button.connect("clicked", on_button)
        page.set_child(button)
    return page


def inline_state(key: str) -> Gtk.Box:
    """Versão compacta para dentro de uma página: ilustração pequena ao lado do texto."""
    state = catalog()[key]
    box = Gtk.Box(spacing=16)
    box.add_css_class("inline-state")
    try:
        picture = Gtk.Image(paintable=Gtk.Svg.new_from_resource(resources.illustration(state.illustration)))
    except GLib.Error:
        picture = Gtk.Image(icon_name="input-gaming-symbolic")
    picture.set_pixel_size(96)
    picture.update_property([Gtk.AccessibleProperty.LABEL], [state.alt])
    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER, hexpand=True)
    title = Gtk.Label(label=state.title, xalign=0, wrap=True)
    title.add_css_class("heading")
    description = Gtk.Label(label=state.description, xalign=0, wrap=True)
    description.add_css_class("dim-label")
    text.append(title)
    text.append(description)
    box.append(picture)
    box.append(text)
    return box

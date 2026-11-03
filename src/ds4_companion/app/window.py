# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Janela principal: barra lateral com as páginas e a tela de serviço parado."""

from __future__ import annotations

import logging
from gettext import gettext as _

from gi.repository import Adw, Gtk

from ..common.models import Status
from ..common.names import SERVICE_UNIT
from .context import Client, Context
from .pages.advanced import AdvancedPage
from .pages.audio import AudioPage
from .pages.base import Page
from .pages.light import LightPage
from .pages.status import StatusPage
from .pages.vibration import VibrationPage
from .states import status_page
from .widgets.loading_page import LoadingPage

log = logging.getLogger(__name__)


class Window(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, client: Client, *, autostart: bool = True) -> None:
        super().__init__(application=application, title="DS4 Companion", default_width=880, default_height=640)
        self.set_size_request(360, 480)
        self.client = client
        self._autostart = autostart
        self._started_once = False
        self._has_status = False  # as páginas só aparecem depois do primeiro estado do daemon

        self.toasts = Adw.ToastOverlay()
        self.ctx = Context(client, self.toasts, self)
        self.root = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        self.toasts.set_child(self.root)
        self.set_content(self.toasts)

        self.advanced = AdvancedPage(self.ctx)
        self.pages: list[Page] = [
            StatusPage(self.ctx),
            AudioPage(self.ctx),
            VibrationPage(self.ctx),
            LightPage(self.ctx),
            self.advanced,
        ]
        self.root.add_named(self._build_main(), "main")
        self.root.add_named(self._build_stopped(), "stopped")
        self.loading = LoadingPage(self.advanced.show_logs)
        self.root.add_named(self.loading, "loading")
        self.root.set_visible_child_name("loading")

        client.connect("status-changed", lambda _c, s: self.update(s))
        client.connect("availability-changed", lambda _c, ok: self._on_availability(ok))

    # --- montagem ---

    def _build_main(self) -> Gtk.Widget:
        self.sidebar = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.sidebar.add_css_class("navigation-sidebar")
        self.sidebar.update_property([Gtk.AccessibleProperty.LABEL], [_("Páginas")])
        for page in self.pages:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=12, margin_start=6, margin_end=6)
            box.append(Gtk.Image(icon_name=page.icon))
            box.append(Gtk.Label(label=page.title, xalign=0))
            row.set_child(box)
            row.page_id = page.page_id
            self.sidebar.append(row)

        menu = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text=_("Menu principal"))
        menu.set_menu_model(self._menu())
        # Sem título centralizado: com os botões da janela à esquerda ele só caberia cortado.
        side_header = Adw.HeaderBar(show_title=False)
        side_header.pack_end(menu)
        side_view = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=self.sidebar))
        side_view.add_top_bar(side_header)
        sidebar_page = Adw.NavigationPage(title="DS4 Companion", child=side_view, tag="sidebar")

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        for page in self.pages:
            self.stack.add_named(page, page.page_id)
        self.banner = Adw.Banner(button_label=_("Reiniciar serviço"))
        self.banner.connect("button-clicked", lambda _b: self.advanced.restart_service())
        content_view = Adw.ToolbarView(content=self.stack)
        content_view.add_top_bar(Adw.HeaderBar())
        content_view.add_top_bar(self.banner)
        for page in self.pages:
            for bar in page.top_bars():
                content_view.add_top_bar(bar)
        self.content_page = Adw.NavigationPage(title=self.pages[0].title, child=content_view, tag="content")

        self.split = Adw.NavigationSplitView(sidebar=sidebar_page, content=self.content_page)
        self.split.set_min_sidebar_width(240)
        self.split.set_max_sidebar_width(280)
        self.sidebar.connect("row-activated", self._on_row)
        self.sidebar.select_row(self.sidebar.get_row_at_index(0))

        breakpoint_ = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 600sp"))
        breakpoint_.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(breakpoint_)
        return self.split

    def _menu(self) -> object:
        from gi.repository import Gio

        menu = Gio.Menu()
        menu.append(_("Sobre o DS4 Companion"), "app.about")
        menu.append(_("Sair"), "app.quit")
        return menu

    def _build_stopped(self) -> Gtk.Widget:
        page = status_page("service-stopped", lambda _b: self.start_service())
        view = Adw.ToolbarView(content=page)
        view.add_top_bar(Adw.HeaderBar(show_title=False))
        return view

    # --- navegação ---

    def _on_row(self, _box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        self.show_page(row.page_id)

    def show_page(self, page_id: str) -> None:
        index, page = next((i, p) for i, p in enumerate(self.pages) if p.page_id == page_id)
        row = self.sidebar.get_row_at_index(index)
        if self.sidebar.get_selected_row() is not row:
            self.sidebar.select_row(row)
        self.stack.set_visible_child(page)
        for other in self.pages:
            other.set_active(other is page)
        self.content_page.set_title(page.title)
        self.split.set_show_content(True)

    # --- estado ---

    def update(self, s: Status) -> None:
        for page in self.pages:
            page.update(s)
        if not self._has_status:
            self._has_status = True
            if self.root.get_visible_child_name() == "loading":
                self._show("main")
        # O que a pessoa perde e como sair disso; o texto técnico do daemon fica na dica.
        self.banner.set_title(_("O PipeWire não respondeu: o som pode não chegar ao controle.") if s.error else "")
        self.banner.set_tooltip_text(s.error or None)
        self.banner.set_revealed(bool(s.error))

    def _show(self, name: str) -> None:
        if name == "loading":
            if self.root.get_visible_child_name() != "loading":
                self.loading.restart()
        else:
            self.loading.stop()
        self.root.set_visible_child_name(name)

    def _on_availability(self, available: bool) -> None:
        if available:
            if self._has_status:
                self._show("main")
            else:
                self.loading.set_phase("reading")
                self._show("loading")
            return
        if self._autostart and not self._started_once:
            # Primeira abertura (ADR 0005): ativa o serviço de usuário sem pedir comando.
            self._started_once = True
            self.start_service(enable=True, quiet=True)
            return
        self._show("stopped")

    def start_service(self, *, enable: bool = False, quiet: bool = False) -> None:
        argv = ["systemctl", "--user", "enable", "--now", SERVICE_UNIT] if enable else None
        argv = argv or ["systemctl", "--user", "start", SERVICE_UNIT]
        self.loading.set_phase("starting")
        self._show("loading")

        def done(code: int, out: str) -> None:
            if code != 0:
                log.warning("serviço não iniciou: %s", out.strip())
                self._show("stopped")
                if not quiet:
                    self.ctx.toast(
                        _("Não deu para iniciar o serviço. Veja: journalctl --user -u {unit}").format(unit=SERVICE_UNIT)
                    )
            # Com sucesso, o daemon aparece no D-Bus e availability-changed troca a tela.

        self.ctx.run(argv, done)

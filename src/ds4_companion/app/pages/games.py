# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Jogos: perfil por jogo do RPCS3 (ADR 0012). Som e volume valem com o jogo aberto; vibração e
luz vão para o arquivo por jogo do RPCS3. O que o perfil não define vem dos ajustes gerais."""

from __future__ import annotations

from gettext import gettext as _
from typing import Any

from gi.repository import Adw, GLib, Gtk

from ...common.db import LIMIT_DB, format_db
from ...common.models import LED_PRESETS, Status
from ..context import Context
from ..states import inline_state
from .base import Page
from .light import preset_names

MIN_DB = -40.0
# Campo do perfil → assinatura D-Bus (SetProfile recebe a{sv}).
SIGNATURES = {
    "title": "s",
    "mirror_enabled": "b",
    "volume_db": "d",
    "large_percent": "i",
    "small_percent": "i",
    "swap_motors": "b",
    "led_color": "s",
}


def profile_summary(values: dict[str, Any]) -> str:
    """O que o perfil muda, em uma linha; o resto vale como nos ajustes gerais."""
    parts = []
    if "mirror_enabled" in values:
        parts.append(_("Som no controle ligado") if values["mirror_enabled"] else _("Som no controle desligado"))
    if "volume_db" in values:
        parts.append(_("Volume {db}").format(db=format_db(values["volume_db"])))
    if "large_percent" in values:
        parts.append(_("Motor forte {n} %").format(n=values["large_percent"]))
    if "small_percent" in values:
        parts.append(_("Motor fraco {n} %").format(n=values["small_percent"]))
    if values.get("swap_motors"):
        parts.append(_("Motores invertidos"))
    if "led_color" in values:
        name = preset_names().get(values["led_color"], values["led_color"])
        parts.append(_("Luz {color}").format(color=name))
    return " · ".join(parts) or _("Sem ajustes próprios: vale o geral")


class ProfileEditor(Adw.Dialog):
    """Ajustes de um jogo. Cada grupo opcional liga com a chave; desligado, vale o geral."""

    def __init__(self, ctx: Context, serial: str, title: str, values: dict[str, Any], *, max_db: float) -> None:
        super().__init__(title=title or serial, content_width=480)
        self.ctx = ctx
        self.serial = serial
        self.title_text = title or serial
        self._max_db = max_db

        prefs = Adw.PreferencesPage()
        sound = Adw.PreferencesGroup(title=_("Som"), description=_("Vale enquanto o jogo está aberto no RPCS3."))
        self.mirror = Adw.ComboRow(
            title=_("Som no controle"),
            model=Gtk.StringList.new([_("Como no geral"), _("Ligado"), _("Desligado")]),
        )
        mirror = values.get("mirror_enabled")
        self.mirror.set_selected(0 if mirror is None else (1 if mirror else 2))
        sound.add(self.mirror)

        self.volume = Adw.ExpanderRow(title=_("Volume próprio"), show_enable_switch=True)
        upper = max(max_db, MIN_DB + 1)
        self.volume_db = Adw.SpinRow(
            title=_("Volume do controle (dB)"),
            adjustment=Gtk.Adjustment(lower=MIN_DB, upper=upper, step_increment=0.5, page_increment=3),
            digits=1,
        )
        self.volume_db.set_value(values.get("volume_db", min(-6.0, upper)))
        self.volume.add_row(self.volume_db)
        self.volume.set_enable_expansion("volume_db" in values)
        sound.add(self.volume)
        prefs.add(sound)

        rpcs3 = Adw.PreferencesGroup(
            title=_("Vibração e luz"),
            description=_("Vão para a configuração deste jogo no RPCS3 e valem ao abrir o jogo."),
        )
        self.motors = Adw.ExpanderRow(title=_("Motores próprios"), show_enable_switch=True)
        self.large = self._percent_row(_("Motor forte (%)"), values.get("large_percent", 100))
        self.small = self._percent_row(_("Motor fraco (%)"), values.get("small_percent", 100))
        self.swap = Adw.SwitchRow(title=_("Inverter motores"), active=bool(values.get("swap_motors", False)))
        for row in (self.large, self.small, self.swap):
            self.motors.add_row(row)
        self.motors.set_enable_expansion(any(k in values for k in ("large_percent", "small_percent", "swap_motors")))
        rpcs3.add(self.motors)

        self.color = Adw.ExpanderRow(title=_("Cor própria"), show_enable_switch=True)
        names = preset_names()
        self._color_ids = [p.id for p in LED_PRESETS]
        current = values.get("led_color")
        if current and current not in self._color_ids:
            self._color_ids.append(current)  # cor personalizada (#RRGGBB) já salva no perfil
        labels = [names.get(c, c) for c in self._color_ids]
        self.color_choice = Adw.ComboRow(title=_("Cor da barra de luz"), model=Gtk.StringList.new(labels))
        self.color_choice.set_selected(self._color_ids.index(current) if current in self._color_ids else 0)
        self.color.add_row(self.color_choice)
        self.color.set_enable_expansion(current is not None)
        rpcs3.add(self.color)
        prefs.add(rpcs3)

        danger = Adw.PreferencesGroup()
        self.delete_row = Adw.ButtonRow(title=_("Apagar perfil"), visible=bool(values))  # perfil novo: nada a apagar
        self.delete_row.add_css_class("destructive-action")
        self.delete_row.connect("activated", lambda _r: self.confirm_delete())
        danger.add(self.delete_row)
        prefs.add(danger)

        # O valor fica à vista no subtítulo, sem precisar expandir a linha.
        for widget, signal in (
            (self.volume, "notify::enable-expansion"),
            (self.volume_db, "notify::value"),
            (self.motors, "notify::enable-expansion"),
            (self.large, "notify::value"),
            (self.small, "notify::value"),
            (self.swap, "notify::active"),
            (self.color, "notify::enable-expansion"),
            (self.color_choice, "notify::selected"),
        ):
            widget.connect(signal, lambda *_a: self._sync_subtitles())
        self._sync_subtitles()

        header = Adw.HeaderBar()
        save = Gtk.Button(label=_("Salvar"))
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda _b: self.save())
        header.pack_end(save)
        view = Adw.ToolbarView(content=prefs)
        view.add_top_bar(header)
        self.set_child(view)

    def _sync_subtitles(self) -> None:
        general = _("Como no geral")
        volume = format_db(round(self.volume_db.get_value() * 2) / 2)
        self.volume.set_subtitle(volume if self.volume.get_enable_expansion() else general)
        motors = _("Forte {large} % · fraco {small} %").format(
            large=int(self.large.get_value()), small=int(self.small.get_value())
        )
        if self.swap.get_active():
            motors += " · " + _("invertidos")
        self.motors.set_subtitle(motors if self.motors.get_enable_expansion() else general)
        color = preset_names().get(self._color_ids[self.color_choice.get_selected()], "")
        color = color or self._color_ids[self.color_choice.get_selected()]
        self.color.set_subtitle(color if self.color.get_enable_expansion() else general)

    @staticmethod
    def _percent_row(title: str, value: int) -> Adw.SpinRow:
        row = Adw.SpinRow(
            title=title, adjustment=Gtk.Adjustment(lower=0, upper=200, step_increment=5, page_increment=10)
        )
        row.set_value(value)
        return row

    def values(self) -> dict[str, Any]:
        """Campos do perfil; os grupos desligados ficam de fora (valem os ajustes gerais)."""
        values: dict[str, Any] = {"title": self.title_text}
        mirror = self.mirror.get_selected()
        if mirror:
            values["mirror_enabled"] = mirror == 1
        if self.volume.get_enable_expansion():
            values["volume_db"] = round(self.volume_db.get_value() * 2) / 2
        if self.motors.get_enable_expansion():
            values["large_percent"] = int(self.large.get_value())
            values["small_percent"] = int(self.small.get_value())
            values["swap_motors"] = self.swap.get_active()
        if self.color.get_enable_expansion():
            values["led_color"] = self._color_ids[self.color_choice.get_selected()]
        return values

    def save(self) -> None:
        values = self.values()
        if values.get("volume_db", LIMIT_DB) > LIMIT_DB:
            self.ctx.confirm(
                _("Passar de 0 dB neste jogo?"),
                _("Acima de 0 dB o som distorce e pode danificar o alto-falante do controle."),
                _("Passar do limite"),
                lambda: self._send(values, confirm=True),
                destructive=True,
            )
            return
        self._send(values, confirm=False)

    def _send(self, values: dict[str, Any], *, confirm: bool) -> None:
        variants = {key: GLib.Variant(SIGNATURES[key], value) for key, value in values.items()}
        self.ctx.call(
            "SetProfile",
            self.serial,
            variants,
            confirm,
            ok=_("Perfil de {game} salvo.").format(game=self.title_text),
            done=lambda _v: self.close(),
        )

    def confirm_delete(self) -> None:
        self.ctx.confirm(
            _("Apagar o perfil de {game}?").format(game=self.title_text),
            _("O jogo volta aos ajustes gerais. Uma configuração do RPCS3 criada pelo app para ele sai junto."),
            _("Apagar"),
            lambda: self.ctx.call(
                "DeleteProfile",
                self.serial,
                ok=_("Perfil de {game} apagado.").format(game=self.title_text),
                done=lambda _v: self.close(),
            ),
            destructive=True,
        )


class GamesPage(Page):
    title = _("Jogos")
    icon = "applications-games-symbolic"
    page_id = "games"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._profiles: dict[str, dict[str, Any]] = {}
        self._listed: list[str] | None = None
        self._status = Status()

        now = Adw.PreferencesGroup(title=_("Jogo aberto"))
        # Título do jogo vem do log do RPCS3: texto puro, nunca markup.
        self.current = Adw.ActionRow(use_markup=False, visible=False)
        self.current_button = Gtk.Button(valign=Gtk.Align.CENTER)
        self.current_button.add_css_class("suggested-action")
        self.current_button.connect("clicked", lambda _b: self.open_editor(self._status.game_serial))
        self.current.add_suffix(self.current_button)
        now.add(self.current)
        self.no_game = Gtk.Label(label=_("Abra um jogo no RPCS3 para criar o perfil dele."), xalign=0, wrap=True)
        self.no_game.add_css_class("dim-label")
        now.add(self.no_game)
        self.prefs.add(now)

        self.list_group = Adw.PreferencesGroup(
            title=_("Perfis"),
            description=_("Cada jogo pode ter som, volume, vibração e luz próprios. O resto vem dos ajustes gerais."),
        )
        self.empty = inline_state("empty-profiles")
        self.list_group.add(self.empty)
        self._profile_rows: list[Adw.ActionRow] = []
        self.prefs.add(self.list_group)

    # --- daemon → tela ---

    def update(self, s: Status) -> None:
        self._status = s
        if s.profiles != self._listed:
            self._listed = list(s.profiles)
            self.ctx.call("GetProfiles", done=self._got_profiles)
        else:
            self._show_profiles()
        game = s.game_serial if s.rpcs3_running else ""
        self.current.set_visible(bool(game))
        self.no_game.set_visible(not game)
        if game:
            self.current.set_title(s.game_title or game)
            self.current.set_subtitle(game)
            label = _("Editar perfil") if game in s.profiles else _("Criar perfil")
            self.current_button.set_label(label)

    def _got_profiles(self, value: Any) -> None:
        self._profiles = dict(value or {})
        self._show_profiles()

    def _show_profiles(self) -> None:
        for row in self._profile_rows:
            self.list_group.remove(row)
        self._profile_rows = []
        for serial, values in sorted(self._profiles.items(), key=lambda kv: str(kv[1].get("title", kv[0])).casefold()):
            subtitle = f"{serial} · {profile_summary(values)}"
            if serial == self._status.profile:
                subtitle = _("Ativo agora") + f" · {subtitle}"
            row = Adw.ActionRow(
                title=str(values.get("title") or serial), subtitle=subtitle, activatable=True, use_markup=False
            )
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _r, sid=serial: self.open_editor(sid))
            self.list_group.add(row)
            self._profile_rows.append(row)
        self.empty.set_visible(not self._profiles)

    def open_editor(self, serial: str) -> ProfileEditor:
        values = self._profiles.get(serial, {})
        title = str(values.get("title") or (self._status.game_title if serial == self._status.game_serial else serial))
        editor = ProfileEditor(self.ctx, serial, title, values, max_db=self._status.configured_max_db)
        editor.present(self)
        return editor

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Renderiza cada página da interface em PNG com estados sintéticos (sem daemon nem hardware).

Uso (sem abrir janela na sua sessão, num mutter headless):
    scripts/screenshots.sh <pasta de saída>
"""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "unit" / "app"))
from fake_client import FakeClient, sample  # noqa: E402

from ds4_companion.app.application import Application  # noqa: E402
from ds4_companion.common.models import Connection  # noqa: E402

SHOTS = [
    ("status", "status", {}),
    ("status-sem-controle", "status", {"connection": Connection.NONE}),
    ("status-sem-permissao", "status", {"hid_access": False}),
    ("audio", "audio", {"mirror_active": True, "game_running": True, "rpcs3_running": True}),
    ("audio-aguardando", "audio", {}),
    ("audio-alto", "audio", {"volume_db": -2.5, "mirror_active": True}),
    ("audio-sem-apps", "audio", {"apps": []}),
    ("audio-sugestoes", "audio", {"apps": ["rpcs3"], "playing": ["Firefox", "eldenring.exe", "Discord"]}),
    ("audio-bluetooth", "audio", {"connection": Connection.BLUETOOTH, "sink_present": False}),
    ("vibracao", "vibration", {"large_percent": 150, "players": [1, 2]}),
    ("audio-acima", "audio", {"volume_db": 2.0, "max_db": 3.0, "configured_max_db": 3.0}),
    ("vibracao-rpcs3-aberto", "vibration", {"rpcs3_running": True, "vibration_pending": True}),
    ("luz", "light", {"led_color": "pink"}),
    ("luz-personalizada", "light", {"led_color": "#FF8800", "led_mode": "battery"}),
    (
        "jogos",
        "games",
        {
            "rpcs3_running": True,
            "game_serial": "BLUS30001",
            "game_title": "Jogo de Teste",
            "profiles": ["BLUS30001", "NPEB00002"],
            "profile": "BLUS30001",
        },
    ),
    ("avancado", "advanced", {}),
    ("erro-pipewire", "status", {"error": "pw-dump não respondeu em 5 s"}),
]


def iterate(seconds: float = 0.4) -> None:
    ctx = GLib.MainContext.default()
    end = GLib.get_monotonic_time() + int(seconds * 1e6)
    while GLib.get_monotonic_time() < end:
        ctx.iteration(False)


def save(window: Gtk.Window, path: Path) -> None:
    paintable = Gtk.WidgetPaintable.new(window)
    width, height = window.get_width(), window.get_height()
    snapshot = Gtk.Snapshot()
    paintable.snapshot(snapshot, width, height)
    node = snapshot.to_node()
    texture = window.get_renderer().render_texture(node, None)
    texture.save_to_png(str(path))


def main(out: Path, width: int, height: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    client = FakeClient()
    client.results["GetProfiles"] = {
        "BLUS30001": {"title": "Jogo de Teste", "volume_db": -3.0, "large_percent": 150},
        "NPEB00002": {"title": "Jogo de Luta", "mirror_enabled": False, "led_color": "red"},
    }
    app = Application(client_factory=lambda: client)

    def run(_app: Adw.Application) -> None:
        window = app.get_active_window()
        window.set_default_size(width, height)
        window.loading._reveal()
        iterate()
        save(window, out / "carregando.png")
        window.loading._slow()
        iterate()
        save(window, out / "carregando-demorado.png")
        client.set_available(False)
        window._autostart = False  # type: ignore[attr-defined]
        client.set_available(False)
        window.root.set_visible_child_name("stopped")
        iterate()
        save(window, out / "servico-parado.png")
        client.set_available(True)
        for name, page, changes in SHOTS:
            client.push(sample(**changes))
            window.show_page(page)
            iterate()
            save(window, out / f"{name}.png")
            if page == "games":
                editor = window.stack.get_visible_child().open_editor("BLUS30001")
                iterate()
                save(window, out / "jogos-editor.png")
                editor.close()
                iterate()
        app.quit()

    app.connect("activate", lambda a: GLib.idle_add(lambda: run(a) or False))
    app.run([])


if __name__ == "__main__":
    size = sys.argv[2] if len(sys.argv) > 2 else "880x640"
    w, h = (int(v) for v in size.split("x"))
    main(Path(sys.argv[1]), w, h)

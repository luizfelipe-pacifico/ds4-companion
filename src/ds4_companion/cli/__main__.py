# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""ds4ctl: controla o ds4-companiond pelo terminal (mesma API D-Bus da interface)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from typing import Any, TextIO

from .. import __version__
from ..common.db import LIMIT_DB, VolumeZone, format_db, zone_for
from ..common.models import LED_ALIASES, Connection, Status, led_preset
from ..common.names import BUS_NAME, INTERFACE, OBJECT_PATH, SERVICE_UNIT

EXIT_OK, EXIT_ERROR, EXIT_NO_DAEMON = 0, 1, 3

CONNECTION_TEXT = {Connection.USB: "cabo USB", Connection.BLUETOOTH: "Bluetooth"}
ZONE_TEXT = {VolumeZone.FREE: "", VolumeZone.HIGH: " (alto)", VolumeZone.OVER_LIMIT: " (acima do limite)"}
LED_NAMES = {v: k for k, v in LED_ALIASES.items() if k != "desligado"}
# Opção da CLI → (campo do perfil, assinatura D-Bus).
PROFILE_OPTIONS = {
    "volume": ("volume_db", "d"),
    "mirror": ("mirror_enabled", "b"),
    "large": ("large_percent", "i"),
    "small": ("small_percent", "i"),
    "swap": ("swap_motors", "b"),
    "led": ("led_color", "s"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ds4ctl", description="Controla o DS4 Companion pelo terminal.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="comando")

    sub.add_parser("status", help="conexão, bateria, áudio e vibração")

    mirror = sub.add_parser("mirror", help="liga ou desliga o som do jogo no controle")
    mirror.add_argument("state", choices=["on", "off"])

    limiter = sub.add_parser("limiter", help="limitador contra picos acima de −1 dBFS")
    limiter.add_argument("state", choices=["on", "off"])

    volume = sub.add_parser("volume", help="volume do controle em dB (ex.: -6)")
    volume.add_argument("db", type=float)
    volume.add_argument("-y", "--yes", action="store_true", help="confirma volume acima de 0 dB sem perguntar")

    vib = sub.add_parser("vibration", help="força dos motores (0–200 %%) no RPCS3")
    vib.add_argument("--large", type=int, help="motor forte, em %%")
    vib.add_argument("--small", type=int, help="motor fraco, em %%")
    swap = vib.add_mutually_exclusive_group()
    swap.add_argument("--swap", dest="swap", action="store_true", default=None, help="inverte os motores")
    swap.add_argument("--no-swap", dest="swap", action="store_false", help="não inverte os motores")
    vib.add_argument("--players", type=int, nargs="+", metavar="N", help="jogadores do RPCS3 (1 a 7)")

    rumble = sub.add_parser("test-rumble", help="testa os motores por 0,5 s")
    rumble.add_argument("motor", choices=["strong", "weak", "both"], nargs="?", default="both")

    led = sub.add_parser("led", help="cor da barra de luz")
    led.add_argument("color", help="azul, vermelho, verde, rosa, roxo, ciano, laranja, branco, desligada ou #RRGGBB")
    led_mode = sub.add_parser("led-mode", help="luz fixa ou mostrando a bateria")
    led_mode.add_argument("mode", choices=["fixed", "battery"])
    per_player = sub.add_parser("led-per-player", help="uma cor por jogador no RPCS3, como no PS4")
    per_player.add_argument("state", choices=["on", "off"])

    sub.add_parser("test-tone", help="toca um apito só no controle")

    profile = sub.add_parser("profile", help="perfis por jogo: list, set ou delete (padrão: o jogo aberto)")
    profile.add_argument("action", choices=["list", "set", "delete"], nargs="?", default="list")
    profile.add_argument("--game", metavar="ID", help="ID do jogo (ex.: BLUS30001); padrão: o aberto no RPCS3")
    profile.add_argument("--volume", type=float, metavar="DB", help="volume do controle no jogo, em dB")
    profile.add_argument("--mirror", choices=["on", "off"], help="som do jogo no controle")
    profile.add_argument("--large", type=int, metavar="N", help="motor forte, em %%")
    profile.add_argument("--small", type=int, metavar="N", help="motor fraco, em %%")
    pswap = profile.add_mutually_exclusive_group()
    pswap.add_argument("--swap", dest="swap", action="store_true", default=None, help="inverte os motores")
    pswap.add_argument("--no-swap", dest="swap", action="store_false", help="não inverte os motores")
    profile.add_argument("--led", metavar="COR", help="cor da luz (nome ou #RRGGBB)")
    profile.add_argument(
        "--reset",
        action="append",
        default=[],
        choices=sorted(PROFILE_OPTIONS),
        help="volta um campo ao ajuste geral (pode repetir)",
    )
    profile.add_argument("-y", "--yes", action="store_true", help="confirma volume acima de 0 dB sem perguntar")

    apps = sub.add_parser("apps", help="apps cujo som vai para o controle (aceita padrões como *.exe)")
    apps.add_argument("action", choices=["list", "add", "remove"], nargs="?", default="list")
    apps.add_argument("name", nargs="?", help="nome do processo ou padrão (ex.: *.exe para Proton)")
    return parser


def format_status(s: Status) -> str:
    lines = []
    if s.connection == Connection.NONE:
        lines.append("Controle: nenhum conectado")
    else:
        battery = "bateria desconhecida" if s.battery < 0 else f"bateria {s.battery} %"
        if s.charging:
            battery += ", carregando"
        lines.append(f"Controle: {s.controller_name or 'DualShock 4'} — {CONNECTION_TEXT[Connection(s.connection)]}")
        lines.append(f"  {battery}")
        if not s.hid_access:
            lines.append("  sem acesso ao controle: desconecte e conecte de novo")
    game = f" · {s.game_title} ({s.game_serial})" if s.rpcs3_running and s.game_serial else ""
    playing = " · jogo tocando" if s.game_running else ""
    lines.append(f"RPCS3: {'aberto' if s.rpcs3_running else 'fechado'}{game}{playing}")
    if s.connection == Connection.BLUETOOTH:
        audio = "indisponível por Bluetooth — conecte o cabo"
    elif not s.mirror_enabled:
        audio = "desligado"
    else:
        audio = "ativo" if s.mirror_active else "ligado, aguardando o jogo"
    lines.append(f"Áudio no controle: {audio}")
    lines.append(f"Volume: {format_db(s.volume_db)}{ZONE_TEXT[zone_for(s.volume_db)]} · teto {format_db(s.max_db)}")
    if not s.limiter:
        lines.append("  limitador desligado")
    elif s.limiter_active:
        lines.append("  limitador ativo: picos até −1 dBFS")
    if s.headphones:
        lines.append("  fone conectado no controle")
    if s.output_name:
        lines.append(f"Saída principal: {s.output_name}")
    swap = " · motores invertidos" if s.swap_motors else ""
    lines.append(f"Vibração: forte {s.large_percent} % · fraco {s.small_percent} %{swap}")
    players = ", ".join(str(p) for p in s.players) or "nenhum"
    lines.append(f"  jogadores {players}{' · vale ao fechar o RPCS3' if s.vibration_pending else ''}")
    mode = " · mostra a bateria" if s.led_mode == "battery" else ""
    per_player = " · uma cor por jogador no RPCS3" if s.led_per_player else ""
    lines.append(f"Luz: {LED_NAMES.get(s.led_color, s.led_color)}{mode}{per_player}")
    if s.error:
        lines.append(f"Aviso: {s.error}")
    return "\n".join(lines)


def confirm_over_limit(db: float, ask: Callable[[str], str] | None = None) -> bool:
    print(
        f"{format_db(db)} passa de 0 dB: o som distorce e pode danificar o alto-falante do controle.",
        file=sys.stderr,
    )
    try:
        return (ask or input)("Continuar? [s/N] ").strip().casefold() in ("s", "sim", "y", "yes")
    except EOFError:
        return False


async def led_outcome(proxy: Any, done: str) -> str:
    """Com o RPCS3 aberto a luz não vai para o controle na hora (ele está usando o controle)."""
    status = Status.from_mapping({k: v.value for k, v in (await proxy.get_status()).items()})
    if status.rpcs3_running:
        return "Salvo. A luz muda no controle quando o RPCS3 fechar."
    return done


async def connect() -> Any:
    from dbus_next.aio.message_bus import MessageBus

    bus = await MessageBus().connect()
    intro = await bus.introspect(BUS_NAME, OBJECT_PATH)
    return bus, bus.get_proxy_object(BUS_NAME, OBJECT_PATH, intro).get_interface(INTERFACE)


async def run(args: argparse.Namespace, proxy: Any, out: TextIO) -> int:
    cmd = args.command
    if cmd == "status":
        raw = await proxy.get_status()
        print(format_status(Status.from_mapping({k: v.value for k, v in raw.items()})), file=out)
    elif cmd == "led-mode":
        await proxy.call_set_led_mode(args.mode)
        text = "mostra a bateria" if args.mode == "battery" else "fica na cor escolhida"
        print(await led_outcome(proxy, f"A luz {text}."), file=out)
    elif cmd == "led-per-player":
        await proxy.call_set_led_per_player(args.state == "on")
        text = (
            "No RPCS3, cada jogador ganha a sua cor (1 azul, 2 vermelho, 3 verde, 4 rosa)."
            if args.state == "on"
            else "No RPCS3, todos os jogadores usam a cor escolhida."
        )
        print(await led_outcome(proxy, text), file=out)
    elif cmd == "limiter":
        await proxy.call_set_limiter(args.state == "on")
        print("Limitador " + ("ligado." if args.state == "on" else "desligado."), file=out)
    elif cmd == "mirror":
        await proxy.call_set_mirror(args.state == "on")
        print("Som no controle " + ("ligado." if args.state == "on" else "desligado."), file=out)
    elif cmd == "volume":
        applied = await proxy.call_set_volume(args.db, args.yes)
        note = f" (teto: pedido {format_db(args.db)})" if abs(applied - args.db) > 0.05 else ""
        print(f"Volume do controle: {format_db(applied)}{note}", file=out)
    elif cmd == "vibration":
        status = Status.from_mapping({k: v.value for k, v in (await proxy.get_status()).items()})
        if args.players:
            await proxy.call_set_players(args.players)
        if args.large is not None or args.small is not None or args.swap is not None:
            large = status.large_percent if args.large is None else args.large
            small = status.small_percent if args.small is None else args.small
            swap = status.swap_motors if args.swap is None else args.swap
            await proxy.call_set_vibration(large, small, swap)
        status = Status.from_mapping({k: v.value for k, v in (await proxy.get_status()).items()})
        print(f"Vibração: forte {status.large_percent} % · fraco {status.small_percent} %", file=out)
        if status.vibration_pending:
            print("O RPCS3 está aberto: a mudança vale quando ele fechar e abrir de novo.", file=out)
        else:
            print("Vale ao abrir o RPCS3.", file=out)
    elif cmd == "test-rumble":
        await proxy.call_test_rumble(args.motor)
    elif cmd == "led":
        await proxy.call_set_led(args.color)
        print(await led_outcome(proxy, "Cor da luz alterada."), file=out)
    elif cmd == "test-tone":
        await proxy.call_play_test_tone()
    elif cmd == "apps":
        return await run_apps(args, proxy, out)
    elif cmd == "profile":
        return await run_profile(args, proxy, out)
    return EXIT_OK


def describe_profile(values: dict[str, Any]) -> str:
    parts = []
    if "mirror_enabled" in values:
        parts.append("som no controle " + ("ligado" if values["mirror_enabled"] else "desligado"))
    if "volume_db" in values:
        parts.append(f"volume {format_db(values['volume_db'])}")
    if "large_percent" in values:
        parts.append(f"forte {values['large_percent']} %")
    if "small_percent" in values:
        parts.append(f"fraco {values['small_percent']} %")
    if "swap_motors" in values:
        parts.append("motores invertidos" if values["swap_motors"] else "motores normais")
    if "led_color" in values:
        parts.append(f"luz {LED_NAMES.get(values['led_color'], values['led_color'])}")
    return " · ".join(parts) or "sem ajustes próprios"


async def run_profile(args: argparse.Namespace, proxy: Any, out: TextIO) -> int:
    from dbus_next.signature import Variant

    status = Status.from_mapping({k: v.value for k, v in (await proxy.get_status()).items()})
    profiles = {
        serial: {key: variant.value for key, variant in values.items()}
        for serial, values in (await proxy.call_get_profiles()).items()
    }
    if args.action == "list":
        if not profiles:
            print("Nenhum perfil. Crie com: ds4ctl profile set --volume -3 (com o jogo aberto)", file=out)
        for serial, values in profiles.items():
            active = " (ativo agora)" if serial == status.profile else ""
            print(f"{serial} · {values.get('title', serial)}{active}", file=out)
            print(f"  {describe_profile(values)}", file=out)
        return EXIT_OK
    serial = args.game or (status.game_serial if status.rpcs3_running else "")
    if not serial:
        print("Nenhum jogo aberto no RPCS3: diga qual com --game <ID> (ex.: BLUS30001).", file=sys.stderr)
        return EXIT_ERROR
    if args.action == "delete":
        if serial not in profiles:
            print(f"Não há perfil para {serial}.", file=sys.stderr)
            return EXIT_ERROR
        await proxy.call_delete_profile(serial)
        print(f"Perfil de {serial} apagado.", file=out)
        return EXIT_OK
    values = dict(profiles.get(serial, {}))
    for option in args.reset:
        values.pop(PROFILE_OPTIONS[option][0], None)
    given = {
        "volume": args.volume,
        "mirror": None if args.mirror is None else args.mirror == "on",
        "large": args.large,
        "small": args.small,
        "swap": args.swap,
        "led": led_preset(args.led).id if args.led else None,
    }
    for option, value in given.items():
        if value is not None:
            values[PROFILE_OPTIONS[option][0]] = value
    signatures = {key: sig for key, sig in PROFILE_OPTIONS.values()} | {"title": "s"}
    await proxy.call_set_profile(serial, {k: Variant(signatures[k], v) for k, v in values.items()}, args.yes)
    print(f"Perfil de {serial}: {describe_profile(values)}", file=out)
    return EXIT_OK


async def run_apps(args: argparse.Namespace, proxy: Any, out: TextIO) -> int:
    status = Status.from_mapping({k: v.value for k, v in (await proxy.get_status()).items()})
    if args.action == "list":
        print("Apps no controle:", file=out)
        for app in status.apps or ["(nenhum)"]:
            print(f"  {app}", file=out)
        if status.playing:
            print(f"Tocando agora: {', '.join(status.playing)}", file=out)
        return EXIT_OK
    if not args.name:
        print("Diga o nome do app: ds4ctl apps add <nome>", file=sys.stderr)
        return EXIT_ERROR
    known = [a.casefold() for a in status.apps]
    if args.action == "add":
        if args.name.casefold() not in known:
            await proxy.call_set_apps([*status.apps, args.name])
        print(f"O som de {args.name} vai para o controle.", file=out)
        return EXIT_OK
    if args.name.casefold() not in known:
        print(f"{args.name} não está na lista.", file=sys.stderr)
        return EXIT_ERROR
    await proxy.call_set_apps([a for a in status.apps if a.casefold() != args.name.casefold()])
    print(f"{args.name} saiu da lista.", file=out)
    return EXIT_OK


async def amain(argv: list[str] | None, out: TextIO = sys.stdout) -> int:
    args = build_parser().parse_args(argv)
    from dbus_next.errors import DBusError

    # A confirmação vem antes de abrir o D-Bus: desconectar no meio do registro do dbus-next
    # (pessoa recusou) despejava um traceback no terminal.
    wanted_db = args.db if args.command == "volume" else getattr(args, "volume", None)
    if args.command in ("volume", "profile") and wanted_db is not None and wanted_db > LIMIT_DB and not args.yes:
        if not confirm_over_limit(wanted_db):
            print("Volume não alterado.", file=out)
            return EXIT_ERROR
        args.yes = True
    if args.command == "profile" and args.led:
        try:
            led_preset(args.led)
        except KeyError:
            print(f"Cor desconhecida: {args.led}.", file=sys.stderr)
            return EXIT_ERROR

    try:
        bus, proxy = await connect()
    except Exception:
        print(
            f"O ds4-companiond não está rodando. Inicie com: systemctl --user start {SERVICE_UNIT}",
            file=sys.stderr,
        )
        return EXIT_NO_DAEMON
    try:
        return await run(args, proxy, out)
    except DBusError as exc:
        print(f"Erro: {exc.text}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        bus.disconnect()


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(amain(argv))


if __name__ == "__main__":
    raise SystemExit(main())

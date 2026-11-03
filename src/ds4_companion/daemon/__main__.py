# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""ds4-companiond: `python -m ds4_companion.daemon --foreground --debug`."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import signal
import sys

from .. import __version__
from ..common.names import BUS_NAME, OBJECT_PATH

log = logging.getLogger("ds4_companion.daemon")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ds4-companiond", description="Daemon do DS4 Companion.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--foreground", action="store_true", help="roda em primeiro plano (padrão no systemd)")
    parser.add_argument("--debug", action="store_true", help="log detalhado")
    parser.add_argument(
        "--stop-motors", action="store_true", help="para os motores do controle e sai (ExecStopPost do serviço)"
    )
    return parser.parse_args(argv)


def stop_motors() -> int:
    from .device import DeviceMonitor
    from .hid import hidraw, reports

    for controller in DeviceMonitor().scan():
        with contextlib.suppress(OSError):
            hidraw.write_report(controller.hidraw, reports.output_report(controller.connection, motors=(0, 0)))
    return 0


async def serve() -> int:
    from dbus_next.aio.message_bus import MessageBus
    from dbus_next.constants import BusType, RequestNameReply
    from dbus_next.errors import DBusError

    from .audio.pipewire import PipeWire
    from .dbus import DaemonInterface
    from .device import DeviceMonitor
    from .service import Daemon

    bus = await MessageBus(bus_type=BusType.SESSION).connect()
    devices = DeviceMonitor()
    audio = PipeWire()
    daemon = Daemon(audio, devices)
    bus.export(OBJECT_PATH, DaemonInterface(daemon))
    reply = await bus.request_name(BUS_NAME)
    if reply not in (RequestNameReply.PRIMARY_OWNER, RequestNameReply.ALREADY_OWNER):
        log.error("outro ds4-companiond já está rodando")
        bus.disconnect()
        return 1

    loop = asyncio.get_running_loop()

    def on_error(loop: asyncio.AbstractEventLoop, context: dict[str, object]) -> None:
        # O dbus-next já respondeu o erro ao cliente e ainda o relança aqui; é erro esperado
        # (ex.: "Nenhum controle conectado"), não falha do daemon.
        if isinstance(context.get("exception"), DBusError):
            log.debug("erro devolvido ao cliente: %s", context["exception"])
            return
        loop.default_exception_handler(context)

    loop.set_exception_handler(on_error)
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    await daemon.refresh()
    try:
        devices.start(loop, daemon.schedule_refresh)
    except OSError as exc:
        log.warning("sem eventos do udev (%s); seguindo só com verificação periódica", exc)
    tasks = [
        asyncio.ensure_future(daemon.poll_forever()),
        asyncio.ensure_future(daemon.watch_audio(audio.events)),
    ]
    log.info("ds4-companiond %s pronto", __version__)
    await stop.wait()

    log.info("encerrando")
    for task in tasks:
        task.cancel()
    devices.stop()
    daemon.stop_motors()
    bus.disconnect()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if args.stop_motors:
        return stop_motors()
    return asyncio.run(serve())


if __name__ == "__main__":
    raise SystemExit(main())

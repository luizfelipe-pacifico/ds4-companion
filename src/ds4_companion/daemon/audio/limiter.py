# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Limitador entre o jogo e o controle (ADR 0010): um `filter-chain` do PipeWire num processo filho.

O plugin `clamp` do próprio PipeWire segura cada amostra em −1 dBFS: nenhum pico passa disso no
alto-falante do controle, sem depender de pacote fora do `extra`. A entrada é um stream sem
conexão automática (não aparece como saída de som do sistema); a saída vai para o sink do controle.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path

from .graph import LIMITER_INPUT as INPUT_NODE
from .graph import LIMITER_OUTPUT as OUTPUT_NODE

log = logging.getLogger(__name__)

LIMIT_DBFS = -1.0
STARTUP_CHECK_SECONDS = 0.2


def limit_amplitude(dbfs: float = LIMIT_DBFS) -> float:
    return float(10 ** (dbfs / 20))


def config_text(target: str, dbfs: float = LIMIT_DBFS) -> str:
    """Configuração do processo filho. `target` (nome do sink, vindo do PipeWire) vai como string JSON."""
    peak = f"{limit_amplitude(dbfs):.6f}"
    return f"""# Gerado pelo ds4-companiond. Limitador: nenhum pico acima de {dbfs:g} dBFS no controle.
context.properties = {{ log.level = 0 }}
context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.*       = support/libspa-support
}}
context.modules = [
    {{ name = libpipewire-module-protocol-native }}
    {{ name = libpipewire-module-client-node }}
    {{ name = libpipewire-module-adapter }}
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "DS4 Companion: limitador"
            media.name       = "DS4 Companion: limitador"
            audio.channels   = 2
            audio.position   = [ FL FR ]
            filter.graph = {{
                nodes = [
                    {{ type = builtin name = limit label = clamp control = {{ "Min" = -{peak} "Max" = {peak} }} }}
                ]
            }}
            capture.props = {{
                node.name         = "{INPUT_NODE}"
                media.class       = "Stream/Input/Audio"
                node.autoconnect  = false
                node.passive      = true
            }}
            playback.props = {{
                node.name          = "{OUTPUT_NODE}"
                media.class        = "Stream/Output/Audio"
                target.object      = {json.dumps(target)}
                node.dont-reconnect = true
                node.passive       = true
                # Sem upmix: no DualSense (4 canais) RL/RR são os atuadores hápticos (ADR 0011).
                channelmix.upmix   = false
            }}
        }}
    }}
]
"""


def runtime_dir() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())


class Limiter:
    """Mantém (ou não) o processo do limitador apontado para o sink certo."""

    def __init__(self, conf_dir: Path | None = None) -> None:
        self._conf_dir = conf_dir
        self._proc: asyncio.subprocess.Process | None = None
        self.target: str | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def ensure(self, target: str | None) -> bool:
        """Liga para `target` (ou desliga com None). Devolve True se algo mudou."""
        if target is None:
            if not self.running:
                return False
            await self.stop()
            return True
        if self.running and self.target == target:
            return False
        await self.stop()
        conf = (self._conf_dir or runtime_dir()) / "ds4-companion-limiter.conf"
        conf.write_text(config_text(target), encoding="utf-8")
        try:
            self._proc = await asyncio.create_subprocess_exec(
                "pipewire",
                "-c",
                str(conf),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as exc:
            log.warning("limitador não iniciou: %s", exc)
            self._proc = None
            return False
        # Se o PipeWire recusar a configuração, o filho sai logo: aí o som segue direto ao controle.
        await asyncio.sleep(STARTUP_CHECK_SECONDS)
        if self._proc.returncode is not None:
            log.warning("limitador saiu ao iniciar (código %s); som direto ao controle", self._proc.returncode)
            self._proc = None
            return False
        self.target = target
        log.info("limitador ligado (picos até %g dBFS)", LIMIT_DBFS)
        return True

    async def stop(self) -> None:
        proc, self._proc = self._proc, None
        self.target = None
        if proc is None or proc.returncode is not None:
            return
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), 3)
        except TimeoutError:
            proc.kill()
            with contextlib.suppress(ProcessLookupError):
                await proc.wait()
        log.info("limitador desligado")

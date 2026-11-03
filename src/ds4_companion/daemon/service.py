# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Núcleo do ds4-companiond: junta controle, PipeWire, hidraw e RPCS3 e aplica os limites.

Regras de segurança aplicadas aqui (SECURITY.md), para valer igual na GUI e na CLI:
- volume nunca passa do teto efetivo (`max_db`, ou `headphone_max_db` com fone); acima de 0 dB só
  com confirmação; ao aparecer o controle, o volume salvo é reaplicado;
- teste de vibração dura 0,5 s (máximo 2 s), com intervalo mínimo entre testes;
- nada vai para o hidraw nem para o Default.yml com o RPCS3 aberto: fica pendente.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import os
import tempfile
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from ..common import config as cfg
from ..common.db import LIMIT_DB, clamp_db, db_to_volume, volume_to_db
from ..common.models import LED_MODES, PLAYER_LEDS, Connection, Model, Motor, Status, led_preset, led_rgb
from .audio import graph as audio_graph
from .audio.pipewire import PipeWireError, write_test_tone
from .device import EDGE_PRODUCT, Controller, pick, read_battery, redact
from .hid import hidraw, reports
from .rpcs3 import game, input_config, process

log = logging.getLogger(__name__)

RUMBLE_SECONDS = 0.5
RUMBLE_MAX_SECONDS = 2.0
RUMBLE_COOLDOWN = 1.0
POLL_SECONDS = 3.0
DEBOUNCE_SECONDS = 0.15
LIMITER_SETTLE_SECONDS = 0.3
VOLUME_TOLERANCE_DB = 0.3
MAX_PLAYING = 16
PROFILE_FIELDS = ("mirror_enabled", "volume_db", "large_percent", "small_percent", "swap_motors", "led_color")
RPCS3_PROFILE_FIELDS = ("large_percent", "small_percent", "swap_motors", "led_color")


class DaemonError(Exception):
    """Erro de uma ação pedida pela GUI/CLI. `code` vira o nome do erro D-Bus."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AudioBackend(Protocol):
    async def dump(self) -> audio_graph.Graph: ...
    async def link(self, output_port: int, input_port: int) -> None: ...
    async def unlink(self, output_port: int, input_port: int) -> None: ...
    async def set_volume(self, node_id: int, volume: float) -> None: ...
    async def play(self, path: Path, target: str) -> None: ...


class LimiterProcess(Protocol):
    async def ensure(self, target: str | None) -> bool: ...
    async def stop(self) -> None: ...


class Devices(Protocol):
    def scan(self) -> list[Controller]: ...


Listener = Callable[[Status], None]


class Daemon:
    def __init__(
        self,
        audio: AudioBackend,
        devices: Devices,
        config_path: Path | None = None,
        *,
        write_report: Callable[[str, bytes], None] = hidraw.write_report,
        read_report: Callable[[str], bytes | None] = hidraw.read_report,
        read_feature: Callable[[str, int, int], bytes] = hidraw.get_feature,
        rpcs3_running: Callable[[], bool] = process.is_running,
        game_watcher: game.LogWatcher | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        limiter: LimiterProcess | None = None,
    ) -> None:
        self._audio = audio
        # Sem limitador por padrão: só o executável do daemon passa o processo real (testes não
        # sobem um PipeWire de verdade).
        self._limiter = limiter
        self._devices = devices
        self._config_path = config_path or cfg.default_path()
        self._write_report = write_report
        self._read_report = read_report
        self._read_feature = read_feature
        self._vibration_v2: bool | None = None  # DualSense: lido do firmware uma vez por conexão
        self._rpcs3_running = rpcs3_running
        self._game_watcher = game_watcher or game.LogWatcher()
        self._sleep = sleep
        self.config, warnings = cfg.load(self._config_path)
        for warning in warnings:
            log.warning("config: %s", warning)
        self.controller: Controller | None = None
        self.graph = audio_graph.Graph()
        self.status = Status()
        # O que os ouvintes viram por último. Alguns campos mudam direto em self.status (RPCS3
        # aberto, jogo, fone): comparar com ele mesmo escondia essas mudanças.
        self._published: Status | None = None
        self._applied_profile: str | None = None  # perfil cujo volume está no controle agora
        self._orphan_rpcs3_files: list[Path] = []  # arquivos por jogo que o app criou e o perfil saiu
        self._listeners: list[Listener] = []
        self._sink_id: int | None = None
        self._last_rumble = -math.inf
        self._rpcs3_pending = False
        self._led_pending = False
        self._backed_up = False  # um backup do Default.yml por execução, não um por ajuste
        self._applied_rgb: tuple[int, int, int] | None = None
        self._refresh_lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[None] | None = None
        self._update_status()

    # --- ciclo de vida ------------------------------------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def refresh(self) -> None:
        """Relê tudo (controle, RPCS3, PipeWire) e reconcilia links, teto e pendências."""
        async with self._refresh_lock:
            self.status.hid_access = True  # recalculado: qualquer falha de acesso abaixo derruba
            self._scan_devices()
            await self._check_rpcs3()
            await self._refresh_audio()
            await self._probe_headphones()
            self._update_status()

    def schedule_refresh(self) -> None:
        """Agrupa rajadas de eventos (udev, PipeWire) num refresh só."""
        if self._refresh_task is not None and not self._refresh_task.done():
            return

        async def later() -> None:
            await self._sleep(DEBOUNCE_SECONDS)
            try:
                await self.refresh()
            except Exception:
                log.exception("falha ao atualizar o estado")

        self._refresh_task = asyncio.ensure_future(later())

    async def poll_forever(self) -> None:
        while True:
            await self._sleep(POLL_SECONDS)
            try:
                await self.refresh()
            except Exception:
                log.exception("falha ao atualizar o estado")

    async def watch_audio(self, events: Callable[[], AsyncIterator[None]]) -> None:
        """Consome o monitor do PipeWire; se ele cair, tenta de novo com espera crescente."""
        delay = 1.0
        while True:
            try:
                async for _ in events():
                    delay = 1.0
                    self.schedule_refresh()
            except (OSError, PipeWireError) as exc:
                log.warning("monitor do PipeWire caiu: %s", exc)
            await self._sleep(delay)
            delay = min(delay * 2, 30.0)

    def stop_motors(self) -> None:
        if self.controller is None:
            return
        with contextlib.suppress(OSError, ValueError):
            self._write_report(self.controller.hidraw, self._report(self.controller, motors=(0, 0)))

    # --- leitura do estado --------------------------------------------------------------------

    def _scan_devices(self) -> None:
        previous = self.controller
        self.controller = pick(self._devices.scan())
        if self.controller != previous:
            if self.controller is None:
                log.info("controle desconectado")
            else:
                log.info("controle conectado: %s (%s)", self.controller.name, self.controller.connection)
                if self.controller.battery_dir:
                    log.debug("bateria em %s", redact(self.controller.battery_dir))
                self._led_pending = True
            self._vibration_v2 = None

    async def _check_rpcs3(self) -> None:
        running = await asyncio.to_thread(self._rpcs3_running)
        self.status.rpcs3_running = running
        if running:
            current = await asyncio.to_thread(self._game_watcher.poll)
            self.status.game_serial = current.serial if current else ""
            self.status.game_title = current.title if current else ""
            return  # o RPCS3 só lê o Default.yml ao abrir e usa o controle: fica pendente
        # Fechado: o log que sobrou é de uma execução que acabou.
        self._game_watcher.reset()
        self.status.game_serial = self.status.game_title = ""
        if self._rpcs3_pending:
            self._write_rpcs3()
        # Modo bateria: a faixa de carga mudou, a cor no controle muda junto.
        if self.controller is not None and self._applied_rgb not in (None, self._effective_led()):
            self._led_pending = True
        if self._led_pending:
            self._apply_led_hid()

    async def _refresh_audio(self) -> None:
        try:
            self.graph = await self._audio.dump()
        except PipeWireError as exc:
            log.warning("PipeWire: %s", exc)
            self.status.error = str(exc)
            return
        apps = self.config.audio.apps
        sink = self.graph.ds4_sink()
        profile = self.active_profile_serial
        if sink is not None and (sink.id != self._sink_id or profile != self._applied_profile):
            log.info("volume do controle: %.1f dB (%s)", self._volume_setting(), profile or "ajuste geral")
            self._sink_id = sink.id
            self._applied_profile = profile
            await self._apply_volume(self._volume_setting())
        elif sink is None:
            self._sink_id = None

        try:
            if await self._sync_limiter(sink):
                await self._sleep(LIMITER_SETTLE_SECONDS)  # os nós do limitador aparecem logo depois
                self.graph = await self._audio.dump()
            if self._mirror_setting():
                pairs = audio_graph.stale_links(self.graph, apps)
                for out_port, in_port in pairs:
                    await self._audio.unlink(out_port, in_port)
                missing = audio_graph.missing_links(self.graph, apps)
                for out_port, in_port in missing:
                    await self._audio.link(out_port, in_port)
                pairs = pairs + missing
            else:
                pairs = audio_graph.mirror_links(self.graph, apps)
                for out_port, in_port in pairs:
                    await self._audio.unlink(out_port, in_port)
            lowered = await self._enforce_ceiling()
            if pairs or lowered:
                self.graph = await self._audio.dump()  # o estado publicado reflete o que mudou
        except PipeWireError as exc:
            log.warning("PipeWire: %s", exc)
            self.status.error = str(exc)
            return
        self.status.error = ""

    async def _sync_limiter(self, sink: audio_graph.Node | None) -> bool:
        """Liga o limitador apontado para o controle quando o espelhamento está ligado."""
        if self._limiter is None:
            return False
        audio = self.config.audio
        want = sink.name if sink is not None and self._mirror_setting() and audio.limiter else None
        return await self._limiter.ensure(want)

    async def stop_limiter(self) -> None:
        if self._limiter is not None:
            await self._limiter.stop()

    async def _enforce_ceiling(self) -> bool:
        sink = self.graph.ds4_sink()
        if sink is None or sink.volume is None:
            return False
        current = volume_to_db(sink.volume)
        ceiling = self.effective_max_db
        if current > ceiling + VOLUME_TOLERANCE_DB:
            log.warning("volume do controle em %.1f dB passou do teto; rebaixando para %.1f dB", current, ceiling)
            await self._audio.set_volume(sink.id, db_to_volume(ceiling))
            self._store_volume(ceiling)
            self._save()
            return True
        return False

    async def _probe_headphones(self) -> None:
        c = self.controller
        if c is None or c.connection != Connection.USB:
            self.status.headphones = False
            return
        try:
            data = await asyncio.to_thread(self._read_report, c.hidraw)
        except hidraw.HidAccessError:
            self.status.hid_access = False
            return
        except OSError:
            return
        parse = reports.parse_dualsense_usb_input if c.model == Model.DUALSENSE else reports.parse_usb_input
        parsed = parse(data) if data else None
        if parsed is not None and parsed.headphones != self.status.headphones:
            self.status.headphones = parsed.headphones
            log.info("fone no controle: %s", "sim" if parsed.headphones else "não")
            try:
                if await self._enforce_ceiling():
                    self.graph = await self._audio.dump()
            except PipeWireError as exc:
                log.warning("PipeWire: %s", exc)

    @property
    def effective_max_db(self) -> float:
        audio = self.config.audio
        ceiling = min(audio.headphone_max_db, audio.max_db) if self.status.headphones else audio.max_db
        return clamp_db(ceiling, audio.max_db)

    def _update_status(self) -> None:
        c = self.controller
        battery, charging = read_battery(c.battery_dir if c else None)
        sink = self.graph.ds4_sink()
        default = self.graph.default_sink_node()
        apps = self.config.audio.apps
        audio, vib = self.config.audio, self.config.vibration
        new = replace(
            self.status,
            connection=c.connection if c else Connection.NONE,
            controller_name=c.name if c else "",
            controller_model=c.model if c else "",
            battery=battery,
            charging=charging,
            hid_access=self.status.hid_access if c else True,
            headphones=self.status.headphones if c else False,
            game_running=bool(self.graph.streams(apps)),
            mirror_enabled=self._mirror_setting(),
            profile=self.active_profile_serial or "",
            profiles=sorted(self.config.profiles),
            mirror_active=audio_graph.is_mirroring(self.graph, apps),
            sink_present=sink is not None,
            volume_db=volume_to_db(sink.volume) if sink and sink.volume is not None else self._volume_setting(),
            max_db=self.effective_max_db,
            configured_max_db=audio.max_db,
            output_name=(default.description or default.name) if default else "",
            apps=list(apps),
            playing=self.graph.playing()[:MAX_PLAYING],
            limiter=audio.limiter,
            limiter_active=self.graph.limiter_input() is not None,
            large_percent=vib.large_percent,
            small_percent=vib.small_percent,
            swap_motors=vib.swap_motors,
            players=list(vib.players),
            vibration_pending=self._rpcs3_pending,
            led_color=self.config.led.color,
            led_mode=self.config.led.mode,
            led_per_player=self.config.led.per_player,
            rpcs3_config_dir=self.config.rpcs3.config_dir,
            backup_before_edit=self.config.rpcs3.backup_before_edit,
        )
        if c is not None and c.hidraw and not hidraw.can_write(c.hidraw):
            new.hid_access = False
        self.status = new
        if new != self._published:
            self._published = replace(new)
            for listener in list(self._listeners):
                listener(new)

    # --- perfis por jogo (ADR 0012) ------------------------------------------------------------

    @property
    def active_profile_serial(self) -> str | None:
        serial = self.status.game_serial
        return serial if self.status.rpcs3_running and serial in self.config.profiles else None

    def _active_profile(self) -> cfg.ProfileConfig | None:
        serial = self.active_profile_serial
        return self.config.profiles[serial] if serial else None

    def _mirror_setting(self) -> bool:
        profile = self._active_profile()
        if profile is not None and profile.mirror_enabled is not None:
            return profile.mirror_enabled
        return self.config.audio.mirror_enabled

    def _volume_setting(self) -> float:
        profile = self._active_profile()
        if profile is not None and profile.volume_db is not None:
            return profile.volume_db
        return self.config.audio.volume_db

    def _store_volume(self, db: float) -> None:
        """Guarda o volume onde ele vale agora: no perfil ativo, se ele define volume, ou no geral."""
        profile = self._active_profile()
        if profile is not None and profile.volume_db is not None:
            profile.volume_db = db
        else:
            self.config.audio.volume_db = db

    def get_profiles(self) -> dict[str, dict[str, object]]:
        """Perfis com os campos definidos (o resto vem dos ajustes gerais)."""
        result: dict[str, dict[str, object]] = {}
        for serial, profile in sorted(self.config.profiles.items()):
            values: dict[str, object] = {"title": profile.title}
            for key in PROFILE_FIELDS:
                value = getattr(profile, key)
                if value is not None:
                    values[key] = value
            result[serial] = values
        return result

    async def set_profile(self, serial: str, values: dict[str, object], confirm: bool = False) -> None:
        """Cria ou substitui o perfil do jogo `serial`; campo ausente = vale o ajuste geral."""
        if not cfg.GAME_SERIAL.fullmatch(serial):
            raise DaemonError("InvalidArgument", "ID de jogo inválido (ex.: BLUS30001).")
        if serial not in self.config.profiles and len(self.config.profiles) >= cfg.MAX_PROFILES:
            raise DaemonError("InvalidArgument", f"No máximo {cfg.MAX_PROFILES} perfis.")
        old = self.config.profiles.get(serial)
        profile = cfg.ProfileConfig(created_rpcs3_file=old.created_rpcs3_file if old else False)
        for key, raw in values.items():
            if key not in (*PROFILE_FIELDS, "title"):
                raise DaemonError("InvalidArgument", f"Campo de perfil desconhecido: {key}.")
            try:
                setattr(profile, key, cfg.PROFILE_SCHEMA[key](raw))
            except cfg.ConfigError as exc:
                raise DaemonError("InvalidArgument", f"Perfil, {key}: {exc}.") from exc
        if profile.volume_db is not None:
            profile.volume_db = clamp_db(profile.volume_db, self.config.audio.max_db)
            if profile.volume_db > LIMIT_DB and not confirm:
                raise DaemonError(
                    "NeedsConfirmation",
                    "Acima de 0 dB o som distorce e pode danificar o alto-falante. Confirme para continuar.",
                )
        if not profile.title:
            same_game = self.status.game_serial == serial and self.status.game_title
            profile.title = self.status.game_title if same_game else (old.title if old and old.title else serial)
        self.config.profiles[serial] = profile
        self._applied_profile = None if serial == self.active_profile_serial else self._applied_profile
        self._rpcs3_pending = True
        self._save()
        await self.refresh()

    async def delete_profile(self, serial: str) -> None:
        profile = self.config.profiles.pop(serial, None)
        if profile is None:
            raise DaemonError("InvalidArgument", f"Não há perfil para {serial}.")
        if profile.created_rpcs3_file:
            self._orphan_rpcs3_files.append(self._per_game_file(serial))
            self._rpcs3_pending = True
        self._save()
        await self.refresh()

    def _per_game_file(self, serial: str) -> Path:
        # serial validado pelo GAME_SERIAL: só letras e números, nunca "..".
        return self.config.rpcs3.input_file.parent.parent / serial / self.config.rpcs3.input_file.name

    def _write_profiles_rpcs3(self, global_text: str | None) -> bool:
        """Vibração e luz dos perfis no arquivo por jogo do RPCS3. True se algo mudou no config."""
        changed = False
        for path in self._orphan_rpcs3_files:
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
                log.info("perfil apagado: %s removido", path.parent.name)
            with contextlib.suppress(OSError):
                path.parent.rmdir()  # só se ficou vazia
        self._orphan_rpcs3_files = []
        vib = self.config.vibration
        for serial, profile in self.config.profiles.items():
            path = self._per_game_file(serial)
            wants = any(getattr(profile, k) is not None for k in RPCS3_PROFILE_FIELDS)
            if not wants:
                if profile.created_rpcs3_file:
                    self._orphan_rpcs3_files.append(path)
                    profile.created_rpcs3_file = False
                    changed = True
                continue
            exists = path.exists()
            if not exists and global_text is None:
                continue  # sem o global para copiar
            text = path.read_text(encoding="utf-8") if exists else str(global_text)
            vibration = input_config.Vibration(
                vib.large_percent if profile.large_percent is None else profile.large_percent,
                vib.small_percent if profile.small_percent is None else profile.small_percent,
                vib.swap_motors if profile.swap_motors is None else profile.swap_motors,
            )
            text, _ = input_config.apply_vibration(text, vib.players, vibration)
            text, _ = self._apply_rpcs3_color(text, profile.led_color)
            if exists:
                input_config.write_with_backup(path, text, backup=False)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_name(f".{path.name}.ds4-companion.tmp")
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, path)
                profile.created_rpcs3_file = True
                changed = True
                log.info("perfil %s: arquivo por jogo do RPCS3 criado a partir do global", serial)
        if self._orphan_rpcs3_files:
            return self._write_profiles_rpcs3(global_text) or changed
        return changed

    # --- ações (GUI e CLI) --------------------------------------------------------------------

    async def set_mirror(self, enabled: bool) -> None:
        self.config.audio.mirror_enabled = enabled
        self._save()
        await self.refresh()

    async def set_volume(self, db: float, confirm: bool = False) -> float:
        if not math.isfinite(db):
            raise DaemonError("InvalidArgument", "Volume precisa ser um número em dB.")
        target = clamp_db(db, self.effective_max_db)
        if target > LIMIT_DB and not confirm:
            raise DaemonError(
                "NeedsConfirmation",
                "Acima de 0 dB o som distorce e pode danificar o alto-falante. Confirme para continuar.",
            )
        await self._apply_volume(target)
        self._store_volume(target)
        self._save()
        await self.refresh()
        return target

    async def _apply_volume(self, db: float) -> None:
        sink = self.graph.ds4_sink()
        if sink is None:
            return
        try:
            await self._audio.set_volume(sink.id, db_to_volume(clamp_db(db, self.effective_max_db)))
        except PipeWireError as exc:
            raise DaemonError("Failed", f"Não deu para mudar o volume: {exc}") from exc

    async def set_limiter(self, enabled: bool) -> None:
        self.config.audio.limiter = enabled
        self._save()
        await self.refresh()

    async def set_vibration(self, large: int, small: int, swap: bool) -> None:
        for value in (large, small):
            if not 0 <= value <= cfg.MAX_PERCENT:
                raise DaemonError("InvalidArgument", f"Força precisa ficar entre 0 e {cfg.MAX_PERCENT} %.")
        vib = self.config.vibration
        vib.large_percent, vib.small_percent, vib.swap_motors = large, small, swap
        self._rpcs3_pending = True
        self._save()
        await self.refresh()

    async def set_players(self, players: list[int]) -> None:
        try:
            self.config.vibration.players = cfg.validate_players(players)
        except cfg.ConfigError as exc:
            raise DaemonError("InvalidArgument", f"Jogadores: {exc}.") from exc
        self._rpcs3_pending = True
        self._save()
        await self.refresh()

    async def test_rumble(self, motor: str) -> None:
        try:
            which = Motor(motor)
        except ValueError:
            raise DaemonError("InvalidArgument", "Motor precisa ser strong, weak ou both.") from None
        c = self._require_hid()
        now = time.monotonic()
        if now - self._last_rumble < RUMBLE_COOLDOWN:
            raise DaemonError("Busy", "Espere um instante entre os testes.")
        self._last_rumble = now
        vib = self.config.vibration
        strong = reports.percent_to_byte(vib.large_percent) if which != Motor.WEAK else 0
        weak = reports.percent_to_byte(vib.small_percent) if which != Motor.STRONG else 0
        if vib.swap_motors:
            strong, weak = weak, strong
        try:
            self._write_report(c.hidraw, self._report(c, motors=(strong, weak)))
            await self._sleep(min(RUMBLE_SECONDS, RUMBLE_MAX_SECONDS))
        except OSError as exc:
            raise self._hid_error(exc) from exc
        finally:
            self.stop_motors()

    async def set_led(self, color: str) -> None:
        try:
            preset = led_preset(color)
        except KeyError:
            raise DaemonError("InvalidArgument", f"Cor desconhecida: {color}.") from None
        self.config.led.color = preset.id
        self._led_pending = True
        self._rpcs3_pending = True
        self._save()
        await self.refresh()

    async def play_test_tone(self) -> None:
        sink = self.graph.ds4_sink()
        if sink is None:
            raise DaemonError("NotConnected", "Conecte o controle pelo cabo para tocar o apito.")
        tone = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / "ds4-companion-apito.wav"
        await asyncio.to_thread(write_test_tone, tone)
        try:
            await self._audio.play(tone, sink.name)
        except PipeWireError as exc:
            raise DaemonError("Failed", f"Não deu para tocar o apito: {exc}") from exc

    async def set_apps(self, apps: list[str]) -> None:
        try:
            self.config.audio.apps = cfg.validate_apps(apps)
        except cfg.ConfigError as exc:
            raise DaemonError("InvalidArgument", f"Apps: {exc}.") from exc
        self._save()
        await self.refresh()

    async def set_rpcs3_dir(self, path: str) -> None:
        if not path.strip() or "\0" in path or not Path(path).expanduser().is_dir():
            raise DaemonError("InvalidArgument", "Escolha uma pasta que exista.")
        self.config.rpcs3.config_dir = path
        self._save()
        await self.refresh()

    async def set_backup(self, enabled: bool) -> None:
        self.config.rpcs3.backup_before_edit = enabled
        self._save()
        await self.refresh()

    async def restore_defaults(self) -> None:
        self.config = cfg.Config()
        self._rpcs3_pending = True
        self._led_pending = True
        self._save()
        self._sink_id = None  # reaplica o volume padrão
        await self.refresh()

    # --- hardware e arquivos ------------------------------------------------------------------

    def _require_hid(self) -> Controller:
        c = self.controller
        if c is None:
            raise DaemonError("NotConnected", "Nenhum controle conectado.")
        if self.status.rpcs3_running:
            raise DaemonError("Busy", "Feche o RPCS3 para testar: ele está usando o controle.")
        return c

    async def set_led_per_player(self, enabled: bool) -> None:
        """Uma cor por jogador no RPCS3 (como no PS4); o controle fora do jogo segue com a cor escolhida."""
        self.config.led.per_player = enabled
        self._rpcs3_pending = True
        self._save()
        await self.refresh()

    def _apply_rpcs3_color(self, text: str, color: str | None) -> tuple[str, list[str]]:
        """Cor da luz no Default.yml: `color` (do perfil) em todos, ou uma por jogador, ou a geral."""
        players = self.config.vibration.players
        if color is None and self.config.led.per_player:
            warnings: list[str] = []
            for player in players:
                rgb = led_preset(PLAYER_LEDS.get(player, self.config.led.color)).rgb
                text, found = input_config.apply_color(text, [player], rgb)
                warnings += found
            return text, warnings
        return input_config.apply_color(text, players, led_preset(color or self.config.led.color).rgb)

    async def set_led_mode(self, mode: str) -> None:
        if mode not in LED_MODES:
            raise DaemonError("InvalidArgument", "Modo da luz precisa ser fixed ou battery.")
        self.config.led.mode = mode
        self._led_pending = True
        self._save()
        await self.refresh()

    def _report(
        self, c: Controller, *, motors: tuple[int, int] | None = None, rgb: tuple[int, int, int] | None = None
    ) -> bytes:
        """Relatório de saída no formato do modelo conectado."""
        if c.model == Model.DUALSENSE and motors is not None and self._vibration_v2 is None:
            try:
                feature = self._read_feature(
                    c.hidraw, reports.DS_FEATURE_FIRMWARE_INFO, reports.DS_FEATURE_FIRMWARE_SIZE
                )
            except OSError as exc:
                log.debug("versão do firmware do DualSense ilegível (%s); usando vibração v2", exc)
                feature = b""
            self._vibration_v2 = c.product == EDGE_PRODUCT or reports.uses_vibration_v2(feature)
        return reports.output_report(
            c.connection, motors=motors, rgb=rgb, model=c.model, vibration_v2=self._vibration_v2 is not False
        )

    def _hid_error(self, exc: OSError) -> DaemonError:
        if isinstance(exc, hidraw.HidAccessError):
            self.status.hid_access = False
            return DaemonError("AccessDenied", "Sem acesso ao controle. Desconecte e conecte de novo.")
        return DaemonError("Failed", f"Falha ao falar com o controle: {exc.strerror or exc}")

    def _effective_led(self) -> tuple[int, int, int]:
        battery, _charging = read_battery(self.controller.battery_dir if self.controller else None)
        return led_rgb(self.config.led.color, self.config.led.mode, battery)

    def _apply_led_hid(self) -> None:
        c = self.controller
        if c is None:
            return
        rgb = self._effective_led()
        try:
            self._write_report(c.hidraw, self._report(c, rgb=rgb))
        except OSError as exc:
            log.warning("luz não aplicada: %s", exc)
            if isinstance(exc, hidraw.HidAccessError):
                self.status.hid_access = False
            return
        self._led_pending = False
        self._applied_rgb = rgb

    def _write_rpcs3(self) -> None:
        path = self.config.rpcs3.input_file
        vib = self.config.vibration
        try:
            text = original = path.read_text(encoding="utf-8")
            text, warnings = input_config.apply_vibration(
                text, vib.players, input_config.Vibration(vib.large_percent, vib.small_percent, vib.swap_motors)
            )
            text, color_warnings = self._apply_rpcs3_color(text, None)
            for warning in dict.fromkeys(warnings + color_warnings):
                log.warning("RPCS3: %s", warning)
            want_backup = self.config.rpcs3.backup_before_edit and not self._backed_up
            backup = input_config.write_with_backup(path, text, want_backup)
        except FileNotFoundError:
            log.info("RPCS3 sem %s; nada a editar", path.name)
            original = None
        except (OSError, input_config.Rpcs3ConfigError) as exc:
            log.warning("não deu para editar o Default.yml: %s", exc)
            return
        else:
            if backup:
                self._backed_up = True
                log.info("Default.yml atualizado (backup: %s)", backup.name)
        try:
            if self._write_profiles_rpcs3(original):
                self._save()
        except (OSError, input_config.Rpcs3ConfigError, DaemonError) as exc:
            log.warning("não deu para gravar os perfis no RPCS3: %s", exc)
            return
        self._rpcs3_pending = False

    def _save(self) -> None:
        cfg.normalize(self.config)
        try:
            cfg.save(self.config, self._config_path)
        except OSError as exc:
            raise DaemonError("Failed", f"Não deu para salvar a configuração: {exc.strerror}") from exc

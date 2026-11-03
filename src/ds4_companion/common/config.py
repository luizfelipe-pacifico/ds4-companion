# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""`~/.config/ds4-companion/config.toml`: leitura, validação, padrões e gravação.

Valor inválido nunca derruba o daemon: volta para o padrão e gera um aviso. O teto de volume
é conferido aqui também, para nenhum caminho gravar um `volume_db` acima de `max_db`.
"""

from __future__ import annotations

import fnmatch
import json
import math
import os
import re
import shutil
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .db import ABSOLUTE_MAX_DB, FLOOR_DB
from .models import DEFAULT_LED, HEX_COLOR, LED_MODES, LED_PRESETS

DEFAULT_APPS = ("rpcs3", "AppRun.wrapped")
MAX_APPS = 32
MAX_APP_NAME = 64
MAX_PERCENT = 200
MAX_PLAYERS = 7
# Apps que nunca devem ir para o controle sem querer: um padrão que pega todos eles pega tudo.
_EVERYDAY_APPS = ("firefox", "discord", "spotify", "chromium", "zoom", "x")


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "ds4-companion" / "config.toml"


@dataclass
class AudioConfig:
    mirror_enabled: bool = True
    apps: list[str] = field(default_factory=lambda: list(DEFAULT_APPS))
    volume_db: float = -6.0
    max_db: float = 0.0
    headphone_max_db: float = -6.0
    limiter: bool = True


@dataclass
class VibrationConfig:
    large_percent: int = 100
    small_percent: int = 100
    swap_motors: bool = False
    players: list[int] = field(default_factory=lambda: [1, 2])


@dataclass
class LedConfig:
    color: str = DEFAULT_LED
    mode: str = "fixed"


@dataclass
class Rpcs3Config:
    config_dir: str = "~/.config/rpcs3"
    backup_before_edit: bool = True

    @property
    def input_file(self) -> Path:
        return Path(self.config_dir).expanduser() / "input_configs" / "global" / "Default.yml"


@dataclass
class UiConfig:
    start_minimized: bool = False
    tray_icon: bool = True


@dataclass
class UpdatesConfig:
    check_on_start: bool = True


@dataclass
class ProfileConfig:
    """Ajustes de um jogo (ADR 0012). None = vale o ajuste geral."""

    title: str = ""
    mirror_enabled: bool | None = None
    volume_db: float | None = None
    large_percent: int | None = None
    small_percent: int | None = None
    swap_motors: bool | None = None
    led_color: str | None = None
    created_rpcs3_file: bool = False
    """O app criou o input_configs/<serial>/Default.yml do RPCS3 (e pode apagá-lo)."""


@dataclass
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    vibration: VibrationConfig = field(default_factory=VibrationConfig)
    led: LedConfig = field(default_factory=LedConfig)
    rpcs3: Rpcs3Config = field(default_factory=Rpcs3Config)
    ui: UiConfig = field(default_factory=UiConfig)
    updates: UpdatesConfig = field(default_factory=UpdatesConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)


class ConfigError(ValueError):
    """Valor recusado; a mensagem é para o usuário."""


# --- validadores -----------------------------------------------------------------------------


def _bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ConfigError("precisa ser true ou false")
    return value


def _db(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ConfigError("precisa ser um número em dB")
    if not FLOOR_DB <= value <= ABSOLUTE_MAX_DB:
        raise ConfigError(f"precisa ficar entre {FLOOR_DB:g} e {ABSOLUTE_MAX_DB:g} dB")
    return float(value)


def _percent(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_PERCENT:
        raise ConfigError(f"precisa ser um inteiro de 0 a {MAX_PERCENT}")
    return value


def app_matches(pattern: str, name: str) -> bool:
    """Nome de app ou padrão com curingas (`*.exe`, `wine*`), sem diferenciar maiúsculas."""
    return bool(name) and fnmatch.fnmatchcase(name.casefold(), pattern.casefold())


def validate_apps(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_APPS:
        raise ConfigError(f"precisa ser uma lista com até {MAX_APPS} nomes")
    apps: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError("cada app precisa ser um texto")
        name = item.strip()
        if not name or len(name) > MAX_APP_NAME or not name.isprintable():
            raise ConfigError(f"nome de app inválido (1 a {MAX_APP_NAME} caracteres visíveis)")
        if all(app_matches(name, app) for app in _EVERYDAY_APPS):
            raise ConfigError(f"o padrão {name} mandaria todo o som do computador para o controle")
        if name.casefold() not in (a.casefold() for a in apps):
            apps.append(name)
    return apps


def validate_players(value: Any) -> list[int]:
    if not isinstance(value, list):
        raise ConfigError("precisa ser uma lista de jogadores")
    players: set[int] = set()
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or not 1 <= item <= MAX_PLAYERS:
            raise ConfigError(f"jogador precisa ser de 1 a {MAX_PLAYERS}")
        players.add(item)
    return sorted(players)


def _led(value: Any) -> str:
    ids = [p.id for p in LED_PRESETS]
    if isinstance(value, str) and HEX_COLOR.match(value):
        return value.upper()
    if value not in ids:
        raise ConfigError(f"cor precisa ser uma de: {', '.join(ids)} ou #RRGGBB")
    return str(value)


def _led_mode(value: Any) -> str:
    if value not in LED_MODES:
        raise ConfigError(f"modo precisa ser um de: {', '.join(LED_MODES)}")
    return str(value)


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise ConfigError("precisa ser um caminho")
    return value


Validator = Callable[[Any], Any]

SCHEMA: dict[str, dict[str, Validator]] = {
    "audio": {
        "mirror_enabled": _bool,
        "apps": validate_apps,
        "volume_db": _db,
        "max_db": _db,
        "headphone_max_db": _db,
        "limiter": _bool,
    },
    "vibration": {
        "large_percent": _percent,
        "small_percent": _percent,
        "swap_motors": _bool,
        "players": validate_players,
    },
    "led": {"color": _led, "mode": _led_mode},
    "rpcs3": {"config_dir": _path, "backup_before_edit": _bool},
    "ui": {"start_minimized": _bool, "tray_icon": _bool},
    "updates": {"check_on_start": _bool},
}


GAME_SERIAL = re.compile(r"[A-Z]{4}\d{5}")
"""ID de jogo do PS3 (BLUS30001): chave dos perfis e nome da pasta por jogo do RPCS3."""
MAX_PROFILES = 200
MAX_TITLE = 128


def clean_title(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ConfigError("precisa ser um texto")
    return "".join(ch for ch in raw if ch.isprintable()).strip()[:MAX_TITLE]


PROFILE_SCHEMA: dict[str, Validator] = {
    "title": clean_title,
    "mirror_enabled": _bool,
    "volume_db": _db,
    "large_percent": _percent,
    "small_percent": _percent,
    "swap_motors": _bool,
    "led_color": _led,
    "created_rpcs3_file": _bool,
}


def profile_from_dict(serial: str, values: dict[str, Any], warnings: list[str]) -> ProfileConfig:
    profile = ProfileConfig()
    for key, raw in values.items():
        validator = PROFILE_SCHEMA.get(key)
        if validator is None:
            warnings.append(f"profiles.{serial}.{key} desconhecido, ignorado")
            continue
        try:
            setattr(profile, key, validator(raw))
        except ConfigError as exc:
            warnings.append(f"profiles.{serial}.{key} {exc}; usando o ajuste geral")
    return profile


def _profiles(value: Any, warnings: list[str]) -> dict[str, ProfileConfig]:
    if not isinstance(value, dict):
        warnings.append("[profiles] precisa ser uma tabela de jogos; perfis ignorados")
        return {}
    profiles: dict[str, ProfileConfig] = {}
    for serial, values in value.items():
        if not GAME_SERIAL.fullmatch(serial) or not isinstance(values, dict):
            warnings.append(f"perfil {serial!r} ignorado: precisa ser [profiles.<ID do jogo>], ex.: BLUS30001")
            continue
        if len(profiles) >= MAX_PROFILES:
            warnings.append(f"mais de {MAX_PROFILES} perfis; o resto foi ignorado")
            break
        profiles[serial] = profile_from_dict(serial, values, warnings)
    return profiles


def from_dict(data: dict[str, Any]) -> tuple[Config, list[str]]:
    """Monta um Config a partir do TOML lido. Devolve também os avisos do que foi ignorado."""
    config = Config()
    warnings: list[str] = []
    for section_name, value in data.items():
        if section_name == "profiles":
            config.profiles = _profiles(value, warnings)
            continue
        if section_name not in SCHEMA:
            warnings.append(f"seção desconhecida [{section_name}] ignorada")
            continue
        if not isinstance(value, dict):
            warnings.append(f"[{section_name}] precisa ser uma tabela; usando padrões")
            continue
        section = getattr(config, section_name)
        for key, raw in value.items():
            validator = SCHEMA[section_name].get(key)
            if validator is None:
                warnings.append(f"{section_name}.{key} desconhecido, ignorado")
                continue
            try:
                setattr(section, key, validator(raw))
            except ConfigError as exc:
                warnings.append(f"{section_name}.{key} {exc}; usando o padrão")
    warnings += normalize(config)
    return config, warnings


def normalize(config: Config) -> list[str]:
    """Regras entre campos: nenhum volume acima do teto."""
    warnings = []
    audio = config.audio
    if audio.headphone_max_db > audio.max_db:
        audio.headphone_max_db = audio.max_db
        warnings.append("audio.headphone_max_db acima de max_db; rebaixado para max_db")
    if audio.volume_db > audio.max_db:
        audio.volume_db = audio.max_db
        warnings.append("audio.volume_db acima de max_db; rebaixado para max_db")
    for serial, profile in config.profiles.items():
        if profile.volume_db is not None and profile.volume_db > audio.max_db:
            profile.volume_db = audio.max_db
            warnings.append(f"profiles.{serial}.volume_db acima de max_db; rebaixado para max_db")
    return warnings


def to_dict(config: Config) -> dict[str, dict[str, Any]]:
    return {
        name: {f.name: getattr(getattr(config, name), f.name) for f in fields(getattr(config, name))} for name in SCHEMA
    }


def load(path: Path | None = None) -> tuple[Config, list[str]]:
    """Lê o arquivo. Se não existe, usa padrões. Se está quebrado, guarda uma cópia e usa padrões."""
    path = path or default_path()
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return Config(), []
    except OSError as exc:
        return Config(), [f"não deu para ler {path}: {exc.strerror}; usando padrões"]
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
        return Config(), [f"{path.name} inválido ({exc}); cópia em {backup.name}, usando padrões"]
    return from_dict(data)


# --- gravação --------------------------------------------------------------------------------


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        # Strings JSON com ensure_ascii são strings básicas válidas em TOML.
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    raise TypeError(f"tipo sem suporte no config: {type(value).__name__}")


def dumps(config: Config) -> str:
    lines = ["# DS4 Companion — editado pela interface. Opções em docs/guia/CONFIGURATION.md", ""]
    for section, values in to_dict(config).items():
        lines.append(f"[{section}]")
        lines += [f"{key} = {_toml_value(value)}" for key, value in values.items()]
        lines.append("")
    for serial, profile in sorted(config.profiles.items()):
        lines.append(f"[profiles.{serial}]")  # o serial já passou pelo GAME_SERIAL: chave TOML simples
        for f in fields(profile):
            value = getattr(profile, f.name)
            if (value is not None and value != f.default) or f.name == "title":
                lines.append(f"{f.name} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines)


def save(config: Config, path: Path | None = None) -> None:
    """Grava de forma atômica (arquivo temporário + rename) para nunca deixar meio arquivo."""
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(dumps(config), encoding="utf-8")
    os.replace(tmp, path)

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Leitura e edição do `input_configs/global/Default.yml` do RPCS3.

O arquivo é dado não confiável e é do usuário: a edição é por linha, só nas chaves de vibração e
cor dentro de `Player N Input → Config`, e só de jogadores com `Handler: DualShock 4` ou `DualSense`. Comentários,
ordem e o resto do arquivo ficam como estão. Os valores escritos são sempre números ou booleanos
gerados aqui, nunca texto vindo de fora.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

HANDLERS = ("DualShock 4", "DualSense")  # nomes do pad_handler no RPCS3
LARGE = "Large Vibration Motor Multiplier"
SMALL = "Small Vibration Motor Multiplier"
SWAP = "Switch Vibration Motors"
COLOR_KEYS = ("Color Value R", "Color Value G", "Color Value B")

_PLAYER = re.compile(r"^Player (\d+) Input:\s*(?:#.*)?$")
_KEY = re.compile(r"^(?P<indent>\s+)(?P<key>[^:#][^:]*?):(?:\s+(?P<value>.*?))?\s*$")


@dataclass(frozen=True)
class Vibration:
    large: int
    small: int
    swap: bool


class Rpcs3ConfigError(ValueError):
    """Arquivo sem o formato esperado; a mensagem é para o usuário."""


def _player_range(lines: list[str], player: int) -> tuple[int, int] | None:
    start = None
    for i, line in enumerate(lines):
        m = _PLAYER.match(line)
        if start is None:
            if m and int(m.group(1)) == player:
                start = i
        elif line.strip() and not line[0].isspace() and not line.lstrip().startswith("#"):
            return start, i
    return (start, len(lines)) if start is not None else None


def _direct_value(lines: list[str], start: int, end: int, key: str) -> str | None:
    """Valor de uma chave no primeiro nível do bloco do jogador (ex.: Handler)."""
    for line in lines[start + 1 : end]:
        m = _KEY.match(line)
        if m and m.group("key") == key and len(m.group("indent")) <= 2:
            return _unquote(m.group("value") or "")
    return None


def _config_range(lines: list[str], start: int, end: int) -> tuple[int, int, int, str]:
    """(linha de `Config:`, fim do bloco, indentação dos filhos) dentro do jogador."""
    for i in range(start + 1, end):
        m = _KEY.match(lines[i])
        if m and m.group("key") == "Config" and not m.group("value"):
            parent = len(m.group("indent"))
            first_child: str | None = None
            j = i + 1
            while j < end:
                line = lines[j]
                if line.strip() and not line.lstrip().startswith("#"):
                    indent = len(line) - len(line.lstrip())
                    if indent <= parent:
                        break
                    if first_child is None:
                        first_child = line[:indent]
                j += 1
            prefix = first_child if first_child is not None else " " * (parent + 2)
            return i, j, len(prefix), prefix
    raise Rpcs3ConfigError("bloco Config não encontrado")


def _unquote(value: str) -> str:
    value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def players(text: str) -> dict[int, str]:
    """Jogadores do arquivo → handler configurado."""
    lines = text.splitlines()
    found: dict[int, str] = {}
    for line in lines:
        m = _PLAYER.match(line)
        if m:
            n = int(m.group(1))
            rng = _player_range(lines, n)
            if rng:
                found[n] = _direct_value(lines, *rng, "Handler") or ""
    return found


def read_values(text: str, player: int) -> dict[str, str]:
    lines = text.splitlines()
    rng = _player_range(lines, player)
    if rng is None:
        return {}
    try:
        cstart, cend, indent, _ = _config_range(lines, *rng)
    except Rpcs3ConfigError:
        return {}
    values = {}
    for line in lines[cstart + 1 : cend]:
        m = _KEY.match(line)
        if m and len(m.group("indent")) == indent:
            values[m.group("key")] = _unquote(m.group("value") or "")
    return values


def read_vibration(text: str, player: int) -> Vibration | None:
    values = read_values(text, player)
    try:
        return Vibration(int(values[LARGE]), int(values[SMALL]), values.get(SWAP, "false").lower() == "true")
    except (KeyError, ValueError):
        return None


def set_values(text: str, player: int, values: dict[str, str]) -> str:
    """Troca ou acrescenta chaves no Config do jogador; o resto do texto fica igual."""
    lines = text.splitlines()
    rng = _player_range(lines, player)
    if rng is None:
        raise Rpcs3ConfigError(f"Jogador {player} não está no arquivo do RPCS3")
    handler = _direct_value(lines, *rng, "Handler")
    if handler not in HANDLERS:
        raise Rpcs3ConfigError(f"Jogador {player} não usa DualShock 4 nem DualSense no RPCS3")
    cstart, cend, indent, prefix = _config_range(lines, *rng)
    pending = dict(values)
    for i in range(cstart + 1, cend):
        m = _KEY.match(lines[i])
        if m and len(m.group("indent")) == indent and m.group("key") in pending:
            lines[i] = f"{prefix}{m.group('key')}: {pending.pop(m.group('key'))}"
    # Chaves que faltam entram no fim do Config, antes de linhas em branco finais.
    insert_at = cend
    while insert_at > cstart + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines[insert_at:insert_at] = [f"{prefix}{k}: {v}" for k, v in pending.items()]
    ending = "\n" if text.endswith("\n") or not text else ""
    return "\n".join(lines) + ending


def apply_vibration(text: str, player_list: list[int], vibration: Vibration) -> tuple[str, list[str]]:
    """Aplica a vibração em cada jogador. Devolve o texto e os avisos dos jogadores pulados."""
    values = {
        LARGE: str(int(vibration.large)),
        SMALL: str(int(vibration.small)),
        SWAP: "true" if vibration.swap else "false",
    }
    return _apply(text, player_list, values)


def apply_color(text: str, player_list: list[int], rgb: tuple[int, int, int]) -> tuple[str, list[str]]:
    values = {k: str(int(v)) for k, v in zip(COLOR_KEYS, rgb, strict=True)}
    return _apply(text, player_list, values)


def _apply(text: str, player_list: list[int], values: dict[str, str]) -> tuple[str, list[str]]:
    warnings = []
    for player in player_list:
        try:
            text = set_values(text, player, values)
        except Rpcs3ConfigError as exc:
            warnings.append(str(exc))
    return text, warnings


def write_with_backup(path: Path, text: str, backup: bool = True) -> Path | None:
    """Grava de forma atômica. Com `backup`, copia o original para `Default.yml.bak-AAAAMMDD-HHMMSS`.

    Não grava nada se o conteúdo não mudou. Devolve o caminho do backup, se houve.
    """
    try:
        current = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Rpcs3ConfigError(f"{path.name} do RPCS3 não encontrado") from None
    if current == text:
        return None
    backup_path = None
    if backup:
        backup_path = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup_path)
    tmp = path.with_name(f".{path.name}.ds4-companion.tmp")
    tmp.write_text(text, encoding="utf-8")
    shutil.copymode(path, tmp)
    os.replace(tmp, path)
    return backup_path

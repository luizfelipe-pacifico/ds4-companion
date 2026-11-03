# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Protótipo: manda áudio para o DualShock 4 pareado por Bluetooth (pesquisa do ROADMAP).

Não é instalado nem usado pelo app. Serve para medir, com o controle na mão, se o caminho
captura → SBC → hidraw funciona e com que latência. Checklist em
docs/desenvolvimento/BLUETOOTH_AUDIO.md.

    python scripts/bt_audio_prototype.py --tone --seconds 5          # apito, sem captura
    python scripts/bt_audio_prototype.py --seconds 30                # som da saída padrão
    python scripts/bt_audio_prototype.py --target headphones --volume 30

O volume começa baixo (30 %) para proteger o alto-falante. Com o RPCS3 aberto o script se recusa a
rodar: o hidraw é dele (SECURITY.md).
"""

from __future__ import annotations

import argparse
import contextlib
import math
import shutil
import struct
import subprocess
import sys
import time
from collections.abc import Iterator

from ds4_companion.common.models import Connection
from ds4_companion.daemon.device import DeviceMonitor
from ds4_companion.daemon.hid import bt_audio, hidraw
from ds4_companion.daemon.hid.bt_audio import CODESIZE, FRAMES_PER_REPORT, REPORT_INTERVAL_S, Target
from ds4_companion.daemon.rpcs3 import process

CHUNK = CODESIZE * FRAMES_PER_REPORT


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hidraw", help="/dev/hidrawN do controle (padrão: o primeiro por Bluetooth)")
    p.add_argument("--target", choices=["speaker", "headphones"], default="speaker")
    p.add_argument("--volume", type=int, default=30, help="0–100 %% (padrão 30)")
    p.add_argument("--seconds", type=float, default=10.0, help="duração (padrão 10 s)")
    p.add_argument("--tone", action="store_true", help="apito de 880 Hz em vez de capturar a saída")
    p.add_argument("--source", help="nó do PipeWire a capturar (padrão: monitor da saída padrão)")
    return p.parse_args()


def find_controller(path: str | None) -> str:
    if path:
        return path
    for c in DeviceMonitor().scan():
        if c.connection == Connection.BLUETOOTH:
            return c.hidraw
    sys.exit("Nenhum DualShock 4 por Bluetooth encontrado. Pareie o controle ou use --hidraw.")


def tone_chunks(seconds: float) -> Iterator[bytes]:
    """PCM s16le estéreo a 32 kHz, −12 dBFS, em blocos de 16 ms, no ritmo do relógio."""
    amplitude = 10 ** (-12 / 20) * 32767
    samples = CHUNK // 4
    start = time.monotonic()
    n = 0
    while n * REPORT_INTERVAL_S < seconds:
        frames = range(n * samples, (n + 1) * samples)
        values = (round(amplitude * math.sin(2 * math.pi * 880 * i / 32000)) for i in frames)
        yield b"".join(struct.pack("<hh", v, v) for v in values)
        n += 1
        delay = start + n * REPORT_INTERVAL_S - time.monotonic()
        if delay > 0:
            time.sleep(delay)


def capture_chunks(seconds: float, source: str | None) -> Iterator[bytes]:
    """Captura a saída padrão (ou `source`) já reamostrada pelo PipeWire para 32 kHz."""
    if shutil.which("pw-record") is None:
        sys.exit("pw-record não encontrado (pacote pipewire).")
    argv = ["pw-record", "--raw", "--rate=32000", "--channels=2", "--format=s16", "--latency=16ms"]
    argv += [f"--target={source}"] if source else []
    argv += ["-P", "stream.capture.sink=true", "-"]
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    assert proc.stdout is not None
    end = time.monotonic() + seconds
    try:
        while time.monotonic() < end:
            data = proc.stdout.read(CHUNK)
            if len(data) < CHUNK:
                break
            yield data
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=2)


def main() -> int:
    args = parse_args()
    if process.is_running():
        sys.exit("O RPCS3 está aberto e usa o controle. Feche-o antes do teste.")
    path = find_controller(args.hidraw)
    target = Target.SPEAKER if args.target == "speaker" else Target.HEADPHONES
    volume = bt_audio.volume_byte(args.volume)
    chunks = tone_chunks(args.seconds) if args.tone else capture_chunks(args.seconds, args.source)

    sent = errors = 0
    gaps: list[float] = []
    try:
        encoder = bt_audio.SbcEncoder()
    except bt_audio.SbcUnavailable as exc:
        sys.exit(str(exc))
    print(f"Controle {path}, destino {args.target}, volume {volume:#04x}. Ctrl+C para parar.")
    hidraw.write_report(path, bt_audio.control_report(target, volume))
    last = time.monotonic()
    try:
        with encoder:
            for counter, pcm in enumerate(chunks):
                frames = [encoder.encode(pcm[i : i + CODESIZE]) for i in range(0, CHUNK, CODESIZE)]
                report = bt_audio.audio_report(frames, counter * FRAMES_PER_REPORT, target)
                try:
                    hidraw.write_report(path, report)
                    sent += 1
                except OSError as exc:
                    errors += 1
                    print(f"falha ao escrever: {exc}", file=sys.stderr)
                now = time.monotonic()
                gaps.append(now - last)
                last = now
    except KeyboardInterrupt:
        pass
    finally:
        with contextlib.suppress(OSError):
            hidraw.write_report(path, bt_audio.control_report(None))

    if gaps:
        gaps.sort()
        p50, p99 = gaps[len(gaps) // 2], gaps[min(len(gaps) - 1, int(len(gaps) * 0.99))]
        print(f"{sent} relatórios enviados, {errors} falhas")
        print(f"intervalo entre relatórios: p50 {p50 * 1000:.1f} ms, p99 {p99 * 1000:.1f} ms (ideal: 16 ms)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

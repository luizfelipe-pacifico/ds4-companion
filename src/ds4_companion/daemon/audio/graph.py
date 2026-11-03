# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Leitura do `pw-dump` e plano dos links extras jogo → controle (ADR 0002).

Tudo que vem do PipeWire é dado não confiável: o parser aceita JSON malformado sem quebrar e
nenhum nome vira argumento de shell. Os links são criados por ID numérico de porta.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ...common.config import app_matches

SINK = "Audio/Sink"
STREAM = "Stream/Output/Audio"
DS4_MARKERS = ("wireless_controller", "dualshock")

# Downmix para o par estéreo do controle: o centro vai para os dois lados, traseiros para o
# lado correspondente; LFE fica de fora (o alto-falante do controle não reproduz grave).
CHANNEL_MAP: dict[str, tuple[str, ...]] = {
    "FL": ("FL",),
    "FR": ("FR",),
    "MONO": ("FL", "FR"),
    "FC": ("FL", "FR"),
    "RL": ("FL",),
    "SL": ("FL",),
    "RR": ("FR",),
    "SR": ("FR",),
}


@dataclass(frozen=True)
class Node:
    id: int
    name: str
    description: str = ""
    media_class: str = ""
    app_name: str = ""
    app_binary: str = ""
    volume: float | None = None
    """Volume na escala cúbica do wpctl (raiz cúbica de channelVolumes)."""
    muted: bool = False


@dataclass(frozen=True)
class Port:
    id: int
    node_id: int
    direction: str
    channel: str
    monitor: bool = False


@dataclass(frozen=True)
class Link:
    id: int
    output_port: int
    input_port: int


@dataclass
class Graph:
    nodes: dict[int, Node] = field(default_factory=dict)
    ports: list[Port] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    default_sink: str = ""

    def ds4_sink(self) -> Node | None:
        for node in sorted(self.nodes.values(), key=lambda n: n.id):
            text = f"{node.name} {node.description}".casefold()
            if node.media_class == SINK and any(m in text for m in DS4_MARKERS):
                return node
        return None

    def streams(self, apps: Iterable[str]) -> list[Node]:
        """Streams de saída cujo nome de app ou binário casa com um nome ou padrão da lista."""
        patterns = list(apps)
        return [
            n
            for n in self._output_streams()
            if any(app_matches(p, n.app_name) or app_matches(p, n.app_binary) for p in patterns)
        ]

    def playing(self) -> list[str]:
        """Nome de cada app tocando agora (sem repetir), para sugerir na interface."""
        names = (n.app_name or n.app_binary for n in self._output_streams())
        return list(dict.fromkeys(name for name in names if name))

    def _output_streams(self) -> list[Node]:
        return [n for n in sorted(self.nodes.values(), key=lambda n: n.id) if n.media_class == STREAM]

    def ports_of(self, node_id: int, direction: str) -> list[Port]:
        return [p for p in self.ports if p.node_id == node_id and p.direction == direction and not p.monitor]

    def default_sink_node(self) -> Node | None:
        for node in self.nodes.values():
            if node.media_class == SINK and node.name == self.default_sink:
                return node
        return None


def _str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _volume(info: dict[str, Any]) -> tuple[float | None, bool]:
    props_list = _dict(info.get("params")).get("Props")
    if not isinstance(props_list, list):
        return None, False
    for props in props_list:
        if not isinstance(props, dict):
            continue
        volumes = props.get("channelVolumes")
        if isinstance(volumes, list) and volumes:
            numbers = [v for v in volumes if isinstance(v, int | float) and not isinstance(v, bool) and v >= 0]
            if numbers:
                return max(numbers) ** (1 / 3), props.get("mute") is True
    return None, False


def parse_dump(data: Any) -> Graph:
    graph = Graph()
    if not isinstance(data, list):
        return graph
    for obj in data:
        if not isinstance(obj, dict):
            continue
        oid = _int(obj.get("id"))
        kind = _str(obj.get("type"))
        info = _dict(obj.get("info"))
        props = _dict(info.get("props"))
        if oid is None:
            continue
        if kind == "PipeWire:Interface:Node":
            volume, muted = _volume(info)
            graph.nodes[oid] = Node(
                id=oid,
                name=_str(props.get("node.name")),
                description=_str(props.get("node.description")),
                media_class=_str(props.get("media.class")),
                app_name=_str(props.get("application.name")),
                app_binary=_str(props.get("application.process.binary")),
                volume=volume,
                muted=muted,
            )
        elif kind == "PipeWire:Interface:Port":
            node_id = _int(props.get("node.id"))
            if node_id is not None:
                graph.ports.append(
                    Port(
                        id=oid,
                        node_id=node_id,
                        direction=_str(props.get("port.direction")),
                        channel=_str(props.get("audio.channel")),
                        monitor=props.get("port.monitor") is True,
                    )
                )
        elif kind == "PipeWire:Interface:Link":
            out_port = _int(info.get("output-port-id"))
            in_port = _int(info.get("input-port-id"))
            if out_port is not None and in_port is not None:
                graph.links.append(Link(oid, out_port, in_port))
        elif kind == "PipeWire:Interface:Metadata" and _str(_dict(obj.get("props")).get("metadata.name")) == "default":
            graph.default_sink = _default_sink(obj.get("metadata")) or graph.default_sink
    return graph


def _default_sink(entries: Any) -> str | None:
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("key") == "default.audio.sink":
            value = entry.get("value")
            if isinstance(value, dict) and isinstance(value.get("name"), str):
                return str(value["name"])
    return None


def wanted_links(graph: Graph, apps: Iterable[str]) -> list[tuple[int, int]]:
    """Todos os pares (porta de saída do jogo, porta de entrada do controle) que devem existir."""
    sink = graph.ds4_sink()
    if sink is None:
        return []
    inputs = {p.channel: p.id for p in graph.ports_of(sink.id, "in")}
    pairs: list[tuple[int, int]] = []
    for stream in graph.streams(apps):
        for port in graph.ports_of(stream.id, "out"):
            for channel in CHANNEL_MAP.get(port.channel, ()):
                if channel in inputs:
                    pairs.append((port.id, inputs[channel]))
    return pairs


def missing_links(graph: Graph, apps: Iterable[str]) -> list[tuple[int, int]]:
    existing = {(link.output_port, link.input_port) for link in graph.links}
    return [pair for pair in wanted_links(graph, apps) if pair not in existing]


def mirror_links(graph: Graph, apps: Iterable[str]) -> list[tuple[int, int]]:
    """Links jogo → controle que existem hoje e são do espelhamento (para desligar).

    Se o controle for a saída padrão, esses links são do próprio WirePlumber e ficam.
    """
    sink = graph.ds4_sink()
    if sink is None or sink.name == graph.default_sink:
        return []
    existing = {(link.output_port, link.input_port) for link in graph.links}
    return [pair for pair in wanted_links(graph, apps) if pair in existing]


def is_mirroring(graph: Graph, apps: Iterable[str]) -> bool:
    """Algum jogo está tocando no controle agora."""
    existing = {(link.output_port, link.input_port) for link in graph.links}
    return any(pair in existing for pair in wanted_links(graph, apps))

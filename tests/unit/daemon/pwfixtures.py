# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Monta `pw-dump` sintéticos (nada copiado de máquina real)."""

from __future__ import annotations

from typing import Any

DS4_SINK = "alsa_output.usb-Sony_Interactive_Entertainment_Wireless_Controller-00.analog-stereo"
HDMI_SINK = "alsa_output.pci-0000_00_1f.3.hdmi-stereo"


def node(oid: int, name: str, media_class: str, **props: Any) -> dict[str, Any]:
    volume = props.pop("volume", None)
    info: dict[str, Any] = {"props": {"node.name": name, "media.class": media_class, **props}}
    if volume is not None:
        info["params"] = {"Props": [{"channelVolumes": [volume**3, volume**3], "mute": False}]}
    return {"id": oid, "type": "PipeWire:Interface:Node", "info": info}


def port(oid: int, node_id: int, direction: str, channel: str, monitor: bool = False) -> dict[str, Any]:
    props = {"node.id": node_id, "port.direction": direction, "audio.channel": channel, "port.monitor": monitor}
    return {"id": oid, "type": "PipeWire:Interface:Port", "info": {"props": props}}


def link(oid: int, out_port: int, in_port: int) -> dict[str, Any]:
    return {
        "id": oid,
        "type": "PipeWire:Interface:Link",
        "info": {"output-port-id": out_port, "input-port-id": in_port},
    }


def default_meta(sink: str) -> dict[str, Any]:
    return {
        "id": 40,
        "type": "PipeWire:Interface:Metadata",
        "props": {"metadata.name": "default"},
        "metadata": [{"subject": 0, "key": "default.audio.sink", "value": {"name": sink}}],
    }


def dump(*, ds4: bool = True, game: bool = True, mirrored: bool = False, default: str = HDMI_SINK) -> list[Any]:
    """HDMI (50) + DS4 (97) + RPCS3 (120) tocando no HDMI; opcionalmente já espelhado."""
    objs: list[Any] = [
        default_meta(default),
        node(50, HDMI_SINK, "Audio/Sink", **{"node.description": "Monitor HDMI"}),
        port(51, 50, "in", "FL"),
        port(52, 50, "in", "FR"),
    ]
    if ds4:
        objs += [
            node(97, DS4_SINK, "Audio/Sink", volume=0.4, **{"node.description": "DualShock 4 Analog Stereo"}),
            port(99, 97, "in", "FL"),
            port(100, 97, "in", "FR"),
            port(88, 97, "out", "FL", monitor=True),
        ]
    if game:
        objs += [
            node(120, "RPCS3", "Stream/Output/Audio", **{"application.name": "RPCS3"}),
            port(121, 120, "out", "FL"),
            port(122, 120, "out", "FR"),
            link(130, 121, 51),
            link(131, 122, 52),
        ]
        if ds4 and mirrored:
            objs += [link(140, 121, 99), link(141, 122, 100)]
    return objs

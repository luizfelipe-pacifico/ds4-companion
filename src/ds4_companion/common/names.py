# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Identificadores fixos do app (ADR 0008)."""

APP_ID = "io.github.luizfelipe_pacifico.DS4Companion"

BUS_NAME = f"{APP_ID}.Daemon"
OBJECT_PATH = "/io/github/luizfelipe_pacifico/DS4Companion/Daemon"
INTERFACE = BUS_NAME

SERVICE_UNIT = "ds4-companion.service"
GETTEXT_DOMAIN = "ds4-companion"
RESOURCE_PREFIX = "/io/github/luizfelipe_pacifico/DS4Companion"

HELP_URL = "https://github.com/luizfelipe-pacifico/ds4-companion/blob/main/docs/guia/TROUBLESHOOTING.md"
AUDIO_HELP_URL = "https://github.com/luizfelipe-pacifico/ds4-companion/blob/main/docs/guia/AUDIO.md#cabo-usb--bluetooth"

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""`python -m ds4_companion.app`: abre a janela (e procura versão nova, ADR 0009)."""

from __future__ import annotations

import gettext
import logging
import sys

from ..common.names import GETTEXT_DOMAIN


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # O domínio vem antes de importar as páginas: os títulos delas são traduzidos na importação.
    gettext.textdomain(GETTEXT_DOMAIN)
    from .application import Application

    return int(Application().run(sys.argv if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())

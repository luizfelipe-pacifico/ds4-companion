# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""No GitHub Actions, cada teste que falha vira uma anotação: os logs dos jobs só abrem com acesso
de administrador, as anotações são públicas."""

from __future__ import annotations

import os

import pytest


def _escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    for report in terminalreporter.stats.get("failed", []) + terminalreporter.stats.get("error", []):
        detail = str(report.longrepr)[-1500:]
        terminalreporter.write_line(f"::error title={_escape(report.nodeid)}::{_escape(detail)}")

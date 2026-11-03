# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
import io
import json
import urllib.error
from typing import Any

import pytest

from ds4_companion.common import updates

PKG = "ds4-companion-0.2.0-1-any.pkg.tar.zst"


def release(tag: str = "v0.2.0", assets: Any = None, **extra: Any) -> dict[str, Any]:
    return {"tag_name": tag, "assets": [{"name": PKG}] if assets is None else assets, **extra}


def test_newer_release_uses_versioned_package() -> None:
    update = updates.from_release(release(), current="0.1.0")
    assert update is not None
    assert update.latest == "0.2.0"
    assert update.package_url == f"{updates.DOWNLOAD_BASE}/v0.2.0/{PKG}"
    assert update.command == f"sudo pacman -U {update.package_url}"
    assert update.argv == ["pkexec", "pacman", "-U", "--noconfirm", update.package_url]


@pytest.mark.parametrize("tag", ["v0.1.0", "0.0.9", "v0.1"])
def test_same_older_or_odd_version_is_not_an_update(tag: str) -> None:
    assert updates.from_release(release(tag), current="0.1.0") is None


def test_compares_numbers_not_text() -> None:
    assert updates.from_release(release("v0.10.0", assets=[]), current="0.9.0") is not None


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {"tag_name": 5},
        release("v0.2.0; rm -rf ~"),
        release(draft=True),
        release(prerelease=True),
    ],
)
def test_invalid_or_unpublished_release_is_ignored(data: Any) -> None:
    assert updates.from_release(data, current="0.1.0") is None


@pytest.mark.parametrize(
    "assets",
    [
        [],
        "x",
        [{"name": "ds4-companion-0.1.0-1-any.pkg.tar.zst"}],
        [{"name": "../../evil-0.2.0-1-any.pkg.tar.zst"}],
        [{"name": f"{PKG} --overwrite *"}],
        [5, {"name": None}],
    ],
)
def test_package_url_never_comes_from_untrusted_names(assets: Any) -> None:
    update = updates.from_release(release(assets=assets), current="0.1.0")
    assert update is not None
    assert update.package_url == updates.LATEST_PACKAGE_URL


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_check_reads_github(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def urlopen(request: Any, timeout: float) -> FakeResponse:
        seen.append((request.full_url, timeout))
        return FakeResponse(json.dumps(release()).encode())

    monkeypatch.setattr(updates.urllib.request, "urlopen", urlopen)
    update = updates.check(current="0.1.0")
    assert update is not None
    assert update.latest == "0.2.0"
    assert seen == [(updates.LATEST_API_URL, updates.TIMEOUT_S)]


@pytest.mark.parametrize(
    "outcome",
    [
        urllib.error.URLError("sem rede"),
        TimeoutError(),
        b"<html>",
        b"\xff\xfe",
        b" " * (updates.MAX_RESPONSE_BYTES + 1),
    ],
)
def test_check_failures_mean_no_update(monkeypatch: pytest.MonkeyPatch, outcome: Any) -> None:
    def urlopen(request: Any, timeout: float) -> FakeResponse:
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)

    monkeypatch.setattr(updates.urllib.request, "urlopen", urlopen)
    assert updates.check(current="0.1.0") is None

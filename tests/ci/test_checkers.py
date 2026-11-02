# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
"""Testes dos verificadores do CI (scripts/ci).

Os exemplos "proibidos" são montados por concatenação para que este arquivo
não seja ele mesmo apontado pelos verificadores.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))

import check_commits  # noqa: E402
import check_sensitive  # noqa: E402
import check_spdx  # noqa: E402
import check_svg  # noqa: E402

SVG_OK = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M0 0h16v16H0z"/></svg>'
SIGNOFF = "Signed-off-by: Pessoa <pessoa@example.com>"


def svg(inner: str, view_box: str = "0 0 16 16") -> bytes:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">{inner}</svg>'.encode()


class SvgTest(unittest.TestCase):
    def test_svg_limpo_passa(self) -> None:
        self.assertEqual(check_svg.check_svg("a.svg", SVG_OK), [])

    def test_bloqueia_elementos_proibidos(self) -> None:
        for tag in ("script", "image", "text", "foreignObject"):
            with self.subTest(tag=tag):
                self.assertTrue(check_svg.check_svg("a.svg", svg(f"<{tag}/>")))

    def test_bloqueia_evento(self) -> None:
        self.assertTrue(check_svg.check_svg("a.svg", svg('<path on' + 'load="x()" d="M0 0"/>')))

    def test_bloqueia_href_externo_e_data_uri(self) -> None:
        for href in ("https://exemplo.invalid/a.png", "data:image/png;base64,AAAA", "javascript:x()"):
            with self.subTest(href=href):
                self.assertTrue(check_svg.check_svg("a.svg", svg(f'<use href="{href}"/>')))

    def test_permite_href_interno(self) -> None:
        self.assertEqual(check_svg.check_svg("a.svg", svg('<use href="#forma"/>')), [])

    def test_bloqueia_doctype_e_entidades(self) -> None:
        data = b'<!DOCTYPE svg [<!ENTITY x "y">]>' + SVG_OK
        self.assertTrue(check_svg.check_svg("a.svg", data))

    def test_xml_invalido(self) -> None:
        self.assertTrue(check_svg.check_svg("a.svg", b"<svg><path></svg>"))

    def test_exige_viewbox(self) -> None:
        self.assertTrue(check_svg.check_svg("a.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>'))

    def test_icone_do_app_precisa_ser_quadrado(self) -> None:
        path = "data/icons/hicolor/scalable/apps/x.svg"
        self.assertTrue(check_svg.check_svg(path, svg("", "0 0 128 64")))
        self.assertEqual(check_svg.check_svg(path, svg("", "0 0 128 128")), [])


class SensitiveTest(unittest.TestCase):
    def test_mac(self) -> None:
        mac = ":".join(["a4", "5e", "60", "c1", "02", "f3"])
        self.assertTrue(check_sensitive.check_text("x.md", f"controle {mac}"))

    def test_hora_nao_e_mac(self) -> None:
        self.assertEqual(check_sensitive.check_text("x.md", "às 12:30:45"), [])

    def test_email_pessoal_e_permitidos(self) -> None:
        pessoal = "fulano" + "@" + "gmail.com"
        self.assertTrue(check_sensitive.check_text("x.md", pessoal))
        for ok in ("a@example.com", "123+x@users.noreply.github.com", "noreply@anthropic.com"):
            with self.subTest(email=ok):
                self.assertEqual(check_sensitive.check_text("x.md", ok), [])

    def test_home_com_usuario(self) -> None:
        self.assertTrue(check_sensitive.check_text("x.md", "/ho" + "me/fulano/.config"))
        self.assertEqual(check_sensitive.check_text("x.md", "~/.config/ds4-companion"), [])

    def test_chave_privada(self) -> None:
        self.assertTrue(check_sensitive.check_text("x", "-----BEGIN " + "OPENSSH PRIVATE KEY-----"))

    def test_serial(self) -> None:
        self.assertTrue(check_sensitive.check_text("x", "uniq=" + "a45e60c102f3"))

    def test_marcador_libera_linha(self) -> None:
        pessoal = "fulano" + "@" + "gmail.com"
        self.assertEqual(check_sensitive.check_text("x", f"{pessoal}  # ds4-allow-sensitive"), [])

    def test_arquivos_proibidos(self) -> None:
        for path in (".env", ".env.local", "a/b.pem", "pw-dump-2026.json", "hid-dump.bin",
                     "daemon.log", "Default.yml.bak-1", "x.pkg.tar.zst", ".claude/settings.local.json"):
            with self.subTest(path=path):
                self.assertTrue(check_sensitive.forbidden_file(path))
        for path in (".env.example", "README.md", "data/x.svg"):
            with self.subTest(path=path):
                self.assertFalse(check_sensitive.forbidden_file(path))

    def test_binario_e_ignorado(self) -> None:
        self.assertEqual(check_sensitive.check_file("a.bin", b"\0\1\2"), [])


class SpdxTest(unittest.TestCase):
    HEADER = (
        "# SPDX-License-Identifier: GPL-3.0-or-later\n"
        "# SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion\n"
    )

    def test_com_cabecalho(self) -> None:
        self.assertEqual(check_spdx.check_header("a.py", self.HEADER + "x = 1\n"), [])

    def test_shebang_antes_do_cabecalho(self) -> None:
        self.assertEqual(check_spdx.check_header("a.sh", "#!/bin/bash\n" + self.HEADER), [])

    def test_sem_cabecalho(self) -> None:
        self.assertEqual(len(check_spdx.check_header("a.py", "x = 1\n")), 2)

    def test_quais_arquivos_sao_codigo(self) -> None:
        self.assertTrue(check_spdx.is_code("src/a.py"))
        self.assertTrue(check_spdx.is_code("install.sh"))
        self.assertTrue(check_spdx.is_code("packaging/PKGBUILD"))
        self.assertFalse(check_spdx.is_code("README.md"))


class CommitsTest(unittest.TestCase):
    def check(self, message: str, email: str = "pessoa@example.com") -> list[str]:
        return [p.message for p in check_commits.check_message("a" * 40, email, message)]

    def test_commit_valido(self) -> None:
        self.assertEqual(self.check(f"feat(audio): espelha som no controle\n\n{SIGNOFF}"), [])

    def test_breaking_change(self) -> None:
        self.assertEqual(self.check(f"feat!: muda formato do config\n\n{SIGNOFF}"), [])

    def test_titulo_invalido(self) -> None:
        self.assertTrue(self.check(f"Adiciona coisa\n\n{SIGNOFF}"))
        self.assertTrue(self.check(f"feature: tipo errado\n\n{SIGNOFF}"))

    def test_merge_e_aceito(self) -> None:
        self.assertEqual(self.check(f"Merge branch 'x'\n\n{SIGNOFF}"), [])

    def test_sem_signoff(self) -> None:
        self.assertTrue(self.check("fix: corrige volume"))

    def test_signoff_de_outra_pessoa(self) -> None:
        self.assertTrue(self.check(f"fix: corrige volume\n\n{SIGNOFF}", email="outra@example.com"))

    def test_atribuicao_de_ia(self) -> None:
        trailers = (
            "Co-" + "Authored-By: Claude <noreply@anthropic.com>",
            "Co-" + "authored-by: GitHub Copilot <x@example.com>",
            "🤖 " + "Generated with [Claude Code](https://claude.com/claude-code)",
        )
        for trailer in trailers:
            with self.subTest(trailer=trailer):
                self.assertTrue(self.check(f"fix: x\n\n{SIGNOFF}\n{trailer}"))

    def test_coautor_humano_e_permitido(self) -> None:
        msg = f"fix: x\n\n{SIGNOFF}\nCo-" + "authored-by: Outra Pessoa <outra@example.com>"
        self.assertEqual(self.check(msg), [])


if __name__ == "__main__":
    unittest.main()

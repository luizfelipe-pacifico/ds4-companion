# 0006. Organização dos arquivos do repositório

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
A documentação cresceu solta na raiz e em `docs/`, e o código ainda não existe. Sem um mapa,
cada arquivo novo vai para um lugar diferente e links quebram quando algo muda de pasta.

## Decisão
- **Raiz:** só arquivos de comunidade do GitHub (`README`, `CONTRIBUTING`, `CODE_OF_CONDUCT`,
  `SECURITY`, `CHANGELOG`, `LICENSE`), `CLAUDE.md`, `pyproject.toml`, `install.sh` e configs de editor/Git.
- **`docs/`** por público: `guia/`, `arquitetura/` (com `adr/`), `design/`, `desenvolvimento/`.
- **`src/ds4_companion/`** em layout `src/`, com `app/`, `daemon/`, `cli/` e `common/`.
- **`data/`** para tudo que é instalado e não é Python: ícones e ilustrações em SVG, `.desktop`,
  AppStream, serviço systemd, regra udev, interface D-Bus, CSS.
- **`tests/`** espelha `src/`; **`packaging/`** guarda o PKGBUILD; **`scripts/`** a automação.
- Imagens existem uma vez só, em `data/`; a documentação aponta para lá.

O mapa completo e a tabela "onde colocar algo novo" ficam em
[STRUCTURE.md](../STRUCTURE.md).

## Consequências
- Todo arquivo novo tem lugar definido; revisão de PR confere isso pela tabela.
- Mover um arquivo exige atualizar `STRUCTURE.md` e os links no mesmo commit.
- Ícone e arquivos com `<app-id>` serão renomeados quando o app ID for decidido (nova ADR).

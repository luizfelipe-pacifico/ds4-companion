# Changelog

## [Não lançado]
### Adicionado
- Documentação inicial: README, arquitetura, segurança, roadmap, instalação, áudio, vibração,
  configuração, interface, design e solução de problemas.
- Licença GPL-3.0-or-later, Código de Conduta, guia de boas práticas.
- `.gitignore`, `.editorconfig`, `.gitattributes`, templates de issue e PR.
- Ícone do app em SVG 1:1 (colorido e simbólico) em `data/icons/hicolor/`.
- ADRs em `docs/arquitetura/adr/` (stack, áudio paralelo, paleta, commits sem atribuição de IA).
- Plano de instalação por um comando (`sudo pacman -U`) e por `install.sh` executável (ADR 0005).
- CI no GitHub Actions (lint, testes, build, pacote, instalador), segurança (gitleaks, CodeQL,
  revisão de dependências, Scorecard), Dependabot, `pre-commit` e `scripts/check.sh` (ADR 0007).
- `CLAUDE.md` e skills de design (`impeccable`, `apple-design`) em `.claude/`.

### Alterado
- Documentação reorganizada em `docs/` por assunto: `guia/`, `arquitetura/`, `design/`, `desenvolvimento/`.
  `ARCHITECTURE.md` e `ROADMAP.md` saíram da raiz.
- README reescrito: ícone, badges, diagrama do fluxo de áudio e índice visual da documentação.
- Design system reduzido a cinco cores (três pretos, azul da barra de luz, branco), visual *slim*;
  faixas de volume passam a usar texto + ícone em vez de verde/amarelo/vermelho.

## [0.0.0] — 2026-11-02 (scripts)
- Vibração do DualShock 4 configurada no RPCS3 (Jogadores 1 e 2).
- `ds4-audio-mirror`: áudio do RPCS3 em paralelo no controle via PipeWire (USB).
- Serviço `ds4-audio-mirror.service` (systemd de usuário).

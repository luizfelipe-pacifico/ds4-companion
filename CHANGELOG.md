# Changelog

## [Não lançado]
### Adicionado
- Pacote Python (`pyproject.toml`, layout `src/`) com ruff, `mypy --strict` e pytest configurados.
- `common/`: conversão volume ↔ dB pela curva cúbica do PipeWire, faixas livre/alto/acima do limite,
  cores da barra de luz e `config.toml` com validação, padrões e gravação atômica.
- App ID `io.github.luizfelipe_pacifico.DS4Companion` e formato da API D-Bus (ADR 0008).
- Aviso de atualização: ao abrir, a interface consulta o GitHub Releases e, com versão nova, mostra
  um pop-up com **Atualizar agora** (`pkexec pacman -U`) e **Copiar comando** para o terminal;
  desligável em `[updates] check_on_start` (ADR 0009).
- Relatórios HID de vibração e barra de luz (USB `0x05`, Bluetooth `0x11` com CRC32), leitura do
  estado do controle (fone, cabo) e escrita no `hidraw` com erro claro quando falta permissão.
- Detecção do DualShock 4 pelo udev (cabo, Bluetooth e adaptador sem fio), bateria pelo
  `power_supply` e MAC sempre mascarado nos logs.
- Edição do `Default.yml` do RPCS3 por linha (vibração e cor da luz), só em jogadores com
  DualShock 4, com backup `Default.yml.bak-AAAAMMDD-HHMMSS` e gravação atômica; detecção do
  RPCS3 aberto pelo `/proc`.
- Áudio em paralelo: leitura do `pw-dump`, plano dos links jogo → controle por ID de porta (com
  downmix de 5.1/7.1 para o par estéreo), `pw-link`, `wpctl`, apito de teste e monitor de eventos
  do PipeWire. Testes de integração num PipeWire isolado, sem hardware (`scripts/ci/run-integration.sh`).
- `ds4-companiond`: daemon de usuário que reconcilia links do PipeWire por eventos, reaplica o
  volume salvo ao conectar o controle, rebaixa qualquer volume acima do teto (e para −6 dB com fone
  no controle), testa os motores por 0,5 s com intervalo mínimo e guarda vibração e cor como
  pendentes enquanto o RPCS3 está aberto (um backup do `Default.yml` por execução, não um por
  ajuste). API no D-Bus de sessão
  (`data/io.github.luizfelipe_pacifico.DS4Companion.Daemon.xml`) e `--stop-motors` para o serviço.
- `ds4ctl`: `status`, `mirror`, `volume` (confirmação acima de 0 dB), `vibration`, `test-rumble`,
  `led` e `test-tone`, com mensagens em português e código de saída 3 quando o daemon não roda.
- Interface GTK4 + libadwaita: barra lateral com Status (cartão do controle com a faixa de luz na
  cor real do LED), Áudio (som no controle, volume em dB com marcas em −6/0 dB, confirmação acima de
  0 dB, apito de teste, apps espelhados), Vibração (força 0–200 %, testes, inverter, jogadores), Luz
  (nove cores) e Avançado (pasta do RPCS3, backup, registros, reiniciar serviço, restaurar padrões).
  Telas de estado com as ilustrações, banner de problema no PipeWire, tela de serviço parado e
  ativação do serviço na primeira abertura. CSS do design system em `data/style.css`, ícone próprio
  de vibração e GResource. `scripts/screenshots.sh` gera capturas num `mutter` headless.
- `PRODUCT.md` e o contrato de direção da interface em `.impeccable/surfaces/app.md`.
- Empacotamento: `packaging/PKGBUILD` (+ `.SRCINFO` e avisos pós-instalação), `.desktop`, AppStream,
  serviço de usuário com `ExecStopPost` que para os motores, ativação D-Bus para o `ds4ctl`, regra
  udev com `uaccess` (cabo, Bluetooth e adaptador) e `install.sh` (confere `SHA256SUMS`, só usa
  `sudo` no `pacman`, migra os scripts da Fase 0, `--uninstall`, `--no-service`).
- Documentação inicial: README, arquitetura, segurança, roadmap, instalação, áudio, vibração,
  configuração, interface, design e solução de problemas.
- Licença GPL-3.0-or-later, Código de Conduta, guia de boas práticas.
- `.gitignore`, `.editorconfig`, `.gitattributes`, templates de issue e PR.
- Ícone do app em SVG 1:1 (colorido e simbólico) em `data/icons/hicolor/`.
- `docs/arquitetura/STRUCTURE.md`: mapa dos arquivos do repositório e onde colocar algo novo (ADR 0006).
- 8 ilustrações flat em SVG para telas de estado em `data/illustrations/`, documentadas em
  `docs/design/ILLUSTRATIONS.md`.
- ADRs em `docs/arquitetura/adr/` (stack, áudio paralelo, paleta, commits sem atribuição de IA).
- Plano de instalação por um comando (`sudo pacman -U`) e por `install.sh` executável (ADR 0005).
- CI no GitHub Actions (lint, testes, build, pacote, instalador), segurança (gitleaks, CodeQL,
  revisão de dependências, Scorecard), Dependabot, `pre-commit` e `scripts/check.sh` (ADR 0007).
- `CLAUDE.md` e skills de design (`impeccable`, `apple-design`) em `.claude/`.

### Alterado
- Ícones renomeados para o app ID: `data/icons/hicolor/*/apps/io.github.luizfelipe_pacifico.DS4Companion*.svg` (ADR 0008).
- Documentação reorganizada em `docs/` por assunto: `guia/`, `arquitetura/`, `design/`, `desenvolvimento/`.
  `ARCHITECTURE.md` e `ROADMAP.md` saíram da raiz.
- README reescrito: ícone, badges, diagrama do fluxo de áudio e índice visual da documentação.
- Design system reduzido a cinco cores (três pretos, azul da barra de luz, branco), visual *slim*;
  faixas de volume passam a usar texto + ícone em vez de verde/amarelo/vermelho.

## [0.0.0] — 2026-11-02 (scripts)
- Vibração do DualShock 4 configurada no RPCS3 (Jogadores 1 e 2).
- `ds4-audio-mirror`: áudio do RPCS3 em paralelo no controle via PipeWire (USB).
- Serviço `ds4-audio-mirror.service` (systemd de usuário).

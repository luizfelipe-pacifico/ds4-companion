# Roadmap

## Fase 0 — Scripts (feito)
- [x] Vibração do DS4 no RPCS3 (Jogador 1 e 2) via `input_configs/global/Default.yml`
- [x] Áudio do RPCS3 em paralelo no controle (USB) — `ds4-audio-mirror` + serviço systemd de usuário
- [x] Regras udev cobrindo USB e Bluetooth
- [x] GameMode automático ao abrir o RPCS3

## Fase 1 — Daemon + CLI (v0.1)
- [x] `ds4-companiond` em Python substituindo o script bash
- [x] Eventos do PipeWire em vez de polling (`pw-dump --monitor`, com verificação a cada 3 s de reserva)
- [x] `ds4ctl status | volume | vibration | test-rumble | mirror on/off | led <cor>`
- [x] Cor da barra de luz: aplicar pelo `hidraw` fora do jogo (mesmo relatório HID da vibração:
      USB `0x05` bytes 6/7/8 = R/G/B; Bluetooth `0x11` com CRC32) e no RPCS3 via `Color Value R/G/B`
      do `Default.yml`. Não manda cor enquanto o RPCS3 está com jogo aberto, igual à vibração
- [x] `config.toml` com validação
- [x] Teto de volume (`max_db`) aplicado automaticamente

## Fase 2 — Interface gráfica (v0.2)
- [x] Janela GTK4/libadwaita: Status, Áudio, Vibração, Luz, Avançado
- [x] Slider de volume em dB com faixas livre/alto/acima do limite (texto + ícone, ver DESIGN.md)
- [x] Botões de teste de vibração (forte, fraco, ambos)
- [x] Indicador de conexão (cabo/Bluetooth) e bateria
- [ ] Ícone na bandeja (extensão AppIndicator) — pendente: exige implementar StatusNotifierItem no D-Bus
- [x] Página **Luz**: escolher a cor da barra de luz do controle entre cores pré-definidas,
      com pré-visualização ao vivo no controle conectado:

  | Cor | RGB do LED |
  |---|---|
  | Azul (padrão, Jogador 1 do PS4) | `#0000FF` |
  | Vermelho (Jogador 2) | `#FF0000` |
  | Verde (Jogador 3) | `#00FF00` |
  | Rosa (Jogador 4) | `#FF1493` |
  | Roxo | `#8000FF` |
  | Ciano | `#00FFFF` |
  | Laranja | `#FF8000` |
  | Branco | `#FFFFFF` |
  | Desligada | `#000000` |

  A cor fica salva em `[led]` no `config.toml` e é reaplicada ao conectar o controle.
- [x] Telas de estado (vazio, espera, aviso, erro, sucesso) com `AdwStatusPage` e as ilustrações de
      [ILLUSTRATIONS.md](../design/ILLUSTRATIONS.md)
- [x] Logo do app em **SVG**, proporção **1:1** (quadrado): ícone colorido `hicolor/scalable/apps/<app-id>.svg` e versão
      simbólica `<app-id>-symbolic.svg` (GNOME HIG), seguindo as regras de marca do
      [DESIGN.md](../design/DESIGN.md): desenho próprio, faixa de luz `led-blue` sobre `black-0`, sem logotipo da PlayStation

## Fase 3 — Empacotamento (v0.3)
- [ ] `PKGBUILD` (instala app, serviço, regra udev, .desktop, ícone SVG)
- [ ] Publicar no AUR
- [ ] Release no GitHub com `.pkg.tar.zst` assinado, `SHA256SUMS` e `install.sh`
      (instalação por um comando: `sudo pacman -U <url>`, ver [ADR 0005](../arquitetura/adr/0005-instalacao-por-um-comando.md))
- [ ] `install.sh`: instala, migra scripts da Fase 0, ativa o serviço; `--uninstall`; `shellcheck` + teste em container no CI
- [x] App ativa o serviço de usuário na primeira abertura
- [ ] Migração automática dos scripts da Fase 0

## Fase 4 — Recursos extras (v0.4+)
- [ ] Limitador via `filter-chain` do PipeWire
- [ ] Perfis por jogo (ex.: FIFA com mais som no controle, Tekken só vibração)
- [ ] Barra de luz além das cores fixas: cor personalizada, cor por jogador, cor por perfil de jogo e modo bateria
- [ ] Suporte a DualSense (PS5): vibração háptica/gatilhos quando o RPCS3 suportar
- [ ] Espelhar áudio de outros apps (Steam/Proton) — lista configurável

## Pesquisa — Áudio por Bluetooth
- [ ] Avaliar viabilidade: o DS4 recebe áudio por Bluetooth em relatórios HID (0x14–0x19) com
      frames SBC, não por perfil A2DP. Não há suporte no kernel nem no PipeWire.
- [ ] Protótipo em espaço de usuário: capturar stream → codificar SBC → enviar via `hidraw`.
- [ ] Só entra no app se tiver latência aceitável (< 60 ms) e não atrapalhar entrada/vibração.

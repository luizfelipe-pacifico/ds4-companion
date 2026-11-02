# Roadmap

## Fase 0 — Scripts (feito)
- [x] Vibração do DS4 no RPCS3 (Jogador 1 e 2) via `input_configs/global/Default.yml`
- [x] Áudio do RPCS3 em paralelo no controle (USB) — `ds4-audio-mirror` + serviço systemd de usuário
- [x] Regras udev cobrindo USB e Bluetooth
- [x] GameMode automático ao abrir o RPCS3

## Fase 1 — Daemon + CLI (v0.1)
- [ ] `ds4-companiond` em Python substituindo o script bash
- [ ] Eventos do PipeWire em vez de polling
- [ ] `ds4ctl status | volume | vibration | test-rumble | mirror on/off`
- [ ] `config.toml` com validação
- [ ] Teto de volume (`max_db`) aplicado automaticamente

## Fase 2 — Interface gráfica (v0.2)
- [ ] Janela GTK4/libadwaita: Status, Áudio, Vibração, Avançado
- [ ] Slider de volume em dB com faixas verde/amarelo/vermelho
- [ ] Botões de teste de vibração (forte, fraco, ambos)
- [ ] Indicador de conexão (cabo/Bluetooth) e bateria
- [ ] Ícone na bandeja (extensão AppIndicator)

## Fase 3 — Empacotamento (v0.3)
- [ ] `PKGBUILD` (instala app, serviço, regra udev, .desktop, ícone)
- [ ] Publicar no AUR
- [ ] Migração automática dos scripts da Fase 0

## Fase 4 — Recursos extras (v0.4+)
- [ ] Limitador via `filter-chain` do PipeWire
- [ ] Perfis por jogo (ex.: FIFA com mais som no controle, Tekken só vibração)
- [ ] Barra de luz: cor por jogador / bateria
- [ ] Suporte a DualSense (PS5): vibração háptica/gatilhos quando o RPCS3 suportar
- [ ] Espelhar áudio de outros apps (Steam/Proton) — lista configurável

## Pesquisa — Áudio por Bluetooth
- [ ] Avaliar viabilidade: o DS4 recebe áudio por Bluetooth em relatórios HID (0x14–0x19) com
      frames SBC, não por perfil A2DP. Não há suporte no kernel nem no PipeWire.
- [ ] Protótipo em espaço de usuário: capturar stream → codificar SBC → enviar via `hidraw`.
- [ ] Só entra no app se tiver latência aceitável (< 60 ms) e não atrapalhar entrada/vibração.

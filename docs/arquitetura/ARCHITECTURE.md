# Arquitetura

## Visão geral

```
┌──────────────────────┐      D-Bus (sessão)      ┌───────────────────────────┐
│  ds4-companion (GUI) │ ◄──────────────────────► │  ds4-companiond (daemon)  │
│  GTK4 + libadwaita   │                          │  serviço systemd --user   │
└──────────────────────┘                          └──────┬──────────┬─────────┘
          ▲                                              │          │
          │ CLI: ds4ctl (mesma API D-Bus)                 │          │
                                                         ▼          ▼
                                            ┌────────────────┐  ┌──────────────────┐
                                            │ PipeWire       │  │ hidraw (DS4)     │
                                            │ links + volume │  │ vibração / luz   │
                                            └────────────────┘  └──────────────────┘
                                                         │
                                                         ▼
                                     ~/.config/rpcs3/input_configs/global/Default.yml
```

### Stack

Nativo do Arch Linux, sem Flatpak/Electron: Python 3, GTK4 + libadwaita (PyGObject),
PipeWire/WirePlumber, `hidraw` + udev (`python-pyudev`), D-Bus (`python-dbus-next`),
systemd de usuário, empacotado em PKGBUILD/AUR. Todos os pacotes vêm do repositório `extra`.
Tabela completa no [README](../../README.md#stack).

### Componentes

| Componente | Papel | Tecnologia proposta |
|---|---|---|
| `ds4-companion` | Interface gráfica | Python 3 + GTK4 + libadwaita (PyGObject) |
| `ds4-companiond` | Daemon do usuário: áudio paralelo, detecção do controle, aplica limites | Python 3, `systemd --user` |
| `ds4ctl` | CLI para scripts e terminal | Python 3 (cliente D-Bus) |
| Configuração | Estado persistente | `~/.config/ds4-companion/config.toml` |

Tudo roda **como usuário comum**. Nada exige root depois da instalação (ver [SECURITY.md](../../SECURITY.md)).

## Áudio em paralelo

O daemon **não** cria saída virtual nem troca a saída padrão. Ele usa uma característica do PipeWire:
uma porta de saída pode ser ligada a **várias** entradas ao mesmo tempo.

```
RPCS3 (Stream/Output/Audio)
  output_FL ──► saída padrão (notebook / HDMI / fone)   ← gerenciado pelo WirePlumber
           └──► DualShock 4 playback_FL                 ← link extra criado pelo daemon
  output_FR ──► saída padrão
           └──► DualShock 4 playback_FR
```

- **Detecção do jogo:** nós `Stream/Output/Audio` cujo `application.name` ou
  `application.process.binary` casa com `rpcs3|AppRun.wrapped` (lista configurável).
- **Detecção do controle:** sink ALSA com `Wireless_Controller`/`DualShock` no nome.
- **Latência:** praticamente zero (sem loopback, sem reamostragem extra além da do próprio sink).
- **Troca de saída:** se o usuário trocar de HDMI para fone, o WirePlumber move o link principal;
  o link do controle fica intacto.
- **Implementação v0 (atual):** polling a cada 2 s com `pw-dump` + `pw-link`.
- **Implementação v1:** escutar eventos do registry via `pw-dump --monitor` (ou bindings de
  libpipewire) e reagir na hora.

### Volume e limitador

1. Volume do sink do controle via `wpctl set-volume` (convertido de/para dB).
2. Teto rígido (`max_db`) aplicado pelo daemon: qualquer volume acima é rebaixado.
3. Limitador: um `filter-chain` do PipeWire (processo filho do daemon) com o `clamp` em −1 dBFS
   entre o jogo e o controle; os links passam a ser jogo → limitador → controle
   ([ADR 0010](adr/0010-limitador-com-filter-chain.md)).

## Vibração

- O RPCS3 controla a vibração em jogo. O app edita
  `Player N Input → Config → Large/Small Vibration Motor Multiplier` e `Switch Vibration Motors`.
- O daemon detecta o RPCS3 aberto e avisa que a mudança vale ao reabrir o emulador
  (o RPCS3 só lê o arquivo ao iniciar).
- Teste de motores: relatório HID direto no `hidraw`:
  - USB: relatório `0x05` (32 bytes), bytes 4/5 = motor fraco/forte.
  - Bluetooth: relatório `0x11` (78 bytes) com CRC32 no final.
- O daemon nunca envia vibração enquanto o RPCS3 está com jogo aberto (evita brigar pelo dispositivo).

## Cabo vs Bluetooth

| | USB | Bluetooth |
|---|---|---|
| Driver do kernel | `hid-playstation` + `snd-usb-audio` | `hid-playstation` |
| hidraw | sim | sim |
| Sink de áudio | sim | **não** |
| Identificação no RPCS3 | `DS4 Pad #N` (independe da conexão) | igual |

O DualSense segue a mesma tabela, com o handler `DualSense` (`DualSense Pad #N`) no RPCS3 e os
relatórios HID dele (USB `0x02`, Bluetooth `0x31`). O sink por cabo tem quatro canais: o som vai só
para FL/FR, porque RL/RR acionam os atuadores hápticos ([ADR 0011](adr/0011-suporte-ao-dualsense.md)).

O daemon detecta a mudança (udev via `pyudev`) e mostra na interface quais recursos estão ativos.

## Estrutura de pastas

Mapa completo do repositório, convenções de nomes e onde colocar cada coisa nova em
[STRUCTURE.md](STRUCTURE.md).

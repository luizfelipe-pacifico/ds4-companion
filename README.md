# DS4 Companion

> App nativo para Arch Linux (GTK4 + libadwaita) que envia o som do RPCS3 em paralelo para o
> DualShock 4, sem trocar sua saída de áudio, com volume em dB e limite de segurança, força da
> vibração e suporte a cabo e Bluetooth.

Tudo numa interface gráfica, sem precisar do terminal.

> Status: **documentação / planejamento**. A versão atual funciona via scripts
> (`~/.local/bin/ds4-audio-mirror` + serviço systemd de usuário). Este projeto transforma isso em app.

## O que ele faz

| Recurso | Cabo USB | Bluetooth |
|---|---|---|
| Vibração (motor forte e fraco, força ajustável) | ✅ | ✅ |
| Som do jogo em paralelo no alto-falante/fone do controle | ✅ | ⚠️ Não suportado pelo Linux hoje (ver [docs/guia/AUDIO.md](docs/guia/AUDIO.md)) |
| Ajuste de volume em dB com aviso de limite | ✅ | — |
| Detecção automática cabo ↔ Bluetooth | ✅ | ✅ |
| Barra de luz (cor/bateria) | ✅ | ✅ |

**"Em paralelo"** quer dizer: a saída de som que você estiver usando (notebook, monitor HDMI,
fone de ouvido) **não muda**. O controle recebe uma cópia do som do jogo ao mesmo tempo.
O juiz apita no jogo → apita na TV **e** no controle.

## Stack

Nativo do Arch Linux: só pacotes do repositório oficial (`extra`), instalado via `pacman`/AUR.
Sem Flatpak, Electron ou runtime embutido.

| Camada | Tecnologia | Pacote Arch |
|---|---|---|
| Linguagem | Python 3 | `python` |
| Interface | GTK4 + libadwaita (PyGObject) | `gtk4`, `libadwaita`, `python-gobject` |
| Fonte | Inter (OFL) — substituta livre da SST | `inter-font` |
| Áudio | PipeWire + WirePlumber | `pipewire`, `wireplumber` |
| Controle (HID) | `hidraw` do kernel + udev | `python-pyudev` |
| Comunicação GUI ↔ daemon | D-Bus de sessão | `python-dbus-next` |
| Serviço em segundo plano | systemd de usuário | `systemd` |
| Empacotamento | PKGBUILD → AUR | `base-devel` |

Visual: preto + azul PlayStation, ver [docs/design/DESIGN.md](docs/design/DESIGN.md).

## Requisitos

- Arch Linux com GNOME (Wayland ou X11)
- PipeWire + WirePlumber (padrão no Arch)
- RPCS3 (`rpcs3-bin` ou AppImage)
- Regras udev para o DualShock 4 (`60-steam-ps4.rules` / pacote `steam-devices` ou instaladas pelo app)

## Instalação (planejada)

```bash
git clone <repo> ds4-companion && cd ds4-companion
makepkg -si
systemctl --user enable --now ds4-companion.service
```

Detalhes em [docs/guia/INSTALL.md](docs/guia/INSTALL.md).

## Documentação

Índice completo em [docs/](docs/README.md).

| Documento | Conteúdo |
|---|---|
| [SECURITY.md](SECURITY.md) | Permissões, limites de volume, proteção do hardware |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como desenvolver e testar |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Código de conduta (Contributor Covenant 2.1) |
| **Guia do usuário** | |
| [docs/guia/INSTALL.md](docs/guia/INSTALL.md) | Instalação, desinstalação, migração dos scripts atuais |
| [docs/guia/CONFIGURATION.md](docs/guia/CONFIGURATION.md) | Arquivo de configuração e opções |
| [docs/guia/AUDIO.md](docs/guia/AUDIO.md) | Áudio paralelo, dB, limitador, limitação do Bluetooth |
| [docs/guia/VIBRATION.md](docs/guia/VIBRATION.md) | Força da vibração e teste dos motores |
| [docs/guia/TROUBLESHOOTING.md](docs/guia/TROUBLESHOOTING.md) | Problemas comuns |
| **Arquitetura** | |
| [docs/arquitetura/ARCHITECTURE.md](docs/arquitetura/ARCHITECTURE.md) | Componentes, fluxo do áudio, integração com PipeWire e RPCS3 |
| **Design** | |
| [docs/design/UI.md](docs/design/UI.md) | Telas da interface |
| [docs/design/DESIGN.md](docs/design/DESIGN.md) | Paleta, tipografia e componentes visuais |
| **Desenvolvimento** | |
| [docs/desenvolvimento/BEST_PRACTICES.md](docs/desenvolvimento/BEST_PRACTICES.md) | Boas práticas de desenvolvimento |
| [docs/desenvolvimento/ROADMAP.md](docs/desenvolvimento/ROADMAP.md) | Fases e próximos passos |

## Licença

[GPL-3.0-or-later](LICENSE). Você pode usar, estudar, modificar e redistribuir; versões modificadas
distribuídas devem manter a mesma licença.

PlayStation, DualShock e PS4 são marcas da Sony Interactive Entertainment. Este projeto não é
afiliado, patrocinado nem endossado pela Sony.

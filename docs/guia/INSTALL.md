# Instalação

## Pelo pacote (planejado)

```bash
git clone <repo> ds4-companion && cd ds4-companion/packaging
makepkg -si
systemctl --user enable --now ds4-companion.service
```

O pacote instala:

| Arquivo | Destino |
|---|---|
| App, daemon, CLI | `/usr/lib/python3.x/site-packages/ds4_companion/`, `/usr/bin/ds4-companion`, `/usr/bin/ds4ctl` |
| Serviço | `/usr/lib/systemd/user/ds4-companion.service` |
| Regra udev | `/usr/lib/udev/rules.d/70-ds4-companion.rules` |
| Atalho e ícone | `/usr/share/applications/`, `/usr/share/icons/hicolor/` |

Depois de instalar, **desconecte e reconecte o controle** (ou rode `sudo udevadm trigger`) para a regra udev valer.

## Dependências

`python`, `python-gobject`, `gtk4`, `libadwaita`, `python-pyudev`, `python-dbus-next`, `inter-font`, `pipewire`, `wireplumber`.
Opcional: `rpcs3-bin` (ou AppImage), `gamemode`, `bluez`.

## Migração dos scripts atuais (Fase 0)

O instalador detecta e desativa a versão em script:

```bash
systemctl --user disable --now ds4-audio-mirror.service
rm ~/.local/bin/ds4-audio-mirror ~/.config/systemd/user/ds4-audio-mirror.service
```

As configurações de vibração do RPCS3 (`~/.config/rpcs3/input_configs/global/Default.yml`) são lidas e mantidas.

## Desinstalação

```bash
systemctl --user disable --now ds4-companion.service
sudo pacman -R ds4-companion
rm -r ~/.config/ds4-companion     # opcional: apaga suas configurações
```

O app não apaga nada do RPCS3; os backups `Default.yml.bak-*` ficam onde estão.

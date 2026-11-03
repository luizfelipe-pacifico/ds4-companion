# Instalação

> Planejado para a v0.3. Decisão em [ADR 0005](../arquitetura/adr/0005-instalacao-por-um-comando.md).

## Jeito mais simples: um comando

```bash
sudo pacman -U https://github.com/luizfelipe-pacifico/ds4-companion/releases/latest/download/ds4-companion.pkg.tar.zst
```

Abra o **DS4 Companion** no menu de apps. Na primeira abertura ele ativa o serviço em segundo plano.

## Pelo instalador (arquivo executável)

Baixe o `install.sh` da [última versão](https://github.com/luizfelipe-pacifico/ds4-companion/releases/latest) e rode **sem** `sudo`
(ele pede a senha só na hora de instalar o pacote):

```bash
curl -fLO https://github.com/luizfelipe-pacifico/ds4-companion/releases/latest/download/install.sh
chmod +x install.sh
./install.sh            # instala, migra os scripts antigos e ativa o serviço
./install.sh --uninstall
```

O instalador confere que o sistema é Arch, verifica o pacote com `SHA256SUMS` antes de instalar e
nunca roda inteiro como root. Para ler antes de rodar: `less install.sh`.

## Pelo AUR

```bash
yay -S ds4-companion     # ou: paru -S ds4-companion
```

## Do código-fonte

```bash
git clone https://github.com/luizfelipe-pacifico/ds4-companion.git && cd ds4-companion/packaging
makepkg -si
systemctl --user enable --now ds4-companion.service
```

## O que é instalado

O pacote instala:

| Arquivo | Destino |
|---|---|
| App, daemon, CLI | `/usr/lib/python3.x/site-packages/ds4_companion/`, `/usr/bin/ds4-companion`, `/usr/bin/ds4ctl` |
| Serviço | `/usr/lib/systemd/user/ds4-companion.service` |
| Regra udev | `/usr/lib/udev/rules.d/70-ds4-companion.rules` |
| Atalho e ícone | `/usr/share/applications/`, `/usr/share/icons/hicolor/` |

Depois de instalar, **desconecte e reconecte o controle** (ou rode `sudo udevadm trigger`) para a regra udev valer.

## Atualização

Ao abrir, o app confere se há versão nova no GitHub Releases. Se houver, aparece o aviso
**Nova versão disponível** com duas opções:

- **Atualizar agora**: o sistema pede sua senha e o app instala a versão nova sozinho. Depois, reabra o app.
- **Copiar comando**: copia o comando abaixo (com a versão certa) para colar no terminal:

  ```bash
  sudo pacman -U https://github.com/luizfelipe-pacifico/ds4-companion/releases/latest/download/ds4-companion.pkg.tar.zst
  ```

Para não consultar, use `check_on_start = false` em `[updates]` ([configuração](CONFIGURATION.md)).
Detalhes em [ADR 0009](../arquitetura/adr/0009-aviso-de-atualizacao.md).

## Dependências

`python`, `python-gobject`, `gtk4`, `libadwaita`, `python-pyudev`, `python-dbus-next`, `polkit`, `inter-font`, `pipewire`, `wireplumber`.
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
./install.sh --uninstall          # se instalou pelo instalador; ou, manualmente:
systemctl --user disable --now ds4-companion.service
sudo pacman -R ds4-companion
rm -r ~/.config/ds4-companion     # opcional: apaga suas configurações
```

O app não apaga nada do RPCS3; os backups `Default.yml.bak-*` ficam onde estão.

# 0001. Stack nativa do Arch: Python + GTK4/libadwaita

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
O app substitui scripts (`ds4-audio-mirror` + serviço systemd de usuário) que já funcionam no Arch
Linux com GNOME. Precisa conversar com PipeWire, `hidraw`, udev, D-Bus e systemd, e ser instalado
pelo `pacman`/AUR.

## Decisão
Python 3 + GTK4 + libadwaita (PyGObject), com `python-pyudev` e `python-dbus-next`. Três partes:
GUI (`ds4-companion`), daemon de usuário (`ds4-companiond`) e CLI (`ds4ctl`), falando por D-Bus
de sessão. Só dependências do repositório `extra`. Sem Flatpak, Electron ou runtime embutido.
Empacotado em PKGBUILD/AUR.

## Consequências
- Visual e comportamento nativos do GNOME (HIG, libadwaita); pacote pequeno.
- Acesso direto a `hidraw` e PipeWire, sem sandbox para contornar.
- Só Arch (e derivados) é suportado oficialmente.
- A GUI não tem lógica de negócio; tudo passa pelo daemon, o que permite usar o `ds4ctl` sem interface.

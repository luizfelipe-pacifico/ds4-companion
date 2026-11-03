# 0008. App ID e API D-Bus

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
A [ADR 0006](0006-organizacao-dos-arquivos.md) deixou o app ID em aberto. Ele dá nome ao `.desktop`,
ao AppStream, ao ícone, ao GResource e ao serviço D-Bus por onde GUI e CLI falam com o daemon.
Também faltava definir o formato dessa API e como a GUI (laço do GLib) e o daemon (asyncio) a usam.

## Decisão
- **App ID:** `io.github.luizfelipe_pacifico.DS4Companion` (DNS reverso do GitHub Pages; o `-` do
  usuário vira `_`, como pede a especificação do D-Bus).
- **Daemon no D-Bus de sessão:** nome `io.github.luizfelipe_pacifico.DS4Companion.Daemon`, objeto
  `/io/github/luizfelipe_pacifico/DS4Companion/Daemon`, interface com o mesmo nome do serviço.
- **Formato:** uma propriedade `Status` (`a{sv}`) com o retrato completo do estado e o sinal
  `PropertiesChanged` a cada mudança; métodos pequenos para cada ação (`SetMirror`, `SetVolume`,
  `SetVibration`, `TestRumble`, `SetLed`…). Erros voltam como erro D-Bus
  `…DS4Companion.Daemon.Error.*` com mensagem para o usuário. Descrição em
  `data/io.github.luizfelipe_pacifico.DS4Companion.Daemon.xml`.
- **Bibliotecas:** daemon e `ds4ctl` usam `python-dbus-next` (asyncio). A GUI usa o `Gio.DBusProxy`
  do próprio PyGObject, que roda no laço do GTK sem ponte com asyncio.
- Ícones, `.desktop`, AppStream e GResource passam a usar o app ID no nome.

## Consequências
- Um sinal só (`Status`) mantém GUI e CLI sempre coerentes; o custo é reenviar o retrato inteiro
  (algumas centenas de bytes) a cada mudança, irrelevante no D-Bus de sessão.
- Trocar o app ID depois quebra atalhos e configurações de quem já instalou: exige nova ADR e migração.
- Testes da GUI usam um cliente falso com a mesma interface do `Gio.DBusProxy`, sem daemon real.
- Risco: o `python-dbus-next` 0.2.3 está parado desde 2021 e usa `typing.no_type_check_decorator`,
  que sai no Python 3.15. Quando o Arch trocar de versão, migrar daemon e CLI para `Gio.DBus`
  (já usado pela GUI) ou para um fork mantido, com nova ADR.

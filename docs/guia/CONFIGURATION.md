# Configuração

Arquivo: `~/.config/ds4-companion/config.toml` (a interface edita por você).

```toml
[audio]
mirror_enabled = true          # espelhar áudio no controle
apps = ["rpcs3", "AppRun.wrapped"]
volume_db = -6.0               # volume do controle
max_db = 0.0                   # teto rígido (nunca passa disso)
headphone_max_db = -6.0        # teto quando há fone na entrada do controle
limiter = true                 # limitador: nenhum pico acima de −1 dBFS no controle

[vibration]
large_percent = 100
small_percent = 100
swap_motors = false
players = [1, 2]               # jogadores do RPCS3 que usam DS4 ou DualSense

[led]
color = "blue"                 # blue, red, green, pink, purple, cyan, orange, white, off ou "#RRGGBB"
mode = "fixed"                 # fixed, ou battery: laranja abaixo de 50 %, vermelha abaixo de 20 %
per_player = false             # no RPCS3, uma cor por jogador como no PS4 (1 azul, 2 vermelho, 3 verde, 4 rosa)

[rpcs3]
config_dir = "~/.config/rpcs3"
backup_before_edit = true

[ui]
start_minimized = false        # abre só na bandeja (precisa de tray_icon e de bandeja na sessão)
tray_icon = true               # ícone na bandeja; no GNOME, com a extensão AppIndicator

[updates]
check_on_start = true          # procurar versão nova ao abrir a interface

[profiles.BLUS30001]           # perfil de um jogo, pelo ID do PS3 (opcional, um por jogo)
title = "FIFA 19"
volume_db = -3.0               # cada campo é opcional: o que faltar vem dos ajustes gerais
mirror_enabled = true
large_percent = 150
small_percent = 100
swap_motors = false
led_color = "#FF8000"
```

## Perfis por jogo

Enquanto um jogo com perfil está aberto no RPCS3, o perfil vale; quando ele para, voltam os ajustes
gerais ([ADR 0012](../arquitetura/adr/0012-perfis-por-jogo.md)).

- **Som no controle e volume** mudam na hora. Mexer no volume com o perfil ativo muda o volume do
  perfil. O teto (`max_db`, fone) vale igual.
- **Vibração e luz** vão para `~/.config/rpcs3/input_configs/<ID>/Default.yml`, o arquivo por jogo
  do próprio RPCS3, gravado com o RPCS3 fechado. Se ele não existe, o app cria a partir do global
  (e só esse arquivo criado pelo app é apagado junto com o perfil). Um arquivo criado assim não
  acompanha mudanças posteriores no global, como trocar o controle de porta.
- O ID do jogo aparece na página Status e no `ds4ctl status` com o jogo aberto.

## Validação

O daemon confere cada valor ao ler o arquivo. Valor inválido não derruba nada: volta para o padrão
e aparece um aviso no journal (`journalctl --user -u ds4-companion`).

| Opção | Aceita |
|---|---|
| `volume_db`, `max_db`, `headphone_max_db` | número de −60 a +6 dB; `volume_db` e `headphone_max_db` nunca ficam acima de `max_db` |
| `apps` | até 32 nomes ou padrões (`*.exe`, `wine*`), 1 a 64 caracteres visíveis cada; um padrão que pegaria qualquer app (`*`) é recusado |
| `large_percent`, `small_percent` | inteiro de 0 a 200 |
| `players` | jogadores de 1 a 7 |
| `color` | uma das cores da lista acima ou `#RRGGBB` |
| `mode` | `fixed` ou `battery` |
| `check_on_start` | `true` ou `false` |

Se o arquivo estiver com erro de sintaxe, o daemon guarda uma cópia (`config.toml.bak-AAAAMMDD-HHMMSS`)
e começa com os padrões.

## CLI (`ds4ctl`)

Fala com o `ds4-companiond` pelo D-Bus, com as mesmas regras da interface.

```bash
ds4ctl status                       # conexão, bateria, áudio, vibração e luz
ds4ctl mirror on|off                # som do jogo no controle
ds4ctl limiter on|off               # limitador contra picos acima de −1 dBFS
ds4ctl volume -6                    # em dB; acima de 0 dB pede confirmação (ou --yes)
ds4ctl vibration --large 80 --small 100 [--swap|--no-swap] [--players 1 2]
ds4ctl test-rumble [strong|weak|both]
ds4ctl led rosa                     # azul, vermelho, …, desligada ou "#FF8800"
ds4ctl led-mode battery             # a luz mostra a bateria (fixed volta à cor escolhida)
ds4ctl led-per-player on            # no RPCS3, uma cor por jogador (5 a 7: ciano, laranja, roxo)
ds4ctl test-tone                    # apito só no controle
ds4ctl apps                         # apps no controle e o que está tocando agora
ds4ctl apps add '*.exe'             # nome do processo ou padrão (Proton: *.exe)
ds4ctl apps remove steam
ds4ctl profile                      # perfis por jogo
ds4ctl profile set --volume -3 --large 150     # perfil do jogo aberto (ou --game BLUS30001)
ds4ctl profile set --reset volume   # o campo volta ao ajuste geral
ds4ctl profile delete --game BLUS30001
```

O volume nunca passa do teto (`max_db`): se pedir mais, o `ds4ctl` aplica o teto e avisa.
Códigos de saída: `0` ok, `1` erro (a mensagem diz o motivo), `3` daemon não está rodando
(`systemctl --user start ds4-companion.service`).

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

[rpcs3]
config_dir = "~/.config/rpcs3"
backup_before_edit = true

[ui]
start_minimized = false        # abre só na bandeja (precisa de tray_icon e de bandeja na sessão)
tray_icon = true               # ícone na bandeja; no GNOME, com a extensão AppIndicator

[updates]
check_on_start = true          # procurar versão nova ao abrir a interface
```

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
ds4ctl test-tone                    # apito só no controle
ds4ctl apps                         # apps no controle e o que está tocando agora
ds4ctl apps add '*.exe'             # nome do processo ou padrão (Proton: *.exe)
ds4ctl apps remove steam
```

O volume nunca passa do teto (`max_db`): se pedir mais, o `ds4ctl` aplica o teto e avisa.
Códigos de saída: `0` ok, `1` erro (a mensagem diz o motivo), `3` daemon não está rodando
(`systemctl --user start ds4-companion.service`).

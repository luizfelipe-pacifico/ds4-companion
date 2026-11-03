# Configuração

Arquivo: `~/.config/ds4-companion/config.toml` (a interface edita por você).

```toml
[audio]
mirror_enabled = true          # espelhar áudio no controle
apps = ["rpcs3", "AppRun.wrapped"]
volume_db = -6.0               # volume do controle
max_db = 0.0                   # teto rígido (nunca passa disso)
headphone_max_db = -6.0        # teto quando há fone na entrada do controle
limiter = true                 # (v1) limitador contra picos

[vibration]
large_percent = 100
small_percent = 100
swap_motors = false
players = [1, 2]               # jogadores do RPCS3 que usam DS4

[led]
color = "blue"                 # blue, red, green, pink, purple, cyan, orange, white, off

[rpcs3]
config_dir = "~/.config/rpcs3"
backup_before_edit = true

[ui]
start_minimized = false
tray_icon = true
```

## Validação

O daemon confere cada valor ao ler o arquivo. Valor inválido não derruba nada: volta para o padrão
e aparece um aviso no journal (`journalctl --user -u ds4-companion`).

| Opção | Aceita |
|---|---|
| `volume_db`, `max_db`, `headphone_max_db` | número de −60 a +6 dB; `volume_db` e `headphone_max_db` nunca ficam acima de `max_db` |
| `apps` | até 32 nomes, 1 a 64 caracteres visíveis cada |
| `large_percent`, `small_percent` | inteiro de 0 a 200 |
| `players` | jogadores de 1 a 7 |
| `color` | uma das cores da lista acima |

Se o arquivo estiver com erro de sintaxe, o daemon guarda uma cópia (`config.toml.bak-AAAAMMDD-HHMMSS`)
e começa com os padrões.

## CLI (`ds4ctl`)

```bash
ds4ctl status                       # conexão, bateria, áudio, vibração
ds4ctl mirror on|off
ds4ctl volume -6                    # em dB; pede confirmação acima de 0
ds4ctl vibration --large 80 --small 100
ds4ctl test-rumble both
```

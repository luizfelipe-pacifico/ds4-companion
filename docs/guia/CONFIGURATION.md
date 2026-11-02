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

[rpcs3]
config_dir = "~/.config/rpcs3"
backup_before_edit = true

[ui]
start_minimized = false
tray_icon = true
```

## CLI (`ds4ctl`)

```bash
ds4ctl status                       # conexão, bateria, áudio, vibração
ds4ctl mirror on|off
ds4ctl volume -6                    # em dB; pede confirmação acima de 0
ds4ctl vibration --large 80 --small 100
ds4ctl test-rumble both
```

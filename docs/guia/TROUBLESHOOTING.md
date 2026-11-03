# Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| Sem som no controle | Controle por Bluetooth | Áudio só funciona por cabo (ver [AUDIO.md](AUDIO.md)) |
| Sem som no controle (cabo) | Serviço parado | Abra o app (ele inicia o serviço) ou `systemctl --user restart ds4-companion.service` |
| Sem som no controle (cabo) | RPCS3 fora da lista de apps | Áudio → Apps no controle: confira `rpcs3` / `AppRun.wrapped` (`ds4ctl status`) |
| Som só no controle, não na TV | Saída padrão virou o DS4 | Configurações → Som → escolha a saída principal |
| Sem vibração | `Device` sem aspas no `Default.yml` | Use `Device: "DS4 Pad #1"` |
| RPCS3 não acha o controle / "Sem acesso ao controle" | Permissão do hidraw | Reconecte o controle; confira `getfacl /dev/hidrawN` |
| Teste de vibração desativado | RPCS3 aberto | Feche o RPCS3: ele está usando o controle |
| Aviso "O PipeWire não respondeu" | PipeWire/WirePlumber travado | `systemctl --user restart pipewire wireplumber` e depois Reiniciar serviço no app |
| Ajuste de vibração ou cor não fez efeito | RPCS3 estava aberto | Feche e abra o RPCS3 (o app aplica ao fechar) |
| Som chiado/distorcido | Volume acima de 0 dB | Baixe para −6 dB |

## Logs

```bash
ds4ctl status
journalctl --user -u ds4-companion -f     # ou: app → Avançado → Ver registros do serviço
grep -iE 'DS4|Pad' ~/.cache/rpcs3/RPCS3.log
pw-link -l
```

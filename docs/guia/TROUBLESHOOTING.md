# Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| Sem som no controle | Controle por Bluetooth | Áudio só funciona por cabo (ver [AUDIO.md](AUDIO.md)) |
| Sem som no controle (cabo) | Serviço parado | `systemctl --user restart ds4-audio-mirror` |
| Som só no controle, não na TV | Saída padrão virou o DS4 | Configurações → Som → escolha a saída principal |
| Sem vibração | `Device` sem aspas no `Default.yml` | Use `Device: "DS4 Pad #1"` |
| RPCS3 não acha o controle | Permissão do hidraw | Reconecte o controle; confira `getfacl /dev/hidrawN` |
| Ajuste não fez efeito | RPCS3 estava aberto | Feche e abra o RPCS3 |
| Som chiado/distorcido | Volume acima de 0 dB | Baixe para −6 dB |

## Logs

```bash
journalctl --user -u ds4-audio-mirror -f
grep -iE 'DS4|Pad' ~/.cache/rpcs3/RPCS3.log
pw-link -l
```

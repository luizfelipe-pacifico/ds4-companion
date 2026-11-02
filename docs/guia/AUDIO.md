# Áudio em paralelo

## Como funciona

O som do RPCS3 vai para **duas** saídas ao mesmo tempo:

1. A saída que você escolheu no GNOME (notebook, HDMI/monitor, fone) — não é alterada.
2. O alto-falante (ou a entrada de fone) do DualShock 4.

Se você trocar a saída no GNOME no meio do jogo, o som principal muda e o controle continua tocando.
Detalhes técnicos em [ARCHITECTURE.md](../arquitetura/ARCHITECTURE.md#áudio-em-paralelo).

## Quais apps são espelhados

Por padrão só o RPCS3 (`rpcs3`, `AppRun.wrapped`). Navegador, Discord etc. **não** vão para o controle.
A lista é configurável (`audio.apps` em [CONFIGURATION.md](CONFIGURATION.md)).

## Volume em dB

| Volume do sink | dB | Observação |
|---|---|---|
| 40 % | 0 dB | volume nativo do hardware (*base volume*) — **teto padrão** |
| 32 % | ≈ −6 dB | recomendado para fone |
| 25 % | ≈ −12 dB | baixo |

A conversão segue a curva cúbica do PipeWire: `dB = 60 · log10(v / v_base)`.

Avisos: ver [SECURITY.md](../../SECURITY.md#proteção-do-alto-falante-do-controle).

## Cabo USB × Bluetooth

| | USB | Bluetooth |
|---|---|---|
| Áudio no controle | ✅ | ❌ |
| Vibração | ✅ | ✅ |

**Por que não tem áudio por Bluetooth:** o DS4 não usa o perfil de áudio Bluetooth comum (A2DP).
O PS4 manda o som codificado (SBC) dentro de relatórios HID proprietários, e nem o kernel Linux
nem o PipeWire implementam isso. Quando o controle está por Bluetooth, o app:

- mostra "Áudio no controle indisponível por Bluetooth — conecte o cabo";
- mantém vibração, luz e bateria funcionando;
- volta a espelhar sozinho quando o cabo é ligado.

Implementar isso em espaço de usuário está na seção *Pesquisa* do [ROADMAP](../desenvolvimento/ROADMAP.md).

## Testar

Na interface: **Áudio → Tocar apito de teste** (toca só no controle, a −12 dB).
No terminal (versão atual em script):

```bash
systemctl --user status ds4-audio-mirror
pw-link -l | grep -A3 -i 'output_FL'
```

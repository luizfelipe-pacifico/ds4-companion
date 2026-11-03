# Pesquisa: áudio no controle por Bluetooth

Item *Pesquisa* do [ROADMAP](ROADMAP.md). Pergunta: dá para levar o som do jogo ao alto-falante ou
ao fone do DualShock 4 quando ele está pareado por Bluetooth, sem cabo?

**Resposta curta:** dá, em espaço de usuário, sem mexer no kernel. O protótipo existe
(`scripts/bt_audio_prototype.py`), mas **ainda não foi testado com o controle**. O recurso só entra
no app depois do checklist abaixo, com latência medida abaixo de 60 ms e sem atrapalhar entrada,
vibração e luz.

## Por que o Linux não faz isso hoje

O DS4 não usa o perfil de áudio Bluetooth (A2DP). Ele recebe o som em **relatórios HID de saída
proprietários**, com quadros SBC dentro. Nem o `hid-playstation` nem o PipeWire implementam isso.
Um patch antigo do `hid-sony` chegou a declarar o relatório 0x17 no descritor, mas foi abandonado.

Pelo código do kernel, o `hidraw` não confere o descritor ao escrever: o relatório vai como está
para o canal de interrupção do Bluetooth (o passo 1 do checklist confirma isso). Por isso um
programa comum, com a permissão `uaccess` que o app já usa, consegue mandar o áudio.

## O protocolo

Montado a partir de três projetos (ver *Fontes*; o dsz deriva do DS4 Sound Link, o PadForge é
independente), que concordam entre si. Nenhum deles publicou teste em hardware. Os offsets contam o ID do relatório como byte 0, igual a `daemon/hid/reports.py`.

### Armar o áudio: relatório 0x11 (78 bytes, CRC32)

| Byte | Valor | Significado |
|---|---|---|
| 0 | `0x11` | ID |
| 1 | `0xC0` | relatório HID + CRC |
| 2 | `0xA0` | modo dos relatórios de entrada; `0xA2` trava a entrada de alguns DS4 (CUH-ZCT2) |
| 3 | `0xB0` | flags: volume do fone (`0x10`, `0x20`) e do alto-falante (`0x80`) |
| 21, 22 | `0x00`–`0x4F` | volume do fone, esquerdo e direito |
| 24 | `0x00`–`0x4F` | volume do alto-falante |
| 25 | `0x85` | liga o caminho de áudio (`0x00` desliga; deixar em 0 deixa o amplificador meio ligado) |
| 74–77 | CRC32 | semente `0xA2`, little-endian |

Acima de `0x4F` o valor invade campos vizinhos do DSP. O protótipo nunca passa disso.

### Mandar o som: relatório 0x17 (462 bytes, CRC32)

| Byte | Valor | Significado |
|---|---|---|
| 0 | `0x17` | ID |
| 1 | `0x40` | só CRC |
| 2 | `0xA0` | modo de entrada (igual ao 0x11) |
| 3–4 | contador | quadros SBC enviados até aqui, 16 bits, avança 4 por relatório |
| 5 | `0x02` / `0x24` | destino: alto-falante / fone |
| 6–441 | 4 × 109 bytes | quatro quadros SBC |
| 442–457 | zeros | preenchimento |
| 458–461 | CRC32 | semente `0xA2` |

### SBC

32 kHz, estéreo conjunto, 16 blocos, 8 sub-bandas, alocação SNR, bitpool 48. Cada quadro tem
109 bytes e leva 128 amostras por canal (4 ms). Quatro quadros = **16 ms por relatório**.
A `libsbc` do pacote `sbc` (repositório `extra`, já puxado pelo `pipewire-audio`) gera exatamente
esses quadros; o teste `tests/unit/daemon/test_bt_audio.py` confere o cabeçalho.

## Orçamento de latência (estimado, não medido)

| Etapa | Tempo |
|---|---|
| Captura no PipeWire (`--latency=16ms`) | ~16 ms |
| Juntar 4 quadros para um relatório | 16 ms |
| Rádio Bluetooth + buffer do controle | desconhecido (é o que falta medir) |
| **Antes do rádio** | **~32 ms** |

Sobram cerca de 28 ms para o rádio e o buffer do controle dentro da meta de 60 ms. É apertado mas
plausível. O relatório 0x14 (dois quadros, 8 ms) poderia cortar 8 ms, se o 0x17 ficar acima da meta.

## Riscos

- **Entrada travada:** com o modo errado no byte 2 o controle para de mandar botões e analógicos.
  O protótipo usa `0xA0`, o valor que as fontes relatam como seguro.
- **Banda do Bluetooth:** ~29 KB/s de áudio no mesmo canal da entrada e da vibração.
- **Disputa pelo hidraw:** o RPCS3 também escreve 0x11 (vibração e luz). Um 0x11 dele sem os bytes
  21–25 pode desarmar o áudio no meio do jogo. É o maior risco para virar recurso do app.
- **Volume:** o alto-falante é pequeno (SECURITY.md). O protótipo começa em 30 % (`0x18`).
- **Bateria:** streaming contínuo deve gastar mais; medir.

## Checklist com hardware

Com o controle pareado por Bluetooth e o RPCS3 **fechado**:

```bash
. .venv/bin/activate
python scripts/bt_audio_prototype.py --tone --seconds 5            # 1. apito no alto-falante
python scripts/bt_audio_prototype.py --tone --target headphones    # 2. apito no fone do controle
python scripts/bt_audio_prototype.py --seconds 60                  # 3. som da saída padrão
```

Anote:

1. O apito sai limpo, sem estalos? O intervalo p50/p99 que o script imprime fica perto de 16 ms?
2. Botões, analógicos e touchpad seguem funcionando durante o som (`evtest` ou um jogo)?
3. Atraso entre a saída do PC e o controle num vídeo com batidas de claquete (meta: < 60 ms).
4. Vibração e luz continuam depois de parar (`ds4ctl test-rumble`, `ds4ctl led verde`)?
5. Bateria antes e depois de 30 minutos de som.

Se os cinco passarem, o próximo passo é uma ADR para levar o streaming ao daemon, resolvendo a
disputa com o RPCS3 (item 3 dos riscos).

## Fontes

- [PadForge — Controller Audio Internals](https://padforge.org/docs/reference/controller-audio-internals/): parâmetros SBC, bytes 1–5 do 0x17, flags e volumes do 0x11.
- [dsz PR #26](https://github.com/MaximumFreak/dsz/pull/26): 0x17 a cada 16 ms com quatro quadros, contador +4, bytes 21–24.
- [DS4 Sound Link](https://github.com/abh1shekbana/DS4-Sound-Link): byte 25 = `0x85`, teto `0x4F` dos volumes.
- [PadForge #528](https://github.com/hifihedgehog/PadForge/issues/528) e [SDL #41](https://github.com/hifihedgehog/SDL/issues/41): `0xA2` no byte 2 trava a entrada; o descritor do kernel não declara mais o 0x17.
- [Patch do hid-sony com o 0x17 no descritor](https://git.zx2c4.com/linux-dev/commit/?id=d829674d29d7eb99aeb3ad11eba61d06cda7aff4).

Nenhuma dessas fontes testou latência em hardware. Só o protocolo vem delas; o código do
protótipo é próprio e o SBC é da `libsbc`.

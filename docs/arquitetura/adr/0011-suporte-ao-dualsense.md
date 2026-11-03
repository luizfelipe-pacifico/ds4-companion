# 0011. Suporte ao DualSense no mesmo app

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
O roadmap (Fase 4) pede suporte ao DualSense (PS5). O RPCS3 tem um handler `DualSense` com as
mesmas chaves de vibração e cor do DualShock 4 no `Default.yml`. Os jogos de PS3 só conhecem
vibração de dois motores: não existe nada para mandar aos atuadores hápticos nem aos gatilhos
adaptativos, e o RPCS3 não emula isso. O controle usa o mesmo driver do kernel
(`hid-playstation`), mas relatórios HID diferentes.

## Decisão
- O DualSense (`054c:0ce6`) e o DualSense Edge (`054c:0df2`) entram no mesmo app, com o mesmo nome
  (*DS4 Companion*), como um segundo **modelo** de controle (`Model.DUALSENSE`). O estado do daemon
  passa a dizer o modelo (`controller_model`).
- **Relatórios HID** seguem o `hid-playstation`: USB `0x02` (63 bytes) e Bluetooth `0x31` (78 bytes,
  número de sequência e CRC32). A vibração usa o modo "compatível" de dois motores; a versão (v1 ou
  v2) vem do relatório de feature `0x20` do firmware, lido uma vez por conexão (o Edge é sempre v2).
  O `--stop-motors` manda o "parar" nos dois formatos, porque ali não há firmware lido.
- **Fone** pelo `status[1]` do relatório de entrada USB, como o kernel faz: o teto do fone vale igual.
- **Áudio por cabo:** o sink do DualSense tem quatro canais; o som vai só para FL/FR. RL/RR acionam
  os atuadores hápticos e nunca recebem o som do jogo (teste em `test_audio.py`). O limitador
  (ADR 0010) liga a saída dele com `channelmix.upmix = false` pelo mesmo motivo.
- **RPCS3:** jogadores com `Handler: DualSense` são editados como os de `DualShock 4`.
- **Fora do escopo:** háptico e gatilhos adaptativos, até o RPCS3 ter algo para mandar a eles.

## Consequências
- Um app só para os dois controles; a regra udev, a detecção e a página Vibração cobrem os dois.
- O dB do volume usa a mesma base do DS4 (40 % = 0 dB). A base do sink do DualSense ainda não foi
  conferida com o controle: até lá o teto continua valendo, mas o "0 dB" pode não ser o 0 dB do
  hardware. O checklist manual de cada versão passa a incluir o DualSense.
- Trocar o nome do app por causa do segundo controle exigiria nova ADR (o app ID da ADR 0008 fica).

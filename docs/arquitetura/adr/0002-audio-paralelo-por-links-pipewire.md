# 0002. Áudio em paralelo por links extras no PipeWire

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
O som do RPCS3 precisa sair no controle **e** na saída que o usuário já usa (notebook, HDMI, fone),
sem trocar a saída padrão e sem latência perceptível.

## Decisão
O daemon cria links extras das portas `output_FL/FR` do stream do RPCS3 para `playback_FL/FR` do
sink do DualShock 4. Não cria saída virtual, loopback nem combina sinks. v0 usa polling com
`pw-dump` + `pw-link`; v1 passa a reagir a eventos do registry.

## Consequências
- Latência praticamente zero; trocar de saída no GNOME não derruba o link do controle.
- Funciona só via cabo USB: no Bluetooth o kernel não expõe sink de áudio do DS4.
- O volume do controle é independente e precisa de teto (`max_db`) aplicado pelo daemon
  (ver [SECURITY.md](../../../SECURITY.md)).

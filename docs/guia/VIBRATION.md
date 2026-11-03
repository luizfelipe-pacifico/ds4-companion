# Vibração

## O que dá e o que não dá

- O DS4 tem **dois motores**: forte (esquerdo, grave) e fraco (direito, agudo).
- Os jogos de PS3 mandam vibração comum; o RPCS3 repassa para o DS4 por cabo e Bluetooth.
- **Não existe** vibração háptica nem gatilho adaptativo estilo PS5 no DS4 (é limitação do hardware).
- O **DualSense** funciona do mesmo jeito, no modo de vibração "compatível" de dois motores (handler
  `DualSense` no RPCS3). Os jogos de PS3 não têm nada para os atuadores hápticos nem para os
  gatilhos adaptativos, então eles ficam parados.

## Ajustes

| Opção | Onde fica no RPCS3 | Faixa | Padrão |
|---|---|---|---|
| Força motor forte | `Large Vibration Motor Multiplier` | 0–200 % | 100 % |
| Força motor fraco | `Small Vibration Motor Multiplier` | 0–200 % | 100 % |
| Inverter motores | `Switch Vibration Motors` | sim/não | não |

Acima de 100 % a interface avisa: o motor fica mais tempo no máximo e gasta mais bateria.
As mudanças valem ao **reabrir o RPCS3**.

Arquivo: `~/.config/rpcs3/input_configs/global/Default.yml`, uma seção por jogador:

```yaml
Player 1 Input:
  Handler: DualShock 4
  Device: "DS4 Pad #1"     # aspas obrigatórias: sem elas o "#1" vira comentário
  Config:
    Large Vibration Motor Multiplier: 100
    Small Vibration Motor Multiplier: 100
    Switch Vibration Motors: false
```

## Teste de motores

Botões **Forte**, **Fraco** e **Ambos** (0,5 s cada). Funciona por cabo e Bluetooth.
Desativado enquanto um jogo está rodando no RPCS3.

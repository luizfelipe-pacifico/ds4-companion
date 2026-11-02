# Interface

Janela GTK4/libadwaita com 4 páginas na barra lateral. Cores e fonte em [DESIGN.md](DESIGN.md).

## Status
```
┌ DS4 Companion ───────────────────────────────┐
│ ● DualShock 4 conectado — Cabo USB           │
│   Bateria: carregando 80%                    │
│   RPCS3: aberto · Áudio no controle: ativo   │
│   Saída principal: SAMSUNG (HDMI)            │
└──────────────────────────────────────────────┘
```

## Áudio
```
 Som do jogo no controle           [ ligado ]
 Volume do controle   −6 dB  ━━━━━━━●─────│───
                            livre   alto  │ acima do limite (branco)
                                         0 dB
 ⚠ Acima de 0 dB o som distorce e pode danificar o alto-falante.
 [ Tocar apito de teste ]
 Apps espelhados: RPCS3  [+ adicionar]
```

## Vibração
```
 Motor forte   100%  ━━━━━━━━━━●━━━━━━━━━   [Testar]
 Motor fraco   100%  ━━━━━━━━━━●━━━━━━━━━   [Testar]
 Inverter motores                    [ desligado ]
 Jogadores: [x] 1  [x] 2
 ℹ Vale ao reabrir o RPCS3.
```

## Avançado
- Pasta do RPCS3, backups, logs do daemon, reiniciar serviço, restaurar padrões.

## Comportamento
- Estados vazios, avisos e erros usam `AdwStatusPage` com as ilustrações de [ILLUSTRATIONS.md](ILLUSTRATIONS.md).
- Bluetooth: cartão de áudio vira aviso "conecte o cabo para ter som no controle".
- Volume acima do teto: slider para no teto; ir além exige diálogo de confirmação.

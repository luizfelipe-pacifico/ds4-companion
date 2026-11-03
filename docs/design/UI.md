# Interface

Janela GTK4/libadwaita com 5 páginas na barra lateral (Status, Áudio, Vibração, Luz, Avançado). Cores e
fonte em [DESIGN.md](DESIGN.md). Abaixo de 600 sp a barra lateral vira navegação com voltar.

Capturas com estados sintéticos, sem daemon nem hardware: `dbus-run-session -- scripts/screenshots.sh <pasta>`
(roda num `mutter` headless, sem abrir janela na sessão).

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
 Apps no controle
   rpcs3                                     [🗑]
   Adicionar pelo nome do processo ou padrão  [✎]
 Sugestões — Tocando agora no computador. Escolha um para mandar o som para o controle.
   Firefox                                    [+]
   Jogos do Steam e Proton (*.exe)            [+]
```
- **Sugestões** só aparece quando há o que sugerir: apps tocando que a lista ainda não pega e o
  atalho do Proton enquanto `*.exe` não está na lista. A linha escolhida sai na hora e um toast
  confirma; se o daemon recusar, o toast diz o motivo e a sugestão volta.

## Vibração
```
 Motor forte   100%  ━━━━━━━━━━●━━━━━━━━━   [Testar]
 Motor fraco   100%  ━━━━━━━━━━●━━━━━━━━━   [Testar]
 Inverter motores                    [ desligado ]
 Jogadores: [x] 1  [x] 2
 ℹ Vale ao reabrir o RPCS3.
```

## Luz
```
 Cor da barra de luz
 (●) Azul  (●) Vermelho  (●) Verde  (●) Rosa  (●) Roxo  (●) Ciano  (●) Laranja  (●) Branco  (○) Desligada
 ℹ O RPCS3 está aberto: a cor vai para o controle quando ele fechar.
```
- As amostras mostram a cor real do LED (exceção da paleta). A escolhida ganha anel branco e rótulo
  em peso 500, além do fundo azul 16 %: a seleção não depende só de cor.

## Avançado
- Pasta do RPCS3 (seletor de pasta), backup antes de editar, ver registros do serviço
  (`journalctl --user`), reiniciar serviço, restaurar padrões (com confirmação).

## Atualização
Ao abrir, a janela consulta o GitHub Releases em segundo plano. Com versão nova, abre um
`AdwAlertDialog` ([ADR 0009](../arquitetura/adr/0009-aviso-de-atualizacao.md)):
```
 Nova versão disponível
 O DS4 Companion 0.2.0 já pode ser instalado. Você está usando a versão 0.1.0.
 Ou cole no terminal:
 sudo pacman -U https://github.com/…/ds4-companion-0.2.0-1-any.pkg.tar.zst
 [ Agora não ]  [ Copiar comando ]  [ Atualizar agora ]
```
- **Atualizar agora** pede a senha (polkit) e mostra o resultado num `AdwToast`; senha cancelada
  vira "Atualização cancelada.", falha oferece copiar o comando.
- Sem rede ou sem versão nova, nada aparece.

## Carregamento
```
                 [ícone do app]
                      ◌
            Conectando ao serviço…
         ( Ver registros do serviço )    ← só depois de 10 s
```
- Aparece ao abrir, enquanto a janela espera o daemon: "Conectando ao serviço…", "Iniciando o
  serviço…" (primeira abertura ou **Iniciar serviço**) e "Lendo o estado do controle…".
- O ícone aparece na hora; spinner e texto só depois de 400 ms, com fade de 150 ms, para uma
  resposta rápida não piscar nada. As páginas só entram com o primeiro estado do daemon, nunca vazias.
- Depois de 10 s: "O serviço está demorando para responder." e o botão dos registros. O espaço do
  botão é reservado desde o início, para o ícone não pular.

## Comportamento
- Estados vazios, avisos e erros usam `AdwStatusPage` com as ilustrações de [ILLUSTRATIONS.md](ILLUSTRATIONS.md);
  dentro de uma página (Áudio aguardando o jogo) a ilustração aparece pequena, ao lado do texto.
- Bluetooth: a página Áudio vira o aviso "Som no controle precisa do cabo".
- Volume: o slider para em 0 dB; passar disso exige confirmação e nunca vai além de `max_db`.
  O valor em dB acompanha o arraste; o daemon recebe o valor final do gesto.
- Vibração: com o RPCS3 aberto aparece um banner dizendo que a mudança vale ao reabrir, e os testes
  ficam desativados com o motivo na dica.
- Serviço parado: a janela inteira vira a tela "Serviço parado". Na primeira abertura o app ativa o
  serviço sozinho (`systemctl --user enable --now ds4-companion.service`).
- Problema no PipeWire: banner no topo com a mensagem do daemon.
- Ícone na bandeja: ainda não implementado (precisa de StatusNotifierItem; ver ROADMAP).

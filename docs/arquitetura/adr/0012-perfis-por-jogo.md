# 0012. Perfis por jogo

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
O roadmap (Fase 4) pede perfis por jogo: por exemplo, FIFA com mais som no controle e Tekken só
com vibração. Para isso o daemon precisa saber qual jogo está aberto, e os ajustes de vibração e
luz precisam chegar ao RPCS3, que só lê a configuração de controle ao abrir o jogo.

O RPCS3 não tem API para dizer o jogo aberto, mas escreve no `RPCS3.log`
(`~/.cache/rpcs3/`) `SYS: Title: <título>` e `SYS: Serial: <ID>` ao abrir um jogo e
`SYS: Stopping emulator...` ao parar; cada execução começa um log novo. Ele também já tem
configuração de controle por jogo: `input_configs/<serial>/Default.yml`, usada no lugar da global
quando existe.

## Decisão
- **Jogo aberto:** o daemon lê o `RPCS3.log` aos poucos (só o que cresceu, em partes de até
  1 MiB) enquanto o processo do RPCS3 está aberto, e publica `game_serial` e `game_title` no
  estado. O log é dado não confiável: o serial precisa casar com `[A-Z]{4}\d{5}` e o título perde
  caracteres de controle e fica com até 128 caracteres. Com o RPCS3 fechado, nada é lido.
- **Perfil = ajustes por serial** no `config.toml` (`[profiles.<serial>]`), cada um opcional: som no
  controle, volume, força e inversão dos motores e cor da luz. O que o perfil não define vem dos
  ajustes gerais.
- **Som e volume** do perfil valem enquanto o jogo está aberto e voltam aos gerais quando ele para.
  O teto (`max_db`, fone) e a confirmação acima de 0 dB valem igual para os perfis.
- **Vibração e luz** do perfil vão para o `input_configs/<serial>/Default.yml` do RPCS3. Se o
  arquivo não existe, ele é criado a partir do global (com as mesmas regras de edição por linha,
  backup e RPCS3 fechado); apagar o perfil apaga só o arquivo que o app criou.

## Consequências
- Funciona com o fluxo normal do RPCS3, sem processo extra nem integração com a interface dele.
- Depende do formato do log, que pode mudar numa versão do RPCS3: sem as linhas, o perfil
  simplesmente não é aplicado (o app segue nos ajustes gerais), e os testes fixam o formato.
- Um arquivo por jogo criado a partir do global não acompanha mudanças posteriores no global
  (dispositivo, botões); a interface avisa disso ao criar o perfil.

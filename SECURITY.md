# Segurança

## Princípios

1. **Sem root em tempo de execução.** GUI, daemon e CLI rodam como usuário.
2. **Root só na instalação**, via `pacman`, para colocar a regra udev em `/usr/lib/udev/rules.d/`.
3. **Nada sai da máquina.** Sem telemetria, sem rede.
4. **Proteção do hardware em primeiro lugar.** Volume e vibração têm limites que a interface não deixa passar sem confirmação.

## Permissões

| Recurso | Como o acesso é dado | Escopo |
|---|---|---|
| `/dev/hidraw*` do DS4 | regra udev com `TAG+="uaccess"` (só VID `054c`, PIDs `05c4`, `09cc`, `0ba0`) | só o usuário logado na sessão ativa |
| PipeWire | sessão do próprio usuário | só os streams do usuário |
| Arquivos do RPCS3 | `~/.config/rpcs3` | só leitura/escrita das chaves de controle |

A regra udev **não** usa `MODE="0666"`. Outro usuário do computador não ganha acesso ao controle.

## Proteção do alto-falante do controle

O alto-falante do DS4 é pequeno (aprox. 0,5 W). Volume alto por muito tempo distorce e pode danificar.

- **Referência:** o sink do DS4 informa *base volume* = 40 % ≈ **0 dB** (volume nativo do hardware).
  Acima disso o sinal é amplificado digitalmente e passa a **clipar**.
- **Faixas na interface:**

| Faixa | Sinal na interface | Comportamento |
|---|---|---|
| ≤ −6 dB | preenchimento azul | livre |
| −6 dB a 0 dB | ícone de aviso + rótulo "alto" | aviso "volume alto" |
| > 0 dB | preenchimento invertido para branco + ícone + "acima do limite" | exige confirmação; nunca passa de `max_db` (padrão **0 dB**) |

A interface não usa verde/amarelo/vermelho (ver [DESIGN.md](docs/design/DESIGN.md#estados-sem-cores-de-alerta)):
cada faixa é indicada por texto e ícone, nunca só por cor.

- **Fone na entrada do controle:** perfil separado com teto padrão de −6 dB (proteção auditiva).
- **Ao conectar o controle**, o daemon reaplica o volume salvo (nunca começa no máximo).
- **Limitador** (v1) contra picos acima de −1 dBFS.

## Proteção dos motores

- Força máxima configurável (padrão 100 % = o que o jogo pedir).
- Teste de vibração: no máximo 2 s por clique, com intervalo mínimo entre testes.
- Se o daemon cair durante um teste, o `ExecStopPost` manda o relatório de parada (motores 0).

## Arquivos de terceiros

- Antes de editar `Default.yml` do RPCS3 o app faz backup (`Default.yml.bak-AAAAMMDD-HHMMSS`).
- Só edita quando o RPCS3 está fechado.
- Strings vindas do PipeWire/udev são tratadas como dados, nunca executadas.

## Versões suportadas

| Versão | Recebe correções de segurança |
|---|---|
| última `0.x` | ✅ |
| anteriores | ❌ |

## Relatar vulnerabilidade

**Não abra issue pública.** Use o relato privado do GitHub: aba **Security → Report a vulnerability**.

- Resposta inicial em até 7 dias.
- Correção e aviso (*GitHub Security Advisory*) coordenados com quem relatou.
- Pedimos que não publique detalhes antes da correção sair.

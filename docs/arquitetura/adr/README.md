# Decisões de arquitetura (ADR)

Cada decisão importante vira um arquivo `NNNN-titulo-curto.md`, numerado em sequência.
Uma ADR aceita não é editada para mudar de ideia: escreva uma nova que a **substitui** e marque a
antiga como *Substituída por NNNN*.

| Nº | Decisão | Status |
|---|---|---|
| [0001](0001-stack-nativa-arch.md) | Stack nativa do Arch: Python + GTK4/libadwaita, sem Flatpak/Electron | Aceita |
| [0002](0002-audio-paralelo-por-links-pipewire.md) | Áudio em paralelo por links extras no PipeWire | Aceita |
| [0003](0003-paleta-de-cinco-cores.md) | Paleta de cinco cores, sem cores de alerta | Aceita |
| [0004](0004-commits-sem-atribuicao-de-ia.md) | Commits e PRs sem atribuição de IA | Aceita |
| [0005](0005-instalacao-por-um-comando.md) | Instalação por um comando (`sudo pacman -U`) ou `install.sh` | Aceita |

## Modelo

```markdown
# NNNN. Título

- **Status:** Proposta | Aceita | Substituída por NNNN
- **Data:** AAAA-MM-DD

## Contexto
O problema e as restrições.

## Decisão
O que foi decidido.

## Consequências
O que fica mais fácil, o que fica mais difícil, o que precisa ser feito.
```

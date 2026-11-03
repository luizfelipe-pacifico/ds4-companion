# 0010. Limitador com `filter-chain` e `clamp` do PipeWire

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
O SECURITY.md pede um limitador contra picos acima de −1 dBFS no alto-falante do controle. O teto em
dB (`max_db`) controla o volume do sink, mas não segura um pico do jogo. O PipeWire do `extra` não traz
compressor nem limitador com *lookahead*: o plugin `builtin` só tem filtros simples, entre eles o
`clamp`. Um limitador LADSPA de verdade (`fast_lookahead_limiter`) exigiria o `swh-plugins`.

## Decisão
- O daemon sobe um processo filho `pipewire -c <conf>` com um `filter-chain` de dois canais usando o
  `clamp` do PipeWire em ±0,891 (−1 dBFS). Nenhuma dependência nova.
- A entrada do filtro é um `Stream/Input/Audio` com `node.autoconnect = false` (não aparece como saída
  de som do sistema nem recebe outros apps); a saída aponta para o sink do controle com `target.object`.
- Com o limitador de pé, os links do espelhamento vão jogo → limitador, e os links diretos antigos
  jogo → controle são removidos. Se o filho não subir ou sair logo, o som segue direto ao controle.
- Liga com o espelhamento e com `audio.limiter = true` (padrão); desliga na interface, no
  `ds4ctl limiter off` ou no `config.toml`.

## Consequências
- Nenhum pico passa de −1 dBFS no controle, medido no teste de integração (tom a 0 dBFS entra, o pico
  medido fica ≤ 0,891; direto ao controle passa disso).
- O `clamp` corta o pico em vez de comprimir: com o volume acima de 0 dB, o corte pode ser audível.
  É o compromisso para não depender de pacote extra; trocar por LADSPA/LV2 é uma ADR futura.
- Um processo `pipewire` a mais por sessão enquanto o espelhamento está ligado.

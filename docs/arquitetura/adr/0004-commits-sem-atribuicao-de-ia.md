# 0004. Commits e PRs sem atribuição de IA

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
Ferramentas de IA (Claude Code) adicionam por padrão `Co-Authored-By` em commits e uma linha de
"gerado por" em PRs, o que faz a ferramenta aparecer como contribuidora no GitHub.

## Decisão
Nenhum commit ou PR leva atribuição de IA. O `.claude/settings.json` do projeto desliga isso
(`attribution` vazio) e o `CLAUDE.md` registra a regra. O commit inicial foi reescrito sem o trailer.

## Consequências
- O histórico mostra só autores humanos; quem assina (`git commit -s`) responde pelo conteúdo (DCO).
- As skills de design (`impeccable`, `apple-design`) ficam versionadas em `.claude/skills/`; o
  binário do impeccable e o `settings.local.json` com os hooks ficam fora do Git.

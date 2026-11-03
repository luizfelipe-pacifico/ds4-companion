# 0009. Aviso de atualização ao abrir o app

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
Quem instala por `sudo pacman -U <url>` ([ADR 0005](0005-instalacao-por-um-comando.md)) não recebe
atualizações pelo `pacman -Syu`, porque o pacote não vem de um repositório. Sem aviso, a pessoa
fica para sempre na versão que instalou. Até aqui o [SECURITY.md](../../../SECURITY.md) dizia
"sem rede", e atualizar exige root.

## Decisão
- **Consulta ao abrir:** cada vez que a interface abre, ela faz **uma** requisição HTTPS a
  `api.github.com/repos/luizfelipe-pacifico/ds4-companion/releases/latest`, em segundo plano, com
  limite de 5 s. Não envia nada do usuário além do `User-Agent: ds4-companion/<versão>`. Falha de
  rede é silenciosa (só um registro no log). Desliga com `[updates] check_on_start = false`.
  Só a GUI consulta; daemon e `ds4ctl` continuam sem rede.
- **Resposta é dado não confiável:** a tag precisa ser `vX.Y.Z`, rascunhos e pré-releases são
  ignorados e a comparação é numérica. A URL do pacote é montada pelo app com a versão conferida
  (`releases/download/vX.Y.Z/ds4-companion-X.Y.Z-N-any.pkg.tar.zst`); se o arquivo versionado não
  existir, usa o nome fixo da última release da ADR 0005. Nada da resposta vira argumento sem passar
  por essas regras.
- **Pop-up:** com versão nova, aparece um `AdwAlertDialog` "Nova versão disponível" com:
  - **Atualizar agora** (ação sugerida): roda `pkexec pacman -U --noconfirm <url>`. O polkit pede a
    senha; só o `pacman` roda como root, e só depois do clique. Ao terminar, reinicia o serviço de
    usuário (`systemctl --user try-restart`) e pede para reabrir o app.
  - **Copiar comando**: copia `sudo pacman -U <url>` (também mostrado no diálogo, selecionável) para
    colar no terminal.
  - **Agora não**: fecha; o aviso volta na próxima abertura.
- O `pacman` confere a assinatura `.sig` publicada na release, como em qualquer `pacman -U`.

**Rejeitado:** atualizar sozinho sem perguntar (instalaria como root sem consentimento); repositório
próprio do pacman (exige servidor e chave no `pacman.conf`, fora do escopo agora); consulta
periódica pelo daemon (rede num serviço que roda sempre).

## Consequências
- A pessoa sabe da versão nova na hora e atualiza com um clique ou um comando.
- O app passa a ter uma conexão de rede, documentada e desligável; o SECURITY.md muda junto.
- `polkit` (para o `pkexec`) entra nas dependências do pacote.
- A API do GitHub tem limite de 60 requisições/hora por IP sem autenticação; uma por abertura fica
  muito abaixo disso.

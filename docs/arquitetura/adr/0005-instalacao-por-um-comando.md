# 0005. Instalação por um comando ou por arquivo executável

- **Status:** Aceita
- **Data:** 2026-11-02

## Contexto
Instalar só com `git clone` + `makepkg -si` exige saber compilar pacote. O app precisa ser
instalável por quem só sabe colar um comando no terminal ou dar dois cliques num arquivo,
sem fugir da [ADR 0001](0001-stack-nativa-arch.md) (pacote nativo, sem Flatpak/AppImage).

## Decisão
Cada versão publica no GitHub Releases:

| Arquivo | Para quê |
|---|---|
| `ds4-companion-X.Y.Z-1-any.pkg.tar.zst` | o pacote do Arch, gerado pelo mesmo `PKGBUILD` do AUR |
| `ds4-companion-X.Y.Z-1-any.pkg.tar.zst.sig` | assinatura GPG do pacote |
| `SHA256SUMS` | somas de verificação |
| `install.sh` | instalador executável |

Formas de instalar, da mais simples para a mais manual:

1. **Um comando:** `sudo pacman -U https://github.com/luizfelipe-pacifico/ds4-companion/releases/latest/download/ds4-companion.pkg.tar.zst`
   (o pacman aceita URL). Um nome fixo sem versão aponta sempre para a última release.
2. **Arquivo executável:** `install.sh`, rodado **como usuário comum**. Ele confere que é Arch,
   baixa o pacote, verifica `SHA256SUMS`, chama `sudo pacman -U` só nesse passo, migra os
   scripts da Fase 0, ativa o serviço de usuário e recarrega as regras udev. `--uninstall` desfaz.
3. **AUR:** `yay -S ds4-companion` (ou `paru`).
4. **Do código:** `makepkg -si` em `packaging/`.

O serviço de usuário é ativado pelo próprio app na primeira abertura, para que a forma 1 não
precise de um segundo comando.

**Rejeitado:** `curl ... | sudo bash` (roda script remoto como root sem chance de leitura ou
verificação); instalador que roda inteiro como root (ativaria o serviço para o root, não para o
usuário); AppImage/Flatpak (ADR 0001).

## Consequências
- Instalação em um comando, com o pacman cuidando de dependências, atualização e remoção.
- O CI precisa gerar e assinar o pacote e anexar os quatro arquivos a cada release.
- O `install.sh` é código que roda `sudo`: segue as regras do [SECURITY.md](../../../SECURITY.md),
  é testado no CI (`shellcheck` + instalação num container `archlinux:latest`) e nunca baixa nada
  sem verificar a soma.

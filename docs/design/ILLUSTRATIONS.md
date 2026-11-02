# Ilustrações

Ilustrações *flat* em SVG para as telas de estado: página vazia, erro, aviso e sucesso.
Ficam em [`data/illustrations/`](../../data/illustrations/). Cores e regras de SVG em [DESIGN.md](DESIGN.md).

## Regras

- **Nenhum texto dentro do SVG.** O texto fica na interface (título, descrição e botão), passa pelo
  `gettext` e pode ser traduzido. Isso vale para todas as ilustrações, inclusive as de erro.
- **A ilustração nunca aparece sozinha.** Toda tela de estado tem ao menos título e descrição que digam
  o que aconteceu e o que fazer. A ilustração reforça a mensagem; ela não a substitui.
- **Espaço pequeno = só texto.** Em barra lateral, popover ou cartão, usar `AdwStatusPage` com a classe
  `.compact` e sem ilustração.
- **Erro ≠ vazio.** Página vazia (nada configurado ainda) não usa vermelho nem sinal de alerta.
  Vermelho (`danger`) só quando algo de fato falhou.
- **Formato:** `viewBox="0 0 256 256"` (1:1), fundo transparente, desenhado para a janela preta
  (`ps-black`). Exibir em 160–200 px. Sem `<image>`, sem script, sem fonte.
- **Mesmo controle do ícone do app**, para a interface parecer uma coisa só. Desenho próprio:
  sem logotipo da PlayStation e sem △◯✕□ (ver [Marca](DESIGN.md#marca)).

## Anatomia

Toda ilustração segue a mesma estrutura, de trás para frente:

1. **Fundo:** círculo `ps-surface` (r = 112) com brilho radial `ps-blue-bright` a 22 %.
2. **Sombra no chão:** elipse `ps-surface-2` embaixo do objeto.
3. **Objeto principal:** o controle (azul = presente, tracejado cinza = ausente), uma engrenagem
   (serviço) ou cartões (listas).
4. **Selo de estado:** círculo colorido no canto superior direito com um símbolo branco ou preto.
   A cor do selo diz o tipo de estado:

| Selo | Cor | Tipo |
|---|---|---|
| ⓘ ampulheta, ＋, Bluetooth | `ps-blue-bright` | informação / vazio |
| ✓ | `ok` | sucesso |
| cadeado, alto-falante mudo | `warn` | aviso: dá para resolver |
| ！, ■ | `danger` | erro: algo falhou |

## Catálogo

| Ilustração | Arquivo | Tipo | Quando aparece |
|:-:|---|---|---|
| <img src="../../data/illustrations/no-controller.svg" width="96" alt=""> | `no-controller.svg` | vazio | Nenhum DualShock 4 detectado |
| <img src="../../data/illustrations/waiting-game.svg" width="96" alt=""> | `waiting-game.svg` | vazio | Controle ok, RPCS3 fechado |
| <img src="../../data/illustrations/empty-list.svg" width="96" alt=""> | `empty-list.svg` | vazio | Lista sem itens (apps espelhados, perfis) |
| <img src="../../data/illustrations/bluetooth-no-audio.svg" width="96" alt=""> | `bluetooth-no-audio.svg` | aviso | Página Áudio com o controle por Bluetooth |
| <img src="../../data/illustrations/no-permission.svg" width="96" alt=""> | `no-permission.svg` | aviso | Sem acesso ao `hidraw` (regra udev não aplicada) |
| <img src="../../data/illustrations/service-stopped.svg" width="96" alt=""> | `service-stopped.svg` | erro | GUI não encontra o `ds4-companiond` no D-Bus |
| <img src="../../data/illustrations/error.svg" width="96" alt=""> | `error.svg` | erro | Falha inesperada sem tela própria |
| <img src="../../data/illustrations/all-set.svg" width="96" alt=""> | `all-set.svg` | sucesso | Fim da primeira configuração; tudo funcionando |

## Descrições e textos

Para cada ilustração: o que o desenho mostra, o texto alternativo (leitor de tela) e os textos da
tela. Os textos são o ponto de partida para o `gettext`.

### `no-controller.svg` — vazio
- **Desenho:** contorno tracejado cinza de um controle (ausente) e, embaixo, um cabo USB azul com o
  plugue solto e três traços de "faísca" indicando que falta conectar.
- **Texto alternativo:** "Controle desconectado"
- **Título:** Nenhum controle conectado
- **Descrição:** Ligue o DualShock 4 pelo cabo USB ou pareie por Bluetooth.
- **Botão:** Como parear (abre a ajuda)
- **Onde:** página Status.

### `waiting-game.svg` — vazio
- **Desenho:** controle azul esmaecido, barra de luz cinza e ondas de som pontilhadas ainda apagadas;
  selo azul com ampulheta.
- **Texto alternativo:** "Aguardando o jogo"
- **Título:** Aguardando o RPCS3
- **Descrição:** Abra um jogo no RPCS3 e o som vai para o controle automaticamente.
- **Botão:** nenhum.
- **Onde:** página Áudio, quando o espelhamento está ligado mas não há stream do RPCS3.

### `empty-list.svg` — vazio
- **Desenho:** dois cartões de lista apagados e, acima, um cartão tracejado azul com selo ＋.
- **Texto alternativo:** "Lista vazia"
- **Título:** depende da lista: *Nenhum app extra* / *Nenhum perfil ainda*
- **Descrição:** *Só o RPCS3 vai para o controle. Adicione outros apps se quiser.* /
  *Crie um perfil para mudar volume e vibração por jogo.*
- **Botão:** ＋ Adicionar
- **Onde:** Áudio → Apps espelhados; Perfis (v0.4).

### `bluetooth-no-audio.svg` — aviso
- **Desenho:** controle azul normal, selo Bluetooth à esquerda e selo amarelo com alto-falante mudo
  à direita.
- **Texto alternativo:** "Bluetooth sem áudio no controle"
- **Título:** Som no controle precisa do cabo
- **Descrição:** Por Bluetooth o Linux ainda não envia áudio para o DualShock 4. Vibração, luz e bateria
  continuam funcionando.
- **Botão:** Saiba mais (abre [AUDIO.md](../guia/AUDIO.md#cabo-usb--bluetooth))
- **Onde:** página Áudio, no lugar dos controles de volume.

### `no-permission.svg` — aviso
- **Desenho:** controle azul com selo amarelo de cadeado.
- **Texto alternativo:** "Sem permissão"
- **Título:** Sem acesso ao controle
- **Descrição:** A regra de permissão ainda não valeu. Desconecte e conecte o controle de novo.
- **Botão:** Tentar de novo
- **Onde:** Status e Vibração, quando abrir o `hidraw` falha com `EACCES`.

### `service-stopped.svg` — erro
- **Desenho:** engrenagem cinza parada com selo vermelho de "parar" (■).
- **Texto alternativo:** "Serviço parado"
- **Título:** Serviço parado
- **Descrição:** O ds4-companiond não está rodando, então o som e a vibração não são ajustados.
- **Botão:** Iniciar serviço (`systemctl --user start ds4-companion.service`)
- **Onde:** janela inteira, quando a GUI não acha o serviço no D-Bus.

### `error.svg` — erro
- **Desenho:** contorno tracejado de controle com um selo vermelho grande de exclamação no centro.
- **Texto alternativo:** "Erro"
- **Título:** Algo deu errado
- **Descrição:** mensagem curta do erro, sem jargão. O detalhe técnico vai para o journal.
- **Botões:** Tentar de novo · Ver logs
- **Onde:** qualquer página, como último recurso.

### `all-set.svg` — sucesso
- **Desenho:** controle azul com barra de luz acesa, ondas de som azuis dos dois lados e selo verde ✓.
- **Texto alternativo:** "Tudo pronto"
- **Título:** Tudo pronto
- **Descrição:** O som do jogo vai tocar na sua saída de áudio e no controle ao mesmo tempo.
- **Botão:** Começar
- **Onde:** última tela da primeira configuração.

## Uso no GTK4/libadwaita

```python
page = Adw.StatusPage(
    paintable=Gdk.Texture.new_from_resource(
        "/<app-id>/illustrations/no-controller.svg"),  # via GResource
    title=_("Nenhum controle conectado"),
    description=_("Ligue o DualShock 4 pelo cabo USB ou pareie por Bluetooth."),
)
```

- Carregar pelo GResource; o caminho segue o app ID, que ainda não foi definido.
- `Gdk.Texture` rasteriza o SVG. Para ficar nítido em telas HiDPI, carregar no tamanho final
  × fator de escala (ou usar `Rsvg`).
- O texto alternativo vai em `accessible-label` do widget da imagem.

## Nova ilustração

1. Copiar a ilustração mais parecida e trocar só o objeto e/ou o selo.
2. Usar só os tokens da [paleta](DESIGN.md#paleta).
3. Conferir no fundo preto em 96 px e em 200 px.
4. Otimizar com `scour` ou `svgo`.
5. Adicionar uma linha no catálogo e uma seção em *Descrições e textos*, no mesmo PR.

## Referências

- [libadwaita — AdwStatusPage](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.StatusPage.html)
- [SAP Fiori — Designing for empty states](https://www.sap.com/design-system/fiori-design-web/v1-136/foundations/best-practices/global-patterns/designing-for-empty-states)
- [Primer — Empty states](https://primer.style/ui-patterns/empty-states)
- [Unity — Empty states](https://unityeditordesignsystem.unity.com/patterns/empty-states)
- [Dynatrace Barista — Empty states](https://barista.dynatrace.com/patterns/empty-states)

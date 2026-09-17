# Contrato da v2b — identidade visual

> Escrito ANTES de qualquer CSS (princípio 1). Célula "Painel v2b", 26/08/2026.
> Série **I** (de Identidade). As séries G (grafo/layout) e V (painel v1) seguem válidas
> e verdes: a v2b **não toca layout nem modelo** — só como as coisas aparecem.

## A pergunta

**A página fica bonita o bastante para ficar aberta o dia todo — sem que a beleza
apague a informação?**

O risco de uma célula de estética é decorar até a leitura piorar. Por isso a maior parte
dos critérios aqui não mede beleza (impossível): mede que a informação **continua
verdadeira e legível** depois do enfeite.

## Fronteira de verificação — declarada, não escondida

| Parte | Quem verifica |
|---|---|
| tokens, contraste, uma-fonte-de-cor, markdown, mono | **máquina** (I1–I6 + mutação) |
| se ficou bonito | **olho humano** — e só ele |

## Os tokens (fonte única, exportada e testável)

```
fundo        #0b0d14      superfície  #12141d      borda    #232838
texto        #e8eaf2      secundário  #9aa3bb      terciário #6b7490
ACENTO       #7c5cff      (violeta — o único acento da casa)
✔ #3ddc97    🔵 #4aa8ff   ⏸ #f5a524   📋 #8892ab
```

Os quatro estados e o acento vivem em **um só lugar** e alimentam CSS, SVG 2D e cena 3D.
Duplicar a tabela é como as vistas divergem — foi o que G10 já provava para o grafo, e
I1 estende para a página inteira.

## Os 6 critérios de aceite (mecânicos)

### I1 · uma fonte de cor para a página inteira
```
TOKENS.estado[s] === CORES[s]  para os 4 estados   (grafo e página não divergem)
o CSS e o SVG não contêm hex de estado fora de TOKENS
```
**Vermelho sem o conserto:** um `#3b82c4` esquecido no CSS e a bolinha da contagem deixa
de ser a mesma cor do nó.

### I2 · contraste que sobrevive a olho cansado
```
texto, secundário e os 4 estados contra o FUNDO  →  contraste ≥ 4.5:1  (WCAG AA)
terciário e bordas                               →  ≥ 3:1   (elemento gráfico)
```
Calculado, não estimado: luminância relativa sRGB.
**Vermelho sem o conserto:** cinza bonito de mockup que ninguém lê às 23h.

### I3 · markdown cru das listas resolvido — e a alma intocada
```
'**a alma**: ...'  na lista  →  <strong>a alma</strong>
'`packages/x`'     na lista  →  <code>packages/x</code>
o PRÓXIMO PASSO continua LITERAL, caractere por caractere (V2 segue verde)
```
**Vermelho sem o conserto:** ou os asteriscos aparecem, ou a frase exata da alma quebra.
A alma é literal por decisão da v1 — beleza nenhuma justifica mexer nela.

### I4 · monoespaçada só para caminho e chave
```
<code> aparece em .area e nas chaves do painel lateral
NUNCA no próximo passo, no nome da célula ou no corpo
```

### I5 · um acento, não uma feira
```
o CSS tem no máximo UM matiz fora da paleta de estado + neutros
```
**Vermelho sem o conserto:** ciano no botão, violeta no card, azul no link — três casas.

### I6 · hexágono, não disco
```
cada nó do SVG 2D é um <polygon> de 6 vértices
continuam 19 nós e 39 arestas — a estética não come informação
```

## Veredito

*(a preencher no fechamento: escopo declarado, resultado, e a varredura formal de
mutação — uma por critério, como na v1, v1-grafo e v2a.)*

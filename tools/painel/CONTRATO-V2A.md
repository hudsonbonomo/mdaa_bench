# Contrato da v2a — grafo 3D com layout no servidor

> Escrito ANTES de qualquer linha de cena (princípio 1). Célula "Painel v2a", 25/08/2026.
> Série **G8–G13**: continua a G da v1-grafo, porque é o MESMO modelo ganhando uma
> projeção a mais. A série G1–G7 e a V1–V6 seguem válidas e verdes — zero retrabalho.

## A pergunta

**O 3D mostra a mesma verdade que o 2D, ou vira um segundo desenho que diverge do primeiro?**

A resposta estrutural é a emenda da caneta: **a cena não calcula nada.** `grafo.mjs`
computa posições, curvas e cores; o cliente recebe JSON e desenha. Não existe segundo
parser nem segundo layout — existe uma fonte e duas projeções.

## Fronteira de verificação — declarada, não escondida

| Parte | Quem verifica |
|---|---|
| `modelo3d()` — posições, curvas, cores, determinismo | **máquina** (G8–G10, varredura de mutação) |
| `/modelo.json` e o vendor servido offline | **máquina** (G11, G13) |
| o mapa real: 18 nós, 39 arestas, 8 colunas | **máquina** (G12) |
| cena, materiais, brilho, hover, foco, rótulos virados | **olho humano** — declarado |

Isto é o oposto de "os testes passam": diz exatamente o que está coberto e o que não está.

## Decisões pré-comprometidas

1. **Zero rede em runtime.** three.js vendorizado e pinado; a página não pode conter
   nenhuma URL externa. G13 verifica.
2. **Pin `three@0.180.0`**, obtido por `npm pack`, com `vendor/VENDOR.md` declarando
   versão, origem, data e SHA-256. Atrito com OrbitControls → reportar e repinar.
3. **O 2D é intocado.** O toggle escolhe a vista; `localStorage` guarda a escolha.
   Sem preferência salva, abre em 2D — é a vista já provada.
4. **Layout determinístico**, sem física: mesma entrada, mesmo JSON, byte a byte.

## Layout 3D — as regras exatas (v2, caneta de 25/08 depois do primeiro olhar)

> A v1 do layout usava Z como três faixas rasas (±70) que só davam relevo. **Girar
> embaralhava em vez de revelar.** Agora o Z carrega significado.

- **X = coluna**: `x = índiceDaColuna × 300`. Blocos A–H na ordem.
- **Z = CAMADA TOPOLÓGICA**, centrada: `z = (camada - maiorCamada / 2) × 800`.
  (Era 420. Medido: com 420 o conteúdo ocupava **46% da vertical** da tela — o grafo
  projeta largo e baixo, e encaixar a largura sobrava altura. Aprofundar as camadas
  enche a tela E separa mais as camadas: as duas coisas de uma vez.)
  `camada` = maior caminho seguindo `injeta`. **Raiz** (pacote que não injeta ninguém)
  = camada 0, no **fundo**; quem injeta mais fundo vai para a **frente**. Girar a cena
  passa a revelar a estrutura de dependência.
  **Ciclo não trava**: o cálculo protege contra recursão e o modelo declara `temCiclo`
  — camadas seguem determinísticas, mas o número perde sentido topológico e isso fica
  dito, não escondido.
- **Y = desempate dentro da célula (bloco, camada)**: para o nó `i` de `n` na mesma
  célula, `y = ((n - 1) / 2 - i) × 120`. É o que impede sobreposição quando dois
  pacotes do mesmo bloco estão na mesma camada.
- **Arestas** = Bézier quadrática amostrada em **16 pontos**, arqueando em Y:
  controle = ponto médio + `(0, 150, 0)`. O ponto 0 é a posição da origem e o ponto 15
  é a do destino — a curva fica **ancorada nos nós**, nunca solta. (Arqueia em Y, não
  em Z, porque agora o Z significa camada e curvar nele mentiria sobre a topologia.)
- **`dependentes`** = quantos pacotes injetam este. É a hierarquia visual: mais
  dependentes → caixa maior e mais clara. Vem do servidor, é testável.
- **`limites`** = caixa envolvente do modelo, calculada no servidor. É o que permite o
  **fit-to-bounds** da câmera sem a cena adivinhar nada.
- **Cor** vem do mesmo mapa do 2D (`✔` verde · `🔵` azul · `⏸` âmbar · `📋`/sem célula
  cinza). Uma fonte de cor para as duas vistas.

## Escopo de resposta declarado ANTES de rodar

**Fixture `mini-mapa`** (3 pacotes, 2 colunas, e **um ciclo de propósito**:
kernel→outros→store→kernel — exercita a proteção):

| nó | bloco | camada | posição esperada | cor |
|---|---|---|---|---|
| `mini-kernel` | A | 3 | `[0, 0, 1200]` | `#2f9e6a` (✔) |
| `mini-store` | A | 1 | `[0, 0, -400]` | `#3b82c4` (🔵) |
| `mini-outros` | B | 2 | `[300, 0, 400]` | `#3a4049` (sem célula) |

- `temCiclo: true` · arestas: **3**, cada uma com **16 pontos**, extremos ancorados
- `JSON.stringify(modelo3d(g))` idêntico em duas execuções

**Mapa real do edtech-nll:** 18 nós · 39 arestas · 8 colunas · **6 camadas, zero ciclos**
· x de 0 a **2100** · z de **-2000 a 2000** · camada 0 = `nll-kernel` sozinho no fundo ·
camada 5 = `nll-learning` sozinho na frente · zero pares de nós na mesma posição.

## Câmera — a pose inicial tem de ser legível sozinha

- **Ortográfica**, não perspectiva: nó da direita não pode virar formiga.
- **Pose inicial quase frontal ao plano A→H**, elevada **15°** (`teta = 0`, `fi = 75°`).
- **Fit-to-bounds calculado dos `limites` do modelo**, nunca posição fixa: o grafo
  inteiro cabe na tela ao abrir.
- **R** volta exatamente a esta pose.
- Rotação, zoom e pan são do usuário — a pose inicial é só o ponto de partida legível.

## Os 6 critérios de aceite (mecânicos)

### G8 · posições determinísticas, sem sobreposição
```
modelo3d(fixture).nos  →  as 3 posições exatas da tabela acima
nenhum par de nós compartilha [x,y,z]   (vale também no mapa real, 18 nós)
duas execuções → JSON idêntico
```
**Vermelho sem o conserto:** Y constante na coluna empilha dois nós no mesmo ponto.

### G9 · arestas ancoradas e curvas
```
cada aresta tem 16 pontos
pontos[0]  === posição do nó de origem
pontos[15] === posição do nó de destino
o ponto do meio NÃO está na reta origem→destino (a curva arqueia)
```
**Vermelho sem o conserto:** com controle no ponto médio a curva vira reta e o meio cai
na linha.

### G10 · uma fonte de cor para as duas vistas
```
cor de cada nó no modelo 3D === cor do mesmo nó no SVG 2D
```
**Vermelho sem o conserto:** tabela de cores duplicada no 3D — as vistas divergem.

### G11 · o modelo trafega como JSON puro
```
GET /modelo.json → 200, application/json
JSON.parse(corpo) reproduz o modelo sem perda (números, não strings)
```
**Vermelho sem o conserto:** Map ou undefined no modelo viram `{}`/sumiço na serialização.

### G12 · realidade — o mapa do edtech-nll
```
18 nós · 39 arestas · 8 colunas · x máximo 1820
e a série G1–G7 + V1–V6 continuam verdes (o 2D não foi tocado)
```

### G13 · offline de verdade
```
a página servida não contém nenhuma URL externa (sem //cdn, sem https://)
GET /vendor/three@0.180.0/three.module.js → 200, javascript
```
**Vermelho sem o conserto:** um `<script src="https://…">` faz o painel depender de rede.

## Veredito — 25/08/2026 ✔

**Funciona:** o layout inteiro é computado no servidor e medido em node; a cena só
desenha. Rodei contra a fixture (posições exatas) e contra o mapa real do edtech-nll
(18 nós · 39 arestas · 8 setores · 6 anéis · zero ciclos), e provei o vermelho de cada
critério por mutação.

**Gates:** painel **52/52** · repo intacto: `tsc --noEmit` limpo + 17/17 no vitest.

**Varredura formal: 11 mutações, 11 vermelhas no critério certo, ZERO fracas.**

| | Mutação | Vermelho observado |
|---|---|---|
| G8 | tira o `Math.round` das posições | posições exatas da fixture quebram |
| G8 (2ª) | apaga os DOIS desempates da célula | dois nós ocupam o mesmo ponto |
| G8b | `z = 0` para todos | some a ordem frente/fundo das 39 arestas |
| G8c | ignora o índice do bloco no ângulo | nós caem fora do seu setor de 45° |
| G9 | controle da Bézier no ponto médio | a curva vira reta |
| G10 | cor fixa no 3D | as duas vistas divergem |
| G10b | não conta `dependentes` | hierarquia visual some |
| G11 | `/modelo.json` em `text/plain` | o modelo deixa de trafegar como JSON |
| G11b | `listaChaves: []` | o painel lateral não teria o que listar |
| G12 | `R_ANEL` 460 → 500 | o anel externo sai do escopo declarado |
| G13 | `<script src="https://…">` na página | o painel passa a depender de rede |

**Achado de método:** a primeira mutação de G8 (tirar o `Math.round`) ficou vermelha,
mas **só exercitou um dos dois mecanismos do critério** — posições exatas. A ausência de
sobreposição seguia não provada. Precisou de uma 11ª mutação, apagando os dois
desempates, para ela ficar vermelha. **Lição: critério com dois mecanismos precisa de
duas mutações — vermelho no nome do critério não é vermelho no mecanismo.**
É irmã da lição da v1 (mutação fraca dá falso verde), numa variante mais sutil: aqui a
mutação era forte, mas mirava só metade do alvo.

**Fronteira de verificação, honrada:** cena, materiais, hover e câmera continuam
verificados por olho humano — e foi o olho que achou os quatro acabamentos da última
rodada (rótulos empilhados, enquadramento frouxo, setores invisíveis, caixas viradas
lascas). Máquina nenhuma aqui teria pego isso.

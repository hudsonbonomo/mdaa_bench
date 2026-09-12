# Estado da célula — `ensemble-e-gates-h1-h4`

Data: 2026-09-11. Escopo executado na ordem pedida. Registro dos comandos rodados,
dos resultados e das decisões que se afastaram do escopo (com o motivo).

---

## Aprovações

```
Grade reduzida aprovada por Hudson em: ____________
```

A grade reduzida está **preparada e NÃO executada** (regra 5 do Modo Celular). O comando
exato está no README, seção "Grade reduzida". Só rodar quando a data acima estiver
preenchida.

---

## Etapa 1 — gate N com nulo de Wiener

**Arquivo novo:** `sim/wiener.py`. O surrogate linear continua; o segundo nulo é
dinâmica linear latente (o espaço de estados) + não linearidade estática de saída
`h` ajustada (tanh com escala livre ou cúbico, o que ajustar melhor). N só ativa se
o ganho superar o q95 dos **dois**. `Fit.hardest["N"]` registra qual venceu.

Comandos e resultados:

```
# linha de base antes da mudança (só nulo linear), M1 observado por tanh, T=600, ruído 0.05
N ativa 1/6 — mas a semente que ativa tem ganho +0.401 contra nulo linear de +0.008

# depois (dois nulos), mesmas sementes
python -m pytest -q tests/test_gates.py -k wiener
CONDIÇÃO A  M1 + tanh:      N ativa 1/6   (alvo: >=5/6 não ativam)  ✔
CONDIÇÃO B  M1+N + h linear: N ativa 4/6  (alvo: continua ativando)  ✔
nulo de Wiener foi o vinculante em 12/12 casos das duas condições
```

Custo de poder: **zero**. Nas mesmas 6 sementes de M1+N o nulo linear sozinho também
daria 4/6 — o nulo de Wiener ficou abaixo dos ganhos reais em todos os casos que
importavam, e subiu a barra de 0.008 para 0.224 exatamente onde havia falso alarme.

Duas correções de robustez necessárias no caminho: o `h` cúbico só é identificado no
suporte observado de `z` (sem clipping o nulo ia a −22), e `_gain_fn` agora devolve
`nan` em entrada não finita.

---

## Fora de escopo, mas bloqueante: bug de divergência no gerador `M1+N`

Encontrado ao investigar um nulo de Wiener que explodia. **Não era o nulo.**

O drift de `M1+N` é `A x + alpha*(tanh(3 x0) - x0)`. Longe da origem o tanh satura,
então o mapa lineariza para `(A - alpha e0 e0')`, **não** para `A`. Sortear `A` estável
portanto não estabilizava o nó.

```
11/60 sementes (18%) divergiam; semente 4: |x|max = 7.2e78, rho(A - alpha e0e0') = 1.461
```

Silencioso do v0 ao v1 porque as 8 células de `M1+N` da grade de 32 publicada não
pegaram nenhuma semente ruim (**0/8** — os números v1 publicados não estão contaminados).
A grade reduzida (reps=5) e a completa (reps=20) pegariam ~18%.

Correção: deslocar `A` para que a matriz de **campo distante** seja o sorteio estável
(`A = A_estável + alpha e0e0'`). Perto da origem o tanh ainda contribui `+2*alpha*x0`,
que é o que abre o poço.

```
depois: 0/120 sementes divergem nos 4 nós; poço duplo preservado (cruzamentos de sinal em 6/6)
testes: test_no_generator_diverges, test_double_well_is_still_bistable
```

---

## Etapa 2 — gate M sobre espaço de estados (resultado NEGATIVO)

**Arquivo novo:** `sim/memory.py`. `sim/statespace.py` generalizado para latente > d
(C = [I 0]; com n = d a matemática é idêntica, reprodutibilidade v1 verificada).

Contest implementado como pedido: kernel de memória (AR(p) companion com ruído de
medida, latente p·d) contra o melhor espaço de estados livre de dimensão d+k, k ∈ {1,2},
ambos cientes de faltantes, pontuados um passo à frente no mesmo bloco futuro. AR(6) em
corridas consecutivas rebaixado a diagnóstico (`gain_M_diag_vs_AR1`, `gain_M_diag_vs_SS`).

**As duas condições exigidas NÃO foram atingidas.** Medições (T=600, 6 sementes):

```
M1   keep=0.5 ruído=0.3  -> M dispara 2/6   (alvo: 0/6)
M1+M keep=0.7 ruído=0.05 -> M dispara 1/6   (alvo: >=3/6)
M1+M keep=1.0 ruído=0.05 -> M dispara 0/6
```

Antes de aceitar isso como "mal implementado", rodei um **oráculo**: o modelo de memória
com o kernel VERDADEIRO e os parâmetros de ruído verdadeiros, contra o mesmo baseline.

```
ORÁCULO, ganho sobre o melhor SSM livre d+k:
  keep=1.0 ruído=0.05: [0.029, 0.039, 0.064, 0.076] -> dispararia 3/4
  keep=0.7 ruído=0.05: [-0.004, -0.003, 0.040, 0.110] -> dispararia 2/4
  keep=1.0 ruído=0.30: [0.031, -0.004, 0.017, 0.025] -> dispararia 1/4
```

Ou seja: **o teto é 0–11% com TOL de 3%**, e a condição "≥3/6 em keep 0.7" está acima do
que o oráculo entrega (2/4 = 50%). Enquanto isso, o piso de ruído de estimação medido na
mesma montagem é **±0.14** num mundo sem memória nenhuma. O efeito é uma ordem de
grandeza menor que o ruído do contest.

Quatro tentativas de fechar a lacuna, todas registradas no código:
1. warm start do companion por regressão de lags (recuperou a forma do kernel:
   perfil ajustado `[·, 0.134, 0.055, 0.040, 0.038, 0.025]` vs verdadeiro
   `[·, 0.195, 0.098, 0.049, 0.024, 0.012]` — decaimento monotônico, ordem certa);
2. prior de decaimento declarado `LAG_PENALTY * (j+1)^2` (parte da classe declarada
   "kernel decrescente", não um botão);
3. projeção de estabilidade do companion (semente 3 estava em raio 0.9912);
4. nulo de Markov calibrado (`markov_null`) — **não resolve**: ele simula de um SSM já
   bem ajustado, então não reproduz a desvantagem de ajuste que o modelo livre sofre
   nos dados reais;
5. warm start simétrico para os dois competidores — derrubou o falso alarme de 5/6 para
   2/6, que é o estado atual.

**Conclusão registrada:** o eixo M não é decidível por disputa de predição entre duas
classes de modelo de dimensão e regularização tão diferentes. O gate foi entregue como
especificado, calibrado pelo nulo, e o README diz explicitamente que ativações de M não
devem ser confiadas em v2. Isso alimenta diretamente a etapa 3: H3 é o mesmo contest,
mas sobre réplicas.

---

## Etapa 3 — ensemble e gates H1–H4

**Arquivos novos:** `sim/ensemble.py`, `sim/density.py`, `tests/test_density.py`.

`generators.py` ganhou dois parâmetros opcionais, ambos preservando a reprodutibilidade
v1 quando omitidos: `noise_seed` (separa o fluxo ESTRUTURA de A/B/u do fluxo REALIZAÇÃO)
e `offset` (constante no drift, move o ponto fixo).

Modo `between`: a dispersão tem duas partes, e só a segunda quebra o pooling. Dispersão
de **forma** (A sorteado em torno de A médio, renormalizado ao mesmo raio espectral)
deixa toda densidade centrada em zero — pooling segue inócuo por maior que seja o raio.
Foi preciso dispersão de **localização** (pontos fixos distintos) para produzir o caso a
que Molenaar objeta. O ponto fixo é especificado direto e a constante é resolvida,
`off = (I - A_i) m_i`: injetar a constante põe o ponto fixo em `(I-A_i)^-1 off`, que
explode quando `(I-A_i)` fica quase singular — uma trajetória foi parar em −30.8 e
dominou a densidade agrupada.

Resultados (N=30, T=400, ruído 0.05):

```
H1  modo within        : passa (instab 0.036)
    between raio 0.15  : passa (instab 0.072, separação de modos 0.20)
    between raio 0.30  : FALHA por bimodalidade (separação 4.66)
    between raio 0.60  : FALHA (6.44)
    between raio 0.90  : FALHA (14.00)
H2  M1 / M1+N / M1+H / M1+M: passa (razão de escalas 1.51–2.16, limite 10)
H3  M1   : PASSA, ganho médio -0.192  (por trajetória: -0.13 a -0.27)
    M1+M : FALHA, ganho médio +0.049  (por trajetória: +0.027 a +0.080)
    -> separação perfeita, sem sobreposição: max(M1) < min(M1+M)
H4  M1 +0.592 / M1+N +0.862 / M1+H +0.395 / M1+M +0.230 : todos passam
    controle negativo (deriva por trajetória, caixa compartilhada): -0.014, falha ✔
```

**O achado da célula:** o mesmo contest que é indecidível numa trajetória (etapa 2,
±0.14 de ruído contra efeito ≤0.11) separa os dois mundos **sem sobreposição** sobre
réplicas da mesma pessoa. As réplicas são a saída, exatamente como os achados 2 e 4 do
v1 previam.

H4 precisou de margem declarada (`H4_MARGIN = 0.05`): o competidor não local emite uma
deriva por janela contra uma por célula do campo local, então empate é o nulo honesto.
O primeiro controle negativo que escrevi (passeio aleatório sob empurrão global) **passou**
H4 — num passeio não limitado a posição codifica o tempo decorrido, então o campo local
vira relógio e prediz legitimamente. A caixa refletora é o que remove isso.

---

## Prova de que os testes não são vazios (mutação)

Cada gate foi substituído por um stub trivial e o teste correspondente foi rodado:

```
python C:/Users/hudso/AppData/Local/Temp/mutation.py

  H1                 stub aplicado -> VERMELHO (bom)
  H2                 stub aplicado -> VERMELHO (bom)
  H3                 stub aplicado -> VERMELHO (bom)
  H4                 stub aplicado -> VERMELHO (bom)
  wiener-null        stub aplicado -> VERMELHO (bom)
  gerador-estavel    stub aplicado -> VERMELHO (bom)
```

---

## Grade de 32 com os gates v2

```
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --reps 2 --jobs 12 --out out_smoke_v2
```

Por eixo, dispara quando plantado / quando ausente (v1 -> v2):

```
N: 0.25 -> 0.25 | 0.00 -> 0.00      nulo vinculante: wiener 23/29, linear 6/29
H: 0.38 -> 0.38 | 0.04 -> 0.04      (medianas: wiener q95 0.022, linear q95 0.008)
M: 0.13 -> 0.13 | 0.04 -> 0.04      gain_M mediana -0.007, nulo q95 +0.005
S: 0.56 -> 0.56 | (sem mundo não estocástico nesta grade)
```

Por nó (exact / spurious): M1 0.88/0.13 igual; **M1+N 0.13 -> 0.25 exact e 0.13 -> 0.00
spurious**; M1+H 0.38/0.00 -> 0.38/0.13; M1+M 0.13/0.00 igual.

Três ressalvas registradas no README e repetidas aqui:
1. a linha M1+N mudou porque os **dados** mudaram (correção da divergência), não só o gate —
   não dá para atribuir a melhora ao nulo de Wiener isoladamente;
2. as taxas de N são idênticas porque esta grade roda só com `nonlinear_h=0`, ou seja, não
   exercita o confundidor que o nulo de Wiener existe para pegar — o resultado relevante está
   no controle de 6 sementes com tanh;
3. as taxas de M são idênticas **por coincidência**: a estatística por trás mudou
   inteiramente (contest latente vs AR), duas medidas diferentes caindo em 1/8 e 1/24.

---

## Suíte de testes (final)

```
python -m pytest -q tests/test_smoke.py     ->  4 passed in  8.89s
python -m pytest -q tests/test_gates.py     -> 10 passed in 91.18s
python -m pytest -q tests/test_density.py   -> 10 passed in 24.71s
                                               24 testes, ~2 min no total
```

Os cinco testes mais lentos são os dois do nulo de Wiener (27.3s e 26.0s, 6 chamadas a
`identify()` a T=600 cada), o do gate S (10.7s), o do achado 1 (8.9s) e o do gate H (7.7s).

Um teste precisou ser corrigido nesta célula: `test_m_gate_is_not_fooled_by_measurement_noise`
referenciava `gains["M_vs_AR1"]`, chave renomeada para `M_diag_vs_AR1` quando o AR(6) virou
diagnóstico. A asserção substantiva do teste (M não dispara) continua valendo: **0/6** em
M1 com ruído 0.3 sob o gate v2.

---

## Nota de custo

`identify()` agora tem dois bootstraps caros ligados por padrão (`s_null`, `m_null`). Um run
v2 completo custa ~60 ajustes EM; a grade de 32 levou ~7 min com `--jobs 12`. Os testes
passam `s_null=False, m_null=False` exceto onde o nulo é o objeto do teste — sem isso a
suíte passa de 2 min para mais de 20.

---

## Um teste antigo que o terceiro nulo quebrou

A suite acusou uma falha, em `test_wiener_null_blocks_nonlinearity_made_by_the_observation_map`.
Ela e anterior a esta celula e dizia duas coisas que o terceiro nulo tornou falsas
pela forma, nao pelo conteudo:

```
assert fit.gains["N_null_q95"] == max(linear_q95, wiener_q95)      # faltava o terceiro
assert bound_by_wiener >= 5                                        # o de chaveamento tambem vincula
```

Na semente que falhou: linear -0.004, Wiener 0.015, chaveamento 0.076. O gate estava
certo; a assercao e que ainda contava dois nulos.

A correcao nao relaxa nada. A primeira linha passou a incluir o terceiro nulo, e a
segunda foi trocada pela alegacao que o teste sempre quis fazer, agora dita direto:
**o nulo linear nunca pode ser o vinculante num mundo cuja nao linearidade mora em h.**
`bound_by_linear == 0` e mais estrito que o `>= 5` antigo, que tolerava uma semente
vinculada pelo linear. Qual dos dois nulos honestos vincula varia por semente e nao e
a questao. Verificado: 0/6.

## Estacionamento

**Célula 6 (agente LLM como `h`) — não aberta, por decisão.** O achado 5 do v1 e a etapa 1
desta célula mudam o papel dela: um agente LLM não é um gerador de dinâmica, é um `h`
que ninguém consegue escrever. Ele nasce como **adversário do gate N** — o nulo de Wiener
desta célula é exatamente a defesa que precisa ser testada contra um `h` não paramétrico
e possivelmente não monotônico (o nulo assume monotonicidade ao construir `z` por posto).
Abrir a célula 6 antes disso seria testar a defesa e o ataque ao mesmo tempo.

**Dívidas registradas:**
- gate M: ou aceitar que é indecidível em trajetória única (posição atual do README), ou
  refazer o contest com as duas classes igualadas em dimensão e regularização — o que
  provavelmente significa comparar `d+k` contra `d+k` com estruturas diferentes, não
  `d+k` contra `p·d`;
- H3 usa no máximo 8 trajetórias (`H3_MAX_TRAJ`), cada uma custa 3 ajustes EM; o corte
  está declarado na nota de parada do gate;
- o nulo de Wiener gaussianiza por posto, o que assume `h` monotônico. Um `h` não
  monotônico escapa.

---
---

# Célula `boundedness-loc-radius-tri-estado`

Data: 2026-09-11. Escopo executado na ordem pedida.

## Aprovações

```
Grade reduzida aprovada por Hudson em: ____________   (AINDA VAZIA -> não rodada)
```

Etapa 5 **não foi executada**. A linha acima segue vazia, então a grade reduzida ficou
apenas preparada: comando exato no README e em `PREREGISTRO_v1.md`. As duas figuras que ela
deve produzir foram implementadas e verificadas em dados já existentes (`recovery_map_v2`
sobre `out_smoke_v2/`, `h3_separation` sobre dois ensembles de 30 réplicas), de modo que
"comando pronto" seja verdade e não promessa.

## Etapa 1 — boundedness como invariante

`tests/test_boundedness.py`: 120 sementes × 4 nós × 2 níveis de ruído de processo, T=800,
falha se `max|x| > 50` ou se aparecer NaN/inf; mais a condição ESTRUTURAL de cada nó,
registrada em comentário de uma linha acima de cada corpo em `generators.py`.

**O teste achou um segundo gerador quebrado.** Em `M1+M`, o polinômio característico vale
`1 = rho(0.5A) + sum(kernel)` em `z = 1`, e os dois termos estavam fixos em 0.45 e 0.55:

```
z = 1 é raiz exata sempre que 0.5A tem autovalor dominante real
-> 60 de 200 sementes (30%) eram passeios aleatórios integrados, não memória estacionária
-> não estouram como o M1+N; só derivam. Em T=800 só 1/200 passava de |x| = 50.
```

Correção: manter a FORMA do kernel (0.5^k) e resolver a MASSA por bisseção para que o raio
do companion caia em `rho` = 0.9.

```
massa: 0.55 -> 0.70 (semente 0);  raio do companion sobre 60 sementes: [0.7987, 0.9000]
|x|max sobre 4 nós × 40 sementes em T=800: 8.9
kernel segue decaindo monotonicamente, k[0]/k[-1] > 50
```

Prova de não-vacuidade (não há git aqui, então por stub temporário):

```
python C:/Users/hudso/AppData/Local/Temp/mutation_bound.py
  M1+N antigo (sem deslocar A)     -> VERMELHO (bom)  3 failed, 7 passed
  M1+M antigo (massa fixa 0.55)    -> VERMELHO (bom)  3 failed, 7 passed
```

Achado de percurso: `generate` estourava com erro ilegível do numpy para T < 24. Agora tem
asserção explícita.

## Etapa 2 — dispersão de localização separada

`generate_ensemble` trocou `spread` por dois raios independentes: `A_radius` (como as
pessoas se movem) e `loc_radius` (onde ficam — ponto fixo sorteado uniformemente numa bola,
dinâmica em `x - x*`, constante resolvida como `off = (I - A_i) x*`).

H1 passou a reportar, além da bimodalidade, a estatística de Molenaar propriamente dita:
variância ENTRE pessoas sobre variância INTRA. Critério declarado: `H1_BETWEEN_WITHIN = 1`.

```
A_radius=0.9  loc_radius=0.0  -> H1 passa, entre/intra = 0.008
A_radius=0.5  loc_radius=0.0  -> H1 passa, entre/intra = 0.018
A_radius=0.0  loc_radius=0.3  -> H1 passa, entre/intra = 0.106
A_radius=0.0  loc_radius=1.0  -> H1 FALHA, entre/intra = 1.123
fronteira por bisseção: 0.973 / 0.652 / 0.711 / 1.005 (sementes 0-3), mediana ~0.84
```

**Divergência do escopo, registrada.** O escopo esperava H1 falhando em `loc_radius >= 0.3`.
Sob o critério declarado a fronteira fica em ~0.84, não 0.3, porque `loc_radius` está em
unidades de estado e o desvio-padrão intra-pessoa é ~0.5: uma bola de raio r em d=2 tem
variância r²/4 por coordenada, então r ≈ 0.3 dá razão ≈ 0.1, não 1. Não ajustei o limiar
para acertar o 0.3 — o número medido é o entregável, como o próprio escopo pede
("fronteira registrada como número"). Os testes usam 0.30 (passa) e 1.50 (falha), ambos
longe da banda 0.65–1.01.

## Etapa 3 — eixo M tri-estado

`Fit.verdicts` com `passa` / `falha` / `nao identificavel`; `GateResult` idem, para todos os
gates. `identify()` aceita `Observed` ou lista de `Observed` da mesma pessoa.

```
trajetória única M1+M       -> nao identificavel   (contest segue reportado como diagnóstico)
ensemble 30 réplicas M1+M   -> passa               (H3 média +0.067)
ensemble 30 réplicas M1     -> falha               (H3 média -0.192)
ensemble 4 réplicas         -> nao identificavel   (MIN_REPLICATES = 10)
margem entre as duas nuvens de ganhos: 0.157, sem sobreposição
```

`recovery.py` ganhou coluna `undecided` e `m_verdict`; `missed` deixou de contar um eixo
indecidível como ausente. Consequência medida: **a grade é toda de trajetória única, então o
eixo M é `nao identificavel` em 100% das células.** O mapa deixou de dizer qualquer coisa
sobre memória — que é a versão honesta do que ele vinha fazendo.

Ganho colateral: como o nulo de Markov não pode mudar um veredito já indecidível, ele só
roda sob pedido explícito. Isso devolveu a velocidade que o v2 tinha perdido.

## Etapa 4 — pré-registro

`make_prereg.py` -> `PREREGISTRO_v1.md` (91 linhas), gerado por introspecção dos módulos:
parâmetros de `generate()`, condição de boundedness por nó lida dos próprios comentários,
tabela de gates com tolerâncias lidas das constantes, separação entre prior declarado e
tolerância exploratória, comando da grade, sementes por CRC32.

`tests/test_prereg.py` regenera o documento e falha se o arquivo em disco divergir.

**Proveniência: o diretório não é um repositório git.** O escopo pede hash do commit; não
existe. O documento diz isso e usa SHA-256 sobre os 10 arquivos de `sim/` como substituto,
declarando que identifica o código mas não prova quando foi escrito. Um pré-registro de
verdade precisa do commit — sugiro `git init` antes de rodar a grade.

## Suíte de testes (final)

```
python -m pytest -q tests      ->  58 passed in 158.28s (2m38s)

  tests/test_boundedness.py   13   novo nesta célula
  tests/test_density.py       14   +4 nesta célula (dois raios, veredito tri-estado)
  tests/test_gates.py         14   +4 nesta célula (eixo M tri-estado)
  tests/test_prereg.py        13   novo nesta célula
  tests/test_smoke.py          4   inalterado
```

Os 24 testes anteriores continuam verdes; nenhum precisou de asserção relaxada. Um deles
falhou uma vez no caminho — `test_document_is_regenerated_from_the_code`, porque editei
`sim/recovery.py` (as figuras) depois de gerar o pré-registro. Era o guardião funcionando:
regenerei o documento e passou. O custo é que `make_prereg.py` precisa rodar depois de
qualquer mudança em `sim/`.

---

## Estacionamento

- **Célula 6 (agente LLM como h)** segue fechada, motivo inalterado: o nulo de Wiener
  gaussianiza por posto e portanto assume `h` monotônico. Antes da 6 é preciso um nulo para
  `h` não monotônico.
- **`git init`** antes da grade reduzida, para o pré-registro ter proveniência real.
- **`E.OFFSET_SCALE`** ficou órfão no caminho de `loc_radius`; o pré-registro já o marca
  como resquício.
- **Dois de quatro nós já foram entregues quebrados** (`M1+N` divergente, `M1+M` com raiz
  unitária). Os outros dois passam o invariante hoje, mas o invariante só existe desde esta
  célula — nenhum dos dois foi testado estruturalmente antes.
- `memory.py` continua sendo o candidato a ser dividido, junto com a decisão de consertar
  ou aposentar o contest de trajetória única.

---
---

# Célula `lyapunov-replicas-grade-v3`

Data: 2026-09-11. Escopo executado na ordem pedida.

## Pré-condição

Verificada e **satisfeita**: existe `.git` com 1 commit (`bf7c50e`, "Initial commit",
2026-09-11 10:35 -0300), árvore limpa no início da célula, 55 arquivos rastreados.
Não criei o repositório — ele já estava lá.

## Aprovações

```
Grade reduzida aprovada por Hudson em: ____________   (v2, superada pela v3)
Grade v3 aprovada por Hudson em: 2026-09-11   (preenchida depois; ver célula final)
```

## Etapa 1 — invariante estrutural de M1+H

`sim/stability.py` (novo): função de Lyapunov quadrática **comum**, P ≻ 0 com
`A'PA − P ≺ 0` e `A2'PA2 − P ≺ 0`, que certifica estabilidade sob chaveamento
**arbitrário**. O nó redesenha A2 até existir P.

Duas candidatas foram medidas antes de escolher:

```
condição de Kronecker rho(A1⊗A1 + A2⊗A2) < 1 : aceita  79/200 -> rejeição 60.5%
viabilidade da LMI com P geral               : aceita 162/200 -> rejeição 19.0%
```

A de Kronecker é suficiente mas conservadora demais. Fiquei com a LMI.

Solver sem SDP: o conjunto viável é um cone convexo, então uma grade que refina em
torno do próprio argmin acha o ótimo global. Para d=2 o corte normalizado tem duas
dimensões e λmax de simétrica 2×2 é forma fechada, então tudo vira numpy vetorizado.

```
grade vetorizada vs Nelder-Mead com 6 restarts: concordância 200/200, 7.6 ms/par
  (descida coordenada, descartada: 198 ms/par e perdia 1 par em 200)
taxa de rejeição por sorteio de A2, no gerador: 24.8%
  re-sorteios por nó: média 0.33, máx 7, zero em 80.5% dos nós
custo adicional por trajetória M1+H: 10.2 ms
```

Testes: 200 nós gerados, todos com P re-verificado contra as duas LMIs por
`certifies()` (a busca não é sua própria testemunha); par de cisalhamentos opostos
(ρ(A1)=ρ(A2)=0.9, ρ(A1A2)=26.6) rejeitado; par trivialmente viável aceito;
dimensão ≠ 2 levanta `NotImplementedError` em vez de certificar nada.

## Etapa 2 — dimensão de réplicas

`recovery.py` ganhou `--reps_per_person`. Em 1, comportamento atual. Acima de 1, o
gerador produz réplicas intra-pessoa e `identify()` roda no ensemble.

Custo medido **serialmente** (um processo):

```
T=300: 11.7 s/célula     T=600: 23.6 s/célula
praticamente INDEPENDENTE de reps_per_person
```

O motivo é estrutural e vale registrar: `identify()` ajusta tudo menos o eixo M na
primeira trajetória, e H3 corta em `H3_MAX_TRAJ` = 8. **Logo reps_per_person acima de
8 não muda o que H3 vê** — 10 e 30 diferem só por sortearem pessoas diferentes. Por
isso a grade v3 usa {1, 10} e não {1, 10, 30}.

Vereditos de M por célula (4 nós × 2 T, reps=10):

```
M1   T=300 falha   T=600 falha      M1+N T=300 falha   T=600 falha
M1+H T=300 PASSA   T=600 falha      M1+M T=300 falha   T=600 PASSA
```

Ou seja: **um falso positivo (M1+H em T=300) e um falso negativo (M1+M em T=300)**
em 8 células. A separação limpa do v3 (margem 0.157) foi medida em T=400 com 30
réplicas e uma semente; as taxas reais são o que a grade v3 vai estabelecer.

## Etapa 3 — grade v3 e pré-registro v2

Fatores do escopo dão 4×2×2×2×2×2×3 = **384 runs**, só 26% do orçamento de ~1500.
Usei a folga em repetições de semente (3 → 10) = **1280 runs**, ≈ 3.1 h serial,
porque "anedótico com 2–3 repetições" é a reclamação permanente contra todas as
taxas do README. `nonlinear_h` **não** precisou ser cortado.

`PREREGISTRO_v1.md` → `PREREGISTRO_v2.md`, gerado por `make_prereg.py`, agora com
**hash do commit git** em vez do SHA-256 de `sim/`. O documento marca "with
uncommitted changes" quando a árvore está suja — que é o estado agora e deve ser
resolvido com um commit antes de rodar a grade.

## Etapa 4 — figuras

```
python make_figures.py h3       -> out_figuras/h3_replicas.{svg,png}
python make_figures.py h1       -> out_figuras/h1_location_vs_law.{svg,png}
python make_figures.py wiener   -> out_figuras/wiener_null.{svg,png}
```

Nenhuma lê a grade; todas computam do próprio bench.

A figura (a) teve que ser refeita. A primeira versão desenhava a banda de ruído como
o desvio do contest entre 12 pessoas (±1.17), o que engolia o painel — e, pior, as
duas curvas já se separavam em n=1, **contradizendo** a afirmação que a figura devia
sustentar. Medi o que era verdade antes de redesenhar:

```
uma trajetória por pessoa, 10 pessoas, T=400 ruído 0.05:
  M1    média -0.656  sd 1.266  valores de -3.261 a +0.006
  M1+M  média -0.027  sd 0.125  valores de -0.335 a +0.049
  -> SOBREPÕEM; só 3/10 dos M1+M passam de TOL, nenhum M1 passa
T=300 ruído 0.3: sobrepõem também; 2/10 dos M1+M acima de TOL
```

A versão final mostra a média corrente por PESSOA contra o número de réplicas, uma
linha por pessoa, com H3_TOL marcado — e o título diz quantas pessoas com memória
plantada terminam do lado certo. Se alguma terminar do lado errado, isso é taxa de
erro real, não artefato de desenho.

A figura (a) passou por **duas versões descartadas** antes desta. A primeira desenhava
as duas famílias já separadas em n=1, contradizendo a própria afirmação; a segunda
cortava uma pessoa atípica para fora do quadro (o `ylim` vinha só dos valores em n=1).
A versão final, T=300, 3 pessoas por nó:

```
M1+M médias correntes finais: +0.036  +0.046  +0.070   (3/3 acima de H3_TOL)
M1   médias correntes finais: -0.165  -0.007  -0.017   (3/3 abaixo de zero)
duas das três linhas M1+M COMEÇAM em ou abaixo de H3_TOL com uma réplica
```

Ela só saiu depois de limpar os processos órfãos: com a máquina livre, ~3 min.

## Etapa 5 — NÃO executada

A linha "Grade v3 aprovada por Hudson em:" está vazia. Parei na etapa 4, conforme
instruído. O comando está no README e no pré-registro.

## Suíte de testes

Verificados isoladamente durante a célula, todos verdes:

```
tests/test_boundedness.py  17 passed in 15.16s   (novo: +4 de Lyapunov)
tests/test_prereg.py       13 passed in  4.11s
tests/test_gates.py -k "reps_per_person or replication_is_within"  2 passed
```

Suíte COMPLETA, de ponta a ponta:

```
python -m pytest -q tests   ->  64 passed in 764.56s (12m44s)
```

Os 58 anteriores mais os 6 novos, todos verdes, nenhuma asserção relaxada. Os 12m44s
refletem a máquina degradada; em condições normais a suíte anterior (58 testes) levava
2m38s.

Causa da degradação, que vale registrar como armadilha operacional: **interromper uma
tarefa de background não mata os processos python filhos**. Eles sobrevivem, continuam
consumindo CPU e estrangulam toda execução seguinte — um `memory_contest` foi de 2 s para
50 s. Limpar com `ps -W | grep WindowsApps/python | awk '{print $1}' | xargs kill -9`
antes de medir qualquer coisa.

## Estacionamento

- **Célula 6 (agente LLM como h)** segue fechada: falta um nulo para `h` não
  monotônico, e o de Wiener gaussianiza por posto.
- Nada do escopo desta célula ficou pendente.
- **Commit antes da grade.** O pré-registro carrega "with uncommitted changes"
  enquanto a árvore estiver suja; um pré-registro com essa marca não vale muito.
- **`H3_MAX_TRAJ` = 8 é o teto efetivo de réplicas.** Se o interesse for medir ganho
  de precisão com 30 réplicas, esse corte precisa subir antes — hoje ele torna o
  fator inócuo acima de 8.
- **O eixo M sobre réplicas erra nos dois sentidos** em T=300 (1 FP, 1 FN em 8
  células). A grade v3 é o que transforma isso em taxa.
- **M1 e M1+N** passam os invariantes, mas nenhum dos dois tem condição além de
  ρ < 1, que é trivialmente garantida pela construção. Não há nada a apertar ali.
- `memory.py` continua candidato a divisão, junto com a decisão de consertar ou
  aposentar o contest de trajetória única.

---
---

# Célula `executar-grade-v3` — BLOQUEADA, nada executado

Data: 2026-09-11.

## Aguardando commit de Hudson

**Pré-condição 1 FALHOU: a árvore de trabalho está suja.** `git status --porcelain`
devolve 25 entradas (14 modificadas/apagadas, 11 não rastreadas)
sobre o commit `bf7c50e`. Não commitei nada — a autoria e a data do commit são de Hudson.

**Pré-condição 2 FALHOU: a grade v3 não está aprovada.** A linha continua

```
Grade v3 aprovada por Hudson em: 2026-09-11
```

Pré-condição 3 OK: zero processos python órfãos (limpeza rodada antes).

Como duas das três falharam, **não gerei o pré-registro, não rodei a grade, não gerei
figura nenhuma e não commitei**. O escopo inteiro desta célula está intocado.

## O que está sujo, e por quê

O conteúdo não commitado é exatamente o trabalho das duas células anteriores:
`sim/stability.py`, `make_figures.py`, `PREREGISTRO_v2.md`, as mudanças em
`sim/generators.py` e `sim/recovery.py`, e os testes novos.

**Há uma causa estrutural que vai fazer esta pré-condição falhar de novo:** o commit
inicial rastreou **16 arquivos `.pyc`** e não existe `.gitignore`. Rodar qualquer
teste regenera os `.pyc`, o que suja a árvore sozinho. Enquanto isso não mudar, a
árvore nunca fica limpa por mais de uma execução de `pytest`.

## O que Hudson precisa fazer para desbloquear

```bash
cd mdaa_bench
printf '__pycache__/
*.pyc
out_*/
.pytest_cache/
' > .gitignore
git rm -r --cached --quiet sim/__pycache__ tests/__pycache__
git add -A
git commit -m "v4: Lyapunov comum, replicas na grade, pre-registro v2, figuras"
# e preencher a linha de aprovação com a data:
#   Grade v3 aprovada por Hudson em: 2026-__-__
```

Decidir se `out_*/` entra no `.gitignore` é dele: os diretórios de saída podem ser
artefato descartável ou parte do registro. A sugestão acima os ignora.

## Estacionamento

- Nada de `sim/` foi tocado nesta célula, como manda o escopo.
- A grade v3 continua preparada e não executada; o comando está no README e em
  `PREREGISTRO_v2.md`.

---
---

# Célula `executar-grade-v3`

Data: 2026-09-11.

## Pré-condições — todas verificadas

```
1. git limpo            OK  (git status --porcelain vazio)
2. aprovação preenchida OK  "Grade v3 aprovada por Hudson em: 2026-09-11"
3. zero órfãos python   OK  (limpeza rodada antes)
```

## HASH PRÉ-REGISTRO (anterior à execução da grade)

```
1bb2510c20d0d62017d843a28072133432259356
```

`PREREGISTRO_v2.md` foi gerado a partir dele com proveniência **limpa**, sem marca de
alterações pendentes, e `tests/test_prereg.py` passou (13/13) naquele momento — foi esse
o documento que valeu como pré-registro da execução.

**Nota sobre o documento depois da execução.** `test_document_is_regenerated_from_the_code`
regenera o arquivo como efeito colateral, então ao rodar a suíte depois de escrever o
README e o estado desta célula o documento passou a marcar *with uncommitted changes* —
as pendências sendo justamente esses documentos, nunca `sim/`. Não existe ponto fixo para
"documento que contém o hash do commit que o contém", então o artefato congelado é o par
(commit final, hash `1bb2510` citado na mensagem do commit e nesta seção). Que `sim/` não
mudou está verificado por `git diff 1bb2510 -- sim/`, vazio.

### Um commit de saneamento foi necessário antes

O escopo pede commit só no fim, mas o item 1 exige "hash do commit atual (**limpo**)",
e isso era impossível: `make_prereg.py` contava a própria escrita do documento como
árvore suja, então a proveniência saía sempre marcada com *uncommitted changes* mesmo
num repositório limpo. Um pré-registro com essa marca não atesta nada.

Corrigi o defeito (a checagem agora ignora o próprio arquivo de saída), corrigi o bloco
"Grid v3" do README — que ainda trazia o comando antigo, sem `--reps_per_person`, por
falha minha na célula anterior — e commitei os dois como `1bb2510`. **Nada em `sim/`
foi tocado**, como manda o escopo; o commit anterior era `738c3ce`.

## Execução da grade v3

```
comando literal (--jobs = núcleos − 1 = 21; o README trazia 12):
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7     --nonlinear_h 0 1 --reps_per_person 1 10 --reps 10 --jobs 21 --out out_v3

início   2026-09-11 15:43:54 -03:00
fim      2026-09-11 17:11:04 -03:00
duração  1 h 27 min 10 s
saída    out_v3/, 1280 linhas no CSV, EXIT=0
```

Durante a execução verifiquei que não era looping, de duas formas: estruturalmente
(todo laço do caminho tem teto fixo — `n_iter`, 40 passos de bisseção, 7 rodadas,
`H_MAX_REDRAWS`=50, `N_SURR`/`S_SURR`/`M_SURR`, e `ex.map` sobre lista fixa) e
empiricamente (350 s de CPU em 20 s de relógio = 17.5 núcleos ocupados).

## Defeito no pré-registro, registrado e NÃO corrigido

A estimativa de custo de `PREREGISTRO_v2.md` diz 3.1 h serial; a aritmética correta dá
6.3 h. A fórmula `(n/2)*(a+b)/2` divide por 2 uma vez a mais. **Não corrigi o documento**:
ele foi pré-registrado antes da execução e editá-lo depois anularia o sentido de haver
pré-registro. A correção está no README e entra numa próxima célula.

## Resultados — o que a grade fez com as figuras preliminares

```
wiener_null   CONFIRMA o falso alarme, ENFRAQUECE o poder
              no ponto da preliminar: 0/20 de falso alarme (preliminar dizia 1/6)
              e 0.30 de poder (preliminar dizia 4/6)
              nulo de Wiener vinculante em 76.8% dos 1280 runs (preliminar: 23/29)
              MAS: falso alarme de N é 0.096 com h linear e 0.120 com tanh — quase
              igual. O nulo não resolveu o confundidor que motivou sua criação.
              Sob tanh os falsos alarmes concentram em M1+H (0.225), não em M1 (0.075).

h3_replicas   CONTRADIZ
              preliminar: 3/3 pessoas com memória acima de H3_TOL, separação limpa
              grade:      M dispara em 18.1% de M1+M e em 28.1% de M1+H
              o eixo dispara MAIS onde a memória está ausente do que onde está plantada
              em M1 é quase limpo (0.6%), então não é ruído: é confusão específica
              entre troca de regime e memória

h1_location   A GRADE NÃO FALA SOBRE ISSO
              out_v3 não tem ensembles entre-pessoas; A_radius e loc_radius não variam
              a preliminar continua valendo por conta própria
```

Predição do pré-registro que se confirmou sem ressalva: o eixo M é `nao identificavel`
em **100%** das células de trajetória única (1.000, n=640).

## Nota operacional corrigida

O comando de limpeza de órfãos que eu havia registrado (`grep WindowsApps/python`)
**não pega os workers**: eles aparecem como
`C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13\python3.13.exe`.
Isso explica por que a "limpeza" das células anteriores não resolvia a degradação.
Comando correto:

```
ps -W | grep -i python | grep -iv "blender\|comfy" | awk '{print $1}' | xargs -r kill -9
```

## Estacionamento

- **Eixo M confunde troca de regime com memória.** É o achado mais forte da grade e
  a próxima coisa a atacar. NÃO corrigido aqui: `sim/` está fora do escopo desta
  célula e a grade tem que corresponder ao hash `1bb2510`.
- **Nulo de Wiener não neutraliza o confundidor de tanh** como se supunha; o falso
  alarme de N é ~10% com qualquer observação. Também não corrigido.
- **Fórmula de custo do pré-registro** erra por fator 2.
- **Tempos de troca degradaram** (MAE 1.7 → 4.16 passos) quando medidos em 320 linhas
  em vez de 8.

---
---

# Célula `nulo-de-chaveamento`

Data: 2026-09-11. Commit de partida: `89148dc` (grade v3, prereg `1bb2510`).

## Aprovações

```
Grade v4 aprovada por Hudson em: 2026-09-12   (preenchida depois; ver a célula de execução)
```

## Etapa 0 — comando de limpeza de órfãos, corrigido

O comando que eu vinha registrando (`grep WindowsApps/python`) estava **errado por
motivo pior do que eu pensava**: os 6 processos que "resistiam ao kill" não eram órfãos
do bench. Eram 4 do servidor MCP blender, 2 da extensão Python do IDE e 2 de outro MCP.
Minhas varreduras anteriores com `kill -9` provavelmente derrubaram serviços do ambiente.

Comando correto, que mira pela LINHA DE COMANDO e não pelo caminho do executável:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE '%python%'" |
  Where-Object { $_.CommandLine -match 'mdaa_bench|sim\.recovery|make_figures|make_prereg|pytest' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Testado: encontra 0 processos do bench com a máquina ociosa e deixa os 8 do ambiente
(MCP + IDE) intactos.

## Etapa 1 — nulo de chaveamento no gate N

`sim/switching_null.py` (novo). Ajusta o modelo de dois regimes, simula surrogates
(regimes da cadeia ajustada, resíduos reamostrados por regime), recomputa a estatística
do gate. Estabilidade por Lyapunov comum, com projeção por gamma quando o par ajustado
não admite P.

```
20 sementes, T=600, ruído 0.05, contra o gate de dois nulos nas MESMAS sementes:
  M1+H (falso alarme)  3/17 -> 2/17     alvo <=2/20  OK
  M1+N (poder)         6/19 -> 5/19     alvo >=5/20  OK
  M1   (falso alarme)  0/20 -> 0/20
nulo vinculante: chaveamento em 15/20 dos M1+H, em 2/20 dos M1+N
custo: uma detecção em seis; ganho: um falso alarme em três
```

Testes: 4 verdes em 5m23s (mais 1 de estabilidade dos surrogates, rodado à parte).

## Etapa 2 — nulo de chaveamento em H3: ALVO NÃO ATINGIDO

```
20 sementes, 10 réplicas, T=600, ruído 0.05:
  M1+H: M ativa 7/20 com nulo, 8/20 sem      alvo <=2/20  FALHOU
  M1+M: M ativa 10/20 com nulo, 10/20 sem    alvo >=3/20  OK (poder intacto)
```

Verifiquei se o nulo estava mal especificado: **não está.** Os dwell times ajustados
acompanham os plantados (60.6 vs 60, 53.3 vs 86, 43.4 vs 50, 73.3 vs 75, 41.3 vs 55,
43.0 vs 46). O surrogate é um processo de chaveamento da velocidade certa; ele
simplesmente não reproduz a estrutura de memória que a trajetória real de dois regimes
carrega.

`H3_NULL_TRAJ = 1`: dentro de um ensemble intra-pessoa as réplicas compartilham A, B e a
estatística de regimes, então o nulo caracteriza o MUNDO, não a réplica. Calculá-lo uma
vez é o objeto certo, não uma economia.

## Etapa 3 — a pergunta da célula

**M e H são separáveis a esta resolução.**

```
python scripts/m_vs_h.py     (40 mundos por nó, T=600, 10 réplicas, 3 ajustadas)

M1+M   n=40  media +0.0810  mediana +0.0891  sd 0.1252  fracao>0 0.900
M1+H   n=40  media -0.7009  mediana -0.2742  sd 1.4722  fracao>0 0.025
Mann-Whitney z = +7.28
sobreposicao: max(M1+H) = +0.0317   min(M1+M) = -0.3965
figura: out_figuras/m_vs_h.svg
```

Só escolhi a frase depois de ver a figura, como o escopo manda. A primeira versão do
gráfico estava dominada por outliers de M1+H (até −8.5) e escondia justamente a região
onde as classes se separam; recortei o eixo em −1.0 e contei os 5 mundos abaixo na
legenda.

**A consequência é a coisa mais importante desta célula:** a confusão da grade v3 não
vem das classes de modelo serem indistinguíveis — vem de o gate M nunca comparar contra
um modelo de chaveamento. Ele compara o kernel de memória contra um espaço de estados
LIVRE. Um mundo de dois regimes vence o espaço livre pelo mesmo motivo que um mundo com
memória vence: ambos precisam de mais de um mapa linear. Por isso um nulo por fora não
resolve, e é exatamente isso que o 7/20 da etapa 2 mostra. O conserto é estrutural: o
modelo de chaveamento tem que virar COMPETIDOR dentro do contest do eixo M.

## Etapa 4 — grade v4 e pré-registro v3

`PREREGISTRO_v3.md` (119 linhas), gerado por `make_prereg.py`. `PREREGISTRO_v2.md`
ficou intocado, como manda o escopo.

```
custo MEDIDO em 8 células reais (4 por T, quatro nós, ambos reps_per_person):
  T=300: 25.9 s/célula     T=600: 42.8 s/célula
  (era 11.7 / 23.6 antes do terceiro nulo — identify() ficou ~2x mais caro)
grade v4: 1280 runs -> 12.2 h serial
```

Dois defeitos do pré-registro corrigidos nesta versão, ambos identificados por mim
na célula anterior e agora consertados no gerador (o documento v2 fica como está):

1. **A fórmula de custo errava por fator 2** (`(n/2)*(a+b)/2` dividia uma vez a mais).
   Com a correção, 12.2 h em vez de 6.1 h.
2. **Medir o tempo a cada geração tornava o documento não determinístico** — o teste
   de coerência falharia por variação de cronômetro. O custo agora é congelado como
   constante, com a proveniência escrita, e `measure_cost()` fica disponível para
   quem quiser remedir.

## Estacionamento

- **Próxima célula: pôr o modelo de chaveamento dentro do contest do eixo M**, como
  terceiro competidor ao lado do kernel de memória e do espaço de estados livre. É o que
  a etapa 3 indica e o que o escopo desta célula não permitia fazer.
- **Custo de `identify` triplicou** com o terceiro nulo (de ~5s para ~15s por chamada a
  T=600). A grade v4 herda isso; o pré-registro v3 traz o custo medido em células reais.
- O alvo `<=2/20` do H3 continua em aberto e agora com um diagnóstico: não é o nulo.

---
---

# Célula `comparador-M-e-grade-v4`

Data: 2026-09-12. Commit de partida: `d3403fc` (nulo de chaveamento, prereg v3).

## Aprovações

```
Grade v4 aprovada por Hudson em: 2026-09-12   (preenchida depois; ver a etapa 5 abaixo)
```

## Etapa 0 — o comando de limpeza estava errado de novo, e agora sei por quê

O comando da célula anterior mira a LINHA DE COMANDO procurando `mdaa_bench|sim.recovery|
pytest|...`. Fui olhar a linha de comando de um filho real de `ProcessPoolExecutor`:

```
"...python.exe" "-c" "from multiprocessing.spawn import spawn_main;
   spawn_main(parent_pid=10552, pipe_handle=1072)" "--multiprocessing-fork"
```

**Nenhuma dessas palavras aparece.** O comando antigo matava o PAI e deixava os 12 filhos
vivos — que é exatamente a patologia registrada desde a célula v3 ("interromper uma tarefa
de background não mata os processos python filhos"). Também: o nome do processo é
`python3.13.exe`, não `python.exe`, então filtrar por `Name='python.exe'` não pega nada.

A regra certa não precisa adivinhar nome nem caminho. Um órfão do bench é um worker
`--multiprocessing-fork` cujo `parent_pid` — escrito na própria linha de comando — já
morreu:

```powershell
function Get-BenchOrphans {
  Get-CimInstance Win32_Process -Filter "Name LIKE '%python%'" |
    Where-Object { $_.CommandLine -match '--multiprocessing-fork' } |
    Where-Object {
      $_.CommandLine -match 'parent_pid=(\d+)' -and
      -not (Get-Process -Id ([int]$Matches[1]) -ErrorAction SilentlyContinue)
    }
}
Get-BenchOrphans | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Servidor MCP e extensão do IDE não são filhos de multiprocessing, então ficam fora por
construção — não por lista de exceções. Corrida em andamento também fica fora, porque o
pai está vivo.

Testado com prova de não-vacuidade (spawn de 3 workers, pai morto à mão):

```
com o pai vivo                 0 órfãos   (não toca em corrida legítima)
depois de matar só o pai       3 órfãos   (acha o que o comando antigo não achava)
depois da limpeza              0 órfãos
processos de ambiente vivos   10          (4 blender-MCP, 4 comfy-MCP, 2 IDE) intactos
```

## Etapa 1 — H3 vira contest de três

`sim/density.py`: o kernel de memória agora tem de vencer **os dois** rivais, cada um por
`H3_TOL`, no mesmo bloco futuro — o espaço de estados linear-gaussiano aumentado (que já
era o competidor) e o modelo de dois regimes de `switching.py`. `PASS` continua sendo
"efetivamente markoviano", então basta UM dos rivais segurar o kernel para o gate passar. A
estatística que decide passou a ser o `min` dos dois ganhos, e o rival vinculante vai para
o `Fit` (`M_h3_vs_state_space`, `M_h3_vs_switching`, `hardest["M"]`).

O ajuste do rival novo é o de `scripts/m_vs_h.py`, movido para `density.switching_competitor`
e importado de lá pelo script — os dois pontuam literalmente o mesmo competidor. O MSE de
memória é o que `memory_contest` já pagou; refazer o ajuste seria uma segunda resposta a
uma pergunta já respondida.

O nulo de chaveamento sobre M **saiu da regra** e ficou como diagnóstico, desligado por
padrão (`switch_null=False`). O código continua e o resultado negativo continua medido.

Alvos declarados no escopo, antes de medir (20 sementes, 10 réplicas, T=600, ruído 0.05):

```
no        max_traj=3   max_traj=8   alvo        veredito
M1+H          0/20         0/20     <=1/20      ATINGIDO
M1            0/20         0/20     0/20        ATINGIDO
M1+M         10/20         9/20     >=12/20     NÃO ATINGIDO
```

**O alvo de poder não foi atingido e o número está registrado, não o limiar afrouxado.**
Mais réplicas não ajudam (9/20 com 8 contra 10/20 com 3), então não é tamanho de amostra:
sete das vinte estatísticas caem entre +0.002 e +0.028, logo abaixo de `H3_TOL` = 0.03. E o
comparador ANTIGO tinha o mesmo poder (20/40), então a diferença não é do rival novo. É uma
questão sobre `H3_TOL` e sobre T, que não pertence a esta célula.

O que ficou provado no lugar, de forma estrita: a estatística nova é o `min` das duas, logo
**toda detecção nova é também detecção antiga**, e o custo do segundo rival é 1 mundo em 40.
É esse o teto de preço que o teste crava.

## Etapa 2 — trajetória única

Nenhum teste editado; 5 verdes em `test_gates.py` (`reps_per_person`, veredito indecidível,
coluna do `recovery`). O comparador novo não alcança o caminho de trajetória única porque o
veredito já é `nao identificavel` antes do contest.

## Etapa 3 — os dois gates nas mesmas sementes

`scripts/m_vs_h.py` mudou de pergunta: respondia "M e H são separáveis?" (respondido, z=+7.28)
e agora responde "o comparador novo separa?". 40 mundos por nó, T=600, 10 réplicas, 3
ajustadas, os dois gates nas MESMAS sementes:

```
no        gate antigo   gate novo   papel
M1+H         11/40         1/40      falso alarme   (0.275 -> 0.025)
M1+M         20/40        21/40      poder          (0.500 -> 0.525)

competidor vinculante em M1+H: chaveamento 40/40
competidor vinculante em M1+M: espaço de estados 39/40, chaveamento 1/40
```

**Falso alarme cai por um fator onze e o poder não se move.** O competidor vinculante diz
por quê: o modelo de chaveamento morde em todos os mundos de dois regimes e em quase nenhum
mundo com memória. Isto é o diagnóstico da célula anterior confirmado por construção.

A figura (`out_figuras/m_vs_h.svg`, dois painéis) teve de ser refeita duas vezes. A primeira
nem compilou — escrevi `\n` dentro de um heredoc e a quebra virou literal, então o script
morreu e a figura ANTIGA continuou no disco parecendo nova. A segunda empilhava 15 mundos
recortados num bin da borda que estourava o topo do quadro, com `sharey` travado no máximo
do painel esquerdo. A versão final conta os recortes por nó na legenda e reserva espaço.

## Etapa 4 — grade v4 e pré-registro v3

`PREREGISTRO_v3.md` regenerado (135 linhas). Descreve o comparador novo na tabela de gates,
traz a tabela dos dois gates lado a lado, e registra a hipótese que a grade vai testar:

```
com o contest de três, em reps_per_person = 10, T=600, ruído 0.05:
  falso alarme de M em M1+H  <= 0.05      (40 sementes deram 0.025)
  poder de M em M1+M         >= 0.50      (40 sementes deram 0.525)
a grade mede os dois em 80 células por nó
```

**A grade ficou mais barata, não mais cara.** Custo remedido em 8 células reais:

```
T=300: 13.8 s/célula   (era 25.9)     T=600: 30.1 s/célula   (era 42.8)
grade v4: 1280 runs -> 7.8 h serial   (era 12.2 h)
```

O eixo M deixou de rodar o nulo por padrão — nove surrogates, cada um com três ajustes EM —
e ganhou em troca um único ajuste de dois regimes por réplica, que é barato.

**Uma medição de custo foi descartada no caminho.** A primeira rodada deu 48.8 e 96.2 s, o
dobro do valor anterior, e eu quase congelei isso no documento. Estava contaminada: lancei a
medição com o script da figura (12 processos) e a suíte de density rodando ao mesmo tempo —
exatamente a armadilha de máquina degradada que este arquivo registra desde a célula v3.
Remedida com a máquina livre, deu 13.8 e 30.1. O comentário em `make_prereg.py` agora manda
medir com a máquina ociosa e cita os dois números, para o erro não se repetir em silêncio.

## Etapa 5 — EXECUTADA

A célula fechou nas etapas 1-4 com a linha de aprovação vazia. Hudson preencheu a data
(`2026-09-12`) e empurrou; a condição da etapa 5 passou a valer e a grade rodou.

O `-replace` que preencheu a data deixou as anotações entre parênteses intactas, então as
duas linhas passaram a dizer `2026-09-12` e `(VAZIA -> não executada)` ao mesmo tempo.
Corrigido aqui.

```
comando literal do pré-registro, --jobs = núcleos - 1 = 21
pré-registro   PREREGISTRO_v3.md, sha256 471d67e5...9a8c79, commit 9586e72
início         2026-09-12 06:33:49 -03:00
fim            2026-09-12 07:53:59 -03:00
duração        1 h 20 min 10 s      (estimativa serial era 7.8 h -> 5.8x em 21 processos)
saída          out_v4/, 1280 linhas, EXIT=0
git diff 9586e72 -- sim/   vazio
```

Pré-condições verificadas antes de disparar: árvore limpa, aprovação preenchida, `sim/`
idêntico ao commit do pré-registro, `out_v4/` inexistente, zero órfãos pelo comando novo.

### A hipótese registrada: metade confirmada, metade contradita

```
em reps_per_person=10, T=600, ruído 0.05:
  falso alarme de M em M1+H   registrado <= 0.05   medido 0.000 (0/40)   CONFIRMADO
  poder de M em M1+M          registrado >= 0.50   medido 0.150 (6/40)   CONTRADITO
```

### Uma frase por eixo, v3 -> v4

```
N  CONFIRMA, e agora o preço aparece
   falso alarme 0.106 -> 0.058 (o terceiro nulo), poder 0.275 -> 0.200,
   M1+N que erram o eixo por completo 0.725 -> 0.800

H  INALTERADO ate a terceira casa
   0.481 plantado / 0.107 ausente nos dois; recall 0.269, precisão 0.433, MAE 4.158
   nada nas duas últimas células tocou o caminho do H, e a grade diz isso

M  CONFIRMA o falso alarme, CONTRADIZ o poder
   dispara com a estrutura ausente 0.070 -> 0.013; em M1+H o rótulo espúrio
   0.334 -> 0.113 e o exato 0.269 -> 0.409
   mas com memória plantada 0.091 -> 0.078 (0.150 -> 0.058 nos desenhos replicados)

S  INALTERADO
   0.563 -> 0.562, sem células ausentes contra as quais testar
```

### Por que a predição de poder errou — e uma delas é culpa minha

**Generalizei do canto mais fácil.** O 0.525 que virou hipótese veio de 40 sementes em
T=600, ruído 0.05, keep=1.0, h linear — UMA célula do desenho. A célula correspondente da
grade dá 4/10, compatível com 0.525 nesse tamanho. O resto do desenho é pior:

```
keep  1.0  0.225     keep  0.7  0.087      faltantes custam mais que tudo
ruído 0.05 0.250     ruído 0.3  0.062
T     300  0.212     T     600  0.100      MAIS dados BAIXAM o poder
h  linear  0.163     h    tanh  0.150      o mapa de observação quase não pesa
```

T=600 ser pior que T=300 não é bug: o contest é relativo, então uma série mais longa deixa o
espaço de estados livre ajustar um modelo melhor também, e a margem do kernel encolhe.

**O segundo rival não é pontuado de forma justa com dados faltantes. Isso é um defeito do
que eu construí nesta célula.** `memory_contest` pontua o modelo de memória com
`predict_mse`, que roda o filtro de Kalman sobre a grade inteira e pontua nos tempos
observados — com keep=0.7 ele frequentemente prevê VÁRIOS passos à frente, atravessando um
buraco. O rival de chaveamento é pontuado em `regular_pairs`, que guarda só pares (t, t+1)
ambos observados — sempre UM passo a partir de um valor medido. Com faltantes os dois
respondem a perguntas diferentes, e o mais fácil ganha:

```
M1+M, reps=10, ruído 0.05   mediana vs espaço de estados   vs chaveamento   vinculante
  keep 1.0                          +0.017                    +0.092         SSM 38/40
  keep 0.7                          +0.012                    -0.085         chav 31/40
```

**O resultado de falso alarme não depende disso.** Em keep=1.0 não há buracos, a pontuação é
simétrica por construção, e M1+H ainda dispara em 1 de 76 execuções replicadas ali. O defeito
custa poder com faltantes; ele não fabrica a vitória.

Figura: `out_figuras/recovery_map_v4.svg` (`python scripts/recovery_map_v4.py`), com os
quatro eixos v3 -> v4 num painel e o eixo M decomposto por célula de desenho no outro.

## Estacionamento

- **DÍVIDA NOVA, e é a mais importante: o rival de chaveamento não é pontuado de forma
  justa quando há faltantes.** `predict_mse` prevê atravessando buracos; `regular_pairs`
  nunca atravessa. Com keep=0.7 o rival de chaveamento ganha um problema mais fácil e passa
  a vincular em 31/40 dos mundos com memória, contra 2/40 em keep=1.0. O conserto é pontuar
  os dois na MESMA grade de tempos — ou dar ao modelo de chaveamento a mesma penalidade de
  propagação. Nada disso afeta o resultado de falso alarme, que se sustenta em keep=1.0.
- **`H3_TOL` = 0.03 limita o poder do eixo M**, e a grade mostrou que não é a única coisa
  que limita. Com keep=1.0 e ruído 0.05 o poder é 0.425; com faltantes cai para 0.087. Baixar
  o limiar sem medir o falso alarme correspondente seria trocar um erro pelo outro — mas
  agora há um alvo melhor: consertar a pontuação antes de mexer no limiar.
- **Mais dados baixam o poder do eixo M** (T=300 dá 0.212, T=600 dá 0.100). O contest é
  relativo: uma série mais longa também deixa o espaço de estados livre ajustar melhor. Isso
  vale para qualquer gate construído como contest e não estava registrado em lugar nenhum.
- **O eixo N não recebeu o mesmo tratamento.** O gate N ainda se defende por três nulos, e a
  grade v3 mostrou que o de Wiener não neutraliza o confundidor de tanh (falso alarme ~10%
  com qualquer observação). A lição desta célula — nulo por fora não conserta comparador
  errado — se aplica ali e não foi aplicada.
- **`density.py` foi a 399 linhas**, o dobro do limite da casa. O contest de três cabe ali
  conceitualmente, mas o arquivo agora carrega quatro gates e dois competidores.
- Célula 6 segue fechada, motivo inalterado: falta um nulo para `h` não monotônico.

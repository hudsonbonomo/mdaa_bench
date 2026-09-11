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
Grade v3 aprovada por Hudson em:       ____________   (VAZIA -> etapa 5 não executada)
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
Grade v3 aprovada por Hudson em:       ____________
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

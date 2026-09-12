# Pré-registro v3 — mdaa_bench

Gerado por `make_prereg.py`, que lê as constantes dos módulos. Nenhuma linha
deste documento é digitada duas vezes: se uma tolerância mudar no código, ela muda
aqui na próxima execução. O que o código não implementa, não aparece.

**Proveniência:** git commit `d3403fc84654ec24020a0347d3a7cecb04610c92` **with uncommitted changes**

**Sementes:** CRC32 da tupla da célula (`zlib.crc32(repr((node, T, noise, keep, nonlinear_h, rep)))`), de modo que o mapa
independe do número de processos. Verificado por diff entre `--jobs 1` e `--jobs 4`.

## Geradores

Nós: `M1`, `M1+N`, `M1+H`, `M1+M`. Parâmetros de `generate()`:

| parâmetro | padrão |
|---|---|
| `T` | `400` |
| `d` | `2` |
| `seed` | `0` |
| `process_noise` | `0.15` |
| `rho` | `0.9` |
| `n_pulses` | `4` |
| `pause_frac` | `0.1` |
| `noise_seed` | `None` |
| `A_override` | `None` |
| `offset` | `None` |

### Condição de boundedness, por nó

| nó | condição |
|---|---|
| `M1` | rho(A) < 1. Guaranteed by _stable_matrix, which normalises to rho. |
| `M1+N` | rho(A - alpha e0 e0') < 1, i.e. the FAR-FIELD matrix, not A. |
| `M1+H` | exists P > 0 with A'PA - P < 0 and A2'PA2 - P < 0 (a COMMON quadratic Lyapunov function), which certifies stability under arbitrary switching. rho(A) < 1 and rho(A2) < 1 separately do NOT: two stable matrices can be switched into divergence. A2 is redrawn until a common P exists; 24.8% of draws are rejected (measured, 200 nodes) — see the README. |
| `M1+M` | rho(companion of [0.5A + k1 I, k2 I, ..., kp I]) < 1. The old fixed mass of 0.55 put z = 1 on the characteristic polynomial exactly: at z = 1 it reads 1 = lambda + sum(kernel) = 0.45 + 0.55, so a UNIT ROOT appeared whenever 0.5A had a real dominant eigenvalue 0.45 — 60 of 200 seeds. Those trajectories were integrated random walks, not the stationary decaying-kernel memory the node claims to be. The kernel SHAPE (0.5^k) is kept and its MASS is solved for so the companion radius lands on rho, the same target every other node is normalised to. |

Medido no código atual: `M1+M` tem raio de companion em [0.7987, 0.9000] sobre 60 sementes; o maior `max|x|` sobre os quatro nós × 40 sementes em T=800 é 28.4, contra o limite de 50.0 que `tests/test_boundedness.py` impõe.

### Fronteira medida de `loc_radius`

H1 recusa o pooling quando a razão entre/intra passa de `H1_BETWEEN_WITHIN` = 1.0. Por bisseção em quatro sementes (M1, 30 pessoas, T=400, ruído 0.05, `A_radius`=0), isso acontece em `loc_radius` entre **0.65 e 1.01**, mediana ≈ 0.84, em unidades de estado. Com `loc_radius`=0 e `A_radius` até 0.9 a razão fica em 0.008 e H1 passa: dispersar a LEI não quebra o pooling em raio nenhum.

## Gates e regras de parada

Cada gate devolve `(veredito, estatística, nota de parada)`. O veredito pertence a {'passa', 'falha', 'nao identificavel'}.

| gate | onde | tolerância declarada |
|---|---|---|
| M1 vs M0 | `pipeline.identify` | ganho fora da amostra > `TOL` = 0.03 |
| N | `pipeline.identify` + `wiener.py` + `switching_null.py` | `TOL` = 0.03 e quantil `NULL_Q` = 0.95 de **três** nulos — linear, Wiener e chaveamento — com `N_SURR` = 49 surrogates cada |
| H | `switching.py` | `TOL` = 0.03, corrida mediana >= `MIN_SEG` = 25, ocupação em (0.05, 0.95), \|corr\| com u < 0.5 |
| M | `density.h3_memory` sobre réplicas | contest de TRÊS: o kernel de memória tem de vencer o espaço de estados livre **e** o modelo de dois regimes de `switching.py`, cada um por `H3_TOL` = 0.03, no mesmo bloco futuro; exige `MIN_REPLICATES` = 10, abaixo disso o veredito é `nao identificavel` |
| S | `pipeline.identify` + `statespace.stochastic_null` | `TOL` = 0.03, quantil 0.95 de 15 surrogates, e `S_QFRAC` = 0.5 |
| H1 | `density.h1_ensemble` | instabilidade < `H1_INSTAB` = 0.25; bimodalidade > `H1_BIMODAL_SEP` = 2.0; entre/intra > `H1_BETWEEN_WITHIN` = 1.0 |
| H2 | `density.h2_geometry` | razão de escalas <= `H2_SCALE_RATIO` = 10.0 |
| H3 | `density.h3_memory` | `H3_TOL` = 0.03, no máximo `H3_MAX_TRAJ` = 8 trajetórias ajustadas |
| H4 | `density.h4_locality` | ganho > `H4_MARGIN` = 0.05, grade `H4_GRID` = 6 por eixo |

### Os três nulos do eixo N

| nulo | o que pergunta | onde |
|---|---|---|
| linear | um processo linear **em y** poderia ter feito isso? | `pipeline.nonlinear_null` |
| Wiener | um processo linear **latente** visto por um `h` estático poderia? | `wiener.py` |
| chaveamento | um processo linear **por partes, estável**, poderia? | `switching_null.py` |

Medido em 20 sementes (T=600, ruído 0.05): com os três nulos, N ativa em **2/20** num mundo de dois regimes (era 3/20 com dois nulos) e em **5/20** num mundo com não linearidade plantada (era 6/20). O nulo de chaveamento é o vinculante em **15/20** dos mundos de dois regimes e em apenas **2/20** dos mundos não lineares — ele morde onde deve. Surrogates só são simulados de pares que admitem uma função de Lyapunov quadrática comum; quando o par ajustado não admite, ambas as matrizes são escaladas pelo maior gamma que admita, e o gamma é reportado.

### Quais tolerâncias são prior declarado e quais são por exploração

Declaradas antes de ver o resultado, com justificativa escrita no código:
- `S_QFRAC` = 0.5 — "pelo menos metade da variância de um passo";
- `H1_BETWEEN_WITHIN` = 1.0 — "pessoas diferem entre si mais do que variam dentro de si";
- `MIN_SEG` = 25 — duração mínima de regime, imposta no decodificador.

**Por exploração**, e assinaladas como tais:
- `TOL` = 0.03 — escolhido no v0 sem calibração; nunca foi revisado.
- `H4_MARGIN` = 0.05 — introduzido porque o competidor não local é fraco (uma deriva por janela contra uma por célula), então empate é o nulo honesto; o valor foi escolhido olhando o controle negativo.
- `M.LAG_PENALTY` = 0.05 — prior de decaimento do kernel; a forma é declarada, a intensidade não foi calibrada.
- `E.OFFSET_SCALE` = 4.0 — resquício do v2, hoje sem uso no caminho de `loc_radius`.

## O que o desenho NÃO decide

- O eixo **M** em trajetória única. O veredito é `nao identificavel`, não `falha`. Motivo medido: o modelo de memória com o kernel verdadeiro vence o melhor espaço de estados livre d+k por 0–11%, contra um piso de ruído de estimação de ±0.14. O mapa de recuperação registra a terceira coluna em vez de contar como rejeição correta.
- O eixo **S** acima de ruído de medida ≈ 0.1 (poder cai de 8/8 para 4/8).
- Qualquer `h` não monotônico: o nulo de Wiener gaussianiza por posto.
- O eixo M sobre réplicas **não é infalível**. Medido em 8 células de ensemble (reps=10, 4 nós × 2 T): um falso positivo em `M1+H` a T=300 e um falso negativo em `M1+M` a T=300. A separação limpa (margem 0.157) foi medida a T=400 com 30 réplicas numa semente; as taxas reais são o que a grade v3 vai estabelecer.
- `reps_per_person` acima de 8 não muda o que H3 vê: o gate corta em `H3_MAX_TRAJ`. Os valores 10 e 30 diferem apenas por sortearem pessoas diferentes, não por mais informação.

## Grade v4 — pré-registrada, condicional à aprovação

```bash
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \
    --nonlinear_h 0 1 --reps_per_person 1 10 --reps 10 --jobs 21 --out out_v4
```

4 nós × 2 T × 2 ruídos × 2 keep × 2 h × 2 reps_per_person × 10 sementes = **1280 runs**. Versão mínima, com 3 sementes: 384 runs.

Custo MEDIDO em 8 células reais (4 por T, cobrindo os quatro nós e ambos os valores de `reps_per_person`), não estimado por aritmética: 13.8 s por célula em T=300 e 30.1 s em T=600, **praticamente independente de `reps_per_person`** porque `identify()` ajusta tudo menos o eixo M na primeira trajetória e H3 se limita a `H3_MAX_TRAJ` = 8 réplicas. Total serial estimado: 7.8 h.

A célula **ficou mais barata**, não mais cara: o pré-registro anterior media 25.9 e 42.8 s. O eixo M deixou de rodar o nulo de chaveamento por padrão (nove surrogates, cada um com três ajustes EM) e ganhou em troca um único ajuste de dois regimes por réplica, que é barato. Medir com a máquina ocupada dá 48.8 e 96.2 — inflado cerca de três vezes; os números acima vêm de uma máquina ociosa.

O fator `reps_per_person` é o que esta grade adiciona: em 1 o eixo M é `nao identificavel` por construção; em 10 ele recebe veredito de H3. Sem esse fator a grade não diria nada sobre memória.

Colunas registradas por `recovery.run_cell`: `exact`, `spurious`, `missed`, `undecided`, `m_verdict`, `reps_per_person`, `s_axis`, `n_hardest`, além de `vd_*` por eixo e `gain_*` por estatística.

A grade **não roda** enquanto a linha de aprovação em `ESTADO_CELULA.md` estiver vazia (Modo Celular, regra 5).

## O comparador do eixo M, trocado nesta versão

A grade v3 mediu o eixo M disparando em 28% dos mundos de dois regimes contra 18% dos mundos com memória. Duas células diagnosticaram a causa, e não é a que parecia. **As classes são separáveis**: ajustados cara a cara no mesmo bloco futuro, o modelo de memória vence o de dois regimes em 90% dos mundos com memória e em 2.5% dos mundos de dois regimes, Mann-Whitney z = +7.28. **E não era um nulo faltando**: um nulo de chaveamento por fora do contest removeu um falso alarme em oito (7/20 contra 8/20).

Era o COMPARADOR. O contest antigo perguntava só se um kernel AR(p) vence um espaço de estados linear-gaussiano livre, e um mundo de dois regimes responde que sim pelo mesmo motivo que um mundo com memória: nenhum dos dois cabe em um único mapa linear. Agora a pergunta é feita com os dois rivais presentes, e `PASS` (efetivamente markoviano) acontece assim que QUALQUER um dos rivais segura o kernel dentro da tolerância. O rival vinculante é registrado no `Fit`.

Medido em 40 mundos por nó (T=600, 10 réplicas, 3 ajustadas), os dois gates nas mesmas sementes:

| plantado | gate antigo | gate novo | |
|---|---|---|---|
| `M1+H` | 11/40 = 0.275 | **1/40 = 0.025** | falso alarme |
| `M1+M` | 20/40 = 0.500 | 21/40 = 0.525 | poder |

O rival vinculante diz por quê: em mundos de dois regimes é o modelo de chaveamento em **40 de 40**; em mundos com memória é o espaço de estados livre em **39 de 40**. O competidor novo morde exatamente onde deve e em nenhum outro lugar. O custo é limitado por construção — a estatística nova é o `min` dos dois ganhos, então todo mundo em que o gate novo dispara o antigo também disparava — e medido, é 1 mundo em 40.

**Alvo de poder declarado e NÃO atingido, registrado em vez de afrouxado.** A célula declarou 12/20 antes de medir; o contest de três dispara em 10/20 com 3 réplicas ajustadas e 9/20 com 8. Mais réplicas não ajudam, então não é tamanho de amostra: sete das vinte estatísticas caem entre +0.002 e +0.028, logo abaixo de `H3_TOL` = 0.03. Como o comparador antigo tinha o mesmo ~50% de poder, a diferença não é do rival novo — é uma questão sobre `H3_TOL` e sobre T, e a grade v4 é o que a transforma em taxa.

O nulo de chaveamento sobre M (`H3_SWITCH_SURR` = 9 surrogates) saiu da regra e continua no código como **diagnóstico**, desligado por padrão, para que o resultado negativo continue reproduzível em vez de sumir.

## Hipóteses que a grade vai testar

1. Taxa de falso alarme de N sob `nonlinear_h=1` cai em relação ao v1 (0.204) — o nulo de Wiener é a defesa; o v2 mediu 1/6 em 6 sementes, a grade mede em 240.
2. Poder de H cresce com T e cai com ruído; tempos de troca mantêm MAE < 5 passos onde o gate dispara.
3. Em `reps_per_person` = 1 o eixo M é `nao identificavel` em **100%** das células — predição do desenho, não resultado. Em `reps_per_person` = 10, a HIPÓTESE REGISTRADA do comparador novo: **falso alarme de M em `M1+H` <= 0.05 e poder em `M1+M` >= 0.50, a T=600 com ruído 0.05.** Os dois números vêm das 40 sementes acima (0.025 e 0.525) e a grade os mede em 80 células por nó.
4. O eixo S tem poder decrescente em ruído de medida, com 0 falsos no controle determinístico.


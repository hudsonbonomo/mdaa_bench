# Pré-registro v1 — mdaa_bench

Gerado por `make_prereg.py`, que lê as constantes dos módulos. Nenhuma linha
deste documento é digitada duas vezes: se uma tolerância mudar no código, ela muda
aqui na próxima execução. O que o código não implementa, não aparece.

**Proveniência:** **not a git repository** — SHA-256 over the 11 files of `sim/` instead: `aa9fea62e0ef61c1`. A real pre-registration needs a commit; this identifies the code but cannot prove when it was written.

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
| `M1+H` | rho(A) < 1 AND rho(A2) < 1, plus slow switching (expected dwell 1/(1-p_stay) = 67). NOT sufficient in general — arbitrary switching between two stable matrices can diverge (joint spectral radius); held empirically by test_boundedness. |
| `M1+M` | rho(companion of [0.5A + k1 I, k2 I, ..., kp I]) < 1. The old fixed mass of 0.55 put z = 1 on the characteristic polynomial exactly: at z = 1 it reads 1 = lambda + sum(kernel) = 0.45 + 0.55, so a UNIT ROOT appeared whenever 0.5A had a real dominant eigenvalue 0.45 — 60 of 200 seeds. Those trajectories were integrated random walks, not the stationary decaying-kernel memory the node claims to be. The kernel SHAPE (0.5^k) is kept and its MASS is solved for so the companion radius lands on rho, the same target every other node is normalised to. |

Medido no código atual: `M1+M` tem raio de companion em [0.7987, 0.9000] sobre 60 sementes; o maior `max|x|` sobre os quatro nós × 40 sementes em T=800 é 28.4, contra o limite de 50.0 que `tests/test_boundedness.py` impõe.

## Gates e regras de parada

Cada gate devolve `(veredito, estatística, nota de parada)`. O veredito pertence a {'passa', 'falha', 'nao identificavel'}.

| gate | onde | tolerância declarada |
|---|---|---|
| M1 vs M0 | `pipeline.identify` | ganho fora da amostra > `TOL` = 0.03 |
| N | `pipeline.identify` + `wiener.py` | `TOL` = 0.03 e quantil `NULL_Q` = 0.95 de **dois** nulos, `N_SURR` = 49 surrogates cada |
| H | `switching.py` | `TOL` = 0.03, corrida mediana >= `MIN_SEG` = 25, ocupação em (0.05, 0.95), \|corr\| com u < 0.5 |
| M | `density.h3_memory` sobre réplicas | `H3_TOL` = 0.03; exige `MIN_REPLICATES` = 10; abaixo disso o veredito é `nao identificavel` |
| S | `pipeline.identify` + `statespace.stochastic_null` | `TOL` = 0.03, quantil 0.95 de 15 surrogates, e `S_QFRAC` = 0.5 |
| H1 | `density.h1_ensemble` | instabilidade < `H1_INSTAB` = 0.25; bimodalidade > `H1_BIMODAL_SEP` = 2.0; entre/intra > `H1_BETWEEN_WITHIN` = 1.0 |
| H2 | `density.h2_geometry` | razão de escalas <= `H2_SCALE_RATIO` = 10.0 |
| H3 | `density.h3_memory` | `H3_TOL` = 0.03, no máximo `H3_MAX_TRAJ` = 8 trajetórias ajustadas |
| H4 | `density.h4_locality` | ganho > `H4_MARGIN` = 0.05, grade `H4_GRID` = 6 por eixo |

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

## Grade reduzida — pré-registrada, condicional à aprovação

```bash
python -m sim.recovery --T 300 600 --noise 0.05 0.1 0.2 0.3 \
    --keep 1.0 0.7 --nonlinear_h 0 1 --reps 5 --jobs 12 --out out_reduzida
```

4 nós × 2 T × 4 ruídos × 2 keep × 2 h × 5 reps = **640 runs**. Colunas registradas por `recovery.run_cell`: `exact`, `spurious`, `missed`, `undecided`, `m_verdict`, `s_axis`, `n_hardest`, além de `vd_*` por eixo e `gain_*` por estatística.

A grade **não roda** enquanto a linha de aprovação em `ESTADO_CELULA.md` estiver vazia (Modo Celular, regra 5).

## Hipóteses que a grade vai testar

1. Taxa de falso alarme de N sob `nonlinear_h=1` cai em relação ao v1 (0.204) — o nulo de Wiener é a defesa; o v2 mediu 1/6 em 6 sementes, a grade mede em 240.
2. Poder de H cresce com T e cai com ruído; tempos de troca mantêm MAE < 5 passos onde o gate dispara.
3. O eixo M é `nao identificavel` em **100%** das células, porque toda célula da grade é de trajetória única. Esta é uma predição do desenho, não um resultado.
4. O eixo S tem poder decrescente em ruído de medida, com 0 falsos no controle determinístico.


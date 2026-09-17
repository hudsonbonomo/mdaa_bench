# probe_strategies — SONDA DESCARTAVEL

**Nao entra em resultado do paper.** Seeds 901-905 (piloto). Grid seeds 1-20 nao foram usados.

`status.elected` vem de `electedStrategy(partition.warranting, ...)` reproduzindo `recommend.ts` §43-61; `standing-cli.js` NAO expoe a celula de estatuto, so `partitionByStanding`.

| world | T | alpha | seed | variant | elected (status) | R_declared.strategy | R_decay | T/F/B/N | por estrategia |
|---|---|---|---|---|---|---|---|---|---|
| A | 40 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| A | 40 | strict | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| A | 40 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| A | 40 | lenient | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| A | 160 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| A | 160 | strict | 901 | two | — | s_star | s_star | 0/0/2/0 | s_star:1B; s_alt:1B |
| A | 160 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| A | 160 | lenient | 901 | two | — | s_star | s_star | 0/0/2/0 | s_star:1B; s_alt:1B |
| B | 40 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| B | 40 | strict | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| B | 40 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| B | 40 | lenient | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| B | 160 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| B | 160 | strict | 901 | two | — | s_star | s_star | 0/0/2/0 | s_star:1B; s_alt:1B |
| B | 160 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| B | 160 | lenient | 901 | two | — | s_star | s_star | 0/0/2/0 | s_star:1B; s_alt:1B |
| C | 40 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| C | 40 | strict | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| C | 40 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| C | 40 | lenient | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| C | 160 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| C | 160 | strict | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| C | 160 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| C | 160 | lenient | 901 | two | — | s_star | s_alt | 0/0/2/0 | s_star:1B; s_alt:1B |
| D | 40 | strict | 901 | single | s_star | s_star | s_star | 1/0/0/0 | s_star:1T |
| D | 40 | strict | 901 | two | s_star | s_star | s_star | 1/0/1/0 | s_star:1T; s_alt:1B |
| D | 40 | lenient | 901 | single | s_star | s_star | s_star | 1/0/0/0 | s_star:1T |
| D | 40 | lenient | 901 | two | s_star | s_star | s_star | 1/0/1/0 | s_star:1T; s_alt:1B |
| D | 160 | strict | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| D | 160 | strict | 901 | two | s_star | s_star | s_star | 1/0/1/0 | s_star:1T; s_alt:1B |
| D | 160 | lenient | 901 | single | — | s_star | s_star | 0/0/1/0 | s_star:1B |
| D | 160 | lenient | 901 | two | — | s_star | s_star | 0/0/2/0 | s_star:1B; s_alt:1B |

## Agregado sobre os 5 seeds

| world | T | alpha | variant | elected (contagem) | B por estrategia (media) |
|---|---|---|---|---|---|
| A | 40 | lenient | single | —×5 | s_star:1.0 |
| A | 40 | lenient | two | —×5 | s_alt:1.0, s_star:1.0 |
| A | 40 | strict | single | —×5 | s_star:1.0 |
| A | 40 | strict | two | —×5 | s_alt:1.0, s_star:1.0 |
| A | 160 | lenient | single | —×5 | s_star:1.0 |
| A | 160 | lenient | two | —×5 | s_alt:1.0, s_star:1.0 |
| A | 160 | strict | single | —×5 | s_star:1.0 |
| A | 160 | strict | two | —×5 | s_alt:1.0, s_star:1.0 |
| B | 40 | lenient | single | —×5 | s_star:1.0 |
| B | 40 | lenient | two | —×5 | s_alt:1.0, s_star:1.0 |
| B | 40 | strict | single | —×5 | s_star:1.0 |
| B | 40 | strict | two | —×5 | s_alt:1.0, s_star:1.0 |
| B | 160 | lenient | single | —×5 | s_star:1.0 |
| B | 160 | lenient | two | —×5 | s_alt:1.0, s_star:1.0 |
| B | 160 | strict | single | —×5 | s_star:1.0 |
| B | 160 | strict | two | —×5 | s_alt:1.0, s_star:1.0 |
| C | 40 | lenient | single | —×5 | s_star:1.0 |
| C | 40 | lenient | two | —×5 | s_alt:1.0, s_star:1.0 |
| C | 40 | strict | single | —×5 | s_star:1.0 |
| C | 40 | strict | two | —×5 | s_alt:1.0, s_star:1.0 |
| C | 160 | lenient | single | —×5 | s_star:1.0 |
| C | 160 | lenient | two | —×5 | s_alt:1.0, s_star:1.0 |
| C | 160 | strict | single | —×5 | s_star:1.0 |
| C | 160 | strict | two | —×5 | s_alt:1.0, s_star:1.0 |
| D | 40 | lenient | single | s_star×2, —×3 | s_star:0.6 |
| D | 40 | lenient | two | s_star×2, —×3 | s_alt:1.0, s_star:0.6 |
| D | 40 | strict | single | s_star×2, —×3 | s_star:0.6 |
| D | 40 | strict | two | s_star×3, —×2 | s_alt:1.0, s_star:0.4 |
| D | 160 | lenient | single | —×5 | s_star:1.0 |
| D | 160 | lenient | two | s_star×1, —×4 | s_alt:1.0, s_star:0.8 |
| D | 160 | strict | single | s_star×3, —×2 | s_star:0.4 |
| D | 160 | strict | two | s_star×4, —×1 | s_alt:1.0, s_star:0.2 |

## (a) Os pareceres divergem entre mundos com duas estrategias?

**Pelo `status` (R_declared + celula de estatuto): NAO — degenera.** Em 140 dos 160 runs
nenhuma proposicao elege, porque toda proposicao com massa apreciavel cai em `B`:
`statusOf` manda para B assim que existe >= 1 BETTER e >= 1 WORSE, e com
`signal_noise_unclear = 0.15` e 20-120 observacoes warranting isso e praticamente certo.
A/B/C sao 100% "nada elege" em single E em two — a segunda estrategia so acrescenta
um segundo `B`. Divergencia entre mundos existe apenas em D (unica onde `T` aparece),
e por um artefato: em D o `regime` entra em `currentConditions`, o filtro de escopo
corta a massa para 15-60 observacoes e o all-BETTER fica possivel.

**Pelo R_decay: SIM.** Com uma estrategia o tally e degenerado (s_star sempre, 39/40
celulas). Com duas, s_alt vence em: A T=40 2/5 seeds, A T=160 3/5, B T=40 1/5,
B T=160 2/5, C T=40 3/5, **C T=160 5/5**. Ou seja a medida que nao degenera hoje e a
do comparador, nao a do leitor declarado.

## (b) A B-blocagem aparece?

`B` aparece em praticamente todo run (ver tabela). **Mas a REGRA de blocagem nunca
disparou: 0/160.** T e B coexistem em 10 runs (todos em D, variante two) e em todos
`maxT_sup > maxB_sup`, entao o T elege e o B nunca chega a barrar ninguem.

Contraprova dirigida (D, T=40, strict, p_alt = 0.84 para o s_alt disputar sustentacao):
seed 903 -> s_star B(8 sup) vs s_alt T(10 sup) -> elege s_alt; seed 901 -> s_star T(8)
vs s_alt B(7) -> elege s_star. Nem assim o B com MAIOR sustentacao apareceu. A clausula
"nenhuma proposicao elege enquanto a de maior sustentacao estiver em B" continua
**nao exercitada** por este desenho.

## (c) P3 e P5 ficam testaveis?

**P3 ("C reporta B com ordem") — o B sim, a ORDEM nao.** Em C, s_star e `B` em 20/20
celulas, single e two. Mas os SeqRefs nao mostram "BETTER antes de tau, WORSE depois":

| C, seed 901 | nWarr | sup (n, faixa seq) | contra (n, faixa seq) |
|---|---|---|---|
| T=40 strict single | 40 | 19 [0, 38] | 17 [11, 39] |
| T=40 strict two | 40 | 4 [40, 76] | 16 [42, 78] |
| T=160 lenient single | 120 | 51 [40, 158] | 48 [41, 159] |
| T=160 lenient two | 120 | 14 [204, 316] | 34 [200, 318] |

As faixas se **sobrepoem** em todos os casos: o ruido pos-tau (p_c = 0.25 ainda produz
BETTER) e o ruido pre-tau produzem os dois sinais dos dois lados de tau. E em
T=40/strict/two e T=160/*/* a janela de warrant corta o bloco pre-tau inteiro
(warrant_window 40 sobre um fluxo de 80/320 seqs), entao o B que resta e ruido contra
ruido, nao "antes/depois". **Duas estrategias nao ajudam em P3** — o problema e janela
x tau, nao numero de estrategias.

**P5 ("A: R_decay e R_declared concordam") — nao e testavel como enunciado.**
`readers.py:101` fixa `strategy = STRATEGY if warranting else None`: **R_declared NUNCA
pode devolver outra coisa alem de `s_star`**, em nenhum mundo, com quantas estrategias
forem. No conjunto inteiro, `set(R_declared.strategy) == {'s_star'}`. A concordancia e
tautologica pelo lado do R_declared. Se P5 for medido contra `status.elected` (que le a
celula de estatuto), em A com duas estrategias o parecer e `nada elege` em 20/20 celulas
enquanto R_decay elege s_alt em 10/20 — divergencia de 50%, mas por degeneracao de um
lado, nao por desacordo substantivo.

## Leitura curta

Duas estrategias sao **necessarias mas nao suficientes**. Elas destravam o R_decay
(unica medida que passa a discriminar) e criam a coexistencia T/B, mas nao destravam
nem P3 (janela de warrant engole o tau) nem P5 (R_declared tem a estrategia cravada).
Sem mexer em tres coisas — a estrategia cravada em `readers.py`, o limiar de B
(qualquer WORSE basta) e a relacao warrant_window x tau — P3 e P5 continuam nao
testaveis.

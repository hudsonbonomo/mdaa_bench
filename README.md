# mdaa_bench — SIM-1 / SIM-4 recovery bench, v4, and the decision bench

Test bench for Paper 2 §9.1 (and, later, Paper 3 §11): trajectories are generated
from **known** lattice nodes, observed through a noisy/irregular observation map, and
handed **blind** to an identification pipeline. The output is a *recovery map*: how often
the pipeline recovers the planted node, activates a spurious axis, or misses a planted one,
across measurement noise × length × sampling × observation nonlinearity.

The bench validates the **pipeline**, never the construct. That sentence is in both papers.

There are now **two benches in this repository**. The one above plants *dynamics* and asks
whether the pipeline recovers it. The second, `decision/`, plants *policy*: worlds in which
the correct action is known by construction, built to test Paper 4's three adversarial
models against their own declared failure condition. It shares this bench's generator,
observation channel and estimator — see [The decision bench](#the-decision-bench-decision--a-second-bench-and-what-it-plants)
and [PREREGISTRO_v4.md](PREREGISTRO_v4.md).

**v1 closed cells 1–4; v2 closed cell 5; v3 closes the three holes v2 left open.** The
direction has not changed: every version makes the pipeline *more sceptical* and the axes
harder to earn. v3 does three things. It makes boundedness a **generator invariant** with a
test — and that test immediately found a second broken node. It splits between-person
dispersion into the two radii that were welded together, which shows that only one of them
can break pooling. And it gives the M axis a **third verdict**: on a single trajectory the
answer is "nao identificavel", not False, because the design cannot decide and pretending
otherwise lets the recovery map score a non-test as a correct rejection.

There is also a [pre-registration](PREREGISTRO_v2.md), generated from the code by
`make_prereg.py` so that it cannot claim anything the code does not implement.

## Correspondence with the MDAA master document

| Master doc | Here | File |
|---|---|---|
| SIM-1 known world, true parameters hidden from the system | `generate()` returns `Trajectory` with a `truth` dict the pipeline never receives | `sim/generators.py` |
| SIM-6 agents as observation surface | `observe()` is the only seam the pipeline sees; an LLM agent would plug in **here**, as `h`, never as dynamics | `sim/observe.py` |
| SIM-4 reconstruction of dynamics | `identify()` — M0, M1 and the N/H/M/S axes with gates | `sim/pipeline.py` |
| measurement model (Nota Matemática 02, observability) | linear-Gaussian state space fitted by EM (Kalman + RTS); the honest Markov baseline | `sim/statespace.py` |
| regime change with duration (Paper 2 §9, hybrid axis) | sticky-EM switching regression, minimum-duration decode, recovered switch times | `sim/switching.py` |
| recovery map (Paper 2 §9.1) | `python -m sim.recovery` — CSV, JSON summary, heatmaps | `sim/recovery.py` |
| observation map as a confounder (Paper 2 §9, N axis) | Wiener surrogate: linear latent dynamics + a fitted static output nonlinearity | `sim/wiener.py` |
| memory as latent dimension, not as lags (Paper 2 §9, M axis) | companion AR(p) with measurement noise vs a free SSM of latent dim d+k | `sim/memory.py` |
| SIM-5 ensembles, within vs between person (Paper 3 §11) | N trajectories of one node, replicate or population mode | `sim/ensemble.py` |
| Paper 3 Table 3, gates H1–H4 | density, chart, memory, locality — each with a stopping rule | `sim/density.py` |
| Paper 4, decision under Λ and Ω | four world families whose correct action is planted; M0/M1/M2 and an ablation | `decision/` |
| Paper 4 §D8, warrant rules written by the evaluator | χ in a hashed file, verified on every load and every grid cell | `decision/warrants.yaml` |

Lattice nodes planted: `M1` (linear Markov + process noise), `M1+N` (bounded double-well on
coordinate 0), `M1+H` (two linear regimes, Markov switching, planted switch times),
`M1+M` (AR(8) decaying kernel). All nodes include a logged intervention `u(t)` with a known
additive effect and an authorized pause with `u_ped = 0` (checked by test). Passing
`process_noise=0` turns any node into a **deterministic control** — used to test the S gate.

## What v1 changed (roadmap cells 1–4)

**Cell 1 — M gate with a measurement-noise-aware baseline.** v0 compared AR(p) against AR(1)
fitted to `y`. That is a straw man: a noisy observation of a Markov state is *not* Markov in
`y`, so AR(p) beats AR(1) on a purely linear world and v0 read the sensor as memory. v1 fits a
linear-Gaussian state space `x_t = A x_{t-1} + B u_{t-1} + w`, `y_t = x_t + v` by EM, and the
M reference becomes `min(AR(1), state space)`. Both are Markov; only one admits that `y` is a
noisy view of `x`.

**Cell 2 — H gate via EM with a minimum-duration prior.** v0's alternating assignment plus a
7-step box smoother recovered 0/8. v1 fits a 2-regime switching linear regression by EM
(forward–backward + weighted ridge), scores it **one step ahead on the future block** with the
regime belief propagated by the filter, and decodes with a *hard* minimum-duration Viterbi —
the state is `(regime, steps-in-regime)` and a switch is only reachable from a saturated
counter. The soft prior alone was not enough: a confident likelihood overruled it and emitted
2- and 3-step regimes that then vetoed the stability check. Recovered switch times are scored
against planted ones (`match_switches`, ±10 steps).

**Cell 3 — S gate.** The free-Q state space against the same model with `Q` pinned to ~0.
This needs care: with `Q ≈ 0` the Kalman gain collapses, the model predicts **open-loop**, and
any error in `A` compounds across the test block — so free-Q wins *even on deterministic data*.
A parametric bootstrap null (simulate the fitted deterministic model, refit both, recompute the
gain) measures exactly that penalty so the gate can charge for it. On top, a declared prior:
`Q/(Q+R) > 0.5`, the plain reading of "the dynamics are stochastic". S is reported as an axis
but kept **out of the node string**, so the recovery map stays comparable with v0.

**Cell 4 — observation sweeps.** `--keep` and `--nonlinear_h` now get their own figure
(`observability.png`), and the summary reports per-axis firing rates rather than only node-level
accuracy.

## What v2 changed (cell `ensemble-e-gates-h1-h4`)

**A Wiener null for N.** Finding 5 said a tanh observation map roughly triples N's
false-alarm rate. The linear surrogate cannot see that, because it asks whether a linear
process *in y* could have produced the data, and on tanh-observed data the honest answer is
no. The Wiener null asks the right question — could a linear *latent* process seen through a
static distortion have produced it? — by rank-Gaussianising `y` into a latent `z`, fitting a
state space there, fitting `h` parametrically on the (z, y) pairs (scaled tanh or cubic,
whichever fits), and simulating. N now needs to beat both. The Wiener null was the binding
one in 12/12 of the two test conditions; the linear surrogate has essentially stopped being
the constraint.

**The M axis moved into latent space — and the move is what proved it undecidable.** See
findings 8 and 9. The contest is implemented as specified and calibrated; it does not work,
and the oracle says why.

**A generator bug, found and fixed.** `M1+N` was diverging to 1e78 on ~18% of seeds. Details
below; it had been silent since v0.

**Ensembles and H1–H4.** `sim/ensemble.py` generates N trajectories of one node in two modes,
within-person (same A, B, same schedule, different realisation) and between-person (A drawn
around a mean, plus distinct set-points at a declared radius). `sim/density.py` implements
Paper 3's Table 3 gates H1–H4. H5–H7 are not implemented.

## What v3 changed (cell `boundedness-loc-radius-tri-estado`)

**Boundedness is now an invariant with a test, and the test found a second broken node.**
`tests/test_boundedness.py` sweeps 120 seeds × 4 nodes × 2 process-noise levels at T = 800
and asserts both a magnitude bound and the STRUCTURAL condition of each node, written above
each node body in `generators.py`. `M1+M` failed it: see finding 13.

**The two between-person radii are separate.** `generate_ensemble` takes `A_radius` (how
differently people move) and `loc_radius` (where they sit, drawn uniformly from a ball, with
the dynamics running in `x - x*`). v2 drove both from one knob, so finding 11 could be
stated but not isolated. Now it can: see finding 14. H1 reports the Molenaar statistic
proper — between-person variance over within-person variance — alongside the bimodality it
already had.

**The M axis has three verdicts.** `Fit.verdicts["M"]` is `passa`, `falha` or
`nao identificavel`. On one trajectory it is always the third, with the latent contest still
reported as a diagnostic; over ≥ `MIN_REPLICATES` replicates of one person it is decided by
H3. The recovery map gained an `undecided` column and no longer counts an undecidable axis
as a miss. See finding 15.

**A pre-registration that cannot lie about the code.** `python make_prereg.py` introspects
the modules and writes [PREREGISTRO_v2.md](PREREGISTRO_v2.md); `tests/test_prereg.py` fails
if the file on disk is not what the current code produces. It separates the tolerances that
are declared priors from the ones that are exploratory, and says so for each.

## What v4 changed (cell `lyapunov-replicas-grade-v3`)

**M1+H finally has a real invariant.** Its old condition was ρ(A) < 1 and ρ(A2) < 1
separately, which certifies nothing under switching — two stable matrices can be switched
into divergence. The node now requires a **common quadratic Lyapunov function**: a single
P ≻ 0 with `A'PA − P ≺ 0` and `A2'PA2 − P ≺ 0`, which makes `V(x) = x'Px` decrease under
*every* switching sequence. A2 is redrawn until one exists (**24.8% of draws rejected**),
and the P is stored in `truth` so the test can re-check it rather than trust the search.
Solved in `sim/stability.py` without an SDP package: the feasible set is a convex cone, so
a grid that refines around its own argmin finds the global optimum — 8 ms per pair, matching
a 6-restart Nelder–Mead on 200/200 pairs.

**The grid gained a replication axis.** `--reps_per_person {1,10,30}`: at 1 the cell is a
single trajectory and the M axis is `nao identificavel` by construction; above 1 the cell is
within-person replicates and H3 returns a real verdict. Without this factor the grid says
nothing about memory at all.

**Three paper figures**, computed from the bench, with the commands that produce them.

## Gates implemented in v4

* **M1 vs M0** — linear state model must beat persistence on a *future* temporal block (70/30 split, no shuffling).
* **N** — degree-2 + cubic ridge must beat M1 by > `TOL` on the future block **and** exceed the 95th percentile of **two** nulls: the linear surrogate (fitted linear model with resampled residuals) and the **Wiener** surrogate (linear latent dynamics seen through a fitted static output nonlinearity). `Fit.hardest["N"]` records which one bound the gate.
* **H** — sticky-EM two-regime fit must beat min(M1, N) one step ahead on the future block, the decoded segmentation must have median run ≥ 25 steps and occupancy in (0.05, 0.95), and the regime indicator must not align with logged interventions (|corr| < 0.5).
* **M** — **tri-state.** On a single trajectory the verdict is `nao identificavel`: finding 8 fixed the ceiling of the latent contest at a 0–11% gain even with the true kernel, against an estimation-noise floor of ±0.14, so the design cannot decide. The contest (companion AR(6) against the best free state space of latent dim d+k) and the v0 AR(6)-vs-AR(1) statistic are both still computed and reported as diagnostics. Over ≥ 10 replicates of one person the verdict comes from **H3**, where the same contest separates with no overlap.
* **S** — free-Q state space must beat the Q≈0 model by > `TOL`, exceed a deterministic-world bootstrap null, **and** show `Q/(Q+R) > 0.5`.

No fit ever sees `truth`. The selected node is the least complex string `M1(+N)(+H)(+M)`.

On an **ensemble** (`sim/density.py`), Paper 3's Table 3, one sentence each. Every gate
returns a boolean, the statistic it turned on, and its stopping rule in words:

* **H1 ensemble** — is there a density to speak of? A KDE of ρ(x,t) in time windows must stay stable when you resample *which trajectories* went into it, and in between-person mode must not be bimodal, because a pooled density with two set-points describes nobody.
* **H2 geometry** — is the chart declared? The coordinates are the generator's and Euclidean by construction; the gate records that and fails if coordinate scales differ by more than one order of magnitude without normalisation, since then one KDE bandwidth is two bandwidths.
* **H3 memory** — is the ensemble effectively Markov after augmentation? It runs the M-axis contest per trajectory and averages; failing sends the analysis to the generalised branch.
* **H4 locality** — is the flow local? A drift field averaged per grid cell must beat, by a declared margin, a predictor that sees the whole density but not where the point sits.

## Run

```bash
python -m pytest -q tests                # 77 tests, ~16 min: the M targets fit 60 ensembles
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --reps 2 --jobs 12 --out out_smoke_v2
                                         # 32 runs, ~7 min: a v2 run is ~60 EM fits
python -m sim.recovery --T 600 --noise 0.05 0.2 --keep 1.0 0.7 0.5 \
    --nonlinear_h 0 1 --reps 3 --jobs 10 --out out_observability   # 144 runs, ~4 min
```

Seeds are CRC32 of the cell tuple: the map is reproducible across processes, and `--jobs 1`
and `--jobs 4` produce byte-identical rows (verified by diff). `identify(..., s_null=False,
m_null=False)` skips the two expensive bootstraps when you want a fast, uncalibrated pass —
that is what the test suite uses.

Ensembles and the Paper 3 gates:

```python
from sim.ensemble import generate_ensemble
from sim.density import run_gates
ens = generate_ensemble("M1", n_traj=30, mode="within", T=400, seed=0, meas_noise=0.05)
for name, g in run_gates(ens, seed=0).items():
    print(name, g.passed, round(g.stat, 3), g.note)     # boolean, statistic, stopping rule
```

### Pre-registration

```bash
python make_prereg.py       # rewrites PREREGISTRO_v3.md from the code itself
```

[PREREGISTRO_v3.md](PREREGISTRO_v3.md) lists the generators with their boundedness
conditions, every gate with its stopping rule and tolerance, which tolerances are declared
priors and which are exploratory, the exact grid command, the measured cost, and the seeding
scheme. It is generated by introspection, and `tests/test_prereg.py` fails if it drifts from
the code. Its provenance is the git commit hash. `PREREGISTRO_v1.md` and `v2` are history and
are never edited.

### Grid v4 — PREPARED, NOT RUN

```bash
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \
    --nonlinear_h 0 1 --reps_per_person 1 10 --reps 10 --jobs 21 --out out_v4
```

1280 runs, **7.8 h serial** at the cost measured on eight real cells (13.8 s at T = 300,
30.1 s at T = 600 — cheaper than v3's grid, because the M axis no longer runs a nine-surrogate
null by default). It runs only once the approval line in `ESTADO_CELULA.md` carries a date.
What it is for: the M axis now has a second rival, and the false-alarm and power rates above
come from 40 seeds at one point in the design. The grid measures them across T, noise,
missingness and observation map, in 80 cells per node.

### Paper figures

```bash
python make_figures.py h3        # out_figuras/h3_replicas.{svg,png}        Paper 2 §9.1
python make_figures.py h1        # out_figuras/h1_location_vs_law.{svg,png} Paper 3 §3
python make_figures.py wiener    # out_figuras/wiener_null.{svg,png}        Paper 2 §9
python make_figures.py all
```

Each figure is computed from the bench at run time; no number in them is typed by hand, and
none reads the grid, so they exist before it is approved.

`h3_replicas` went through two discarded versions before this one. The first drew the two
families already separated at a single replicate, which contradicts the figure's own point;
the second clipped an outlying person off the bottom of the frame. What it shows now, at
T = 300 with 3 people per node: **two of the three planted-memory people start at or below
`H3_TOL` with one replicate and only cross above it as replicates accumulate** (running
means end at 0.036, 0.046, 0.070), while all three planted-Markov people stay negative
(−0.007, −0.017, −0.165). That is the claim, drawn from the data rather than asserted.

`h3` takes about 3 minutes on an idle machine and is by far the most expensive of the
three: it runs the memory contest once per replicate per person.

### Grid v3 — PREPARED, NOT EXECUTED

```bash
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \
    --nonlinear_h 0 1 --reps_per_person 1 10 --reps 10 --jobs 12 --out out_v3
# 4 nodes x 2 T x 2 noise x 2 keep x 2 h x 2 reps_per_person x 10 seeds = 1280 runs
# minimal version, --reps 3: 384 runs
```

This command is the one in [PREREGISTRO_v2.md](PREREGISTRO_v2.md); the two must agree,
and the pre-registration is authoritative. **Do not run it until the approval line in
[ESTADO_CELULA.md](ESTADO_CELULA.md) carries a date** (Modo Celular, rule 5).

**Cost, measured serially on this machine:** 11.7 s per cell at T = 300, 23.6 s at T = 600 —
and **nearly flat in `reps_per_person`**, because `identify()` fits everything but the M axis
on the first trajectory and H3 caps at `H3_MAX_TRAJ` = 8 replicates. So 1280 runs is ≈ 3.1 h
serial. The specified factors give only 384 runs, 26% of the ~1500 budget; the headroom went
into seed repetitions (3 → 10), because "anecdotal at 2–3 reps" is the standing complaint
against every rate in this README. `nonlinear_h` did **not** need to be cut.

`reps_per_person` above 8 buys nothing in the current implementation: H3 fits at most
`H3_MAX_TRAJ` trajectories, so 10 and 30 differ only by which person is drawn. That is why
the grid uses {1, 10} and not {1, 10, 30}.

It writes `recovery_map_v3.svg` (exact / spurious / missed / **undecided** per node)
alongside the other figures.

**Batch rule:** the full grid (`--T 200 400 800 1600 --noise 0.02 0.05 0.1 0.2 0.4 --keep
1.0 0.7 0.5 --nonlinear_h 0 1 --reps 20`, ≈ 9,600 runs) stays prepared and **not executed**,
on the GPU server, under the same rule. Note that the M1+N divergence bug (below) would have
poisoned ~18% of that grid's M1+N cells had it been run before this cell.

## The 32-run smoke grid, v0 → v1 → v2 (2 reps per cell — anecdotal, not a result)

Per-axis is the honest table: a gate is characterised by its false-alarm rate on worlds where
the axis is absent, not by node-level accuracy.

| axis | fires when planted (v0 → v1 → v2) | fires when absent (v0 → v1 → v2) |
|---|---|---|
| N | 0.25 → 0.25 → 0.25 | 0.00 → 0.00 → 0.00 |
| H | 0.00 → 0.38 → 0.38 | 0.00 → 0.04 → 0.04 |
| M | 0.38 → 0.13 → 0.13 | 0.29 → 0.04 → 0.04 |
| S | — → 0.56 → 0.56 | no non-stochastic world in this grid; see the control below |

| planted | exact (v0 → v1 → v2) | spurious | missed |
|---|---|---|---|
| M1 | 0.75 → 0.88 → 0.88 | 0.25 → 0.13 → 0.13 | 0.00 → 0.00 → 0.00 |
| M1+N | 0.13 → 0.13 → **0.25** | 0.38 → 0.13 → **0.00** | 0.75 → 0.75 → 0.75 |
| M1+H | 0.00 → 0.38 → 0.38 | 0.25 → 0.00 → 0.13 | 1.00 → 0.63 → 0.63 |
| M1+M | 0.38 → 0.13 → 0.13 | 0.00 → 0.00 → 0.00 | 0.63 → 0.88 → 0.88 |

**Read the v1 → v2 column carefully, because it mostly says "nothing moved", and that is
three separate facts, not one:**

* **The M1+N row moved for a reason that is not the gate.** Its trajectories are *different
  data* in v2 — the divergence fix (finding 12) changed the generator. Exact recovery
  0.13 → 0.25 and spurious 0.13 → 0.00 mix that with the Wiener null and cannot be
  attributed to either alone.
* **The N axis rates are identical because this grid cannot exercise the confound.** It runs
  at `nonlinear_h = 0` only, so there is no observation nonlinearity for the Wiener null to
  catch, and the null costs no power when there is nothing to catch — which is the good news.
  The Wiener null was nonetheless the **binding** one in **23 of 29** runs (median q95 0.022
  against the linear surrogate's 0.008): even under a linear observation map it is what the
  gate now has to clear. The condition it was built for is measured separately, below.
* **The M axis rates are identical by coincidence, not by continuity.** The statistic behind
  them changed completely: `gain_M` is now the latent-space contest (median −0.007, against a
  Markov-null q95 of +0.005), and the v0/v1 AR statistic survives only as `gain_M_diag_vs_AR1`
  (median −0.002). Two different instruments landing on 1/8 and 1/24.

Planted vs recovered switch times, M1+H rows: recall 0.58, precision 0.65, **timing MAE 1.7
steps** at ±10 tolerance.

### Controls run outside the grid

* **N gate, Wiener null.** Planted M1 observed through **tanh**, T = 600, noise 0.05, 6 seeds:
  N fires **1/6**, and the Wiener null is the binding one **6/6**. The one surviving activation
  had gain +0.401 against a *linear* null of +0.008 — the Wiener null raises that bar to
  +0.224 without killing it. On planted M1+N with a linear `h`, same seeds: N still fires
  **4/6**, exactly what the linear null alone gives. **Power unchanged, false-alarm bar raised
  28-fold.**
* **M gate, latent contest.** Planted M1 at `keep_frac` 0.5, noise 0.3: fires **2/6** (target
  was 0/6). Planted M1+M at `keep_frac` 0.7: fires **1/6** (target was ≥3/6). The gate does not
  work; findings 8 and 9 establish that the target was never reachable.
* **M gate, oracle ceiling.** The memory model given the *true* kernel beats the best free d+k
  state space by 0–11% — see finding 8 for the table.
* **S gate.** Deterministic control (`process_noise=0`), T = 600, 8 seeds × 2 noise levels:
  **0/16** false activations. Stochastic: **8/8** at noise 0.05, **4/8** at noise 0.2.
* **Ensemble, H1–H4.** N = 30, T = 400, noise 0.05. H1 passes within-person (instability
  0.036) and fails between-person by bimodality from radius 0.30 up (mode separation 4.66,
  6.44, 14.0 at radii 0.30/0.60/0.90). H2 passes on all four nodes (scale ratio 1.51–2.16
  against a limit of 10). H3 passes on M1 (mean gain −0.192) and fails on M1+M (+0.049), with
  **no overlap between the two sets of per-trajectory gains**. H4 passes on all four nodes
  (+0.23 to +0.86) and fails its negative control (−0.014).

## Findings

1. **Measurement noise no longer reads as memory — cell 1 is closed.** The M axis' false-alarm
   rate on worlds without planted memory fell from 0.29 to 0.04, and to 0/6 on the dedicated
   control. The mechanism is confirmed, not just the symptom: on those same runs AR(6) still
   beats AR(1)-on-`y` by up to +0.45, and loses to the state space. Paper 2 §9 can now say
   *which* baseline makes Markovianity a testable claim after the observation step.
2. **…and the M axis barely survives the fix.** On planted `M1+M` (AR(8), decaying kernel),
   AR(6) beats AR(1) by up to +0.24 but matches or loses to the 2-dimensional state space in
   **7 of 8** cells, and recovery fell from 0.38 to 0.13. A low-dimensional latent Markov state
   seen through noise already produces non-Markov structure in `y` that mimics a decaying memory
   kernel. This is the mirror image of finding 1 and the sharper claim: **on a single trajectory,
   an M activation is close to unearnable against an honest Markov baseline.** Paper 2 should
   state this as a limit on what the memory axis can assert, not as a detector to be tuned.
3. **Regime switching is now visible, and its timing is good — cell 2 is closed, with a caveat.**
   0/8 → 3/8 exact recovery and 0.00 → 0.38 axis power, bought with 1 false activation in 24 —
   v0's spotless 0.00 false-alarm rate was the rate of a gate that never fired. When the gate
   does fire, the recovered switch times are essentially exact (MAE 1.7 steps, and 0.0–0.5 steps
   on the low-noise control). The caveat is **recall**: 0.58, because the 25-step minimum-duration
   prior merges the short dwells that the planted chain (p_stay = 0.985) produces about a third
   of the time. The prior buys precision and timing at the cost of short regimes — a stated
   trade, not a bug. An H activation now means something; an H *non*-activation still means little.
4. **The S axis is decidable only at low measurement noise — cell 3 is closed as a negative
   result.** With the bootstrap null and the `Q/(Q+R) > 0.5` prior, the gate is clean on the
   deterministic control (0/16) and has full power at noise 0.05 (8/8), but power halves at
   noise 0.2 (4/8) and the whole smoke grid gives 0.56. The reason is visible in the
   decomposition: `Q/(Q+R)` on deterministic worlds runs 0.07–0.60 and on stochastic worlds
   0.42–0.84 — cleanly separated at noise 0.05, overlapping at 0.2. Two routes out, and both
   are already on the roadmap: lower measurement noise, or replicate trajectories (Paper 3's
   ensemble branch, cell 5).
5. **Observation nonlinearity manufactures the N axis — cell 4, and this is the one to carry
   into Paper 2.** Under a tanh observation map, N's false-alarm rate roughly triples
   (0.07 → 0.20 across 54 runs per condition) with no gain in power (0.33 → 0.33). The pipeline
   is detecting `h`, not the dynamics. This is finding 1 again on a different axis: **an N
   activation on real data is confounded with the observation map** until `h` is pinned down
   independently. Sample sizes are small — suggestive, not established.
6. **Irregular sampling destroys the M axis outright — cell 4.** AR(6) needs 6 *consecutive*
   observations and the bench refuses to interpolate. At `keep_frac` 1.0 / 0.7 / 0.5 the usable
   AR(6) rows go 594 / 57 / 0 out of 600, and `M1+M` recovery goes 0.08 / 0.00 / 0.00. The
   linear axis is untouched (M1 flat at 0.75 across all three). So sampling density is not a
   uniform quality knob: it is specifically the memory claim that dies first, and a study that
   samples at 50 % cannot make one at all.
7. **Nonlinearity still needs length.** Unchanged from v0 and not re-tested here: N was
   recovered only at T = 600, low noise. At T = 300 the surrogate null and the effect are the
   same size. This bounds the micro-world block length.

### v2

8. **The M axis is not decidable on a single trajectory, and now we know the ceiling.**
   The contest was rebuilt exactly as specified — a decaying kernel against the best free
   state space of latent dim d+k — and it does not work: at T = 600 it fires 2/6 on a world
   with *no* memory and 1/6 on a world with memory planted. Before blaming the fit, we ran an
   **oracle**: the memory model handed the true kernel and the true noise parameters.

   | condition | oracle gain over the best free d+k SSM | would fire |
   |---|---|---|
   | keep 1.0, noise 0.05 | +0.029, +0.039, +0.064, +0.076 | 3/4 |
   | keep 0.7, noise 0.05 | −0.004, −0.003, +0.040, +0.110 | 2/4 |
   | keep 1.0, noise 0.30 | +0.031, −0.004, +0.017, +0.025 | 1/4 |

   So the *ceiling* is a 0–11% gain against a `TOL` of 3%, while the estimation-noise floor of
   the same comparison — measured on a world with no memory at all — is **±0.14**. The effect
   is an order of magnitude below the noise of the instrument that is supposed to measure it.
   This is not a detector to be tuned. It is a statement for Paper 2: **on one trajectory, a
   decaying memory kernel and a slightly larger latent Markov state are not distinguishable by
   held-out prediction.**
9. **…and the confound is the model classes, not the data.** On a planted-linear world at
   `keep_frac` 0.5 and noise 0.3 the memory model beat the free state space by up to +0.14 —
   on regularisation and initialisation, not on memory. Warm-starting only the memory model
   was worth more than the entire effect being tested; matching the warm start cut the
   false-alarm rate from 5/6 to 2/6. A Markov-world bootstrap null does **not** price this,
   because it simulates from an already well-fitted state space and so cannot reproduce the
   handicap the free model suffers on real data. Any contest between model classes of
   different dimension and regularisation needs this checked before its gains mean anything.
10. **Replicates break the deadlock — this is the cell's result.** The same per-trajectory
    contest, averaged over an ensemble of the *same person* (N = 30, T = 400, noise 0.05),
    separates the two worlds with **no overlap**: planted-Markov trajectories give gains
    −0.13 to −0.27 (H3 passes, mean −0.192), planted-memory trajectories give +0.027 to
    +0.080 (H3 fails, mean +0.049). `max(M1) < min(M1+M)` across every trajectory tested.
    What one trajectory cannot decide, thirty replicates of one person decide cleanly. That
    is Paper 3's argument, and findings 2, 4 and 8 all pointed at it.
11. **Pooling breaks on set-points, not on dynamics.** Building the between-person mode
    exposed something worth stating. Dispersing **A** — each person moving differently, all
    renormalised to the same spectral radius — never breaks pooling, no matter how large the
    radius: every density stays centred on zero and H1 keeps passing. What breaks pooling is
    dispersion of **location**: a population with distinct set-points. H1's bimodality test
    goes from separation 0.20 at radius 0.15 (passes) to 4.66 at radius 0.30 and 14.0 at 0.90
    (fails). Molenaar's objection is about where people sit at least as much as about how they
    move — and only the second kind of heterogeneity is visible in a pooled density.
12. **A generator that diverged for two versions.** `M1+N`'s drift is
    `A x + α(tanh(3x₀) − x₀)`. Far from the origin the tanh saturates, so the map linearises to
    `(A − α e₀e₀ᵀ)`, **not** to `A` — drawing `A` stable never made the node stable.
    **11 of 60 seeds (18%) ran away to 1e78.** The published v0/v1 smoke grid missed it
    entirely (0/8 of its M1+N cells), which is exactly how a 32-cell grid can look healthy
    while an unrun 9,600-cell grid is already poisoned. Fixed by shifting `A` so the far-field
    matrix is the stable draw; the well is preserved, and 0/120 seeds now diverge. The lesson
    is procedural: **the reduced grid is the first thing that would have caught this, and it
    is precisely what the batch rule keeps unrun.** Cheap invariant tests on the generator are
    not optional.

### v3

13. **A second generator was broken, and the invariant test is what found it.** `M1+M`'s
    characteristic polynomial reads `1 = rho(0.5A) + sum(kernel)` at `z = 1`, and the two
    terms were fixed at 0.45 and 0.55. So **z = 1 was an exact root whenever `0.5A` had a
    real dominant eigenvalue — 60 of 200 seeds (30%)**. Those trajectories were integrated
    random walks, not the stationary decaying-kernel memory the node is named after, and
    nothing caught them: they do not blow up to 1e78 like `M1+N` did, they just drift. At
    T = 800 only 1 seed in 200 exceeded the magnitude bound. The fix keeps the kernel shape
    and solves for its mass so the companion radius lands on `rho` = 0.9, the same target
    every other node is normalised to; mass moved 0.55 → 0.70, radius now spans
    [0.799, 0.900] over 60 seeds, and the kernel still decays monotonically over two orders
    of magnitude. **Two of four nodes have now shipped broken.** The lesson is not about
    these two nodes: a magnitude check is a symptom test, and the structural condition has
    to be asserted on its own.
14. **Only location dispersion breaks pooling — now isolated, not just asserted.** With the
    two radii separated, `A_radius` can be pushed to 0.9 with `loc_radius = 0` and H1 still
    passes, with a between/within variance ratio of 0.008. People moving under visibly
    different laws pool fine. Holding the laws identical and scattering only the set points
    is what breaks it. **The boundary is a number: H1 flips at `loc_radius` between 0.65 and
    1.01 across seeds, median ≈ 0.84**, in state units, where the within-person standard
    deviation is ≈ 0.5. The declared criterion is between/within > 1, and that is what the
    boundary measures — not a threshold chosen to land there.
15. **The M axis has a third verdict, and the recovery map now reports mostly that.**
    Single trajectory → `nao identificavel`; ≥ 10 replicates of one person → decided by H3.
    On the 30-replicate ensembles the separation is clean and unchanged by the generator
    fix: planted-Markov trajectories give −0.13 to −0.27, planted-memory ones +0.03 to
    +0.08, **margin 0.157 with no overlap**. The consequence for the grid is blunt and worth
    stating plainly: **every cell of the recovery grid is a single trajectory, so the M axis
    is `nao identificavel` in 100% of them.** The map can no longer say anything about
    memory, which is the honest version of what it was doing before — reporting a 0.04
    false-alarm rate for a test whose effect size is an order of magnitude under its own
    noise floor.

### v4

16. **The switched node had no invariant at all, only an argument.** `M1+H` asserted
    ρ(A) < 1 and ρ(A2) < 1 separately and leaned on "slow switching" for the rest. That
    certifies nothing: two individually stable matrices can be switched into divergence, and
    the bench's own regression test now contains the counterexample — opposite shears at
    ρ = 0.9 each, whose product has ρ = 26.6. The node now requires a **common quadratic
    Lyapunov function**, which certifies stability under *arbitrary* switching, far more than
    the node needs and the point is that it is checkable. **24.8% of A2 draws are rejected**
    (mean 0.33 redraws per node, max 7, none at all for 80.5% of nodes). Two conditions were
    measured before choosing: the Kronecker condition ρ(A1⊗A1 + A2⊗A2) < 1 is also sufficient
    but rejects 60.5%, so the LMI won. Three of four nodes now carry a condition that is not
    trivially true by construction; `M1` and `M1+N` carry ρ < 1, which is.
17. **The replication factor is nearly free, and capped.** `--reps_per_person` costs almost
    nothing beyond generating the trajectories — 11.7 s per cell at T = 300 whether the cell
    is 1 trajectory or 30 — because `identify()` fits every axis but M on the first trajectory
    and H3 stops at `H3_MAX_TRAJ` = 8. The corollary matters for grid design: **10 and 30
    replicates give H3 identical information.** They differ only in which person is drawn.
    Anyone wanting to measure what 30 replicates buy has to raise that cap first.
18. **The ensemble M axis is not infallible, and the figure had to be rebuilt to say so.**
    The first version of `h3_replicas` showed both families already separated at one
    replicate, which would have contradicted the claim it was drawn to support. Measuring
    first: with **one trajectory per person across 10 people**, planted-M1 gains run
    −3.26 to +0.006 and planted-memory gains −0.335 to +0.049. They overlap, and only 3 of
    10 memory worlds clear `H3_TOL` — that is the single-trajectory problem, and it lives
    *between* people, not between replicates of one. Averaging over replicates pulls each
    person onto their own value; it does not rescue a person whose structure the contest
    handles badly. On the 8 ensemble cells measured at 10 replicates there is already one
    false positive (`M1+H` at T = 300) and one false negative (`M1+M` at T = 300). The clean
    0.157 margin quoted in v3 was one person, 30 replicates, T = 400. Grid v3 is what turns
    any of this into a rate.

## Grid v3 — EXECUTED, 1280 runs

Pre-registration hash `1bb2510`, approval 2026-09-11. Started 15:43:54, finished 17:11:04:
**1 h 27 min** at `--jobs 21` on 22 logical cores. Command exactly as pre-registered:

```bash
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7     --nonlinear_h 0 1 --reps_per_person 1 10 --reps 10 --jobs 21 --out out_v3
```

**The pre-registration's cost estimate was wrong by a factor of 2** — it said 3.1 h serial
where the arithmetic gives 6.3 h (`(n/2)·(a+b)/2` divides by two once too often). The number
is wrong in a document that was pre-registered before the run, so it stays wrong there and is
corrected here rather than edited back. Nothing else in the pre-registration was affected.

### Per node × replication factor

| node | reps | n | exact | spurious | missed | undecided |
|---|---|---|---|---|---|---|
| M1 | 1 | 160 | 0.875 | 0.125 | 0.000 | 0.000 |
| M1 | 10 | 160 | 0.875 | 0.125 | 0.000 | 0.000 |
| M1+N | 1 | 160 | 0.256 | 0.075 | 0.725 | 0.000 |
| M1+N | 10 | 160 | 0.181 | 0.231 | 0.725 | 0.000 |
| M1+H | 1 | 160 | 0.312 | 0.256 | 0.531 | 0.000 |
| M1+H | 10 | 160 | 0.225 | 0.412 | 0.506 | 0.000 |
| M1+M | 1 | 160 | 0.000 | 0.188 | 0.000 | **1.000** |
| M1+M | 10 | 160 | 0.119 | 0.188 | 0.819 | 0.000 |

The pre-registration predicted the M axis would be `nao identificavel` in 100% of
single-trajectory cells. It is: exactly 1.000, which is the one prediction the grid confirms
without qualification.

### False-alarm rate per axis on a linear world (node `M1`, n = 320)

| axis | fires |
|---|---|
| N | 0.044 |
| H | 0.081 |
| M | 0.003 |
| S | 0.637 (every world here is stochastic, so this is power, not false alarm) |

Across all worlds where the axis is absent (n = 960): N 0.106, H 0.107, M 0.070.

### What the grid says about each preliminary figure

**`wiener_null` — confirms the false-alarm claim, weakens the power claim.** At the
preliminary's own operating point (T = 600, noise 0.05, keep 1.0) the grid gives N firing
**0/20** on tanh-observed linear worlds where the preliminary reported 1/6, and **0.30** power
on planted nonlinearity where the preliminary reported 4/6 = 0.67. So the defence is better
than advertised and the detection is half as good. The Wiener null is the binding one in
**76.8%** of all 1280 runs, which confirms the preliminary's 23/29.

**But the Wiener null does not do the job it was built for.** Over the whole grid, N's
false-alarm rate is 0.096 under a linear observation and 0.120 under tanh — almost the same.
The null was introduced to neutralise a confound specific to tanh; the grid shows N simply
carries a ~10% false-alarm rate either way. And under tanh the false alarms concentrate on
**`M1+H`: 0.225**, against 0.075 for `M1` and 0.056 for `M1+M`. Regime switching seen through
a saturating sensor reads as nonlinearity. That is a new confound, not the one v2 was chasing.

**`h3_replicas` — contradicts it.** The preliminary showed 3 of 3 planted-memory people
ending above `H3_TOL` and all planted-Markov people below, and was captioned as the figure
that justifies deciding M on the ensemble. Over 160 cells per node at 10 replicates the M
axis fires on **18.1% of `M1+M`** — and on **28.1% of `M1+H`**, a world with no memory at all.
The axis fires more often where memory is absent than where it is planted. It is close to
clean on `M1` (0.6% false positives), so it is not noise: it is specifically confusing regime
switching for memory. Three people were not a sample.

**`h1_location_vs_law` — the grid cannot speak to it.** `out_v3` contains no between-person
ensembles; `A_radius` and `loc_radius` never vary in the grid, which runs within-person
replicates only. The preliminary figure stands on its own 8-point sweep and this run neither
confirms nor weakens it. Testing H1 at grid scale needs a different grid.

### Other rates worth recording

* **H axis**: power 0.481, false alarm 0.107. Power tracks length and noise as expected —
  0.750 at T = 600 / noise 0.05, down to 0.287 at T = 300 / noise 0.3.
* **Switch timing** degraded badly against the 8-row v2 sample: recall 0.269 (was 0.58),
  precision 0.433 (was 0.65), **timing MAE 4.16 steps (was 1.7)**, over 320 rows.
* **S axis**: fires on 0.563 of worlds, all of which are stochastic — a 44% false-negative
  rate, consistent with v1's finding that S is undecidable above measurement noise ≈ 0.1.
* **`M1+H` is the worst node in the map**: exact 0.269, spurious 0.334. Its regime switching
  is what the N axis and the M axis are both mistaking for their own signal.

Figures over the grid: `out_v3/recovery_map_v3.svg`, `out_v3/wiener_null.svg`,
`out_v3/h3_replicas.svg`, produced by `python make_figures_v3.py`.

## The switching null, and the question it answered

Grid v3's dominant finding was that a two-regime world fires N on ~25% of runs and,
over ten replicates, M on 28% — more than the memory world's 18%. Both gates were
missing the same null: **could a stable linear SWITCHING process have produced this?**
`sim/switching_null.py` fits the two-regime model already in the bench, simulates from
the fit (regimes from the fitted chain, noise resampled from the fit's own residuals per
regime), and recomputes whichever statistic the gate uses. Surrogates are simulated only
from pairs admitting a common quadratic Lyapunov function; when the fitted pair does not,
both matrices are scaled by the largest gamma that does, and the gamma is reported.

### The N axis now clears three nulls

| null | asks | where |
|---|---|---|
| linear | could a linear process **in y** have done this? | `pipeline.nonlinear_null` |
| Wiener | could a linear **latent** process seen through a static `h`? | `wiener.py` |
| switching | could a stable **piecewise-linear** process? | `switching_null.py` |

Measured over 20 seeds at T = 600, noise 0.05, against the two-null gate on the same seeds:

| world | 2 nulls | 3 nulls |
|---|---|---|
| `M1+H` (false alarm) | 3/17 | **2/17** |
| `M1+N` (power) | 6/19 | **5/19** |
| `M1` (false alarm) | 0/20 | 0/20 |

The switching null is the binding one in **15/20** of two-regime worlds and only **2/20**
of planted-nonlinear ones: it bites where it should. It costs one detection in six and
removes one false alarm in three.

### The M axis: the null did not rescue it

The same null in H3, over 20 seeds with 10 replicates at T = 600: the M axis fires on
**7/20** two-regime worlds with the null against **8/20** without it, while power on
memory worlds holds at 10/20. **One false alarm removed in eight.** The target for this
cell was ≤ 2/20 and it was not met.

It is not a mis-specified null. The fitted dwell times track the planted ones closely
(60.6 against 60, 43.4 against 50, 89.9 against 75), so the surrogate really is a
switching process of the right speed. A switching surrogate simply does not reproduce the
memory-like structure the real two-regime trajectory carries.

## Is M an axis, or a case of H?

**M and H are separable at this resolution.**

Fitting both candidate models to the same trajectories and scoring both one step ahead on
the same future block — 40 worlds per node, T = 600, 10 replicates, 3 fitted per world,
no `truth` used to fit anything:

| planted | memory model beats switching | median relative gain |
|---|---|---|
| `M1+M` | **90%** of worlds | **+0.089** |
| `M1+H` | **2.5%** of worlds | **−0.274** |

Mann-Whitney **z = +7.28**. The overlap is small: the best switching world reaches +0.032,
the worst memory world −0.397.

**So the confusion in grid v3 is not the model classes being indistinguishable — it is the
gate never asking the question that distinguishes them.** The M gate compared a memory
kernel against a *free state space*; it never compared it against a *switching model*. A
switching world beats the free state space for the same reason a memory world does — both
need more than one linear map — so the gate fired on both. Adding a switching null outside
the contest cannot fix that, which is exactly what the 7/20 above shows. The fix had to be
structural, and the next section is that fix.

## The M contest with two rivals

The memory kernel now has to beat **both** the free linear-Gaussian state space **and** the
two-regime model of `switching.py`, each by at least `H3_TOL`, on the same future block.
`PASS` still means "effectively Markov", so the gate passes as soon as *either* rival holds
the kernel to within tolerance, and the binding rival is reported.

Both gates on the same 40 worlds per node, T = 600, 10 replicates, 3 fitted
(`python scripts/m_vs_h.py`, figure `out_figuras/m_vs_h.svg`):

| planted | old gate (one rival + null) | new gate (two rivals) | |
|---|---|---|---|
| `M1+H` | **11/40** = 0.275 | **1/40** = 0.025 | false alarm |
| `M1+M` | **20/40** = 0.500 | **21/40** = 0.525 | power |

**The false alarm drops by a factor of eleven and the power does not move.** Which rival
binds says why, and it is as clean as the rates: on two-regime worlds the switching model
is the binding rival in **40 of 40**; on memory worlds it is the free state space in **39
of 40**. The new competitor bites exactly where it should and nowhere else. This is
guaranteed in one direction — the new statistic is `min` of the two gains, so every world
the new gate fires on, the old one fired on too — which makes the cost measurable, and it
is 1 world in 40.

**The declared power target of 12/20 was not met, and the number is registered rather than
the threshold moved.** Over 20 seeds the three-way contest fires on 10/20 with 3 replicates
fitted and 9/20 with 8. More replicates do not help, so this is not a sample-size problem:
seven of the twenty statistics land between +0.002 and +0.028, just under `H3_TOL` = 0.03.
Since the old comparator had the same ~50% power, the shortfall is not the new rival's
doing — it is a question about `H3_TOL` and about T, and it is not attempted here.

## Grid v4 — EXECUTED, 1280 runs

```
python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \
    --nonlinear_h 0 1 --reps_per_person 1 10 --reps 10 --jobs 21 --out out_v4

pre-registration   PREREGISTRO_v3.md, sha256 471d67e5...9a8c79, committed at 9586e72
start              2026-09-12 06:33:49 -03:00
end                2026-09-12 07:53:59 -03:00
wall               1 h 20 min 10 s        serial estimate was 7.8 h
output             out_v4/, 1280 rows, EXIT=0
```

`git diff 9586e72 -- sim/` is empty: the code that ran is the code the pre-registration
describes.

### The registered hypothesis

Pre-registered before the run, at `reps_per_person` = 10, T = 600, noise 0.05:
**false alarm of M on `M1+H` ≤ 0.05 and power on `M1+M` ≥ 0.50.**

| | registered | measured | |
|---|---|---|---|
| false alarm `M1+H` | ≤ 0.05 | **0.000** (0/40) | **confirmed** |
| power `M1+M` | ≥ 0.50 | **0.150** (6/40) | **contradicted** |

The false alarm is confirmed decisively and the power prediction is wrong by more than a
factor of three. Both halves are worth reading, and the second one is mine to answer for.

### One sentence per axis, v3 → v4

**N — confirms, and the price is now visible.** False alarm 0.106 → **0.058**, nearly
halved by the third null, exactly the direction the 20-seed preliminary showed; the cost is
real and was also predicted — power 0.275 → 0.200, and `M1+N` runs that miss the axis
entirely go from 0.725 to 0.800.

**H — unchanged, to three decimals.** Fires 0.481 when planted and 0.107 when absent in
both grids, with identical switch-timing recall (0.269), precision (0.433) and MAE (4.158
steps); nothing in the last two cells touched the H path, and the grid says so rather than
leaving it assumed.

**M — confirms the false alarm, contradicts the power.** Firing when the structure is
absent collapses 0.070 → **0.013**, and on `M1+H` specifically the spurious-label rate goes
0.334 → **0.113** while exact identification rises 0.269 → 0.409; but firing when memory IS
planted falls 0.091 → 0.078 (0.150 → 0.058 among replicated designs), so the second rival
bought a threefold drop in false alarms at a real cost in detections.

**S — unchanged.** 0.563 → 0.562 with no absent cells to test against, which is the same
non-statement the v3 grid made and remains the weakest axis in the bench.

### Why the power prediction was wrong

Two reasons, and only the first is a measurement artefact.

**I generalised from the easiest corner.** The 0.525 that went into the hypothesis came
from 40 seeds at T = 600, noise 0.05, `keep` = 1.0, linear `h` — one cell of the design.
The grid's matching cell gives 4/10, compatible with 0.525 at that sample size. Everywhere
else is worse, and the marginals say why:

```
keep  1.0  0.225      keep  0.7  0.087        missingness costs the most
noise 0.05 0.250      noise 0.3  0.062
T     300  0.212      T     600  0.100        MORE data LOWERS power
h  linear  0.163      h    tanh  0.150        the observation map barely matters
```

That T = 600 is *worse* than T = 300 is not a bug: the contest is relative, so a longer
series lets the free state space fit a better model too, and the memory kernel's margin
over it shrinks.

**The second rival is not scored fairly when data are missing.** `memory_contest` scores
the memory model with `predict_mse`, which runs the Kalman filter across the whole grid and
scores at observed times — so with `keep` = 0.7 it is often predicting several steps ahead,
across a gap. The switching rival is scored on `regular_pairs`, which keeps only (t, t+1)
pairs where both are observed — always exactly one step from a measured value. Under
missingness the two rivals are answering different questions, and the easier one wins:

```
M1+M, reps 10, noise 0.05    median gain vs state space   vs switching   binding rival
  keep 1.0                            +0.017                  +0.092      state space 38/40
  keep 0.7                            +0.012                  -0.085      switching    31/40
```

**The false-alarm result does not depend on this.** At `keep` = 1.0 there are no gaps, so
the scoring is symmetric by construction, and `M1+H` still fires on 1 of 76 replicated runs
there. The defect costs power under missingness; it does not manufacture the win.

Figures: `out_figuras/axes_v3_vs_v4.svg` (the four axes across the two grids, and
the M axis by design cell), from `python scripts/recovery_map_v4.py`; and
`out_v4/recovery_map_v4.svg`, the node-level map, redrawn from the grid's own rows by
`python scripts/replot_v4.py`.

## The M axis, re-measured on one scoring problem

The v4 grid's power figure for M was **not interpretable**, and the fault was mine. Under
irregular sampling the competitors were scored on different problems: `predict_mse` runs the
Kalman filter across the whole grid and scores at observed times, so with `keep` = 0.7 the
memory model was often predicting across a gap, while the switching rival scored only on
(t, t+1) pairs with both ends measured — always one step from a measured value. The easier
problem won: the switching rival was the binding one in 31 of 40 memory worlds at
`keep` = 0.7, against 2 of 40 with complete data.

There is now **one eligibility predicate**, `observe.scorable_steps`, used by every
competitor in the contest: a step counts only if t and t−1 are both observed, which is what
the most demanding model needs. Nothing is interpolated — a step whose predecessor was never
measured is dropped from the *score*, not reconstructed, and models still *fit* on whatever
their own likelihood can reach.

### Before and after, per design cell

`M1` × `M1+H` × `M1+M` at T {300, 600} × noise {0.05, 0.3} × keep {1.0, 0.7}, 10 replicates,
linear `h`. Before is the v4 grid's matching cell (10 seeds); after is
`python scripts/remeasure_m.py` (8 seeds). The two runs draw different seeds, so single
cells are noisy and the aggregates are the thing to read.

| planted | T | noise | keep | before (v4) | after | |
|---|---|---|---|---|---|---|
| `M1+M` | 300 | 0.05 | 1.0 | 5/10 = 0.50 | 4/8 = 0.50 | power |
| `M1+M` | 300 | 0.05 | 0.7 | 1/10 = 0.10 | **3/8 = 0.38** | power |
| `M1+M` | 600 | 0.05 | 1.0 | 4/10 = 0.40 | 4/8 = 0.50 | power |
| `M1+M` | 600 | 0.05 | 0.7 | 0/10 = 0.00 | **2/8 = 0.25** | power |
| `M1+M` | 300 | 0.3 | 1.0 | 0/10 = 0.00 | 0/8 = 0.00 | power |
| `M1+M` | 300 | 0.3 | 0.7 | 2/10 = 0.20 | 0/8 = 0.00 | power |
| `M1+M` | 600 | 0.3 | 1.0 | 1/10 = 0.10 | 0/8 = 0.00 | power |
| `M1+M` | 600 | 0.3 | 0.7 | 0/10 = 0.00 | 1/8 = 0.12 | power |
| `M1+H` | 300 | 0.3 | 1.0 | 0/10 = 0.00 | 2/8 = 0.25 | false alarm |
| `M1+H` | 300 | 0.3 | 0.7 | 1/10 = 0.10 | 2/8 = 0.25 | false alarm |
| `M1+H` | all other cells | | | 0/60 | 0/48 | false alarm |
| `M1` | every cell | | | 0/80 | 0/64 | false alarm |

Aggregated, which is what the sample sizes support:

```
                        before (v4)        after
M1+M  keep 1.0           0.250             0.250      regression: unchanged, as required
M1+M  keep 0.7           0.075             0.188      the artefact, removed
M1+M  keep 0.7, noise 0.05   0.050         0.312      where the asymmetry actually bit
switching binds in M1+M, keep 0.7:  31/40  ->  4/16
median gain over the switching rival there:  -0.085  ->  +0.073
```

### Which explanation survives

**(a) and (b), in different cells: the missing-data power WAS an artefact of the asymmetry
and rose fourfold once the scoring was symmetrised (0.05 → 0.31 at noise 0.05), and what
remains is a real threshold effect — with complete data the statistics land continuously
around `H3_TOL` = 0.03 (median +0.034, with five of sixteen between 0 and the threshold), so
the gate stops where the threshold is put.**

(c) is not needed for those, but it is needed for one thing the threshold cannot fix: at
noise 0.3 a minority of planted-memory worlds produce a *negative* statistic — the memory
model loses outright — and no threshold turns a loss into a detection.

### The threshold curve, not a threshold

Since (b) is part of the answer, the sweep is owed. Each world's binding statistic is
recorded, so the sweep costs no refits: the axis fires exactly when `stat > tol`.

| `H3_TOL` | power `M1+M` | false alarm `M1+H` | false alarm `M1` | |
|---|---|---|---|---|
| 0.01 | 0.516 | 0.281 | 0.094 | all cells |
| 0.02 | 0.359 | 0.109 | 0.016 | |
| **0.03** | **0.219** | **0.062** | **0.000** | current |
| 0.05 | 0.156 | 0.047 | 0.000 | |
| 0.01 | **0.688** | **0.000** | 0.000 | noise 0.05 only |
| 0.02 | 0.562 | 0.000 | 0.000 | |
| **0.03** | **0.406** | **0.000** | 0.000 | current |
| 0.05 | 0.312 | 0.000 | 0.000 | |

**At noise 0.05 the false alarm is zero at every threshold down to 0.01, so lowering the
threshold there would buy 0.406 → 0.688 of power for nothing.** The entire cost of a lower
threshold comes from the noise 0.3 cells. No threshold is chosen here: choosing one is a
statement about which error is worse, which is not a measurement.
Figure: `out_figuras/h3_tol_tradeoff.svg`, from `python scripts/h3_tol_sweep.py`.

### This contradicts the number above

**The grid v4 block above reports M-axis power of 0.15 and the registered hypothesis as
contradicted. With symmetric scoring the comparable figure is 0.25, and at noise 0.05 with
complete data it is 0.50.** The v4 numbers stand as what that pre-registered grid produced;
they are not what the gate does now, and the paper should quote neither as "the power of the
M axis" without the sampling condition attached.

## The decision bench (`decision/`) — a second bench, and what it plants

The bench above plants **dynamics** and asks whether the pipeline recovers it. `decision/`
plants **policy**: synthetic worlds in which the *correct action* is known by construction,
recorded in `truth` and never handed to a decision module. It exists to test Paper 4, which
declares three adversarial models with an explicit failure condition — *if M1 does not beat
M0 the propositional evidence layer has no operational role; if M2 does not beat M1 the
warrant layer leaves the architecture.*

It is the same repository and the same machinery. `decision/worlds.py` draws its latent from
the `M1` node of `sim/generators.py`, observes it through `sim/observe.py`, the one estimator
every model shares is `sim/statespace.py`'s EM fit, and the eligibility predicate is built on
`observe.scorable_steps`. Only the decision layer above the observation channel is new.

Four families, one distinction each. Each also carries **baseline** steps where the evidence
is sufficient and concordant and the correct action is to act — without them a constant
policy would score a family perfectly and the family would measure nothing.

| family | what is on the record | correct action |
|---|---|---|
| `W-absence` | nothing admissible about `p` (the record is not empty: there is an item about `q`) | `OBSERVE` |
| `W-conflict` | two items, **same** scope, opposite values | `PROBE` |
| `W-scope` | two items, **different conditions**, opposite, each true in its own | `COMPARE` — never a deficit of S |
| `W-pause` | the evidence decides and an authorized pause is in force | `WAIT` |

**Non-vacuity is asserted, not hoped for.** For each family, the policy that collapses
exactly the distinction that family plants (`epistemic.blind_action`: N→B, B→N, drop C, drop
Ω) is wrong on **0.765 / 0.790 / 0.892 / 0.828** of the steps, measured over 20 seeds against
a declared floor of 0.60.

### The three models, and the ablation

`M0` is a policy over b(t) and the observed context, where the evidence arrives as a scalar
aggregate — *count and mean* — over exactly the items Λ would admit. Nothing is withheld from
M0 except structure; it has the count, so separating "nothing known" from "as much either
way" is inside its reach and its failures cannot be blamed on a crippled baseline. `M1` adds
Λ(t): T/F/B/N per proposition, per scope, with provenance attached but **not acted on** —
requiring a provenance is a norm, not a reading. `M2` adds Ω(t): warrant per action under a
frozen χ. **`M1+pausa` is the ablation** — M1 plus one line, never act under a standing
authorization — and it is what keeps the ω claim from being a demonstration.

The estimator is the *same object* in all four, and the test compares the **fitted
parameters** (A, B, Q, R, loglik), not the types: a better Kalman filter must never be
creditable to the epistemic layer. All four are scored on the *same index set*, asserted as
a set and not as a count, because M2 abstains where M1 acts and a model allowed to pick its
own denominator wins by answering less.

χ lives in `decision/warrants.yaml`, is hashed into `decision/warrants.sha256`, is verified
on every load and on every grid cell, and the same hash is written into
[PREREGISTRO_v4.md](PREREGISTRO_v4.md). This is the vulnerability Paper 4 declares itself
(D8), turned into an invariant: a rule cannot be adjusted after seeing a result without
leaving a commit that says so.

### What the pilot says — 64 cells, not the grid

`python -m decision.bench --T 300 --flip 0.05 0.25 --reps 8`, one T and one measurement
noise. Figure: [decision_M0_M1_M2.svg](out_figuras/decision_M0_M1_M2.svg), one panel per
family, three bars, the external criterion of that family, with the ablation drawn as a tick
across the M2 bar.

| family | primary external criterion | M0 | M1 | M2 | M1+pausa |
|---|---|---|---|---|---|
| `W-absence` | `request_resolution_rate` ↑ | 0.644 | 0.644 | **0.688** | 0.644 |
| `W-conflict` | `request_resolution_rate` ↑ | 0.561 | 0.561 | **0.603** | 0.561 |
| `W-scope` | `deficit_inference_rate` ↓ | 1.000 | **0.243** | **0.243** | 0.243 |
| `W-pause` | `pause_violation_rate` ↓ | 1.000 | 1.000 | **0.000** | **0.000** |

Accuracy against the planted action, with the record ceiling in brackets: `W-absence`
0.945 / 0.945 / **1.000** (1.0); `W-conflict` 0.944 / 0.944 / **1.000** (1.0); `W-scope`
0.110 / 0.724 / **0.756** (0.756); `W-pause` 0.163 / 0.163 / **1.000** (1.0), with the
ablation at 0.957.

### The sentence the paper asks for, written from the numbers

**Λ earns its place on exactly one family of four.** On `W-absence` and `W-conflict` M1 and
M0 are identical to three decimals on every criterion, because a scalar aggregate that
carries the item count already separates N from B. The whole operational case for the
propositional layer, in this bench, is `W-scope`: a condition difference and a conflict have
the same aggregate, and only a layer that keeps C can tell them apart. M0 reads **every**
condition difference as a property of S — `deficit_inference_rate` 1.000 against M1's 0.243 —
and the probe it then issues cannot resolve what it asked. That is a real result and a narrow
one, and it was predicted in the pre-registration before it was measured.

**ω survives, but not for the reason it is usually argued for.** On `pause_violation_rate`
M2 and `M1+pausa` are both exactly 0.000: on the pause criterion itself, the warrant layer
buys nothing a boolean flag would not have bought, and if that were Ω's only claim it should
be removed and replaced by the flag. What separates them is the other clause — provenance.
M2 refuses to act when no admissible item followed a support that was actually given
(`unsupported_counterfactual_rate` 0.000 against 0.044 for both M1 and the ablation), and
that clause binds in the two families where no pause exists at all. **So: ω stays, and the
pause is not what pays for it.** If the grid removes the provenance gap, ω reduces to a flag
check and leaves.

The third number worth writing down is the one that limits both claims: evidence noise. At
`flip_p` = 0.25, M1's `deficit_inference_rate` on `W-scope` goes from 0.093 to 0.394. The
layer does not stop working; the sensor does. And the `W-scope` record ceiling is 0.756, not
1.0, because a cross-condition disagreement on a record may be a flipped item and no reader
of the record can tell — M2 sits exactly on that ceiling.

### Grid — PREPARED, NOT RUN

```bash
python -m decision.bench --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \
    --flip 0.05 0.25 --reps 20 --jobs 8 --out out_decision_v4
```

4 families x 2 T x 2 measurement noises x 2 `keep` x 2 `flip_p` x 20 seeds = 1280 cells,
5120 rows. Cost **measured on 8 real cells**, idle machine: 0.27 s at T=300 and 0.54 s at
T=600, so 8.6 min serial — two orders of magnitude below the dynamics grid, because a cell
fits one state space and the rest is policy. Reported per family and never pooled: pooling
would let the family where the warrant layer is decisive pay for the families where it
changes nothing. It does not run until the approval line in `ESTADO_CELULA.md` carries a
date (Modo Celular, rule 5).

## Files

```
sim/generators.py          176   SIM-1 generators, a boundedness condition per node, split seed streams
sim/stability.py            89   common quadratic Lyapunov function for the switched node, no SDP package
sim/observe.py              54   observation map h, sampling, regular-pairs design, pair times
sim/statespace.py          183   linear-Gaussian SSM by EM (Kalman + RTS), Q/R split, deterministic null
sim/switching.py           195   sticky-EM switching regression, min-duration decode, switch matching
sim/wiener.py              113   Wiener surrogate for N: linear latent dynamics + fitted static h
sim/switching_null.py      129   switching surrogate for N, Lyapunov-projected; diagnostic only for M
sim/memory.py              220   the M contest: companion AR(p) kernel vs free SSM of latent d+k
sim/ensemble.py            125   ensembles; within-person, and between-person with TWO radii
sim/density.py             399   Paper 3 gates H1-H4; the M contest with TWO rivals; tri-state verdicts
sim/pipeline.py            319   blind identification: M0, M1, N (three nulls), H, M (two rivals), S
sim/recovery.py            269   grid runner (--jobs, --reps_per_person), per-axis rates, CSV/JSON, figures
make_prereg.py             353   writes PREREGISTRO_v3.md by introspecting the modules
decision/record.py          81   scope (S,O,C,t), evidence, provenance, the authorization record
decision/worlds.py         195   SIM-7: four families whose correct action is planted in `truth`
decision/epistemic.py      137   Lambda(t): T/F/B/N per proposition per scope; the family collapses
decision/warrants.yaml       -   chi, DECLARED AND FROZEN; hashed into decision/warrants.sha256
decision/warrant.py        117   Omega(t): warrant per action, hash guard, remedy per denial
decision/eligible.py        33   the single eligibility predicate, built on observe.scorable_steps
decision/models.py         153   M0 / M1 / M2 and the M1+pausa ablation; ONE shared estimator
decision/metrics.py        156   the external criteria, on denominators defined by the world
decision/bench.py          134   the decision grid runner: CSV, per-family summary, cost probe
decision/figures.py         91   decision_M0_M1_M2.svg from the CSV, never recomputed
make_prereg_decision.py    356   writes PREREGISTRO_v4.md by introspecting decision/
scripts/decision_nonvacuity.py 53   the non-vacuity of the four families, measured over seeds
make_figures.py            185   the three paper figures, computed from the bench
scripts/m_vs_h.py          116   the old M gate and the new one, scored on the same worlds
tests/test_smoke.py         36   shapes, pause invariant, truth never leaks
tests/test_boundedness.py  151   the generator invariants: magnitude, structure, common Lyapunov P
tests/test_gates.py        272   the three nulls of N, the tri-state M axis, the replication factor
tests/test_density.py      314   ensemble modes, the truth seam, H1-H4, the three-way M contest
tests/test_prereg.py        46   the pre-registration matches the code it describes
tests/test_decision_worlds.py    125   the planted action, and the non-vacuity of each family
tests/test_decision_epistemic.py  86   the four values, scope separation, the collapses
tests/test_decision_warrants.py  118   the frozen hash, the rules biting, the mutation test
tests/test_decision_models.py    115   one estimator, one index set, the layers actually differing
tests/test_decision_metrics.py   110   shared denominators, the record ceiling, the instruments
```

Over the 200-line house limit: `memory.py` 220, `density.py` 399, `pipeline.py` 319, `recovery.py` 269, `make_prereg.py` 353, `make_prereg_decision.py` 356, `test_gates.py` 272, `test_density.py` 314. The gate logic,
the four Paper 3 gates and the grid runner are the places where splitting costs more in
indirection than it buys in length. `memory.py` is the one candidate that should actually be
split — once the M axis is either repaired or retired, most of it goes with it.

Every gate in `density.py` returns `(passed, stat, note)` where `note` spells out the
stopping rule, so a reader can disagree with a threshold instead of reverse-engineering it.

## Next cells (in order of value)

1-6. ~~Cells 1-5 of the original roadmap, plus the Wiener null.~~ **Done (v1, v2).**
7. **Run the reduced grid** (command above) once the approval line carries a date, and
   re-derive every rate in this README from 960 runs instead of 32. Everything under
   "Findings" is still anecdotal by the bench's own standard. Do `git init` first, so the
   pre-registration has a commit instead of a content hash.
8. **Repair or retire the single-trajectory M contest.** It is now formally
   `nao identificavel`, which is honest but is not an answer. Two routes, unchanged from
   v2: compare `d+k` against `d+k` with different *structure* rather than `d+k` against
   `p·d`, or retire it and test the axis only over replicates, where it already works.
9. **An invariant test for the two nodes that have not been caught yet.** `M1` and `M1+H`
   pass the boundedness test today, but the test only exists as of v3 and neither was ever
   checked structurally before. `M1+H`'s condition is the weak one: two stable matrices plus
   slow switching is not sufficient in general, and the joint spectral radius is not computed.
10. **H5–H7** of Paper 3's Table 3, on the ensemble machinery now in place.
11. **A null for a non-monotone `h`.** The Wiener null Gaussianises by rank, so it assumes
    `h` is monotone. This is the blocker for cell 6, not an aside.
12. **SIM-6: an LLM agent as `h`.** Still deliberately closed. It is an `h` nobody can write
    down, so it arrives as the adversary of the N gate, and the defence it would be tested
    against has a known hole (item 11). Opening it first means testing the attack and the
    defence at the same time.
13. **Run the decision grid** (command above) once its approval line carries a date, and
    re-derive the four panels from 1280 cells instead of 64. Everything in the decision
    section is a pilot by this bench's own standard.
14. **A second family in which Λ has a case to make.** The pilot says the propositional
    layer earns its place on `W-scope` and nowhere else. Either that is the finding — and
    Paper 4 should claim scope rather than Belnap in general — or a family exists that
    turns on the N/B distinction in a way a scalar count cannot reach, and it has not been
    written yet. The honest version of this cell starts by trying to *fail* to find one.
15. **A competing χ.** The bench measures whether the declared warrant rules survive
    external criteria; it says nothing about whether a different χ would do better. The
    frozen-hash machinery is what would make that comparison honest, and it already exists.
16. **The N-axis debt, still untouched.** Inherited from the previous cell and unchanged:
    the N axis is defended by three nulls and a single comparator, and the lesson this
    repository has now paid for twice — a null bolted on outside does not repair a
    comparator that asks two different questions — applies there in full.

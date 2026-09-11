# mdaa_bench — SIM-1 / SIM-4 recovery bench, v3

Test bench for Paper 2 §9.1 (and, later, Paper 3 §11): trajectories are generated
from **known** lattice nodes, observed through a noisy/irregular observation map, and
handed **blind** to an identification pipeline. The output is a *recovery map*: how often
the pipeline recovers the planted node, activates a spurious axis, or misses a planted one,
across measurement noise × length × sampling × observation nonlinearity.

The bench validates the **pipeline**, never the construct. That sentence is in both papers.

**v1 closed cells 1–4; v2 closed cell 5; v3 closes the three holes v2 left open.** The
direction has not changed: every version makes the pipeline *more sceptical* and the axes
harder to earn. v3 does three things. It makes boundedness a **generator invariant** with a
test — and that test immediately found a second broken node. It splits between-person
dispersion into the two radii that were welded together, which shows that only one of them
can break pooling. And it gives the M axis a **third verdict**: on a single trajectory the
answer is "nao identificavel", not False, because the design cannot decide and pretending
otherwise lets the recovery map score a non-test as a correct rejection.

There is also a [pre-registration](PREREGISTRO_v1.md), generated from the code by
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
the modules and writes [PREREGISTRO_v1.md](PREREGISTRO_v1.md); `tests/test_prereg.py` fails
if the file on disk is not what the current code produces. It separates the tolerances that
are declared priors from the ones that are exploratory, and says so for each.

## Gates implemented in v3

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
python -m pytest -q tests                # 58 tests, ~2m40s (EM fits; test_smoke alone is < 1 s)
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
python make_prereg.py       # rewrites PREREGISTRO_v1.md from the code itself
```

[PREREGISTRO_v1.md](PREREGISTRO_v1.md) lists the generators with their boundedness
conditions, every gate with its stopping rule and tolerance, which tolerances are declared
priors and which are exploratory, the exact grid command, and the seeding scheme. It is
generated by introspection, and `tests/test_prereg.py` fails if it drifts from the code.
**Its provenance line currently says "not a git repository"** — it hashes `sim/` instead,
which identifies the code but cannot date it. Run `git init` before the grid.

### Reduced grid — PREPARED, NOT EXECUTED

The 32-cell smoke grid with enough repetition to stop being anecdotal: same axes, 5 reps,
≈ 960 runs.

```bash
python -m sim.recovery --T 300 600 --noise 0.05 0.1 0.2 0.3 \
    --keep 1.0 0.7 --nonlinear_h 0 1 --reps 5 --jobs 12 --out out_reduced
# 4 nodes x 2 T x 4 noise x 2 keep x 2 h x 5 reps = 960 runs
```

**Do not run it until the approval line in [ESTADO_CELULA.md](ESTADO_CELULA.md) carries a
date** (Modo Celular, rule 5). As of v3 the line is still blank and the grid has not run.

Cost: a v3 run is cheaper than v2 because the Markov null no longer fires on single
trajectories — it cannot change a verdict that is already `nao identificavel`. Expect the
wall clock to be dominated by the Wiener and S bootstraps.

When it does run it writes `recovery_map_v2.svg` (exact / spurious / missed / **undecided**
per node) alongside the existing figures. `h3_separation.svg` comes from ensembles rather
than the grid; both plotting paths are already exercised on existing data in `out_figuras/`.

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

## Files

```
sim/generators.py          164   SIM-1 generators, boundedness condition per node, split seed streams
sim/observe.py              54   observation map h, sampling, regular-pairs design, pair times
sim/statespace.py          183   linear-Gaussian SSM by EM (Kalman + RTS), Q/R split, deterministic null
sim/switching.py           195   sticky-EM switching regression, min-duration decode, switch matching
sim/wiener.py              113   Wiener surrogate for N: linear latent dynamics + fitted static h
sim/memory.py              220   the M contest: companion AR(p) kernel vs free SSM of latent d+k
sim/ensemble.py            125   ensembles; within-person, and between-person with TWO radii
sim/density.py             295   Paper 3 gates H1-H4, tri-state verdicts, Molenaar between/within
sim/pipeline.py            307   blind identification: M0, M1, N, H, M (tri-state), S
sim/recovery.py            244   grid runner (--jobs), per-axis rates incl. undecided, CSV/JSON, figures
make_prereg.py             211   writes PREREGISTRO_v1.md by introspecting the modules
tests/test_smoke.py         36   shapes, pause invariant, truth never leaks
tests/test_boundedness.py  104   the generator invariant: magnitude AND structural condition
tests/test_gates.py        175   cells 1-3, the Wiener null, the tri-state M axis
tests/test_density.py      189   ensemble modes, the truth seam, H1-H4, the two radii
tests/test_prereg.py        46   the pre-registration matches the code it describes
```

Over the 200-line house limit: `memory.py` 220, `density.py` 295, `pipeline.py` 307, `recovery.py` 244, `make_prereg.py` 211. The gate logic, the four Paper 3 gates
and the grid runner are the places where splitting costs more in indirection than it buys in
length. `memory.py` is the one candidate that should actually be split — once the M axis is
either repaired or retired, most of it goes with it.

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

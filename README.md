# mdaa_bench — SIM-1 / SIM-4 recovery bench, v4

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
python -m pytest -q tests                # 64 tests, ~3 min on a quiet machine (EM fits; test_smoke alone is < 1 s)
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
python make_prereg.py       # rewrites PREREGISTRO_v2.md from the code itself
```

[PREREGISTRO_v2.md](PREREGISTRO_v2.md) lists the generators with their boundedness
conditions, every gate with its stopping rule and tolerance, which tolerances are declared
priors and which are exploratory, the exact grid command, and the seeding scheme. It is
generated by introspection, and `tests/test_prereg.py` fails if it drifts from the code.
**Its provenance line currently says "not a git repository"** — it hashes `sim/` instead,
which identifies the code but cannot date it. Run `git init` before the grid.

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

## Files

```
sim/generators.py          176   SIM-1 generators, a boundedness condition per node, split seed streams
sim/stability.py            89   common quadratic Lyapunov function for the switched node, no SDP package
sim/observe.py              54   observation map h, sampling, regular-pairs design, pair times
sim/statespace.py          183   linear-Gaussian SSM by EM (Kalman + RTS), Q/R split, deterministic null
sim/switching.py           195   sticky-EM switching regression, min-duration decode, switch matching
sim/wiener.py              113   Wiener surrogate for N: linear latent dynamics + fitted static h
sim/memory.py              220   the M contest: companion AR(p) kernel vs free SSM of latent d+k
sim/ensemble.py            125   ensembles; within-person, and between-person with TWO radii
sim/density.py             295   Paper 3 gates H1-H4, tri-state verdicts, Molenaar between/within
sim/pipeline.py            307   blind identification: M0, M1, N, H, M (tri-state), S
sim/recovery.py            269   grid runner (--jobs, --reps_per_person), per-axis rates, CSV/JSON, figures
make_prereg.py             244   writes PREREGISTRO_v2.md by introspecting the modules
make_figures.py            177   the three paper figures, computed from the bench
tests/test_smoke.py         36   shapes, pause invariant, truth never leaks
tests/test_boundedness.py  151   the generator invariants: magnitude, structure, common Lyapunov P
tests/test_gates.py        199   the Wiener null, the tri-state M axis, the replication factor
tests/test_density.py      189   ensemble modes, the truth seam, H1-H4, the two radii
tests/test_prereg.py        46   the pre-registration matches the code it describes
```

Over the 200-line house limit: `memory.py` 220, `density.py` 295, `pipeline.py` 307, `recovery.py` 269, `make_prereg.py` 244.py` 220, `density.py` 295, `pipeline.py` 307, `recovery.py` 244, `make_prereg.py` 211. The gate logic, the four Paper 3 gates
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

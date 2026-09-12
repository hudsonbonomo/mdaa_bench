"""Paper 3, Table 3: gates H1-H4 on an ensemble of trajectories.

Each gate returns a GateResult — a boolean, the statistic it turned on, and the
stopping rule that produced the boolean, written out so a reader can disagree
with the threshold rather than guess it. H5-H7 are not implemented here.

  H1 ensemble   is there a density to talk about? KDE of rho(x, t) in time
                windows, and it must be STABLE when you resample which
                trajectories went into it. In `between` mode it must also not be
                bimodal: a pooled density with two modes describes nobody, which
                is Molenaar's comparability objection made into a test.
  H2 geometry   is the chart declared? The coordinates are the generator's and
                Euclidean by construction; the gate records that and fails if the
                coordinate scales differ by more than an order of magnitude
                without normalisation, because then a KDE bandwidth means two
                different things on the two axes.
  H3 memory     is the ensemble effectively Markov once the state is augmented?
                Runs the M-axis contest (memory.py) per trajectory and averages.
                Failing H3 sends you to the generalised branch.
  H4 locality   does a LOCAL flow field govern the density? The drift averaged
                per grid cell must predict the future block better than a
                predictor that sees the whole density but not where the point is.

This module never receives `truth`. It takes `obs` plus the design facts an
analyst really has: how many trajectories, and whether they are replicates of
one person or a sample of many.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .ensemble import pooled_window, windows
from .memory import memory_contest
from .observe import regular_pairs, pair_times
from .switching import fit_switching
from .switching_null import switching_null
from .statespace import to_grid

H1_INSTAB = 0.25        # max bootstrap instability of rho (mean relative L1)
H1_BIMODAL_SEP = 2.0    # mode separation, in pooled within-component sd, that counts as bimodal
H1_BETWEEN_WITHIN = 1.0  # between-person variance may not exceed within-person variance.
                         # A DECLARED PRIOR: "people differ from each other more than they
                         # vary within themselves" is exactly when a pooled density stops
                         # describing any individual. Not tuned — the boundary it implies
                         # in loc_radius is measured and reported, not chosen.
H2_SCALE_RATIO = 10.0   # one order of magnitude
H3_TOL = 0.03           # same TOL the M axis uses on a single trajectory
H3_MAX_TRAJ = 8         # trajectories actually fitted (each is 3 EM fits)
H3_NULL_TRAJ = 1        # replicates that get a switching null. Within-person
                        # replicates share A, B and the regime statistics, so the
                        # null characterises the WORLD, not the replicate: computing
                        # it once is the right object, not a saving.
H3_SWITCH_SURR = 9      # switching surrogates per trajectory for the M null.
                        # DIAGNOSTIC ONLY since the three-way contest: the null was
                        # built to fix the false alarm below and did not (7/20 against
                        # 8/20). Kept, off by default, so the negative result stays
                        # reproducible rather than being quietly deleted.
H3_MIN_DUR = 25         # minimum regime dwell for the switching competitor; same
                        # MIN_SEG the H axis uses, so the two gates fit the same model
H4_GRID = 6             # cells per axis for the local flow field
H4_MARGIN = 0.05        # local must win by a declared margin, not by a hair: the
                        # non-local competitor emits one drift per window against the
                        # local field's one per cell, so a tie is the honest null


PASS = "passa"
FAIL = "falha"
UNIDENTIFIABLE = "nao identificavel"        # the design cannot decide, either way
VERDICTS = (PASS, FAIL, UNIDENTIFIABLE)


@dataclass
class GateResult:
    """A gate returns three things and never fewer: a verdict, the statistic it
    turned on, and the stopping rule in words so a reader can disagree with the
    threshold instead of reverse-engineering it.

    The verdict is TRI-STATE. "nao identificavel" is not a hedge and not a
    failure: it is the gate saying the design cannot settle the question, which
    is a different claim from "the axis is absent" and must not be collapsed into
    it. The M axis on a single trajectory is the case this exists for.
    """
    name: str
    verdict: str
    stat: float
    note: str
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        assert self.verdict in VERDICTS, self.verdict

    @property
    def passed(self) -> bool:
        return self.verdict == PASS

    def __bool__(self) -> bool:
        return self.passed


def kde(points, grid, bw):
    """Isotropic Gaussian KDE evaluated on `grid`. Normalised to sum to 1."""
    if len(points) == 0:
        return np.zeros(len(grid))
    d2 = ((grid[:, None, :] - points[None, :, :]) ** 2).sum(-1)
    w = np.exp(-0.5 * d2 / bw ** 2).sum(1)
    s = w.sum()
    return w / s if s > 0 else w


def _grid_for(obs_list, n=12):
    lo = np.min([o.y.min(0) for o in obs_list], axis=0)
    hi = np.max([o.y.max(0) for o in obs_list], axis=0)
    axes = [np.linspace(a, b, n) for a, b in zip(lo, hi)]
    mesh = np.meshgrid(*axes, indexing="ij")
    return np.column_stack([m.ravel() for m in mesh])


def _bandwidth(points):
    """Silverman, on the pooled cloud."""
    n, d = points.shape
    sd = float(np.mean(points.std(0))) + 1e-9
    return sd * n ** (-1.0 / (d + 4)) * 1.06


def _two_component_1d(x, n_iter=60):
    """Tiny 1-D two-component Gaussian EM. Returns (means, sds, weights)."""
    x = np.asarray(x, float)
    mu = np.array([np.quantile(x, 0.25), np.quantile(x, 0.75)])
    sd = np.full(2, x.std() / 2 + 1e-9)
    w = np.array([0.5, 0.5])
    for _ in range(n_iter):
        p = w * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        tot = p.sum(1, keepdims=True)
        g = p / np.maximum(tot, 1e-300)
        nk = g.sum(0) + 1e-9
        mu = (g * x[:, None]).sum(0) / nk
        sd = np.sqrt((g * (x[:, None] - mu) ** 2).sum(0) / nk) + 1e-9
        w = nk / len(x)
    return mu, sd, w


def h1_ensemble(obs_list, mode: str, n_boot: int = 20, n_windows: int = 5,
                seed: int = 0) -> GateResult:
    rng = np.random.default_rng(seed + 31_000)
    grid = _grid_for(obs_list)
    wins = windows(obs_list, n_windows)
    instab, n_used = [], 0
    for t0, t1 in wins:
        pts = pooled_window(obs_list, t0, t1)
        if len(pts) < 20:
            continue
        n_used += 1
        bw = _bandwidth(pts)
        full = kde(pts, grid, bw)
        for _ in range(n_boot):
            pick = rng.integers(0, len(obs_list), len(obs_list))
            bpts = pooled_window([obs_list[i] for i in pick], t0, t1)
            if len(bpts) < 20:
                continue
            instab.append(0.5 * np.abs(kde(bpts, grid, bw) - full).sum())
    if not instab:
        return GateResult("H1", UNIDENTIFIABLE, float("nan"), "no window had enough observations")
    stat = float(np.mean(instab))
    passed = stat < H1_INSTAB
    note = (f"mean total-variation distance between bootstrap and full rho = {stat:.3f}; "
            f"pass if < {H1_INSTAB} over {n_used} windows x {n_boot} resamples of TRAJECTORIES")
    detail = dict(instability=stat, n_windows=n_used, n_boot=n_boot)

    if mode == "between":
        pts = np.vstack([pooled_window(obs_list, a, b) for a, b in wins])
        pts = pts - pts.mean(0)
        _, _, V = np.linalg.svd(pts, full_matrices=False)
        proj = pts @ V[0]                               # leading principal axis
        mu, sd, w = _two_component_1d(proj)
        pooled_sd = float(np.sqrt((w * sd ** 2).sum()))
        sep = float(abs(mu[0] - mu[1]) / (pooled_sd + 1e-9))
        bimodal = bool(sep > H1_BIMODAL_SEP and w.min() > 0.15)

        # The Molenaar statistic proper: how much of the spread is BETWEEN people
        # rather than within any of them. Bimodality only catches the extreme
        # case of two clumps; a population whose set points are scattered over a
        # ball is just as unppoolable and stays perfectly unimodal. Centres are
        # medians, so a heavy-tailed trajectory does not masquerade as a person
        # sitting somewhere else.
        centres = np.array([np.median(o.y, axis=0) for o in obs_list])
        within = float(np.mean([np.mean(np.var(o.y - np.median(o.y, axis=0), axis=0))
                                for o in obs_list]))
        between = float(np.mean(np.var(centres, axis=0)))
        ratio = between / (within + 1e-12)
        too_disperse = bool(ratio > H1_BETWEEN_WITHIN)
        detail.update(mode_separation=sep, min_component_weight=float(w.min()),
                      bimodal=bimodal, between_within=ratio,
                      var_between=between, var_within=within)
        note += (f"; between-person: modes {sep:.2f} pooled sd apart "
                 f"(bimodal if > {H1_BIMODAL_SEP} with both weights > 0.15) -> "
                 f"{'BIMODAL' if bimodal else 'unimodal'}"
                 f"; between/within variance = {ratio:.3f} "
                 f"(pooling refused above {H1_BETWEEN_WITHIN}) -> "
                 f"{'people differ more than they vary' if too_disperse else 'poolable'}")
        passed = passed and not bimodal and not too_disperse
    return GateResult("H1", PASS if passed else FAIL, stat, note, detail)


def h2_geometry(obs_list, normalised: bool = False) -> GateResult:
    sd = np.mean([o.y.std(0) for o in obs_list], axis=0)
    ratio = float(sd.max() / (sd.min() + 1e-12))
    passed = bool(normalised or ratio <= H2_SCALE_RATIO)
    note = (f"chart DECLARED: generator coordinates, Euclidean by construction. "
            f"Coordinate scale ratio {ratio:.2f}; pass if <= {H2_SCALE_RATIO} or the "
            f"analyst declares normalisation (normalised={normalised}). A larger ratio "
            f"means one KDE bandwidth is two different bandwidths.")
    return GateResult("H2", PASS if passed else FAIL, ratio, note,
                      dict(scale_ratio=ratio, sd=sd.tolist()))


def switching_competitor(o, kt, steps, min_dur: int = H3_MIN_DUR, K: int = 2):
    """The two-regime rival, scored on the steps the contest hands it.

    `steps` comes from `memory_contest`, which got it from
    `observe.scorable_steps`. Passing it in rather than choosing a test block here
    is the whole point: before this cell the rival picked its own rows from
    `regular_pairs` and ended up scoring an easier problem than the memory model
    whenever data were missing. Returns (mse, steps_used).

    Fitting still uses every consecutive pair in the train block — a model may
    learn from whatever its likelihood can reach; it is the SCORE that has to be
    the same question.
    """
    steps = np.asarray(steps, dtype=int)
    prev_ok = np.diff(o.t) == 1
    tr_tgt = o.t[1:][prev_ok & (o.t[1:] < kt)]
    te_tgt = steps[steps >= kt]
    if len(tr_tgt) < 10 or len(te_tgt) < 5:
        return float("nan"), np.empty(0, int)

    def rows(times):
        pos = np.searchsorted(o.t, times)
        return o.y[pos - 1], o.y[pos], o.u[pos - 1]

    mse = fit_switching(rows(tr_tgt), rows(te_tgt), K=K, min_dur=min_dur).mse_test
    ok = mse > 0 and np.isfinite(mse)
    return (float(mse) if ok else float("nan")), te_tgt


def h3_memory(obs_list, p: int = 6, max_traj: int = H3_MAX_TRAJ, n_iter: int = 25,
              switch_null: bool = False, three_way: bool = True,
              seed: int = 0) -> GateResult:
    """The memory kernel against TWO competitors, both scored on the future block.

    Grid v3 found the M axis firing on 28% of two-regime worlds and 18% of memory
    worlds. The diagnosis took two cells. It is not that the classes are
    indistinguishable — fitted head to head they separate at z = +7.28 — and it is
    not a missing null: a switching null on the outside removed one false alarm in
    eight. It is the COMPARATOR. The old contest asked only

        does an AR(p) kernel beat a free linear-Gaussian state space?

    and a two-regime world answers yes for the same reason a memory world does:
    one linear map is not enough for either. So the question a memory claim has to
    survive is now asked with both rivals present:

        does the kernel beat the free state space AND the two-regime model,
        each by at least H3_TOL?

    PASS still means "effectively Markov after augmentation", so the gate passes as
    soon as EITHER rival holds the kernel to within tolerance. The binding rival is
    reported: a memory claim that only just cleared the switching model is a
    different object from one that cleared it easily.

    `three_way=False` restores the pre-cell rule, kept so the figure can show the
    two gates side by side on the same worlds and so the recorded negative result
    about the null stays reproducible.
    """
    gains, sw_gains, nulls = [], [], []
    rng = np.random.default_rng(seed + 41_000)
    used = obs_list[:max_traj]
    for o in used:
        y, u, m = to_grid(o)
        kt = max(int(len(y) * 0.7), 20)
        idx = o.t[o.t >= kt]
        con = memory_contest(y, u, m, kt, idx, p=p, n_iter=n_iter)
        g = con["gain"]
        if not np.isfinite(g):
            continue
        g_sw = float("nan")
        if three_way:
            mse_sw, _ = switching_competitor(o, kt, con["scored_idx"])
            if np.isfinite(mse_sw):
                # the memory MSE is the one memory_contest already paid for; refitting
                # it here would be a second answer to a question already answered
                g_sw = (mse_sw - con["mse_memory"]) / mse_sw
            if not np.isfinite(g_sw):
                continue          # no switching fit, no three-way verdict on this replicate
            sw_gains.append(float(g_sw))
        gains.append(g)
        if switch_null and len(nulls) < H3_NULL_TRAJ:
            def mem_gain(ys, _y=y, _u=u, _m=m, _kt=kt, _idx=idx):
                r = memory_contest(ys, _u, _m, _kt, _idx, p=p, n_iter=n_iter)["gain"]
                return r if np.isfinite(r) else float("nan")
            q, _ = switching_null(y, u, m, kt, mem_gain, rng,
                                  n_surr=H3_SWITCH_SURR, min_dur=H3_MIN_DUR)
            nulls.append(float(np.quantile(q, 0.95)))
    if not gains:
        why = ("no trajectory yielded both a usable contest and a switching fit"
               if three_way else "no trajectory yielded a usable contest")
        return GateResult("H3", UNIDENTIFIABLE, float("nan"), why)

    g_ss = float(np.mean(gains))
    g_sw = float(np.mean(sw_gains)) if sw_gains else float("nan")
    q_switch = float(np.mean(nulls)) if nulls else float("-inf")
    if three_way:
        # the binding rival is the one that held the kernel to the smaller gain
        hardest = "state_space" if g_ss <= g_sw else "switching"
        stat = min(g_ss, g_sw)
        passed = bool(stat <= H3_TOL)
        note = (f"memory kernel against TWO rivals over {len(gains)} trajectories "
                f"(of {len(obs_list)}; capped at {max_traj}): gain over the free state "
                f"space {g_ss:+.3f}, over the two-regime model {g_sw:+.3f}. The binding "
                f"one is the {hardest} model at {stat:+.3f}. PASS means effectively "
                f"Markov, i.e. the kernel failed to beat at least one rival by "
                f"{H3_TOL}. Failing sends the analysis to the generalised branch.")
    else:
        hardest = "state_space"
        stat = g_ss
        passed = bool(stat <= H3_TOL or stat <= q_switch)
        note = (f"mean memory-kernel gain over {len(gains)} trajectories (of "
                f"{len(obs_list)}; capped at {max_traj}) = {stat:+.3f}; PASS means gain "
                f"<= {H3_TOL} OR gain <= the switching null's q95 = {q_switch:+.3f}. "
                f"PRE-CELL RULE, kept for comparison only.")
    return GateResult("H3", PASS if passed else FAIL, stat, note,
                      dict(mean_gain=g_ss, per_traj=gains, switching_gain=g_sw,
                           per_traj_switching=sw_gains, hardest=hardest,
                           three_way=three_way, switching_q95=q_switch,
                           n_nulls=len(nulls)))


def _cells(pts, lo, hi, n):
    ix = np.clip(((pts - lo) / (hi - lo + 1e-12) * n).astype(int), 0, n - 1)
    return ix[:, 0] * n + ix[:, 1] if pts.shape[1] == 2 else ix[:, 0]


def h4_locality(obs_list, n_grid: int = H4_GRID, frac: float = 0.7) -> GateResult:
    """Local flow field vs a predictor that sees the whole density but not x."""
    steps = []                                          # (t, x, dx) over all trajectories
    for o in obs_list:
        ok = np.flatnonzero(np.diff(o.t) == 1)          # consecutive pairs only
        for i in ok:
            steps.append((o.t[i], o.y[i], o.y[i + 1] - o.y[i]))
    if len(steps) < 100:
        return GateResult("H4", UNIDENTIFIABLE, float("nan"), "too few consecutive transitions")
    ts = np.array([s[0] for s in steps])
    X = np.vstack([s[1] for s in steps])
    D = np.vstack([s[2] for s in steps])
    t_split = int(np.quantile(ts, frac))
    tr, te = ts < t_split, ts >= t_split
    if tr.sum() < 50 or te.sum() < 20:
        return GateResult("H4", UNIDENTIFIABLE, float("nan"), "train or future block too thin")

    lo, hi = X[tr].min(0), X[tr].max(0)
    c_tr, c_te = _cells(X[tr], lo, hi, n_grid), _cells(X[te], lo, hi, n_grid)
    glob = D[tr].mean(0)
    local = np.tile(glob, (n_grid ** X.shape[1], 1))
    for c in np.unique(c_tr):                           # J(x): mean drift per cell
        sel = c_tr == c
        if sel.sum() >= 5:
            local[c] = D[tr][sel].mean(0)
    mse_local = float(np.mean((D[te] - local[c_te]) ** 2))

    # non-local competitor: drift regressed on the whole density of its window,
    # with no access to where the point sits inside that density
    wins = windows(obs_list, 8)
    grid = _grid_for(obs_list, n=8)
    bw = _bandwidth(X[tr])
    feats, targ, is_tr = [], [], []
    for t0, t1 in wins:
        sel = (ts >= t0) & (ts < t1)
        if sel.sum() < 5:
            continue
        rho = kde(X[sel & tr] if (sel & tr).sum() > 5 else X[sel], grid, bw)
        feats.append(rho); targ.append(D[sel].mean(0)); is_tr.append(t1 <= t_split)
    F, Tg, M = np.array(feats), np.array(targ), np.array(is_tr)
    if M.sum() >= 2:
        Fs = np.hstack([F, np.ones((len(F), 1))])
        W = np.linalg.solve(Fs[M].T @ Fs[M] + 1e-3 * np.eye(Fs.shape[1]), Fs[M].T @ Tg[M])
        pred = {}
        for (t0, t1), f in zip([w for w in wins], Fs):
            pred[t0] = f @ W
        wid = np.array([max([t0 for t0, _ in wins if t0 <= t], default=wins[0][0]) for t in ts[te]])
        nonlocal_pred = np.vstack([pred[w] for w in wid])
    else:
        nonlocal_pred = np.tile(D[tr].mean(0), (te.sum(), 1))
    mse_nonlocal = float(np.mean((D[te] - nonlocal_pred) ** 2))

    stat = (mse_nonlocal - mse_local) / mse_nonlocal if mse_nonlocal > 0 else float("nan")
    passed = bool(np.isfinite(stat) and stat > H4_MARGIN)
    note = (f"local flow field J(x) on a {n_grid}x{n_grid} grid vs a predictor regressed on "
            f"the ENTIRE density of the window; one-step MSE on the future block "
            f"{mse_local:.4g} vs {mse_nonlocal:.4g}; pass if gain {stat:+.3f} > {H4_MARGIN}")
    return GateResult("H4", PASS if passed else FAIL, float(stat), note,
                      dict(mse_local=mse_local, mse_nonlocal=mse_nonlocal))


def run_gates(ens, seed: int = 0, **kw) -> dict:
    """All four gates on an Ensemble. Receives design facts only, never `truth`."""
    obs, design = ens.obs, ens.design()
    return {"H1": h1_ensemble(obs, design["mode"], seed=seed),
            "H2": h2_geometry(obs),
            "H3": h3_memory(obs, **kw),
            "H4": h4_locality(obs)}

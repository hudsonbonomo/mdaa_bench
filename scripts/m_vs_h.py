"""Is M an axis, or a case of H?

Grid v3 forced the question: the memory axis fired on 28% of two-regime worlds and
18% of memory worlds. Either the M gate is broken, or the two model classes are
not distinguishable at this resolution — and those call for different repairs.

The measurement is symmetric and does not use `truth` to fit anything. For each
planted world, fit BOTH candidate models to the same trajectory and score both one
step ahead on the same future block:

    (a) memory   — companion AR(p) kernel with measurement noise (`memory.py`)
    (b) switching — two-regime linear model, sticky EM (`switching.py`)

The statistic is the relative gain of (a) over (b) per trajectory:

    delta = (mse_switching - mse_memory) / mse_switching

positive when the memory model predicts better. On a planted-memory world delta
should be positive; on a planted-switching world it should be negative. If both
distributions sit on the same side of zero, one class absorbs the other.

    python scripts/m_vs_h.py            # writes out_figuras/m_vs_h.svg + .png
"""
from __future__ import annotations
import os
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.ensemble import generate_ensemble
from sim.statespace import to_grid
from sim.memory import memory_model
from sim.switching import fit_switching
from sim.observe import regular_pairs, pair_times
from sim.pipeline import MEM_P, M_ITERS, MIN_SEG

N_SEEDS = 40
N_REPL = 10
T = 600
NOISE = 0.05
MAX_TRAJ = 3          # replicates fitted per world; both models see the same ones


def _delta_one(o, seed):
    """Memory model against switching model on one trajectory, same future block."""
    y, u, m = to_grid(o)
    kt = max(int(len(y) * 0.7), 20)
    idx = o.t[o.t >= kt]
    if len(idx) < 5:
        return np.nan
    mse_mem, _ = memory_model(y, u, m, kt, idx, p=MEM_P, n_iter=M_ITERS)

    y0, y1, uu = regular_pairs(o)
    ts = pair_times(o)
    k = int(np.searchsorted(ts, kt))
    if k < 10 or len(y0) - k < 5:
        return np.nan
    tr = (y0[:k], y1[:k], uu[:k])
    te = (y0[k:], y1[k:], uu[k:])
    mse_sw = fit_switching(tr, te, min_dur=MIN_SEG).mse_test
    if not (mse_sw > 0 and np.isfinite(mse_mem)):
        return np.nan
    return (mse_sw - mse_mem) / mse_sw


def one_world(a):
    node, seed = a
    ens = generate_ensemble(node, n_traj=N_REPL, mode="within", T=T, seed=seed,
                            meas_noise=NOISE)
    ds = [_delta_one(o, seed) for o in ens.obs[:MAX_TRAJ]]
    ds = [d for d in ds if np.isfinite(d)]
    return node, seed, (float(np.mean(ds)) if ds else np.nan)


def main():
    jobs = [(n, s) for n in ("M1+M", "M1+H") for s in range(N_SEEDS)]
    with ProcessPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(one_world, jobs))
    data = {n: np.array([d for nd, _, d in res if nd == n and np.isfinite(d)])
            for n in ("M1+M", "M1+H")}

    for n, v in data.items():
        print(f"{n:6s} n={len(v):3d}  media {v.mean():+.4f}  mediana {np.median(v):+.4f}  "
              f"sd {v.std(ddof=1):.4f}  fracao>0 {np.mean(v > 0):.3f}")
    a, b = data["M1+M"], data["M1+H"]
    # Mann-Whitney U, normal approximation: are the two distributions even distinct?
    allv = np.concatenate([a, b])
    ranks = allv.argsort().argsort().astype(float) + 1
    ra = ranks[:len(a)].sum()
    U = ra - len(a) * (len(a) + 1) / 2
    mu = len(a) * len(b) / 2
    sd = np.sqrt(len(a) * len(b) * (len(a) + len(b) + 1) / 12)
    z = (U - mu) / sd
    print(f"\nMann-Whitney z = {z:+.2f}  (|z| > 1.96 => distribuicoes distintas)")
    print(f"sobreposicao: max(M1+H) = {b.max():+.4f}  min(M1+M) = {a.min():+.4f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # a handful of switching worlds are catastrophic for the memory model (down to
    # -8); plotting the full range hides the region where the two classes actually
    # separate, so the tail is clipped into the edge bin and counted in the legend
    lo, hi = -1.0, 0.4
    n_clip_a = int(np.sum(a < lo)); n_clip_b = int(np.sum(b < lo))
    ac, bc = np.clip(a, lo, hi), np.clip(b, lo, hi)
    fig, ax = plt.subplots(figsize=(7.4, 4.2), dpi=150)
    bins = np.linspace(lo, hi, 36)
    ax.hist(ac, bins=bins, alpha=0.72, color="#2a9d8f",
            label=f"planted M1+M (n={len(a)}, median {np.median(a):+.3f})")
    ax.hist(bc, bins=bins, alpha=0.72, color="#8d99ae",
            label=f"planted M1+H (n={len(b)}, median {np.median(b):+.3f}, "
                  f"{n_clip_b} below {lo})")
    ax.axvline(0, color="#e76f51", lw=1.4, ls="--",
               label="0 = the two models predict equally well")
    for v, c in ((a, "#2a9d8f"), (b, "#8d99ae")):
        ax.axvline(np.median(v), color=c, lw=1.8)
    ax.set_xlim(lo, hi)
    ax.set_xlabel("relative gain of the memory model over the two-regime model\n"
                  "(positive: memory predicts better)")
    ax.set_ylabel("worlds")
    ax.set_title("Is M an axis, or a case of H?\n"
                 f"Both models fitted to the same trajectories, scored on the same future "
                 f"block; T = {T}, {N_REPL} replicates, {MAX_TRAJ} fitted per world; "
                 f"Mann-Whitney z = {z:+.2f}", fontsize=9)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    os.makedirs("out_figuras", exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(f"out_figuras/m_vs_h.{ext}", bbox_inches="tight")
    print("out_figuras/m_vs_h.svg + .png")


if __name__ == "__main__":
    main()

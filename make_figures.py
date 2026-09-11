"""Paper figures, computed from the bench itself — no number is typed by hand.

    python make_figures.py h3        # (a) Paper 2 §9.1: M is decided in the ensemble
    python make_figures.py h1        # (b) Paper 3 §3:   location, not law
    python make_figures.py wiener    # (c) Paper 2 §9:   the N gate and its two nulls
    python make_figures.py all

Each writes SVG and PNG into out_figuras/. Nothing here reads the reduced grid:
these run on ensembles and single trajectories that cost minutes, not hours, so
the figures exist before the grid is approved.
"""
from __future__ import annotations
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sim.generators import generate
from sim.observe import observe
from sim.statespace import to_grid
from sim.ensemble import generate_ensemble
from sim.density import h3_memory, h1_ensemble, H3_TOL, H1_BETWEEN_WITHIN
from sim.memory import memory_contest
from sim.pipeline import identify, MEM_P, M_ITERS
from sim.wiener import wiener_null
from sim.pipeline import _gain_fn

OUT = "out_figuras"
MEM, MK = "#2a9d8f", "#8d99ae"
ACCENT = "#e76f51"


def _save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(f"{OUT}/{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"{OUT}/{name}.svg + .png")


# --- (a) h3_replicas ---------------------------------------------------------

def _person_gains(node, n_traj, T, noise, person):
    """Per-replicate contest gain for ONE person (one structural seed)."""
    ens = generate_ensemble(node, n_traj=n_traj, mode="within", T=T,
                            seed=person, meas_noise=noise)
    out = []
    for o in ens.obs:
        y, u, m = to_grid(o)
        kt = max(int(len(y) * 0.7), 20)
        g = memory_contest(y, u, m, kt, o.t[o.t >= kt], p=MEM_P, n_iter=M_ITERS)["gain"]
        out.append(g if np.isfinite(g) else np.nan)
    return np.asarray(out, dtype=float)


def fig_h3(n_max=6, people=range(3), T=300, noise=0.05):
    """Running mean of the H3 statistic against the number of replicates, one line
    per PERSON. The single-trajectory problem is a between-person problem: at
    n = 1 a person's estimate carries the full realisation noise and the two
    families overlap. Averaging over replicates of the same person pulls each
    line onto that person's own value, which is what separates the families —
    and any line that ends on the wrong side of H3_TOL is a real error rate, not
    a drawing artefact."""
    ns = np.arange(1, n_max + 1)
    curves = {}
    for node in ("M1", "M1+M"):
        rows = []
        for p in people:
            rows.append(_person_gains(node, n_max, T, noise, p))
            print(f"  {node} person {p}: mean {np.nanmean(rows[-1]):+.3f}", flush=True)
        curves[node] = rows

    fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=150)
    ax.axhline(H3_TOL, color=ACCENT, lw=1.3, ls="--", zorder=3,
               label=f"H3_TOL = {H3_TOL}: above it the M axis is earned")
    ends = {}
    for node, colour in (("M1+M", MEM), ("M1", MK)):
        for i, g in enumerate(curves[node]):
            run = np.array([np.nanmean(g[:n]) for n in ns])
            ax.plot(ns, run, color=colour, lw=1.4, alpha=0.8,
                    label=f"planted {node} (one line per person)" if i == 0 else None)
        ends[node] = np.array([np.nanmean(g) for g in curves[node]])
    runs = [np.array([np.nanmean(g[:n]) for n in ns])
            for node in curves for g in curves[node]]
    lo, hi = float(np.nanmin(runs)), float(np.nanmax(runs))
    pad = 0.12 * (hi - lo)                       # every line stays inside the frame
    ax.set_ylim(lo - pad, hi + pad)
    right = ends["M1+M"] > H3_TOL
    ax.set_xlabel("replicates of the same person (within-person, same A, B and u schedule)")
    ax.set_ylabel("running mean of the memory-kernel gain")
    ax.set_title("The M axis is decided over replicates, not in one trajectory\n"
                 f"T = {T}, measurement noise {noise}, {len(list(people))} people per node; "
                 f"{right.sum()}/{len(right)} planted-memory people end above H3_TOL",
                 fontsize=9)
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    _save(fig, "h3_replicas")
    print(f"  M1+M ends: {np.round(ends['M1+M'], 3)}")
    print(f"  M1   ends: {np.round(ends['M1'], 3)}")


# --- (b) h1_location_vs_law --------------------------------------------------

def fig_h1(radii=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.3, 1.6), n_traj=30, T=400,
           noise=0.05, seed=0):
    """Between/within variance against each dispersion radius, on one panel. The
    two curves are the whole claim: dispersing the LAW never approaches the
    threshold, dispersing the LOCATION crosses it."""
    def ratio(A_r, loc_r):
        ens = generate_ensemble("M1", n_traj=n_traj, mode="between", T=T, seed=seed,
                                meas_noise=noise, A_radius=A_r, loc_radius=loc_r)
        g = h1_ensemble(ens.obs, "between", seed=seed)
        return g.detail["between_within"], g.verdict

    loc = [ratio(0.0, r) for r in radii]
    law = [ratio(min(r, 1.0), 0.0) for r in radii]        # A_radius is a mixing weight in [0,1]

    fig, ax = plt.subplots(figsize=(6.6, 3.8), dpi=150)
    ax.axhline(H1_BETWEEN_WITHIN, color=ACCENT, lw=1.2, ls="--",
               label=f"H1 refuses pooling above {H1_BETWEEN_WITHIN}")
    ax.plot(radii, [v for v, _ in loc], "o-", color=MEM,
            label="loc_radius (where people sit), A_radius = 0")
    ax.plot(radii, [v for v, _ in law], "s-", color=MK,
            label="A_radius (how people move), loc_radius = 0")
    cross = [r for r, (v, _) in zip(radii, loc) if v > H1_BETWEEN_WITHIN]
    if cross:
        ax.annotate(f"H1 fails from ≈ {cross[0]}", xy=(cross[0], H1_BETWEEN_WITHIN),
                    xytext=(cross[0] - 0.55, H1_BETWEEN_WITHIN * 2.2), fontsize=8,
                    arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1))
    ax.set_yscale("log")
    ax.set_xlabel("dispersion radius (state units for loc_radius; mixing weight for A_radius)")
    ax.set_ylabel("between-person / within-person variance")
    ax.set_title("Pooling breaks on location, not on law\n"
                 f"M1, {n_traj} people, T = {T}, measurement noise {noise}", fontsize=9)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "h1_location_vs_law")


# --- (c) wiener_null ---------------------------------------------------------

def fig_wiener(seeds=range(6), T=600, noise=0.05):
    """Observed N gain against both nulls, for the world the Wiener null was built
    for (linear dynamics seen through tanh) and the world it must not damage
    (planted nonlinearity, linear observation)."""
    cond = {"M1 through tanh\n(no nonlinear dynamics)": ("M1", True),
            "M1+N, linear observation\n(nonlinearity is real)": ("M1+N", False)}
    data = {}
    for label, (node, nh) in cond.items():
        rows = []
        for s in seeds:
            tj = generate(node, T=T, seed=s)
            fit = identify(observe(tj, meas_noise=noise, nonlinear_h=nh, seed=s),
                           seed=s, s_null=False, m_null=False)
            rows.append((fit.gains["N"], fit.gains["N_null_linear_q95"],
                         fit.gains["N_null_wiener_q95"], bool(fit.axes["N"])))
        data[label] = rows

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8), dpi=150, sharey=True)
    for ax, (label, rows) in zip(axes, data.items()):
        x = np.arange(len(rows)); w = 0.27
        ax.bar(x - w, [r[0] for r in rows], w, color=MEM, label="observed gain")
        ax.bar(x, [r[1] for r in rows], w, color=MK, label="linear null q95")
        ax.bar(x + w, [r[2] for r in rows], w, color=ACCENT, label="Wiener null q95")
        for i, r in enumerate(rows):
            if r[3]:
                ax.annotate("N fires", (i - w, r[0]), ha="center", fontsize=7,
                            color=MEM, xytext=(0, 4), textcoords="offset points")
        ax.set_xticks(x); ax.set_xticklabels([f"s{ s }" for s in seeds], fontsize=8)
        ax.set_title(label, fontsize=9); ax.grid(axis="y", alpha=0.3)
        ax.axhline(0, color="k", lw=0.6)
    axes[0].set_ylabel("relative held-out gain")
    axes[0].legend(fontsize=8)
    fig.suptitle("The N gate is bound by the Wiener null, not the linear one\n"
                 f"T = {T}, measurement noise {noise}", fontsize=9)
    _save(fig, "wiener_null")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("h3", "all"):
        fig_h3()
    if which in ("h1", "all"):
        fig_h1()
    if which in ("wiener", "all"):
        fig_wiener()

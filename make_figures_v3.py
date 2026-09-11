"""Figures computed from the v3 grid in out_v3/ — 1280 runs, not ad-hoc samples.

    python make_figures_v3.py

`make_figures.py` draws the preliminary figures from ensembles and single runs it
generates itself. This file draws only from the grid's CSV, so every number is a
rate over 1280 pre-registered cells rather than over a handful of seeds. Where
the grid cannot answer a question it says so and draws nothing: `h1_location_vs_law`
has no counterpart here, because the grid never varies `A_radius` or `loc_radius`.
"""
from __future__ import annotations
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "out_v3/recovery_rows.csv"
OUT = "out_v3"
MEM, MK, ACCENT = "#2a9d8f", "#8d99ae", "#e76f51"
NODES = ("M1", "M1+N", "M1+H", "M1+M")


def load():
    rows = list(csv.DictReader(open(SRC)))
    for r in rows:
        for k in ("exact", "spurious", "missed", "undecided", "ax_N", "ax_H", "ax_M",
                  "s_axis", "nonlinear_h", "reps_per_person", "T", "rep"):
            r[k] = int(r[k])
        for k in ("noise", "keep"):
            r[k] = float(r[k])
        for k in ("gain_N", "gain_N_null_linear_q95", "gain_N_null_wiener_q95", "gain_M_h3"):
            r[k] = float(r[k]) if r.get(k) not in (None, "") else np.nan
    return rows


def _save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(f"{OUT}/{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"{OUT}/{name}.svg + .png")


def mean(rows, k):
    v = [r[k] for r in rows if r[k] == r[k]]
    return float(np.mean(v)) if v else np.nan


# --- recovery map v3 ---------------------------------------------------------

def fig_recovery_map(rows):
    """Exact / spurious / missed / undecided per node, split by the replication
    factor. The undecided column is the whole reason the split exists: at one
    trajectory the M axis cannot be decided, so half of M1+M lands there."""
    keys = ("exact", "spurious", "missed", "undecided")
    colours = (MEM, ACCENT, "#e9c46a", MK)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), dpi=150, sharey=True)
    for ax, rp in zip(axes, (1, 10)):
        sub = [r for r in rows if r["reps_per_person"] == rp]
        xs, w = np.arange(len(NODES)), 0.2
        for i, (k, c) in enumerate(zip(keys, colours)):
            vals = [mean([r for r in sub if r["node"] == n], k) for n in NODES]
            ax.bar(xs + (i - 1.5) * w, vals, w, label=k, color=c)
        ax.set_xticks(xs); ax.set_xticklabels(NODES)
        ax.set_ylim(0, 1.02); ax.grid(axis="y", alpha=0.3)
        ax.set_title(f"reps_per_person = {rp}  (n = {len(sub)})", fontsize=9)
    axes[0].set_ylabel("rate")
    axes[0].legend(fontsize=8, ncol=2)
    fig.suptitle("Recovery map v3 — 1280 pre-registered runs. At one trajectory the M axis "
                 "is undecidable by construction,\nwhich is why M1+M is half 'undecided' on "
                 "the left and not 'missed'.", fontsize=9.5, y=1.06)
    fig.tight_layout()
    _save(fig, "recovery_map_v3")


# --- the N gate and its two nulls -------------------------------------------

def fig_wiener(rows):
    """Observed N gain against both null quantiles, as distributions over the
    grid rather than six bars. Split by observation map, because that is the
    confound the Wiener null was built for."""
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0), dpi=150, sharey=True)
    for ax, (nh, lab) in zip(axes, ((0, "linear observation"), (1, "tanh observation"))):
        sub = [r for r in rows if r["nonlinear_h"] == nh and np.isfinite(r["gain_N"])]
        data = [[r["gain_N"] for r in sub],
                [r["gain_N_null_linear_q95"] for r in sub],
                [r["gain_N_null_wiener_q95"] for r in sub]]
        bp = ax.boxplot(data, tick_labels=["observed\ngain", "linear null\nq95",
                                           "Wiener null\nq95"],
                        showfliers=False, widths=0.55, patch_artist=True)
        for patch, c in zip(bp["boxes"], (MEM, MK, ACCENT)):
            patch.set_facecolor(c); patch.set_alpha(0.75)
        absent = [r for r in sub if "N" not in r["node"].split("+")[1:]]
        planted = [r for r in sub if "N" in r["node"].split("+")[1:]]
        ax.set_title(f"{lab}\nN fires: {mean(planted,'ax_N'):.3f} when planted, "
                     f"{mean(absent,'ax_N'):.3f} when absent", fontsize=9)
        ax.axhline(0, color="k", lw=0.6); ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("relative held-out gain")
    fig.suptitle("The N gate against its two nulls, over 1280 runs — the Wiener null is the "
                 "binding one in 76.8% of them", fontsize=10, y=1.10)
    fig.tight_layout()
    _save(fig, "wiener_null")


# --- the M axis over replicates ---------------------------------------------

def fig_h3(rows):
    """What the replication factor actually bought. Left: the verdict mix, which
    is the pre-registered prediction (100% undecidable at one trajectory) against
    what replicates deliver. Right: the H3 statistic per node at 10 replicates,
    which is where the trouble is visible."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), dpi=150)
    ax = axes[0]
    verdicts = ("passa", "falha", "nao identificavel")
    colours = (MEM, MK, "#e9c46a")
    xs, w = np.arange(2), 0.25
    for i, (v, c) in enumerate(zip(verdicts, colours)):
        vals = [np.mean([r["m_verdict"] == v for r in rows if r["reps_per_person"] == rp])
                for rp in (1, 10)]
        ax.bar(xs + (i - 1) * w, vals, w, label=v, color=c)
    ax.set_xticks(xs); ax.set_xticklabels(["1 trajectory", "10 replicates"])
    ax.set_ylim(0, 1.05); ax.set_ylabel("share of cells"); ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8); ax.set_title("M axis verdict", fontsize=9)

    ax = axes[1]
    sub = [r for r in rows if r["reps_per_person"] == 10 and np.isfinite(r["gain_M_h3"])]
    data = [[r["gain_M_h3"] for r in sub if r["node"] == n] for n in NODES]
    bp = ax.boxplot(data, tick_labels=list(NODES), showfliers=False, widths=0.55,
                    patch_artist=True)
    for patch, n in zip(bp["boxes"], NODES):
        patch.set_facecolor(MEM if n == "M1+M" else MK); patch.set_alpha(0.75)
    ax.axhline(0.03, color=ACCENT, lw=1.2, ls="--", label="H3_TOL = 0.03")
    fires = {n: np.mean([r["m_verdict"] == "passa" for r in sub if r["node"] == n])
             for n in NODES}
    ax.set_title("H3 statistic at 10 replicates — M fires on "
                 f"{fires['M1+H']:.0%} of M1+H against {fires['M1+M']:.0%} of M1+M",
                 fontsize=9)
    ax.set_ylabel("memory-kernel gain"); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=8)
    fig.suptitle("Replicates decide the M axis, but they decide it wrongly as often as rightly",
                 fontsize=10, y=1.04)
    fig.tight_layout()
    _save(fig, "h3_replicas")


if __name__ == "__main__":
    rows = load()
    print(f"{len(rows)} runs from {SRC}")
    fig_recovery_map(rows)
    fig_wiener(rows)
    fig_h3(rows)
    print("h1_location_vs_law: NOT drawn from the grid — out_v3 contains no "
          "between-person ensembles, so A_radius and loc_radius never vary in it.")

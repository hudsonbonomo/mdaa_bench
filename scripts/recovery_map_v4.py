"""The v4 grid against the v3 grid, and the M axis decomposed.

Same design in both grids (4 nodes x 2 T x 2 noise x 2 keep x 2 h x 2
reps_per_person x 10 seeds = 1280 runs), so every rate is directly comparable.
Two things changed between them, both in the identification code and neither in
the generators: the N gate gained a third null, and the M gate gained a second
rival inside its contest.

Left panel: what each axis does when its structure is planted and when it is not.
Right panel: the M axis by the two design factors that move it, which is where
the pre-registered hypothesis lives.

    python scripts/recovery_map_v4.py      # writes out_figuras/recovery_map_v4.svg
"""
from __future__ import annotations
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

V3, V4 = "out_v3", "out_v4"
AXES = ("N", "H", "M", "S")


def rates(path):
    return json.load(open(os.path.join(path, "recovery_summary.json"), encoding="utf-8"))


def m_cells(path, node):
    """M-axis firing rate per (keep, noise) cell, replicated designs only."""
    rows = [r for r in csv.DictReader(open(os.path.join(path, "recovery_rows.csv"),
                                           encoding="utf-8"))
            if r["node"] == node and r["reps_per_person"] == "10"]
    out = {}
    for keep in ("1.0", "0.7"):
        for noise in ("0.05", "0.3"):
            c = [r for r in rows if r["keep"] == keep and r["noise"] == noise]
            out[(keep, noise)] = (sum(1 for r in c if r["m_verdict"] == "passa"), len(c))
    return out


def main():
    a, b = rates(V3), rates(V4)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.6), dpi=150,
                                   gridspec_kw=dict(width_ratios=[1.15, 1]))

    x = np.arange(len(AXES)); w = 0.2
    def val(s, ax, key):
        v = s["by_axis"][ax][key]
        return 0.0 if v is None else v
    bars = (("v3 planted", [val(a, k, "fires_when_planted") for k in AXES], "#2a9d8f", 0.45),
            ("v4 planted", [val(b, k, "fires_when_planted") for k in AXES], "#2a9d8f", 1.0),
            ("v3 absent",  [val(a, k, "fires_when_absent") for k in AXES], "#e76f51", 0.45),
            ("v4 absent",  [val(b, k, "fires_when_absent") for k in AXES], "#e76f51", 1.0))
    for i, (lab, vals, col, alpha) in enumerate(bars):
        ax1.bar(x + (i - 1.5) * w, vals, w, color=col, alpha=alpha, label=lab,
                edgecolor="white", linewidth=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{k}\n" + ("(S has no\nabsent cells)" if k == "S" else "")
                         for k in AXES])
    ax1.set_ylabel("fraction of runs where the axis fires")
    ax1.set_title("Every axis, v3 grid → v4 grid\n1280 runs each, identical design",
                  fontsize=9)
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3, axis="y")
    for k, ax_name in enumerate(AXES):
        d = val(b, ax_name, "fires_when_planted") - val(a, ax_name, "fires_when_planted")
        if abs(d) >= 0.01:
            ax1.annotate(f"{d:+.3f}", (k - w, max(val(a, ax_name, "fires_when_planted"),
                                                  val(b, ax_name, "fires_when_planted")) + 0.02),
                         ha="center", fontsize=7, color="#2a9d8f")
        d = val(b, ax_name, "fires_when_absent") - val(a, ax_name, "fires_when_absent")
        if abs(d) >= 0.01:
            ax1.annotate(f"{d:+.3f}", (k + w, max(val(a, ax_name, "fires_when_absent"),
                                                  val(b, ax_name, "fires_when_absent")) + 0.02),
                         ha="center", fontsize=7, color="#e76f51")

    pw, fa = m_cells(V4, "M1+M"), m_cells(V4, "M1+H")
    keys = [("1.0", "0.05"), ("1.0", "0.3"), ("0.7", "0.05"), ("0.7", "0.3")]
    xs = np.arange(len(keys))
    ax2.bar(xs - 0.2, [pw[k][0] / pw[k][1] for k in keys], 0.4, color="#2a9d8f",
            label="power: M1+M (memory planted)", edgecolor="white")
    ax2.bar(xs + 0.2, [fa[k][0] / fa[k][1] for k in keys], 0.4, color="#8d99ae",
            label="false alarm: M1+H (two regimes)", edgecolor="white")
    ax2.axhline(0.50, color="#2a9d8f", ls="--", lw=1.3,
                label="registered: power >= 0.50")
    ax2.axhline(0.05, color="#8d99ae", ls="--", lw=1.3,
                label="registered: false alarm <= 0.05")
    ax2.set_xticks(xs)
    ax2.set_xticklabels([f"keep {k}\nnoise {n}" for k, n in keys], fontsize=8)
    ax2.set_ylim(0, 1.0)
    ax2.set_title("The M axis with two rivals, by design cell\n"
                  "replicated designs only (reps_per_person = 10), 40 runs per bar",
                  fontsize=9)
    ax2.legend(fontsize=7.5); ax2.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    os.makedirs("out_figuras", exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(f"out_figuras/recovery_map_v4.{ext}", bbox_inches="tight")
    print("out_figuras/recovery_map_v4.svg + .png")
    for k in keys:
        print(f"  keep={k[0]} noise={k[1]}   poder M1+M {pw[k][0]:2d}/{pw[k][1]}   "
              f"falso alarme M1+H {fa[k][0]:2d}/{fa[k][1]}")


if __name__ == "__main__":
    main()

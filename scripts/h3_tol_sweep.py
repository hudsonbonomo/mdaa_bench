"""Power against false alarm as H3_TOL moves. The curve, not a choice.

Every world in `out_remedida/m_cells.csv` carries the statistic the gate decides
on, so a threshold sweep costs no refits: the axis fires exactly when
`stat > tol`. Nothing here picks a threshold — picking one is a decision about
which error is worse, and that is not a measurement.

Two series, because they answer different questions. "All cells" is the
pre-specified subset and includes noise 0.3, where the memory signal is simply
not there. "Noise 0.05" is where a threshold could plausibly help.

    python scripts/h3_tol_sweep.py       # writes out_figuras/h3_tol_tradeoff.svg
"""
from __future__ import annotations
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.density import H3_TOL

TOLS = (0.01, 0.02, 0.03, 0.05)
SRC = "out_remedida/m_cells.csv"


def load():
    rows = []
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        if r["stat"] == "":
            continue                    # undecidable: never fires, at any threshold
        r["stat"] = float(r["stat"]); r["noise"] = float(r["noise"])
        rows.append(r)
    return rows


def rate(rows, node, tol, only_low_noise):
    r = [x for x in rows if x["node"] == node
         and (x["noise"] == 0.05 if only_low_noise else True)]
    return sum(1 for x in r if x["stat"] > tol) / len(r), len(r)


def main():
    rows = load()
    series = {}
    for low, label in ((False, "todas as células"), (True, "ruído 0.05 apenas")):
        pts = []
        for tol in TOLS:
            p, npw = rate(rows, "M1+M", tol, low)
            f, nfa = rate(rows, "M1+H", tol, low)
            c, _ = rate(rows, "M1", tol, low)
            pts.append((tol, p, f, c, npw, nfa))
        series[label] = pts
        print(f"\n{label}")
        print(f"  {'H3_TOL':>8}{'poder M1+M':>13}{'falso M1+H':>13}{'falso M1':>11}")
        for tol, p, f, c, npw, nfa in pts:
            mark = "  <- atual" if abs(tol - H3_TOL) < 1e-9 else ""
            print(f"  {tol:>8.2f}{p:>13.3f}{f:>13.3f}{c:>11.3f}{mark}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=150)
    for (label, pts), col, mk in zip(series.items(), ("#8d99ae", "#2a9d8f"), ("s", "o")):
        fs = [p[2] for p in pts]; ps = [p[1] for p in pts]
        ax.plot(fs, ps, "-", color=col, lw=1.5, alpha=0.8, zorder=1)
        ax.scatter(fs, ps, s=70, color=col, marker=mk, zorder=2,
                   label=f"{label} (n={pts[0][4]} / {pts[0][5]})")
        for tol, p, f, *_ in pts:
            ax.annotate(f"{tol:g}", (f, p), textcoords="offset points",
                        xytext=(7, -3), fontsize=8, color=col)
    ax.set_xlabel("false alarm on M1+H (two regimes, no memory)")
    ax.set_ylabel("power on M1+M (memory planted)")
    ax.set_title("H3_TOL: what each threshold buys and what it costs\n"
                 "one point per threshold; labels are the threshold. No choice is made here.",
                 fontsize=9)
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(left=-0.01); ax.set_ylim(bottom=-0.02)
    os.makedirs("out_figuras", exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(f"out_figuras/h3_tol_tradeoff.{ext}", bbox_inches="tight")
    print("\nout_figuras/h3_tol_tradeoff.svg + .png")


if __name__ == "__main__":
    main()

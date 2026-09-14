"""decision_M0_M1_M2.svg — one panel per world family, three bars per panel.

    python -m decision.figures --src out_decision_pilot --out out_figuras

Each panel shows the EXTERNAL criterion that family was built to expose
(`metrics.PRIMARY`), never accuracy and never "the models chose differently".
The ablation M1+pausa is drawn as a tick across the M2 bar rather than as a
fourth bar: where the tick sits on top of M2, omega bought nothing that a pause
flag would not have bought, and the README has to say so.

Nothing here recomputes anything. The figure is drawn from the bench CSV, so a
number in the paper and a number in the panel cannot drift apart.
"""
from __future__ import annotations
import argparse
import csv
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .metrics import HIGHER_IS_BETTER, PRIMARY
from .models import ABLATION, MODELS
from .worlds import FAMILIES

BAR = {"M0": "#8d99ae", "M1": "#2a9d8f", "M2": "#e76f51"}
TICK = "#22223b"


def load(src):
    rows = list(csv.DictReader(open(pathlib.Path(src) / "decision_rows.csv", encoding="utf-8")))
    for r in rows:
        for k, v in list(r.items()):
            if k in ("family", "model", "chi_sha256"):
                continue
            r[k] = float(v) if v not in ("", None) else np.nan
    return rows


def _mean(rows, fam, model, key):
    v = [r[key] for r in rows if r["family"] == fam and r["model"] == model
         and r[key] == r[key]]
    return float(np.mean(v)) if v else np.nan


def draw(rows, out: pathlib.Path, name="decision_M0_M1_M2"):
    fams = [f for f in FAMILIES if any(r["family"] == f for r in rows)]
    fig, axes = plt.subplots(1, len(fams), figsize=(3.1 * len(fams), 4.1), dpi=150)
    axes = np.atleast_1d(axes)
    for ax, fam in zip(axes, fams):
        key = PRIMARY[fam]
        vals = [_mean(rows, fam, m, key) for m in MODELS]
        abl = _mean(rows, fam, ABLATION, key)
        ax.bar(range(len(MODELS)), vals, color=[BAR[m] for m in MODELS], width=0.66)
        ax.plot([1.67, 2.33], [abl, abl], color=TICK, lw=1.8, solid_capstyle="butt",
                zorder=5, label=ABLATION)
        for i, v in enumerate(vals):
            ax.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        ax.set_xticks(range(len(MODELS)))
        ax.set_xticklabels(MODELS, fontsize=9)
        ax.set_ylim(0, 1.12)
        arrow = "maior é melhor" if HIGHER_IS_BETTER[key] else "menor é melhor"
        n = int(np.nanmean([r["n_steps"] for r in rows if r["family"] == fam]))
        ax.set_title(f"{fam}\n{key}\n({arrow}, n≈{n} passos/célula)", fontsize=8.5)
        ax.grid(axis="y", alpha=0.25, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("taxa")
    axes[-1].legend(loc="upper right", fontsize=7.5, frameon=False)
    fig.suptitle("M0 / M1 / M2 por família de mundo — critério externo de cada família",
                 fontsize=10.5, y=1.03)
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(out / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    return [str(out / f"{name}.{e}") for e in ("svg", "png")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="out_decision_pilot")
    ap.add_argument("--out", default="out_figuras")
    a = ap.parse_args(argv)
    for p in draw(load(a.src), pathlib.Path(a.out)):
        print(p)


if __name__ == "__main__":
    main()

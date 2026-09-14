"""decision_M0_M1_M2.svg — one panel per world family, FOUR bars per panel.

    python -m decision.figures --src out_decision_v4 --out out_figuras

Each panel shows the EXTERNAL criterion that family was built to expose
(`metrics.PRIMARY`), never accuracy and never "the models chose differently".

M1+pausa — M1 plus one line, never act under a standing authorization, and
nothing else of Omega — is a BAR and no longer a tick over M2. In the pilot it
was a footnote; the grid made it the finding. On `W-pause` it sits at 0.000
exactly where M2 does, which says that on the pause criterion itself the warrant
layer buys nothing a boolean would not have bought. Drawing it as an annotation
of M2 would have hidden a result behind a legend entry, so it is drawn as what
it is: a competitor that ties.

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
from .models import ABLATION, ALL_MODELS
from .worlds import FAMILIES

#: The ablation carries M2's colour hatched, because that is what it is: M2 with
#: everything but the pause clause removed. Where the two bars match, the hatch is
#: the whole story.
BAR = {"M0": "#8d99ae", "M1": "#2a9d8f", "M2": "#e76f51", ABLATION: "#f4a261"}
HATCH = {ABLATION: "//"}


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
    fig, axes = plt.subplots(1, len(fams), figsize=(3.5 * len(fams), 4.3), dpi=150)
    axes = np.atleast_1d(axes)
    for ax, fam in zip(axes, fams):
        key = PRIMARY[fam]
        vals = [_mean(rows, fam, m, key) for m in ALL_MODELS]
        ax.bar(range(len(ALL_MODELS)), vals, width=0.72,
               color=[BAR[m] for m in ALL_MODELS],
               hatch=[HATCH.get(m, "") for m in ALL_MODELS],
               edgecolor=["none" if m != ABLATION else "#e76f51" for m in ALL_MODELS])
        for i, v in enumerate(vals):
            ax.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)
        ax.set_xticks(range(len(ALL_MODELS)))
        ax.set_xticklabels([m.replace("+pausa", "\n+pausa") for m in ALL_MODELS], fontsize=8)
        ax.set_ylim(0, 1.12)
        arrow = "maior é melhor" if HIGHER_IS_BETTER[key] else "menor é melhor"
        n = int(np.nanmean([r["n_steps"] for r in rows if r["family"] == fam]))
        ax.set_title(f"{fam}\n{key}\n({arrow}, n≈{n} passos/célula)", fontsize=8.5)
        ax.grid(axis="y", alpha=0.25, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("taxa")
    fig.suptitle("M0 / M1 / M2 e a ablação M1+pausa, por família — critério externo de cada família",
                 fontsize=10.5, y=1.04)
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(out / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    return [str(out / f"{name}.{e}") for e in ("svg", "png")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="out_decision_v4")
    ap.add_argument("--out", default="out_figuras")
    a = ap.parse_args(argv)
    for p in draw(load(a.src), pathlib.Path(a.out)):
        print(p)


if __name__ == "__main__":
    main()

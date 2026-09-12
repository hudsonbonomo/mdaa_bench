"""Does the three-way contest stop a two-regime world from buying a memory claim?

The earlier version of this script answered a prior question — are M and H even
separable? — and found that they are, decisively (memory wins 90% of memory worlds
and 2.5% of two-regime worlds head to head, Mann-Whitney z = +7.28). That answer
is what motivated this cell: the classes separate, so the confusion measured in
grid v3 came from the COMPARATOR. The old M gate asked only whether an AR(p)
kernel beats a free linear-Gaussian state space, and a two-regime world beats that
for the same reason a memory world does.

So this script now scores the two gates on the SAME worlds and the same seeds:

    old gate   gain over the free state space, with the switching null
               (the rule as committed at d3403fc)
    new gate   the BINDING gain — the smaller of (over the free state space)
               and (over the two-regime model of switching.py)

The M axis fires when the statistic clears H3_TOL. False alarm is M1+H above the
line; power is M1+M above it. Neither gate sees `truth`.

    python scripts/m_vs_h.py            # writes out_figuras/m_vs_h.svg + .png
"""
from __future__ import annotations
import os
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.ensemble import generate_ensemble
from sim.density import h3_memory, H3_TOL, FAIL

N_SEEDS = 40
N_REPL = 10
T = 600
NOISE = 0.05
MAX_TRAJ = 3          # replicates fitted per world; both gates see the same ones
NODES = ("M1+M", "M1+H")


def one_world(a):
    """Both gates on one planted world. Returns the statistic each one decides on."""
    node, seed = a
    ens = generate_ensemble(node, n_traj=N_REPL, mode="within", T=T, seed=seed,
                            meas_noise=NOISE)
    old = h3_memory(ens.obs, max_traj=MAX_TRAJ, seed=seed,
                    three_way=False, switch_null=True)
    new = h3_memory(ens.obs, max_traj=MAX_TRAJ, seed=seed, three_way=True)
    return (node, seed, float(old.stat), float(new.stat),
            int(old.verdict == FAIL), int(new.verdict == FAIL),
            new.detail.get("hardest", ""))


def main():
    jobs = [(n, s) for n in NODES for s in range(N_SEEDS)]
    with ProcessPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(one_world, jobs))

    stats, fires = {}, {}
    for node in NODES:
        r = [x for x in res if x[0] == node]
        stats[node] = (np.array([x[2] for x in r]), np.array([x[3] for x in r]))
        fires[node] = (sum(x[4] for x in r), sum(x[5] for x in r), len(r))

    print(f"eixo M sobre {N_SEEDS} mundos por no (T={T}, {N_REPL} replicas, "
          f"{MAX_TRAJ} ajustadas, ruido {NOISE})\n")
    print(f"{'no':7}{'gate antigo':>14}{'gate novo':>12}   papel")
    for node, papel in (("M1+H", "falso alarme"), ("M1+M", "poder")):
        a, b, n = fires[node]
        print(f"{node:7}{a:>8}/{n:<5}{b:>7}/{n:<5}   {papel}")
    hard = [x[6] for x in res if x[0] == "M1+H"]
    print(f"\ncompetidor vinculante em M1+H: "
          f"{ {h: hard.count(h) for h in set(hard)} }")
    hard_m = [x[6] for x in res if x[0] == "M1+M"]
    print(f"competidor vinculante em M1+M: "
          f"{ {h: hard_m.count(h) for h in set(hard_m)} }")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    lo, hi = -0.35, 0.25
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3), dpi=150, sharey=True)
    bins = np.linspace(lo, hi, 30)
    top = 0
    panels = (("gate antigo", "só contra o espaço de estados livre", 0),
              ("gate novo", "contra ambos; ganho vinculante", 1))
    for ax, (head, sub, col) in zip(axes, panels):
        for node, color in (("M1+M", "#2a9d8f"), ("M1+H", "#8d99ae")):
            v = stats[node][col]
            out = int(np.sum((v < lo) | (v > hi)))
            f = fires[node][col]
            # the out-of-range worlds pile into the edge bin rather than vanishing;
            # saying how many, per node, keeps that bar from reading as a mode
            h, _, _ = ax.hist(np.clip(v, lo, hi), bins=bins, alpha=0.72, color=color,
                              label=f"{node}: dispara {f}/{fires[node][2]}"
                                    + (f", {out} recortados na borda" if out else ""))
            top = max(top, h.max())
        ax.axvline(H3_TOL, color="#e76f51", lw=1.5, ls="--",
                   label=f"H3_TOL = {H3_TOL} (à direita, M dispara)")
        ax.set_title(head + "\n(" + sub + ")", fontsize=9)
        ax.set_xlim(lo, hi); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper center")
        ax.set_xlabel("estatística que o gate decide")
    axes[0].set_ylim(0, top * 1.45)      # headroom for the legend AND the edge bin
    axes[0].set_ylabel("mundos")
    fig.suptitle("O eixo M com um competidor e com dois — mesmas 40 sementes por nó",
                 fontsize=11)
    fig.tight_layout()
    os.makedirs("out_figuras", exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(f"out_figuras/m_vs_h.{ext}", bbox_inches="tight")
    print("\nout_figuras/m_vs_h.svg + .png")


if __name__ == "__main__":
    main()

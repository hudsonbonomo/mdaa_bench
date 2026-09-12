"""Re-measure the M axis once every competitor is scored on the same steps.

The v4 grid reported power 0.15 on planted memory, but that number was not
interpretable: under keep=0.7 the memory model was scored across gaps while the
switching rival only ever predicted one step from a measured value, so the two
were answering different questions and the easier one won. The contest now hands
every competitor the same steps (`observe.scorable_steps`). This runs the slice
of the design that decides the M axis and writes the binding statistic per world,
so a threshold sweep costs no refits.

    python scripts/remeasure_m.py            # writes out_remedida/m_cells.csv
"""
from __future__ import annotations
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sim.ensemble import generate_ensemble
from sim.density import h3_memory, FAIL, UNIDENTIFIABLE, H3_TOL

NODES = ("M1", "M1+H", "M1+M")
TS = (300, 600)
NOISES = (0.05, 0.3)
KEEPS = (1.0, 0.7)
N_SEEDS = 8
N_REPL = 10
OUT = "out_remedida"


def one(a):
    node, T, noise, keep, seed = a
    ens = generate_ensemble(node, n_traj=N_REPL, mode="within", T=T, seed=seed,
                            meas_noise=noise, keep_frac=keep)
    g = h3_memory(ens.obs, seed=seed, three_way=True)
    d = g.detail
    return dict(node=node, T=T, noise=noise, keep=keep, seed=seed,
                verdict=g.verdict,
                fires=int(g.verdict == FAIL),
                stat=round(float(g.stat), 6) if np.isfinite(g.stat) else "",
                gain_ss=round(float(d.get("mean_gain", np.nan)), 6),
                gain_sw=round(float(d.get("switching_gain", np.nan)), 6),
                hardest=d.get("hardest", ""))


def main():
    jobs = [(n, T, no, k, s) for n in NODES for T in TS for no in NOISES
            for k in KEEPS for s in range(N_SEEDS)]
    print(f"{len(jobs)} mundos ({len(NODES)} nos x {len(TS)} T x {len(NOISES)} ruidos "
          f"x {len(KEEPS)} keep x {N_SEEDS} sementes), {N_REPL} replicas cada")
    with ProcessPoolExecutor(max_workers=12) as ex:
        rows = list(ex.map(one, jobs))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "m_cells.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    print(f"\n{'no':6}{'T':>5}{'ruido':>7}{'keep':>6}   dispara   vinculante")
    for node in NODES:
        for T in TS:
            for noise in NOISES:
                for keep in KEEPS:
                    r = [x for x in rows if x["node"] == node and x["T"] == T
                         and x["noise"] == noise and x["keep"] == keep]
                    f_ = sum(x["fires"] for x in r)
                    hard = [x["hardest"] for x in r]
                    sw = hard.count("switching")
                    print(f"{node:6}{T:>5}{noise:>7}{keep:>6}   {f_:>3}/{len(r):<3}   "
                          f"chav {sw}/{len(r)}")
    print(f"\nout_remedida/m_cells.csv  ({len(rows)} linhas)")


if __name__ == "__main__":
    main()

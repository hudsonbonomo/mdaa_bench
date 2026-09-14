"""The decision bench runner — M0 vs M1 vs M2, per world family.

    python -m decision.bench --family W-scope --T 300 --reps 2 --out out_decision_pilot

Reported PER FAMILY and never pooled. Pooling would let the family where the
warrant layer is decisive pay for the families where it changes nothing, which
is the opposite of a falsification condition: the point of four families is that
each one can come back empty on its own.

Rows are long: one row per (cell, model). Every metric in a row was computed on
the same eligible steps as every other model in that cell — `metrics.evaluate`
asserts it rather than trusting it.

Seeds are CRC32 of the cell tuple, so a result does not depend on how the work
was split across processes. The grid is a BATCH operation: on the production
machine it runs only with the approval recorded in ESTADO_CELULA.md (Modo
Celular, rule 5).
"""
from __future__ import annotations
import argparse
import csv
import itertools
import json
import pathlib
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .metrics import METRICS, PRIMARY, ceiling, evaluate
from .models import ALL_MODELS, run_models
from .warrant import load_chi
from .worlds import FAMILIES, make_world

CELL_KEYS = ("family", "T", "noise", "keep", "flip_p", "rep")


def run_cell(family: str, T: int, noise: float, keep: float, flip_p: float, rep: int):
    """One cell: one world, one estimator, four policies, one set of metrics."""
    seed = zlib.crc32(repr((family, T, noise, keep, flip_p, rep)).encode()) % (2 ** 31)
    chi = load_chi()                                   # verifies the frozen hash, every cell
    w = make_world(family, T=T, seed=seed, meas_noise=noise, keep_frac=keep, flip_p=flip_p)
    runs = run_models(w.inp, chi)
    res = evaluate(w, runs)
    cap = ceiling(w)
    rows = []
    for name in ALL_MODELS:
        row = dict(family=family, T=T, noise=noise, keep=keep, flip_p=flip_p, rep=rep,
                   seed=seed, model=name, chi_sha256=chi.sha256[:12],
                   record_ceiling=round(cap["record_ceiling"], 4),
                   signature_frac=round(w.truth["signature_frac_realised"], 4))
        row.update({k: (None if isinstance(v, float) and np.isnan(v) else
                        (round(v, 4) if isinstance(v, float) else v))
                    for k, v in res[name].items()})
        rows.append(row)
    return rows


def _cell(args):
    return run_cell(*args)


def summarise(rows):
    """Mean of each metric per (family, model). NaN cells — a pause rate where no
    pause was authorized — are dropped from their own mean and counted, not
    silently read as zero."""
    out = {}
    for fam in sorted({r["family"] for r in rows}):
        out[fam] = {"primary": PRIMARY[fam], "models": {}}
        for name in ALL_MODELS:
            sel = [r for r in rows if r["family"] == fam and r["model"] == name]
            entry = {"n_cells": len(sel)}
            for k in METRICS:
                vals = [r[k] for r in sel if r[k] is not None]
                entry[k] = round(float(np.mean(vals)), 4) if vals else None
                entry[f"n_{k}"] = len(vals)
            entry["record_ceiling"] = round(float(np.mean([r["record_ceiling"] for r in sel])), 4)
            out[fam]["models"][name] = entry
    return out


def measure_cost(T=300, noise=0.1, keep=1.0, flip_p=0.05, reps=2):
    """Wall clock per cell, MEASURED on real cells covering all four families —
    the pre-registration quotes this, not an arithmetic estimate. Run it on an
    idle machine: the dynamics bench measured 3x inflation under load."""
    t0 = time.time()
    n = 0
    for fam, rep in itertools.product(FAMILIES, range(reps)):
        run_cell(fam, T, noise, keep, flip_p, rep)
        n += 1
    return {"T": T, "n_cells": n, "seconds_per_cell": round((time.time() - t0) / n, 2)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--family", nargs="+", default=list(FAMILIES), choices=list(FAMILIES))
    ap.add_argument("--T", nargs="+", type=int, default=[300])
    ap.add_argument("--noise", nargs="+", type=float, default=[0.1])
    ap.add_argument("--keep", nargs="+", type=float, default=[1.0])
    ap.add_argument("--flip", nargs="+", type=float, default=[0.05])
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", default="out_decision")
    a = ap.parse_args(argv)

    cells = list(itertools.product(a.family, a.T, a.noise, a.keep, a.flip, range(a.reps)))
    t0 = time.time()
    if a.jobs > 1:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            batches = list(ex.map(_cell, cells))
    else:
        batches = [_cell(c) for c in cells]
    rows = [r for b in batches for r in b]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "decision_rows.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    summary = {"n_cells": len(cells), "seconds": round(time.time() - t0, 1),
               "chi_sha256": load_chi().sha256, "by_family": summarise(rows)}
    (out / "decision_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{len(cells)} cells, {len(rows)} rows -> {out}  ({summary['seconds']} s)")
    for fam, blob in summary["by_family"].items():
        k = blob["primary"]
        got = "  ".join(f"{m}={blob['models'][m][k]}" for m in ALL_MODELS)
        print(f"  {fam:12s} {k:28s} {got}")
    return summary


if __name__ == "__main__":
    main()

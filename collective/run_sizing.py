"""Sizing run for the collective bench (Paper 8).

Seeds 300001-300300. Runs all generators and control readers.
For each cell and quantity with a threshold, records the estimated rate
and the suggested theta.

WRITTEN, NOT EXECUTED. Do not run before check_plugin() passes AND explicit
authorisation from Hudson A. R. Bonomo.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import time
from scipy.stats import binom

from .worlds import WORLDS, load_policy
from .measure import measure_run
from .freeze_check import check_plugin

_P = load_policy()
SEEDS = tuple(range(
    _P["seeds"]["sizing"][0], _P["seeds"]["sizing"][1] + 1))
OUT_DIR = Path(__file__).resolve().parent / "resultados"


def _suggest_theta(rate: float, n_seeds: int = 20) -> float:
    """Largest theta in [0,1] (step 0.05) such that
    P(Binom(n_seeds, rate) >= ceil(n_seeds*theta)) >= 0.80."""
    best = 0.0
    for th_100 in range(0, 101, 5):
        th = th_100 / 100.0
        k = math.ceil(n_seeds * th)
        if binom.sf(k - 1, n_seeds, rate) >= 0.80:
            best = th
    return best


def _rate_for(rows, check_fn) -> float:
    ok = sum(1 for r in rows if check_fn(r))
    return ok / len(rows) if rows else 0.0


def run_sizing() -> dict:
    check_plugin()
    started = time.time()
    rows: list[dict] = []

    # O worlds
    for k in _P["O"]["k"]:
        for seed in SEEDS:
            rows.append(measure_run("O", seed, k=k))
        print(f"O k={k}: {len(SEEDS)} seeds done", flush=True)

    # Pn worlds
    for n in _P["Pn"]["n"]:
        for seed in SEEDS:
            rows.append(measure_run("Pn", seed, n=n))
        print(f"Pn n={n}: {len(SEEDS)} seeds done", flush=True)

    # Pop worlds
    for wn in _P["Pop"]["worlds"]:
        for n in _P["Pop"]["n"]:
            for T in _P["Pop"]["T"]:
                for seed in SEEDS:
                    rows.append(measure_run(wn, seed, n=n, T=T))
                print(f"{wn} n={n} T={T}: {len(SEEDS)} seeds", flush=True)

    # G worlds
    for n in _P["G"]["n"]:
        for p in _P["G"]["p"]:
            for rho in _P["G"]["rho"]:
                m = _P["G"]["m"]
                for seed in SEEDS:
                    rows.append(measure_run(
                        "G", seed, n=n, m=m, p=p, rho=rho))
                print(f"G n={n} p={p} rho={rho}: done", flush=True)

    suggestions: dict = {}
    # Q1 sizing
    o_rows = [r for r in rows if r["world"] == "O"]
    if o_rows:
        rate = _rate_for(o_rows,
                         lambda r: r.get("Q1_statute_dup") == "T")
        suggestions["Q1_count_T"] = {
            "rate": rate, "theta": _suggest_theta(rate)}

    # Q2 sizing
    pn_rows = [r for r in rows if r["world"] == "Pn"]
    if pn_rows:
        rate = _rate_for(pn_rows,
                         lambda r: r.get("Q2_R_pool_elected") is not None)
        suggestions["Q2_pool_elects"] = {
            "rate": rate, "theta": _suggest_theta(rate)}

    result = {"seeds": list(SEEDS), "suggestions": suggestions,
              "n_rows": len(rows),
              "elapsed_seconds": round(time.time() - started, 2)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "sizing_collective.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_sizing(), indent=2, ensure_ascii=False, default=str))
